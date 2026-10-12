"""Pydantic schemas for Reservation validation."""

from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, Field, root_validator


class ReservationCreate(BaseModel):
    """Schema for creating a reservation.

    Explicitly excludes user_id and status to prevent parameter tampering (RS-05, CA-03).
    """

    room_id: uuid.UUID
    start_datetime: datetime
    end_datetime: datetime

    @root_validator
    def validate_times(cls, values):
        start = values.get("start_datetime")
        end = values.get("end_datetime")

        if start and end:
            # RB-10: start must be before end
            if start >= end:
                raise ValueError("La hora de inicio debe ser anterior a la hora de finalización.")

            # RB-11: reservation must be in the future
            now = datetime.now(timezone.utc)
            start_utc = start if start.tzinfo is not None else start.replace(tzinfo=timezone.utc)
            if start_utc < now:
                raise ValueError("La fecha y hora de inicio debe ser futura.")

        return values


class AvailabilityCheck(BaseModel):
    """Schema for checking room availability."""

    room_id: uuid.UUID
    start_datetime: datetime
    end_datetime: datetime

    @root_validator
    def validate_times(cls, values):
        start = values.get("start_datetime")
        end = values.get("end_datetime")
        if start and end and start >= end:
            raise ValueError("La hora de inicio debe ser anterior a la hora de finalización.")
        return values


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

    class Config:
        orm_mode = True
