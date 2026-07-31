"""
Watchlist Pydantic schemas.
"""

from datetime import datetime

from pydantic import BaseModel


class WatchlistItemBase(BaseModel):
    symbol: str
    notes: str | None = None


class WatchlistItemCreate(WatchlistItemBase):
    pass


class WatchlistItemResponse(WatchlistItemBase):
    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
