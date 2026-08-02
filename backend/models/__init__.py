# Import all models here so Alembic can discover them via Base.metadata
from backend.models.user import User, UserRole
from backend.models.portfolio import Portfolio
from backend.models.holding import Holding
from backend.models.transaction import Transaction
from backend.models.watchlist import WatchlistItem

# Epic 2: Event-sourced domain model
from backend.models.asset import Asset
from backend.models.financial_event import FinancialEvent
from backend.models.import_job import ImportJob

# Epic 5: Decision Intelligence
from backend.models.decision_history import DecisionRecord

# Epic 6: SaaS Platform
from backend.models.user_profile import UserProfile

__all__ = [
    "User",
    "UserRole",
    "Portfolio",
    "Holding",
    "Transaction",
    "WatchlistItem",
    # Epic 2
    "Asset",
    "FinancialEvent",
    "ImportJob",
    # Epic 5
    "DecisionRecord",
    # Epic 6
    "UserProfile",
]
