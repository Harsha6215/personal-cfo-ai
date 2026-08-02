"""
NSE/BSE Provider — implements IMarketDataProvider using nsetools + bselib.

Provides real-time quotes and basic company info from NSE India and BSE India.
Uses httpx to call NSE/BSE APIs directly (no heavy dependencies).

For historical data, falls back to Yahoo since NSE doesn't provide free OHLCV easily.

Ticker format: Plain ticker without suffix (e.g., "RELIANCE", "TCS", "INFY")
"""

from datetime import date, datetime, timezone

import structlog
import httpx

from backend.services.market_data.provider import (
    CompanyInfo,
    IMarketDataProvider,
    PriceBar,
    Quote,
)

logger = structlog.get_logger(__name__)

# NSE API endpoints
NSE_BASE = "https://www.nseindia.com"
NSE_QUOTE_URL = f"{NSE_BASE}/api/quote-equity"
NSE_SEARCH_URL = f"{NSE_BASE}/api/search/autocomplete"

# BSE API endpoints
BSE_BASE = "https://api.bseindia.com/BseIndiaAPI/api"
BSE_QUOTE_URL = f"{BSE_BASE}/getScripHeaderData/Equity"

# Common headers to mimic browser (NSE blocks raw API calls)
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}

BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.bseindia.com/",
}


class NSEProvider(IMarketDataProvider):
    """
    NSE India market data provider.

    Fetches real-time quotes from NSE's web API.
    Falls back to BSE if NSE fails for a ticker.
    """

    provider_name = "nse"

    def __init__(self):
        self._session_cookie: str | None = None

    async def _get_nse_session(self, client: httpx.AsyncClient) -> None:
        """Get NSE session cookies (required before API calls)."""
        try:
            resp = await client.get(NSE_BASE, headers=NSE_HEADERS, follow_redirects=True)
            # Cookies are automatically stored in the client
        except Exception:
            pass

    async def get_quote(self, ticker: str) -> Quote | None:
        """Get real-time quote from NSE India."""
        ticker = ticker.upper().strip()

        # Try NSE first
        quote = await self._get_nse_quote(ticker)
        if quote:
            return quote

        # Fallback to BSE
        quote = await self._get_bse_quote(ticker)
        return quote

    async def _get_nse_quote(self, ticker: str) -> Quote | None:
        """Fetch quote from NSE India API."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                # First get session cookies
                await self._get_nse_session(client)

                # Fetch quote
                resp = await client.get(
                    NSE_QUOTE_URL,
                    params={"symbol": ticker},
                    headers=NSE_HEADERS,
                )

                if resp.status_code != 200:
                    return None

                data = resp.json()
                price_info = data.get("priceInfo", {})
                info = data.get("info", {})

                price = price_info.get("lastPrice", 0)
                prev_close = price_info.get("previousClose", 0)
                change = price_info.get("change", 0)
                change_pct = price_info.get("pChange", 0)

                if not price:
                    return None

                return Quote(
                    ticker=ticker,
                    price=float(price),
                    change=round(float(change), 2),
                    change_pct=round(float(change_pct), 2),
                    volume=int(data.get("preOpenMarket", {}).get("totalTradedVolume", 0) or 0),
                    market_cap=None,  # Not in this endpoint
                    pe_ratio=float(data.get("metadata", {}).get("pdSymbolPe", 0) or 0) or None,
                    high_52w=float(price_info.get("weekHighLow", {}).get("max", 0) or 0) or None,
                    low_52w=float(price_info.get("weekHighLow", {}).get("min", 0) or 0) or None,
                    day_high=float(price_info.get("intraDayHighLow", {}).get("max", 0) or 0) or None,
                    day_low=float(price_info.get("intraDayHighLow", {}).get("min", 0) or 0) or None,
                    prev_close=float(prev_close) if prev_close else None,
                    open=float(price_info.get("open", 0) or 0) or None,
                    currency="INR",
                    exchange="NSE",
                    timestamp=datetime.now(timezone.utc),
                )
        except Exception as e:
            logger.debug("nse.get_quote.error", ticker=ticker, error=str(e))
            return None

    async def _get_bse_quote(self, ticker: str) -> Quote | None:
        """Fetch quote from BSE India API as fallback."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # BSE uses scrip codes, but also supports search by ticker
                resp = await client.get(
                    f"{BSE_BASE}/getScripHeaderData/Equity/{ticker}",
                    headers=BSE_HEADERS,
                )

                if resp.status_code != 200:
                    return None

                data = resp.json()
                header = data.get("Header", {})

                price = header.get("LTP") or header.get("LastTradedPrice")
                if not price:
                    return None

                # Clean price string (BSE returns "2,345.60" format)
                price_clean = str(price).replace(",", "")
                prev_close = str(header.get("PrevClose", "0")).replace(",", "")

                price_val = float(price_clean)
                prev_val = float(prev_close) if prev_close else 0
                change = price_val - prev_val
                change_pct = (change / prev_val * 100) if prev_val else 0

                return Quote(
                    ticker=ticker,
                    price=price_val,
                    change=round(change, 2),
                    change_pct=round(change_pct, 2),
                    volume=0,
                    high_52w=float(str(header.get("FiftyTwoWeekHighPrice", "0")).replace(",", "")) or None,
                    low_52w=float(str(header.get("FiftyTwoWeekLowPrice", "0")).replace(",", "")) or None,
                    currency="INR",
                    exchange="BSE",
                    timestamp=datetime.now(timezone.utc),
                )
        except Exception as e:
            logger.debug("bse.get_quote.error", ticker=ticker, error=str(e))
            return None

    async def get_history(
        self, ticker: str, start: date, end: date
    ) -> list[PriceBar]:
        """
        NSE doesn't provide free historical OHLCV easily.
        Return empty — let Yahoo handle history as fallback.
        """
        return []

    async def get_company_info(self, ticker: str) -> CompanyInfo | None:
        """Get basic company info from NSE."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                await self._get_nse_session(client)

                resp = await client.get(
                    NSE_QUOTE_URL,
                    params={"symbol": ticker.upper()},
                    headers=NSE_HEADERS,
                )

                if resp.status_code != 200:
                    return None

                data = resp.json()
                info = data.get("info", {})
                metadata = data.get("metadata", {})

                name = info.get("companyName") or metadata.get("companyName") or ticker

                return CompanyInfo(
                    ticker=ticker.upper(),
                    name=name,
                    sector=metadata.get("industry"),
                    industry=metadata.get("industry"),
                    exchange="NSE",
                    currency="INR",
                    isin=info.get("isin") or metadata.get("isin"),
                    pe_ratio=float(metadata.get("pdSymbolPe", 0) or 0) or None,
                )
        except Exception as e:
            logger.debug("nse.get_company_info.error", ticker=ticker, error=str(e))
            return None

    async def search(self, query: str) -> list[dict]:
        """Search NSE for tickers."""
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                await self._get_nse_session(client)

                resp = await client.get(
                    NSE_SEARCH_URL,
                    params={"q": query},
                    headers=NSE_HEADERS,
                )

                if resp.status_code != 200:
                    return []

                data = resp.json()
                symbols = data.get("symbols", [])

                return [
                    {
                        "ticker": s.get("symbol", ""),
                        "name": s.get("symbol_info", ""),
                        "exchange": "NSE",
                    }
                    for s in symbols[:10]
                ]
        except Exception:
            return []
