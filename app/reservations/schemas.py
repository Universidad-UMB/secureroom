"""Pydantic schemas for reservation validation."""

from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, model_validator


class ReservationCreate(BaseModel):
    """Schema for creating a reservation."""

    room_id: uuid.UUID
    start_datetime: datetime
    end_datetime: datetime

    @model_validator(mode="after")
    def validate_times(self) -> "ReservationCreate":
        if self.start_datetime >= self.end_datetime:
            raise ValueError("La hora de inicio debe ser anterior a la hora de finalización.")

        now = datetime.now(timezone.utc)
        start_utc = (
            self.start_datetime
            if self.start_datetime.tzinfo is not None
            else self.start_datetime.replace(tzinfo=timezone.utc)
        )
        if start_utc < now:
            raise ValueError("La fecha y hora de inicio debe ser futura.")
        return self


class AvailabilityCheck(BaseModel):
    """Schema for checking room availability."""

    room_id: uuid.UUID
    start_datetime: datetime
    end_datetime: datetime

    @model_validator(mode="after")
    def validate_times(self) -> "AvailabilityCheck":
        if self.start_datetime >= self.end_datetime:
            raise ValueError("La hora de inicio debe ser anterior a la hora de finalización.")
        return self


class ReservationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    room_id: uuid.UUID
    start_datetime: datetime
    end_datetime: datetime
    status: str
    created_at: datetime
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[uuid.UUID] = None

    # Enriched view fields
    room_name: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
