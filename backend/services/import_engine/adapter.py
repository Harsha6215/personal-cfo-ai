"""
ImportAdapter — abstract base class for all broker adapters.

Each adapter knows how to:
1. Detect if a file belongs to it (from headers/structure)
2. Validate the file format
3. Parse rows into a canonical ParsedTransaction format
4. Normalize data (clean symbols, map exchanges, etc.)

To add a new broker, create a class that inherits ImportAdapter:
    class GrowwAdapter(ImportAdapter):
        source = ImportSource.GROWW
        ...
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from backend.models.import_job import ImportSource


@dataclass
class ParsedTransaction:
    """
    Canonical transaction format — broker-agnostic.
    Every adapter normalizes its data into this shape.
    """
    # Required
    ticker: str
    event_type: str           # BUY, SELL, DIVIDEND, etc.
    quantity: float
    price: float
    executed_at: datetime

    # Optional — enriched during normalization
    isin: str | None = None
    exchange: str = "NSE"
    amount: float = 0.0       # quantity * price (or explicit from CSV)
    fees: float = 0.0
    source: str | None = None
    notes: str | None = None

    # For splits/mergers
    split_ratio_from: float | None = None
    split_ratio_to: float | None = None

    # Validation state
    row_number: int | None = None
    error: str | None = None
    is_duplicate: bool = False


@dataclass
class ValidationResult:
    """Result of file validation — errors prevent import."""
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    detected_source: ImportSource | None = None
    row_count: int = 0


@dataclass
class PreviewResult:
    """What the user sees before confirming import."""
    total_rows: int = 0
    valid_transactions: int = 0
    duplicates: int = 0
    errors: int = 0
    new_assets: list[str] = field(default_factory=list)  # tickers not in DB yet
    transactions: list[ParsedTransaction] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)


class ImportAdapter(ABC):
    """
    Base class for all broker/source adapters.

    Subclass and implement:
        - source: ImportSource enum value
        - detect(content, filename) -> bool
        - validate(content) -> ValidationResult
        - parse(content) -> list[ParsedTransaction]
    """

    source: ImportSource

    @abstractmethod
    def detect(self, content: str, filename: str | None = None) -> bool:
        """
        Does this file belong to this adapter?
        Check headers, column names, filename patterns, etc.
        """
        ...

    @abstractmethod
    def validate(self, content: str) -> ValidationResult:
        """
        Validate file structure and content.
        Return errors that would prevent import.
        """
        ...

    @abstractmethod
    def parse(self, content: str) -> list[ParsedTransaction]:
        """
        Parse file content into canonical ParsedTransaction objects.
        Each row becomes one ParsedTransaction.
        """
        ...

    def normalize_ticker(self, raw_ticker: str) -> str:
        """
        Clean up ticker symbols. Override for broker-specific cleanup.
        Default: strip whitespace, uppercase, remove -EQ suffix.
        """
        ticker = raw_ticker.strip().upper()
        # Remove common suffixes added by Indian brokers
        for suffix in ["-EQ", "-BE", "-BL", "-SM"]:
            if ticker.endswith(suffix):
                ticker = ticker[: -len(suffix)]
        return ticker

    def normalize_event_type(self, raw_type: str) -> str:
        """Map broker-specific trade types to canonical EventType values."""
        mapping = {
            "buy": "BUY",
            "sell": "SELL",
            "b": "BUY",
            "s": "SELL",
            "purchase": "BUY",
            "redemption": "SELL",
            "dividend": "DIVIDEND",
            "bonus": "BONUS",
            "split": "SPLIT",
            "sip": "SIP",
        }
        return mapping.get(raw_type.strip().lower(), raw_type.strip().upper())
