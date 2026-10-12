"""CSRF protection module for SecureRoom."""

from fastapi import Request
from app.core.config import settings
from app.core.exceptions import CSRFError
from app.core.security import generate_csrf_token, verify_csrf_token, generate_session_id


def get_or_create_csrf_token(request: Request) -> str:
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        return generate_csrf_token(session_id)

    visitor_csrf = request.cookies.get("secureroom_csrf_anon")
    if visitor_csrf:
        return generate_csrf_token(visitor_csrf)

    anon_id = generate_session_id()
    request.state.new_anon_csrf = anon_id
    return generate_csrf_token(anon_id)


async def validate_csrf(request: Request) -> None:
    submitted_token = None
    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        submitted_token = form.get("csrf_token")
    if not submitted_token:
        submitted_token = request.headers.get("X-CSRF-Token")

    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        if not submitted_token or not verify_csrf_token(session_id, str(submitted_token)):
            raise CSRFError("Token CSRF inválido o expirado.")
        return

    anon_id = request.cookies.get("secureroom_csrf_anon")
    if anon_id:
        if not submitted_token or not verify_csrf_token(anon_id, str(submitted_token)):
            raise CSRFError("Token CSRF de visitante inválido.")
        return

    raise CSRFError("Token CSRF ausente.")
