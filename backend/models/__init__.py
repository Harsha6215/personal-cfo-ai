# Import all models here so Alembic can discover them via Base.metadata
from backend.models.user import User
from backend.models.portfolio import Portfolio
from backend.models.holding import Holding
from backend.models.transaction import Transaction
from backend.models.watchlist import WatchlistItem

__all__ = ["User", "Portfolio", "Holding", "Transaction", "WatchlistItem"]
