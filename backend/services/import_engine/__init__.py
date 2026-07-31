"""
Import Engine — Generic pipeline for ingesting financial data from any source.

Architecture:
    Upload File → Source Detection → Validate → Parse → Normalize → Preview → Persist

Every broker adapter implements the ImportAdapter interface.
The ImportService orchestrates the pipeline.
"""

from backend.services.import_engine.adapter import ImportAdapter, ParsedTransaction
from backend.services.import_engine.service import ImportService
from backend.services.import_engine.registry import AdapterRegistry

__all__ = ["ImportAdapter", "ParsedTransaction", "ImportService", "AdapterRegistry"]
