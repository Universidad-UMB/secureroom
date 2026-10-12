"""Authentication service implementing login, session lifecycle, and logout."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import uuid

from app.audit.service import AuditService
from app.auth.models import UserSession
from app.auth.repository import SessionRepository
from app.core.config import settings
from app.core.exceptions import AuthenticationError, RateLimitError
from app.core.rate_limiter import login_rate_limiter
from app.core.security import generate_session_id, verify_password
from app.users.models import User
from app.users.repository import UserRepository


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        audit_service: AuditService,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.audit_service = audit_service

    def authenticate_and_login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, UserSession]:
        """Authenticates user credentials, enforces rate limiting, and issues a server-side session."""
        rate_limit_key = f"{ip_address or 'unknown'}:{email.lower()}"

        # 1. Check rate limit lockout (CA-04, RS-01)
        is_locked, remaining = login_rate_limiter.is_locked(rate_limit_key)
        if is_locked:
            self.audit_service.log_event(
                action="LOGIN_FAILED",
                resource_type="USER",
                resource_id=email,
                result="BLOCKED_RATE_LIMIT",
                ip_address=ip_address,
            )
            raise RateLimitError(
                f"Demasiados intentos fallidos. Intente nuevamente en {remaining} segundos.",
                retry_after=remaining,
            )

        # 2. Lookup user
        user = self.user_repo.get_by_email(email.lower())

        # 3. Verify password
        if not user or not verify_password(password, user.password_hash):
            login_rate_limiter.record_failure(rate_limit_key)
            self.audit_service.log_event(
                action="LOGIN_FAILED",
                resource_type="USER",
                resource_id=email,
                result="FAILURE",
                ip_address=ip_address,
            )
            # Generic error message to prevent user enumeration (RS-12)
            raise AuthenticationError("Credenciales inválidas.")

        # 4. Check active status (RB-24)
        if not user.is_active:
            self.audit_service.log_event(
                action="LOGIN_FAILED",
                resource_type="USER",
                resource_id=str(user.id),
                user_id=user.id,
                result="ACCOUNT_INACTIVE",
                ip_address=ip_address,
            )
            raise AuthenticationError("La cuenta se encuentra inactiva.")

        # 5. Success -> reset rate limiter, create session, audit
        login_rate_limiter.record_success(rate_limit_key)

        session_id = generate_session_id()
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.session_max_age_seconds
        )

        user_session = UserSession(
            id=session_id,
            user_id=user.id,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else None,
        )

        created_session = self.session_repo.create(user_session)

        self.audit_service.log_event(
            action="LOGIN_SUCCESS",
            resource_type="USER",
            resource_id=str(user.id),
            user_id=user.id,
            result="SUCCESS",
            ip_address=ip_address,
        )

        return user, created_session

    def logout(
        self,
        session_id: str,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Invalidates server-side session and records audit log (RS-09, CA-05)."""
        if session_id:
            self.session_repo.delete(session_id)

        self.audit_service.log_event(
            action="LOGOUT",
            resource_type="SESSION",
            resource_id=session_id[:8] if session_id else None,
            user_id=user_id,
            result="SUCCESS",
            ip_address=ip_address,
        )

    def get_user_from_session(self, session_id: str) -> Optional[User]:
        """Resolves active, non-expired session to authenticated User."""
        if not session_id:
            return None

        session = self.session_repo.get_by_id(session_id)
        if not session:
            return None

        user = self.user_repo.get_by_id(session.user_id)
        if not user or not user.is_active:
            return None

        return user
