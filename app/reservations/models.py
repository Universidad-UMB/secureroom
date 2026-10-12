"""Reservation model definition for SecureRoom."""

from datetime import datetime, timezone
import uuid

from app.database.base import (
    Base,
    Column,
    String,
    DateTime,
    ForeignKey,
    CheckConstraint,
    PG_UUID,
)


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    room_id = Column(PG_UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False, index=True)
    start_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    end_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(20), default="ACTIVE", nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        CheckConstraint("start_datetime < end_datetime", name="check_reservation_time_order"),
        CheckConstraint("status IN ('ACTIVE', 'CANCELLED')", name="check_reservation_status"),
    )

    def __repr__(self) -> str:
        return f"<Reservation id={self.id} room_id={self.room_id} user_id={self.user_id} status={self.status}>"
