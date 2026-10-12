"""Session domain entities and session manager for SecureRoom."""

from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid


class SessionData:
    def __init__(
        self,
        session_id: str,
        user_id: uuid.UUID,
        expires_at: datetime,
        created_at: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.expires_at = expires_at
        self.created_at = created_at or datetime.now(timezone.utc)
        self.ip_address = ip_address
        self.user_agent = user_agent

    @property
    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.expires_at.tzinfo is None:
            return self.expires_at.replace(tzinfo=timezone.utc) < now
        return self.expires_at < now


def calculate_expiration(seconds: int = 28800) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)
