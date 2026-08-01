"""
Corporate Actions API — Dividends, Splits, Bonus history for a stock.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.services.market_data import MarketDataService, YahooFinanceProvider

router = APIRouter(tags=["Corporate Actions"])

_market_service = MarketDataService(provider=YahooFinanceProvider())


class DividendResponse(BaseModel):
    date: str
    amount: float
    currency: str = "INR"


class SplitResponse(BaseModel):
    date: str
    ratio_from: int
    ratio_to: int


class CorporateActionsResponse(BaseModel):
    ticker: str
    dividends: list[DividendResponse]
    splits: list[SplitResponse]


@router.get(
    "/{ticker}",
    response_model=CorporateActionsResponse,
    summary="Get corporate actions (dividends + splits)",
    description="Returns dividend history and stock split history from Yahoo Finance.",
)
async def get_corporate_actions(
    ticker: str,
    user: User = Depends(get_current_user),
):
    dividends = await _market_service.get_dividends(ticker.upper())
    splits = await _market_service.get_splits(ticker.upper())

    if not dividends and not splits:
        raise HTTPException(status_code=404, detail=f"No corporate actions found for {ticker}")

    return CorporateActionsResponse(
        ticker=ticker.upper(),
        dividends=[
            DividendResponse(date=d.date.isoformat(), amount=d.amount, currency=d.currency)
            for d in dividends
        ],
        splits=[
            SplitResponse(date=s.date.isoformat(), ratio_from=s.ratio_from, ratio_to=s.ratio_to)
            for s in splits
        ],
    )
