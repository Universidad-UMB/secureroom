"""UserSession model definition for SecureRoom."""

from datetime import datetime, timezone

from app.database.base import (
    Base,
    Column,
    String,
    DateTime,
    ForeignKey,
    PG_UUID,
)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<UserSession id={self.id[:8]}... user_id={self.user_id} expires_at={self.expires_at}>"
