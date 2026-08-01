"""
Market Data Service — abstraction layer for all market data providers.

Architecture:
    Dashboard / AI Agents
        ↓
    MarketDataService
        ↓
    IMarketDataProvider (interface)
        ↓
    YahooFinanceProvider | NSEProvider | PolygonProvider (implementations)

If tomorrow Yahoo changes their API, you only replace one provider.
"""

from backend.services.market_data.provider import (
    IMarketDataProvider,
    Quote,
    PriceBar,
    CompanyInfo,
)
from backend.services.market_data.service import MarketDataService
from backend.services.market_data.yahoo_provider import YahooFinanceProvider

__all__ = [
    "IMarketDataProvider",
    "Quote",
    "PriceBar",
    "CompanyInfo",
    "MarketDataService",
    "YahooFinanceProvider",
]
