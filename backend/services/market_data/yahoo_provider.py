"""
Yahoo Finance Provider — implements IMarketDataProvider using yfinance library.

For Indian stocks, Yahoo Finance uses the format: TICKER.NS (NSE) or TICKER.BO (BSE)
Example: RELIANCE.NS, TCS.NS, GOLDBEES.NS

This provider handles the .NS/.BO suffix mapping automatically.
"""

from datetime import date, datetime, timezone

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


def _to_yahoo_ticker(ticker: str, exchange: str = "NSE") -> str:
    """Convert local ticker to Yahoo Finance format."""
    ticker = ticker.upper().strip()
    # If already has suffix, return as is
    if ticker.endswith(".NS") or ticker.endswith(".BO"):
        return ticker
    # Map exchange to suffix
    suffix = ".NS" if exchange.upper() in ("NSE", "NSE") else ".BO"
    return f"{ticker}{suffix}"


class YahooFinanceProvider(IMarketDataProvider):
    """
    Yahoo Finance market data provider via yfinance library.

    Requires: pip install yfinance
    """

    provider_name = "yahoo"

    def __init__(self, default_exchange: str = "NSE"):
        self.default_exchange = default_exchange
        self._yf = None

    def _get_yf(self):
        """Lazy import yfinance."""
        if self._yf is None:
            try:
                import yfinance as yf
                self._yf = yf
            except ImportError:
                raise RuntimeError(
                    "yfinance not installed. Run: pip install yfinance"
                )
        return self._yf

    async def get_quote(self, ticker: str) -> Quote | None:
        """Get current price quote from Yahoo Finance."""
        try:
            yf = self._get_yf()
            yahoo_ticker = _to_yahoo_ticker(ticker, self.default_exchange)
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info

            if not info or "regularMarketPrice" not in info:
                # Try fast_info as fallback
                try:
                    fast = stock.fast_info
                    return Quote(
                        ticker=ticker,
                        price=float(fast.get("lastPrice", 0) or fast.get("last_price", 0)),
                        change=0,
                        change_pct=0,
                        volume=int(fast.get("lastVolume", 0) or 0),
                        currency="INR",
                        exchange=self.default_exchange,
                    )
                except Exception:
                    return None

            price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose", 0)
            change = price - prev_close if price and prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            return Quote(
                ticker=ticker,
                price=float(price),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                volume=int(info.get("regularMarketVolume", 0) or 0),
                market_cap=float(info.get("marketCap", 0) or 0),
                pe_ratio=float(info.get("trailingPE", 0) or 0) or None,
                eps=float(info.get("trailingEps", 0) or 0) or None,
                high_52w=float(info.get("fiftyTwoWeekHigh", 0) or 0) or None,
                low_52w=float(info.get("fiftyTwoWeekLow", 0) or 0) or None,
                day_high=float(info.get("dayHigh", 0) or 0) or None,
                day_low=float(info.get("dayLow", 0) or 0) or None,
                prev_close=float(prev_close) if prev_close else None,
                open=float(info.get("open", 0) or 0) or None,
                currency=info.get("currency", "INR"),
                exchange=self.default_exchange,
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning("yahoo.get_quote.error", ticker=ticker, error=str(e))
            return None

    async def get_history(
        self, ticker: str, start: date, end: date
    ) -> list[PriceBar]:
        """Get daily OHLCV history from Yahoo Finance."""
        try:
            yf = self._get_yf()
            yahoo_ticker = _to_yahoo_ticker(ticker, self.default_exchange)
            stock = yf.Ticker(yahoo_ticker)

            df = stock.history(start=start.isoformat(), end=end.isoformat())

            if df is None or df.empty:
                return []

            bars = []
            for idx, row in df.iterrows():
                bars.append(PriceBar(
                    date=idx.date() if hasattr(idx, 'date') else idx,
                    open=round(float(row.get("Open", 0)), 2),
                    high=round(float(row.get("High", 0)), 2),
                    low=round(float(row.get("Low", 0)), 2),
                    close=round(float(row.get("Close", 0)), 2),
                    adj_close=round(float(row.get("Close", 0)), 2),  # yfinance already adjusts
                    volume=int(row.get("Volume", 0)),
                ))

            logger.info("yahoo.get_history", ticker=ticker, bars=len(bars))
            return bars

        except Exception as e:
            logger.warning("yahoo.get_history.error", ticker=ticker, error=str(e))
            return []

    async def get_company_info(self, ticker: str) -> CompanyInfo | None:
        """Get company profile from Yahoo Finance."""
        try:
            yf = self._get_yf()
            yahoo_ticker = _to_yahoo_ticker(ticker, self.default_exchange)
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info

            if not info or not info.get("shortName"):
                return None

            return CompanyInfo(
                ticker=ticker,
                name=info.get("shortName") or info.get("longName") or ticker,
                sector=info.get("sector"),
                industry=info.get("industry"),
                description=info.get("longBusinessSummary"),
                website=info.get("website"),
                ceo=None,  # Not available in yfinance
                employees=info.get("fullTimeEmployees"),
                headquarters=f"{info.get('city', '')}, {info.get('country', '')}".strip(", "),
                country=info.get("country", "India"),
                currency=info.get("currency", "INR"),
                exchange=self.default_exchange,
                isin=info.get("isin"),
                market_cap=float(info.get("marketCap", 0) or 0) or None,
                pe_ratio=float(info.get("trailingPE", 0) or 0) or None,
                eps=float(info.get("trailingEps", 0) or 0) or None,
                dividend_yield=float(info.get("dividendYield", 0) or 0) or None,
                beta=float(info.get("beta", 0) or 0) or None,
                high_52w=float(info.get("fiftyTwoWeekHigh", 0) or 0) or None,
                low_52w=float(info.get("fiftyTwoWeekLow", 0) or 0) or None,
            )
        except Exception as e:
            logger.warning("yahoo.get_company_info.error", ticker=ticker, error=str(e))
            return None

    async def get_dividends(self, ticker: str) -> list[DividendEvent]:
        """Get dividend history from Yahoo Finance."""
        try:
            yf = self._get_yf()
            yahoo_ticker = _to_yahoo_ticker(ticker, self.default_exchange)
            stock = yf.Ticker(yahoo_ticker)
            divs = stock.dividends

            if divs is None or divs.empty:
                return []

            return [
                DividendEvent(
                    date=idx.date() if hasattr(idx, 'date') else idx,
                    amount=round(float(val), 2),
                )
                for idx, val in divs.items()
            ]
        except Exception as e:
            logger.warning("yahoo.get_dividends.error", ticker=ticker, error=str(e))
            return []

    async def get_splits(self, ticker: str) -> list[SplitEvent]:
        """Get stock split history from Yahoo Finance."""
        try:
            yf = self._get_yf()
            yahoo_ticker = _to_yahoo_ticker(ticker, self.default_exchange)
            stock = yf.Ticker(yahoo_ticker)
            splits = stock.splits

            if splits is None or splits.empty:
                return []

            events = []
            for idx, ratio in splits.items():
                # yfinance returns ratio as float (e.g., 2.0 for 1:2 split)
                ratio_val = float(ratio)
                events.append(SplitEvent(
                    date=idx.date() if hasattr(idx, 'date') else idx,
                    ratio_from=1,
                    ratio_to=int(ratio_val) if ratio_val == int(ratio_val) else int(ratio_val * 10),
                ))
            return events
        except Exception as e:
            logger.warning("yahoo.get_splits.error", ticker=ticker, error=str(e))
            return []

    async def search(self, query: str) -> list[dict]:
        """Search for tickers (limited in yfinance)."""
        # yfinance doesn't have great search. Return empty for now.
        # In production, use Yahoo's search API or a local ticker database.
        return []
