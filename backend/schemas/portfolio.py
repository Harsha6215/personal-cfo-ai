"""
Portfolio Pydantic schemas.
"""

from datetime import datetime

from pydantic import BaseModel


class PortfolioBase(BaseModel):
    name: str
    currency: str = "INR"


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioUpdate(BaseModel):
    name: str | None = None
    currency: str | None = None


class PortfolioResponse(PortfolioBase):
    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
