"""
User Pydantic schemas.
These are the request/response contracts for the API — separate from the ORM model.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Used for POST /auth/register (Story 6)."""
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """Returned by the API — never includes hashed_password."""
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
