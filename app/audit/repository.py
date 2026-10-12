"""Repository layer for append-only AuditLog persistence (RS-11, RB-22, CA-09).

Explicitly does NOT provide update or delete methods to ensure log immutability.
"""

from abc import ABC, abstractmethod
from typing import List
import threading

from app.audit.models import AuditLog


class AuditRepository(ABC):
    @abstractmethod
    def create(self, log: AuditLog) -> AuditLog:
        pass

    @abstractmethod
    def list_all(self, limit: int = 200) -> List[AuditLog]:
        pass


class SQLAlchemyAuditRepository(AuditRepository):
    def __init__(self, db_session):
        self.db = db_session

    def create(self, log: AuditLog) -> AuditLog:
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_all(self, limit: int = 200) -> List[AuditLog]:
        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )


class InMemoryAuditRepository(AuditRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._logs: List[AuditLog] = []

    def create(self, log: AuditLog) -> AuditLog:
        with self._lock:
            self._logs.append(log)
            return log

    def list_all(self, limit: int = 200) -> List[AuditLog]:
        with self._lock:
            # Sort newest first
            sorted_logs = sorted(
                self._logs,
                key=lambda x: getattr(x, "created_at", None) or 0,
                reverse=True,
            )
            return sorted_logs[:limit]

    def clear(self):
        with self._lock:
            self._logs.clear()


in_memory_audit_repo = InMemoryAuditRepository()
