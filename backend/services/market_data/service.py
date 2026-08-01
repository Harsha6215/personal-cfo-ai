"""
MarketDataService — the single entry point for all market data.

This service:
    1. Depends only on IMarketDataProvider (never on Yahoo directly)
    2. Handles provider fallback (try Yahoo, then NSE, etc.)
    3. Adds caching layer (Redis, in-memory)
    4. Provides a clean API for the rest of the application

Usage:
    from backend.services.market_data import MarketDataService, YahooFinanceProvider

    service = MarketDataService(provider=YahooFinanceProvider())
    quote = await service.get_quote("GOLDBEES")
    history = await service.get_history("TCS", start, end)
    info = await service.get_company_info("RELIANCE")
"""

from datetime import date

import structlog

from backend.services.market_data.provider import (
    CompanyInfo,
    DividendEvent,
    IMarketDataProvider,
    PriceBar,
    Quote,
    SplitEvent,
)

logger = structlog.get_logger(__name__)


class MarketDataService:
    """
    High-level market data service.

    Supports multiple providers with fallback:
        primary → fallback1 → fallback2

    Future enhancements:
        - Redis cache for quotes (TTL: 1 min during market hours)
        - In-memory cache for company info (TTL: 1 day)
        - Rate limiting per provider
    """

    def __init__(
        self,
        provider: IMarketDataProvider,
        fallback_providers: list[IMarketDataProvider] | None = None,
    ):
        self.provider = provider
        self.fallbacks = fallback_providers or []
        self._all_providers = [provider] + self.fallbacks

    async def get_quote(self, ticker: str) -> Quote | None:
        """
        Get current price quote.
        Tries primary provider first, then fallbacks.
        """
        for p in self._all_providers:
            try:
                result = await p.get_quote(ticker)
                if result and result.price > 0:
                    logger.debug("market.quote", ticker=ticker, provider=p.provider_name, price=result.price)
                    return result
            except Exception as e:
                logger.warning("market.quote.provider_error", ticker=ticker, provider=p.provider_name, error=str(e))
                continue

        logger.warning("market.quote.all_failed", ticker=ticker)
        return None

    async def get_history(
        self, ticker: str, start: date, end: date
    ) -> list[PriceBar]:
        """
        Get historical OHLCV data.
        Tries primary provider first, then fallbacks.
        """
        for p in self._all_providers:
            try:
                bars = await p.get_history(ticker, start, end)
                if bars:
                    logger.debug("market.history", ticker=ticker, provider=p.provider_name, bars=len(bars))
                    return bars
            except Exception as e:
                logger.warning("market.history.provider_error", ticker=ticker, provider=p.provider_name, error=str(e))
                continue

        return []

    async def get_company_info(self, ticker: str) -> CompanyInfo | None:
        """Get company profile. Tries primary, then fallbacks."""
        for p in self._all_providers:
            try:
                info = await p.get_company_info(ticker)
                if info:
                    return info
            except Exception as e:
                logger.warning("market.company.provider_error", ticker=ticker, provider=p.provider_name, error=str(e))
                continue
        return None

    async def get_dividends(self, ticker: str) -> list[DividendEvent]:
        """Get dividend history."""
        for p in self._all_providers:
            try:
                divs = await p.get_dividends(ticker)
                if divs:
                    return divs
            except Exception:
                continue
        return []

    async def get_splits(self, ticker: str) -> list[SplitEvent]:
        """Get split history."""
        for p in self._all_providers:
            try:
                splits = await p.get_splits(ticker)
                if splits:
                    return splits
            except Exception:
                continue
        return []

    async def get_quotes_bulk(self, tickers: list[str]) -> dict[str, Quote]:
        """Get quotes for multiple tickers. Returns dict of ticker → Quote."""
        results = {}
        for ticker in tickers:
            quote = await self.get_quote(ticker)
            if quote:
                results[ticker] = quote
        return results
