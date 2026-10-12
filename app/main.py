"""SecureRoom v1 — Main FastAPI Application Entrypoint.

Configures routes, static file serving, secure cookie sessions,
and global exception handlers to prevent sensitive information disclosure (RS-12, CA-10).
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.admin.router import router as admin_router
from app.auth.deps import get_current_user_optional
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CSRFError,
    RateLimitError,
    ReservationConflictError,
    ResourceNotFoundError,
    SecureRoomError,
    ValidationError,
)
from app.core.logging import logger
from app.reservations.router import router as reservations_router
from app.rooms.router import router as rooms_router

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Include Routers
app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(reservations_router)
app.include_router(admin_router)


@app.get("/health")
async def health_check():
    """Health check endpoint (RF/RNF and contract compliance)."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": settings.app_env,
    }


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root redirect: directs to dashboard if authenticated, or login otherwise."""
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


# ==========================================
# Secure Global Exception Handlers (RS-12, CA-10)
# ==========================================

@app.exception_handler(CSRFError)
async def csrf_exception_handler(request: Request, exc: CSRFError):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "current_user": None,
                "status_code": 403,
                "title": "Error de Validación CSRF",
                "message": exc.message,
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return JSONResponse(status_code=403, content={"error": exc.message})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        title_map = {
            401: "No Autenticado",
            403: "Acceso Denegado",
            404: "Recurso No Encontrado",
            500: "Error Interno del Servidor",
        }
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "current_user": None,
                "status_code": exc.status_code,
                "title": title_map.get(exc.status_code, "Aviso"),
                "message": exc.detail,
            },
            status_code=exc.status_code,
            headers=exc.headers,
        )
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail}, headers=exc.headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Global catch-all prevents stack traces, internal paths, and SQL from leaking (RS-12)."""
    logger.error(f"Unhandled exception during {request.method} {request.url.path}: {str(exc)}", exc_info=True)

    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "current_user": None,
                "status_code": 500,
                "title": "Error Inesperado",
                "message": "Ha ocurrido un error en el servidor. Por favor, intente nuevamente más tarde.",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Ha ocurrido un error inesperado en el servidor."},
    )
