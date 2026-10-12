"""Pydantic validation schemas for Users."""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, Field, root_validator, validator
from app.core.security import validate_password_strength


class UserCreate(BaseModel):
    """Schema for public user registration (RB-01, RS-05, RS-06).

    Explicitly excludes role, is_active, and id to prevent parameter tampering (CA-03).
    """

    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=10, max_length=128)
    password_confirmation: str = Field(..., min_length=10, max_length=128)

    @validator("email")
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("El correo electrónico no tiene un formato válido.")
        return clean

    @validator("name")
    def validate_name_not_blank(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("El nombre no puede estar vacío.")
        return clean

    @root_validator
    def validate_passwords_match(cls, values):
        password = values.get("password")
        confirmation = values.get("password_confirmation")
        if password and confirmation and password != confirmation:
            raise ValueError("Las contraseñas no coinciden.")
        if password:
            validate_password_strength(password)
        return values


class UserLogin(BaseModel):
    """Schema for login credentials."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @validator("email")
    def clean_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Safe schema for user details, excluding password_hash (RS-12)."""

    id: uuid.UUID
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
