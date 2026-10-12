"""AuditService for recording and querying security audit events."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.audit.models import AuditLog
from app.audit.repository import AuditRepository


class AuditService:
    def __init__(self, audit_repo: AuditRepository):
        self.audit_repo = audit_repo

    def log_event(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        result: str = "SUCCESS",
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Records an immutable security audit event (RS-10, RS-11)."""
        log = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            result=result,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc),
        )
        return self.audit_repo.create(log)

    def list_events(self, limit: int = 200) -> List[AuditLog]:
        """Lists audit events for administrative review (RF-25)."""
        return self.audit_repo.list_all(limit=limit)
