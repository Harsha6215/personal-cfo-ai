"""
Financial Statements API — Income Statement, Balance Sheet, Cash Flow.

Data fetched from Yahoo Finance. In production, store in DB and serve from cache.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.services.market_data.financials import fetch_financials

router = APIRouter(tags=["Financials"])


class FinancialPeriod(BaseModel):
    period_date: str
    data: dict


class FinancialsResponse(BaseModel):
    ticker: str
    statement_type: str
    period: str
    statements: list[FinancialPeriod]


@router.get(
    "/{ticker}",
    response_model=FinancialsResponse,
    summary="Get financial statements",
    description="Returns Income Statement, Balance Sheet, or Cash Flow for a ticker.",
)
async def get_financials(
    ticker: str,
    type: str = Query("income", description="income, balance, or cashflow"),
    period: str = Query("quarterly", description="quarterly or annual"),
    user: User = Depends(get_current_user),
):
    if type not in ("income", "balance", "cashflow"):
        raise HTTPException(status_code=400, detail="type must be: income, balance, or cashflow")
    if period not in ("quarterly", "annual"):
        raise HTTPException(status_code=400, detail="period must be: quarterly or annual")

    statements = await fetch_financials(ticker.upper(), type, period)
    if not statements:
        raise HTTPException(status_code=404, detail=f"No {type} statement data for {ticker}")

    return FinancialsResponse(
        ticker=ticker.upper(),
        statement_type=type,
        period=period,
        statements=[FinancialPeriod(**s) for s in statements],
    )
