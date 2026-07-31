"""
Transaction Pydantic schemas.
"""

from datetime import datetime

from pydantic import BaseModel

from backend.models.transaction import TransactionType


class TransactionBase(BaseModel):
    type: TransactionType
    quantity: float
    price: float
    executed_at: datetime
    notes: str | None = None


class TransactionCreate(TransactionBase):
    holding_id: str


class TransactionResponse(TransactionBase):
    id: str
    holding_id: str
    total_value: float
    created_at: datetime

    model_config = {"from_attributes": True}
