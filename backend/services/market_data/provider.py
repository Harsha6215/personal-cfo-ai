"""
IMarketDataProvider — abstract interface for all market data sources.

Every provider implements these methods. The MarketDataService depends
only on this interface, never on a concrete provider directly.

To add a new provider:
    1. Create a class implementing IMarketDataProvider
    2. Register it in MarketDataService
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Quote:
    """Real-time (or delayed) price quote for a security."""
    ticker: str
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    market_cap: float | None = None
    pe_ratio: float | None = None
    eps: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    prev_close: float | None = None
    open: float | None = None
    currency: str = "INR"
    exchange: str = "NSE"
    timestamp: datetime | None = None


@dataclass
class PriceBar:
    """Single OHLCV bar (daily, weekly, etc.)."""
    date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int


@dataclass
class CompanyInfo:
    """Company profile/fundamentals."""
    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
    description: str | None = None
    website: str | None = None
    ceo: str | None = None
    employees: int | None = None
    headquarters: str | None = None
    country: str = "India"
    currency: str = "INR"
    exchange: str = "NSE"
    isin: str | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    eps: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None


@dataclass
class DividendEvent:
    """A single dividend payment."""
    date: date
    amount: float
    currency: str = "INR"


@dataclass
class SplitEvent:
    """A stock split event."""
    date: date
    ratio_from: int  # e.g., 1 (old)
    ratio_to: int    # e.g., 5 (new) → 1:5 split


class IMarketDataProvider(ABC):
    """
    Abstract interface for market data providers.

    Every provider must implement:
        - get_quote(ticker) → current price + basic stats
        - get_history(ticker, start, end) → list of daily OHLCV bars
        - get_company_info(ticker) → company profile

    Optional (override if provider supports):
        - get_dividends(ticker) → dividend history
        - get_splits(ticker) → split history
        - search(query) → search for tickers
    """

    provider_name: str  # "yahoo", "nse", "polygon"

    @abstractmethod
    async def get_quote(self, ticker: str) -> Quote | None:
        """Get current/latest price quote for a ticker."""
        ...

    @abstractmethod
    async def get_history(
        self, ticker: str, start: date, end: date
    ) -> list[PriceBar]:
        """Get daily OHLCV history between two dates."""
        ...

    @abstractmethod
    async def get_company_info(self, ticker: str) -> CompanyInfo | None:
        """Get company profile and fundamentals."""
        ...

    async def get_dividends(self, ticker: str) -> list[DividendEvent]:
        """Get dividend history. Override if supported."""
        return []

    async def get_splits(self, ticker: str) -> list[SplitEvent]:
        """Get stock split history. Override if supported."""
        return []

    async def search(self, query: str) -> list[dict]:
        """Search for tickers by name. Override if supported."""
        return []
