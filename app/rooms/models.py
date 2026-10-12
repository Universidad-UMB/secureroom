"""Room model definition for SecureRoom."""

from datetime import datetime, timezone
import uuid

from app.database.base import (
    Base,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    CheckConstraint,
    PG_UUID,
)


class Room(Base):
    __tablename__ = "rooms"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    location = Column(String(200), nullable=False)
    capacity = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("capacity > 0", name="check_room_capacity_positive"),
    )

    def __repr__(self) -> str:
        return f"<Room id={self.id} name={self.name} capacity={self.capacity} active={self.is_active}>"
