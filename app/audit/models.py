"""AuditLog model definition for SecureRoom."""

from datetime import datetime, timezone
import uuid

from app.database.base import (
    Base,
    Column,
    String,
    DateTime,
    ForeignKey,
    PG_UUID,
)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    result = Column(String(20), nullable=False)  # SUCCESS, FAILURE
    ip_address = Column(String(45), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} result={self.result} at={self.created_at}>"
