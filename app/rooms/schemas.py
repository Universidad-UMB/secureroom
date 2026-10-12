"""Pydantic schemas for room operations."""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoomCreate(BaseModel):
    """Schema for creating a new room (admin only)."""

    name: str = Field(..., min_length=1, max_length=100)
    location: str = Field(..., min_length=1, max_length=200)
    capacity: int = Field(..., gt=0, description="Capacity must be strictly greater than zero")
    description: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("El nombre de la sala no puede estar vacío.")
        return clean

    @field_validator("location")
    @classmethod
    def clean_location(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("La ubicación no puede estar vacía.")
        return clean


class RoomUpdate(BaseModel):
    """Schema for updating an existing room (admin only)."""

    name: str = Field(..., min_length=1, max_length=100)
    location: str = Field(..., min_length=1, max_length=200)
    capacity: int = Field(..., gt=0)
    description: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("El nombre de la sala no puede estar vacío.")
        return clean

    @field_validator("location")
    @classmethod
    def clean_location(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("La ubicación no puede estar vacía.")
        return clean


class RoomResponse(BaseModel):
    id: uuid.UUID
    name: str
    location: str
    capacity: int
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
