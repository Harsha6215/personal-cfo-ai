"""
Zerodha Import Adapter — handles Zerodha Holdings CSV export.

Zerodha Holdings CSV format:
    "Instrument","Qty.","Avg. cost","LTP","Invested","Cur. val","P&L","Net chg.","Day chg.",""

This is a snapshot of current holdings. We import each row as a BUY event
at the average cost price. This gives us:
    - Current positions
    - Cost basis
    - Invested amount

For full transaction history, Zerodha also exports a Trade Book CSV
(different format — will be added as ZerodhaTradeBookAdapter later).
"""

import csv
import io
from datetime import datetime, timezone

from backend.models.import_job import ImportSource
from backend.services.import_engine.adapter import (
    ImportAdapter,
    ParsedTransaction,
    ValidationResult,
)


class ZerodhaHoldingsAdapter(ImportAdapter):
    """Adapter for Zerodha Holdings CSV export (Kite → Portfolio → Holdings → Download)."""

    source = ImportSource.ZERODHA

    # Expected headers in the Zerodha holdings CSV
    EXPECTED_HEADERS = {"instrument", "qty.", "avg. cost", "ltp", "invested", "cur. val", "p&l"}

    def detect(self, content: str, filename: str | None = None) -> bool:
        """
        Detect if this file is a Zerodha Holdings CSV.
        Check for characteristic column headers.
        """
        first_line = content.strip().split("\n")[0].lower()

        # Check for Zerodha holdings headers
        if "instrument" in first_line and "avg. cost" in first_line and "cur. val" in first_line:
            return True

        # Also check filename pattern
        if filename and "zerodha" in filename.lower():
            return True
        if filename and filename.lower().startswith("holdings"):
            return True

        return False

    def validate(self, content: str) -> ValidationResult:
        """Validate the CSV structure."""
        result = ValidationResult(detected_source=ImportSource.ZERODHA)

        lines = content.strip().split("\n")
        if len(lines) < 2:
            result.is_valid = False
            result.errors.append("File has no data rows (only header or empty)")
            return result

        # Parse header
        reader = csv.reader(io.StringIO(content))
        try:
            headers = [h.strip().lower() for h in next(reader)]
        except StopIteration:
            result.is_valid = False
            result.errors.append("Could not read CSV headers")
            return result

        # Check required headers
        found = set(headers)
        missing = self.EXPECTED_HEADERS - found
        if missing:
            result.is_valid = False
            result.errors.append(f"Missing required columns: {', '.join(missing)}")
            return result

        result.row_count = len(lines) - 1  # excluding header
        return result

    def parse(self, content: str) -> list[ParsedTransaction]:
        """Parse Zerodha Holdings CSV into canonical transactions."""
        transactions: list[ParsedTransaction] = []

        reader = csv.DictReader(io.StringIO(content))

        for row_num, row in enumerate(reader, start=2):  # row 1 is header
            try:
                # Clean field names (remove quotes, whitespace)
                cleaned = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}

                instrument = cleaned.get("instrument", "").strip().strip('"')
                qty_str = cleaned.get("qty.", "0").strip().strip('"')
                avg_cost_str = cleaned.get("avg. cost", "0").strip().strip('"')
                invested_str = cleaned.get("invested", "0").strip().strip('"')

                # Skip empty rows
                if not instrument or instrument == "":
                    continue

                # Parse numbers
                quantity = float(qty_str) if qty_str else 0
                avg_cost = float(avg_cost_str) if avg_cost_str else 0
                invested = float(invested_str) if invested_str else 0

                if quantity <= 0:
                    continue

                # Normalize ticker
                ticker = self.normalize_ticker(instrument)

                # Create canonical transaction (BUY at average cost)
                txn = ParsedTransaction(
                    ticker=ticker,
                    event_type="BUY",
                    quantity=quantity,
                    price=avg_cost,
                    executed_at=datetime.now(timezone.utc),  # holdings snapshot = "as of now"
                    amount=invested if invested > 0 else quantity * avg_cost,
                    exchange="NSE",
                    source="zerodha",
                    notes=f"Imported from Zerodha holdings snapshot",
                    row_number=row_num,
                )
                transactions.append(txn)

            except (ValueError, KeyError) as e:
                txn = ParsedTransaction(
                    ticker=cleaned.get("instrument", "UNKNOWN"),
                    event_type="BUY",
                    quantity=0,
                    price=0,
                    executed_at=datetime.now(timezone.utc),
                    row_number=row_num,
                    error=f"Row {row_num}: {str(e)}",
                )
                transactions.append(txn)

        return transactions
