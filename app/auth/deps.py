"""FastAPI authentication and role-based access control dependencies (RS-01, RS-03)."""

from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.auth.service import AuthService
from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.database.deps import get_auth_service
from app.users.models import User


def get_current_user_optional(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[User]:
    """Resolves authenticated user from session cookie if present, otherwise returns None."""
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        return None
    return auth_service.get_user_from_session(session_id)


def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Enforces authentication (RS-01).

    If unauthenticated:
    - HTML requests are redirected to /login.
    - API / JSON requests return HTTP 401 Unauthorized.
    """
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/login"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida.",
        )

    user = auth_service.get_user_from_session(session_id)
    if not user:
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/login"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada.",
        )

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforces administrator role authorization (RS-03, CA-01)."""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requieren permisos de administrador.",
        )
    return current_user
