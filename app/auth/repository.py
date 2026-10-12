"""Session persistence repository (RS-08, RS-09, CA-05)."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
import threading
import uuid

from app.auth.models import UserSession


class SessionRepository(ABC):
    @abstractmethod
    def create(self, session: UserSession) -> UserSession:
        pass

    @abstractmethod
    def get_by_id(self, session_id: str) -> Optional[UserSession]:
        pass

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        pass

    @abstractmethod
    def delete_expired(self) -> int:
        pass


class SQLAlchemySessionRepository(SessionRepository):
    def __init__(self, db_session):
        self.db = db_session

    def create(self, session: UserSession) -> UserSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: str) -> Optional[UserSession]:
        return self.db.query(UserSession).filter(UserSession.id == session_id).first()

    def delete(self, session_id: str) -> bool:
        session = self.get_by_id(session_id)
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False

    def delete_expired(self) -> int:
        now = datetime.now(timezone.utc)
        count = (
            self.db.query(UserSession)
            .filter(UserSession.expires_at < now)
            .delete()
        )
        self.db.commit()
        return count


class InMemorySessionRepository(SessionRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._sessions = {}

    def create(self, session: UserSession) -> UserSession:
        with self._lock:
            self._sessions[session.id] = session
            return session

    def get_by_id(self, session_id: str) -> Optional[UserSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            now = datetime.now(timezone.utc)
            # Check expiration
            exp = session.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                # Expired -> delete and return None
                del self._sessions[session_id]
                return None
            return session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def delete_expired(self) -> int:
        now = datetime.now(timezone.utc)
        with self._lock:
            expired_keys = [
                k for k, s in self._sessions.items()
                if (s.expires_at.replace(tzinfo=timezone.utc) if s.expires_at.tzinfo is None else s.expires_at) < now
            ]
            for k in expired_keys:
                del self._sessions[k]
            return len(expired_keys)

    def clear(self):
        with self._lock:
            self._sessions.clear()


in_memory_session_repo = InMemorySessionRepository()
