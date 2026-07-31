"""
Holding Pydantic schemas.
"""

from datetime import datetime

from pydantic import BaseModel

from backend.models.holding import AssetType


class HoldingBase(BaseModel):
    symbol: str
    quantity: float
    average_cost: float
    asset_type: AssetType = AssetType.STOCK


class HoldingCreate(HoldingBase):
    portfolio_id: str


class HoldingUpdate(BaseModel):
    quantity: float | None = None
    average_cost: float | None = None


class HoldingResponse(HoldingBase):
    id: str
    portfolio_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
