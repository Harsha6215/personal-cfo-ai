"""
Market data service factory — returns a pre-configured MarketDataService.

Uses NSE as the primary provider for real-time Indian quotes,
with Yahoo Finance as fallback for historical data and company info.

Usage (replace all MarketDataService(provider=YahooFinanceProvider()) calls):
    from backend.services.market_data.factory import get_market_service

    market = get_market_service()
    quote = await market.get_quote("RELIANCE")
"""

from functools import lru_cache

from backend.services.market_data.nse_provider import NSEProvider
from backend.services.market_data.service import MarketDataService
from backend.services.market_data.yahoo_provider import YahooFinanceProvider


@lru_cache(maxsize=1)
def get_market_service() -> MarketDataService:
    """
    Get a configured MarketDataService instance.

    Provider order:
    1. NSE (primary) — real-time quotes from NSE/BSE India
    2. Yahoo (fallback) — historical data, company info, dividends, splits

    NSE is faster and more reliable for Indian stocks during market hours.
    Yahoo provides better historical data and global coverage.
    """
    return MarketDataService(
        provider=NSEProvider(),
        fallback_providers=[YahooFinanceProvider()],
    )
