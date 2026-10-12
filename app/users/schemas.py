"""Pydantic validation schemas for users."""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.security import validate_password_strength


class UserCreate(BaseModel):
    """Schema for public user registration."""

    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=10, max_length=128)
    password_confirmation: str = Field(..., min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("El correo electrónico no tiene un formato válido.")
        return clean

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("El nombre no puede estar vacío.")
        return clean

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "UserCreate":
        if self.password != self.password_confirmation:
            raise ValueError("Las contraseñas no coinciden.")
        validate_password_strength(self.password)
        return self


class UserLogin(BaseModel):
    """Schema for login credentials."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Safe schema for user details, excluding password_hash."""

    id: uuid.UUID
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
