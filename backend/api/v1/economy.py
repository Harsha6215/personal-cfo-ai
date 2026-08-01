"""
Economic Indicators API — key macro data for India.

Fetches live data for USDINR, Gold, Silver, Crude Oil, India VIX, Nifty 50, etc.
from Yahoo Finance. These become inputs to the Macro AI agent later.
"""

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.services.market_data import MarketDataService, YahooFinanceProvider

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Economy"])

_market_service = MarketDataService(provider=YahooFinanceProvider())

# Yahoo Finance tickers for Indian economic indicators
INDICATORS = {
    "USDINR": {"yahoo": "INR=X", "name": "USD/INR Exchange Rate", "unit": "₹"},
    "NIFTY50": {"yahoo": "^NSEI", "name": "Nifty 50", "unit": "pts"},
    "SENSEX": {"yahoo": "^BSESN", "name": "BSE Sensex", "unit": "pts"},
    "GOLD": {"yahoo": "GC=F", "name": "Gold (USD/oz)", "unit": "$"},
    "SILVER": {"yahoo": "SI=F", "name": "Silver (USD/oz)", "unit": "$"},
    "CRUDE_OIL": {"yahoo": "CL=F", "name": "Crude Oil WTI", "unit": "$"},
    "INDIA_VIX": {"yahoo": "^INDIAVIX", "name": "India VIX", "unit": ""},
    "US_10Y": {"yahoo": "^TNX", "name": "US 10Y Treasury Yield", "unit": "%"},
}


class IndicatorResponse(BaseModel):
    key: str
    name: str
    value: float
    change: float
    change_pct: float
    unit: str


class EconomyResponse(BaseModel):
    indicators: list[IndicatorResponse]


@router.get(
    "",
    response_model=EconomyResponse,
    summary="Get economic indicators",
    description="Returns key Indian/global macro indicators: USDINR, Nifty, Gold, Crude, VIX, etc.",
)
async def get_economic_indicators(
    user: User = Depends(get_current_user),
):
    results: list[IndicatorResponse] = []

    for key, config in INDICATORS.items():
        try:
            import yfinance as yf
            ticker = yf.Ticker(config["yahoo"])
            info = ticker.info

            price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
            prev = info.get("regularMarketPreviousClose") or info.get("previousClose", 0)

            if not price:
                # Try fast_info
                try:
                    fast = ticker.fast_info
                    price = float(fast.get("lastPrice", 0) or fast.get("last_price", 0))
                    prev = float(fast.get("previousClose", 0) or fast.get("previous_close", price))
                except Exception:
                    continue

            change = price - prev if price and prev else 0
            change_pct = (change / prev * 100) if prev else 0

            results.append(IndicatorResponse(
                key=key,
                name=config["name"],
                value=round(float(price), 2),
                change=round(float(change), 2),
                change_pct=round(float(change_pct), 2),
                unit=config["unit"],
            ))
        except Exception as e:
            logger.warning("economy.indicator.error", key=key, error=str(e))

    return EconomyResponse(indicators=results)
