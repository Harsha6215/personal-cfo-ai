"""
Financial Statements Service — fetches and stores Income Statement, Balance Sheet, Cash Flow.

Data is stored as JSON blobs per period — never overwritten.
This becomes the backbone of the Financial Analyst AI later.
"""

import structlog

from backend.services.market_data.yahoo_provider import _to_yahoo_ticker

logger = structlog.get_logger(__name__)


async def fetch_financials(ticker: str, statement_type: str = "income", period: str = "quarterly") -> list[dict]:
    """
    Fetch financial statements from Yahoo Finance.

    Args:
        ticker: Stock ticker (e.g. "TCS", "RELIANCE")
        statement_type: "income", "balance", "cashflow"
        period: "quarterly" or "annual"

    Returns:
        List of dicts, each representing one period's data.
    """
    try:
        import yfinance as yf

        yahoo_ticker = _to_yahoo_ticker(ticker)
        stock = yf.Ticker(yahoo_ticker)

        if statement_type == "income":
            df = stock.quarterly_income_stmt if period == "quarterly" else stock.income_stmt
        elif statement_type == "balance":
            df = stock.quarterly_balance_sheet if period == "quarterly" else stock.balance_sheet
        elif statement_type == "cashflow":
            df = stock.quarterly_cashflow if period == "quarterly" else stock.cashflow
        else:
            return []

        if df is None or df.empty:
            return []

        # Convert DataFrame to list of dicts (each column = one period)
        results = []
        for col in df.columns:
            period_date = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
            period_data = {}
            for idx, val in df[col].items():
                key = str(idx)
                if val is not None and str(val) != "nan":
                    try:
                        period_data[key] = float(val)
                    except (ValueError, TypeError):
                        period_data[key] = str(val)

            if period_data:
                results.append({
                    "period_date": period_date,
                    "data": period_data,
                })

        logger.info("financials.fetched", ticker=ticker, type=statement_type, period=period, count=len(results))
        return results

    except Exception as e:
        logger.warning("financials.error", ticker=ticker, error=str(e))
        return []
