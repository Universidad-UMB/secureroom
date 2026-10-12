"""Login rate limiting module.
Protects against brute force and credential stuffing attacks (CA-04, RS-01, RS-10).
"""

from collections import defaultdict
from datetime import datetime, timezone, timedelta
import threading
from typing import Dict, List, Tuple
from app.core.config import settings


class LoginRateLimiter:
    def __init__(
        self,
        max_attempts: int = settings.login_max_failed_attempts,
        lockout_seconds: int = settings.login_lockout_seconds,
    ):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._lock = threading.Lock()
        self._failures: Dict[str, List[datetime]] = defaultdict(list)
        self._lockouts: Dict[str, datetime] = {}

    def _cleanup_old(self, key: str, now: datetime) -> None:
        window = timedelta(seconds=self.lockout_seconds)
        self._failures[key] = [t for t in self._failures[key] if now - t <= window]

    def is_locked(self, key: str) -> Tuple[bool, int]:
        now = datetime.now(timezone.utc)
        with self._lock:
            locked_until = self._lockouts.get(key)
            if locked_until:
                if now < locked_until:
                    remaining = int((locked_until - now).total_seconds()) + 1
                    return True, remaining
                else:
                    del self._lockouts[key]
                    self._failures.pop(key, None)
                    return False, 0
            self._cleanup_old(key, now)
            return False, 0

    def record_failure(self, key: str) -> Tuple[bool, int]:
        now = datetime.now(timezone.utc)
        with self._lock:
            self._cleanup_old(key, now)
            self._failures[key].append(now)
            if len(self._failures[key]) >= self.max_attempts:
                locked_until = now + timedelta(seconds=self.lockout_seconds)
                self._lockouts[key] = locked_until
                return True, self.lockout_seconds
            return False, 0

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._lockouts.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._failures.clear()
            self._lockouts.clear()


login_rate_limiter = LoginRateLimiter()
