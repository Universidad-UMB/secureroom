"""Authentication HTTP routes (Login, Register, Logout, Profile)."""

import os
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError
from fastapi.templating import Jinja2Templates

from app.auth.deps import get_current_user, get_current_user_optional
from app.auth.service import AuthService
from app.core.config import settings
from app.core.csrf import get_or_create_csrf_token, validate_csrf
from app.core.exceptions import AuthenticationError, RateLimitError, ValidationError
from app.database.deps import get_auth_service, get_user_service
from app.users.models import User
from app.users.schemas import UserCreate
from app.users.service import UserService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _friendly_registration_error(error: PydanticValidationError) -> str:
    """Convert Pydantic validation details into safe user-facing Spanish text."""
    for issue in error.errors():
        location = issue.get("loc", ())
        field = location[-1] if location else None
        issue_type = issue.get("type")

        if issue_type == "string_too_short":
            if field in {"password", "password_confirmation"}:
                return "La contraseña debe tener al menos 10 caracteres."
            if field == "name":
                return "El nombre no puede estar vacío."
            if field == "email":
                return "El correo electrónico no puede estar vacío."

        if issue_type == "value_error":
            message = issue.get("msg", "")
            return message.removeprefix("Value error, ") or "Revisa los datos ingresados."

    return "Revisa los datos ingresados e inténtalo nuevamente."


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    csrf_token = get_or_create_csrf_token(request)
    registered = request.query_params.get("registered")
    success_msg = "Cuenta creada exitosamente. Inicie sesión para continuar." if registered else None

    response = templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "request": request,
            "csrf_token": csrf_token,
            "current_user": None,
            "success_msg": success_msg,
            "error_msg": None,
            "email": "",
        },
    )
    if hasattr(request.state, "new_anon_csrf"):
        response.set_cookie(
            key="secureroom_csrf_anon",
            value=request.state.new_anon_csrf,
            httponly=True,
            samesite="lax",
            secure=settings.effective_cookie_secure,
            path="/",
        )
    return response


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
):
    # Validate CSRF
    await validate_csrf(request)

    ip_address = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")

    try:
        user, session = auth_service.authenticate_and_login(
            email=email,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        # Set secureroom_session cookie with strict security flags (RS-08)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session.id,
            max_age=settings.session_max_age_seconds,
            httponly=settings.session_cookie_httponly,
            samesite=settings.session_cookie_samesite,
            secure=settings.effective_cookie_secure,
            path="/",
        )
        # Clear anonymous visitor token
        response.delete_cookie("secureroom_csrf_anon", path="/")
        return response

    except (AuthenticationError, RateLimitError) as err:
        csrf = get_or_create_csrf_token(request)
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "csrf_token": csrf,
                "current_user": None,
                "error_msg": str(err.message),
                "email": email,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={
            "request": request,
            "csrf_token": csrf_token,
            "current_user": None,
            "error_msg": None,
            "name": "",
            "email": "",
        },
    )
    if hasattr(request.state, "new_anon_csrf"):
        response.set_cookie(
            key="secureroom_csrf_anon",
            value=request.state.new_anon_csrf,
            httponly=True,
            samesite="lax",
            secure=settings.effective_cookie_secure,
            path="/",
        )
    return response


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirmation: str = Form(...),
    csrf_token: str = Form(...),
    user_service: UserService = Depends(get_user_service),
):
    # Validate CSRF
    await validate_csrf(request)

    try:
        data = UserCreate(
            name=name,
            email=email,
            password=password,
            password_confirmation=password_confirmation,
        )
        user_service.register_user(data)
        return RedirectResponse(url="/login?registered=1", status_code=status.HTTP_303_SEE_OTHER)

    except PydanticValidationError as err:
        csrf = get_or_create_csrf_token(request)
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={
                "request": request,
                "csrf_token": csrf,
                "current_user": None,
                "error_msg": _friendly_registration_error(err),
                "name": name,
                "email": email,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except (ValueError, ValidationError) as err:
        csrf = get_or_create_csrf_token(request)
        error_text = err.message if hasattr(err, "message") else str(err)
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={
                "request": request,
                "csrf_token": csrf,
                "current_user": None,
                "error_msg": error_text,
                "name": name,
                "email": email,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.post("/logout")
async def logout_submit(
    request: Request,
    csrf_token: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user_optional),
):
    await validate_csrf(request)

    session_id = request.cookies.get(settings.session_cookie_name)
    ip_address = request.client.host if request.client else "127.0.0.1"

    if session_id:
        auth_service.logout(
            session_id=session_id,
            user_id=current_user.id if current_user else None,
            ip_address=ip_address,
        )

    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    # Expire and delete cookie (RS-09)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=settings.session_cookie_httponly,
        samesite=settings.session_cookie_samesite,
        secure=settings.effective_cookie_secure,
    )
    return response


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request=request,
        name="user/profile.html",
        context={
            "request": request,
            "current_user": current_user,
            "csrf_token": csrf_token,
            "active_page": "profile",
        },
    )
