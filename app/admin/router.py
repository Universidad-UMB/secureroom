"""Administrative HTTP router (Dashboard, Rooms, Reservations, Users, Audit).

All routes enforce strict administrator role authorization via require_admin (RS-03, CA-01).
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.audit.service import AuditService
from app.auth.deps import require_admin
from app.core.csrf import get_or_create_csrf_token, validate_csrf
from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.database.deps import (
    get_audit_service,
    get_reservation_service,
    get_room_service,
    get_user_service,
)
from app.reservations.service import ReservationService
from app.rooms.schemas import RoomCreate, RoomUpdate
from app.rooms.service import RoomService
from app.users.models import User
from app.users.service import UserService

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
    room_service: RoomService = Depends(get_room_service),
    reservation_service: ReservationService = Depends(get_reservation_service),
    audit_service: AuditService = Depends(get_audit_service),
):
    users = user_service.list_all()
    all_rooms = room_service.list_all_rooms()
    active_rooms = [r for r in all_rooms if r.is_active]
    all_res = reservation_service.list_all_reservations()
    active_res = [r for r in all_res if r.status == "ACTIVE"]
    recent_logs = audit_service.list_events(limit=10)
    all_logs = audit_service.list_events(limit=1000)

    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "request": request,
            "current_user": admin_user,
            "csrf_token": csrf_token,
            "active_page": "admin_dashboard",
            "total_users": len(users),
            "total_rooms": len(all_rooms),
            "active_rooms": len(active_rooms),
            "total_reservations": len(all_res),
            "active_reservations": len(active_res),
            "total_audit_events": len(all_logs),
            "recent_events": recent_logs,
        },
    )


@router.get("/rooms", response_class=HTMLResponse)
async def admin_rooms_list(
    request: Request,
    admin_user: User = Depends(require_admin),
    room_service: RoomService = Depends(get_room_service),
):
    rooms = room_service.list_all_rooms()
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request=request,
        name="admin/rooms.html",
        context={
            "request": request,
            "current_user": admin_user,
            "csrf_token": csrf_token,
            "rooms": rooms,
            "active_page": "admin_rooms",
        },
    )


@router.get("/rooms/new", response_class=HTMLResponse)
async def admin_room_new_page(
    request: Request,
    admin_user: User = Depends(require_admin),
):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request=request,
        name="admin/room_form.html",
        context={
            "request": request,
            "current_user": admin_user,
            "room": None,
            "csrf_token": csrf_token,
            "active_page": "admin_rooms",
            "error_msg": None,
        },
    )


@router.post("/rooms", response_class=HTMLResponse)
async def admin_room_create_submit(
    request: Request,
    name: str = Form(...),
    location: str = Form(...),
    capacity: int = Form(...),
    description: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    admin_user: User = Depends(require_admin),
    room_service: RoomService = Depends(get_room_service),
):
    await validate_csrf(request)

    try:
        data = RoomCreate(
            name=name,
            location=location,
            capacity=capacity,
            description=description,
        )
        room_service.create_room(data, admin_user)
        return RedirectResponse(url="/admin/rooms", status_code=status.HTTP_303_SEE_OTHER)

    except (ValidationError, ValueError) as err:
        csrf = get_or_create_csrf_token(request)
        error_text = err.message if hasattr(err, "message") else str(err)
        return templates.TemplateResponse(
            request=request,
            name="admin/room_form.html",
            context={
                "request": request,
                "current_user": admin_user,
                "room": None,
                "name": name,
                "location": location,
                "capacity": capacity,
                "description": description,
                "csrf_token": csrf,
                "active_page": "admin_rooms",
                "error_msg": error_text,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/rooms/{room_id}/edit", response_class=HTMLResponse)
async def admin_room_edit_page(
    room_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(require_admin),
    room_service: RoomService = Depends(get_room_service),
):
    try:
        room = room_service.get_room(room_id)
    except ResourceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala no encontrada.")

    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request=request,
        name="admin/room_form.html",
        context={
            "request": request,
            "current_user": admin_user,
            "room": room,
            "csrf_token": csrf_token,
            "active_page": "admin_rooms",
            "error_msg": None,
        },
    )


@router.post("/rooms/{room_id}/edit", response_class=HTMLResponse)
async def admin_room_edit_submit(
    room_id: uuid.UUID,
    request: Request,
    name: str = Form(...),
    location: str = Form(...),
    capacity: int = Form(...),
    description: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    admin_user: User = Depends(require_admin),
    room_service: RoomService = Depends(get_room_service),
):
    await validate_csrf(request)

    try:
        data = RoomUpdate(
            name=name,
            location=location,
            capacity=capacity,
            description=description,
        )
        room_service.update_room(room_id, data, admin_user)
        return RedirectResponse(url="/admin/rooms", status_code=status.HTTP_303_SEE_OTHER)

    except (ValidationError, ValueError) as err:
        room = room_service.get_room(room_id)
        csrf = get_or_create_csrf_token(request)
        error_text = err.message if hasattr(err, "message") else str(err)
        return templates.TemplateResponse(
            request=request,
            name="admin/room_form.html",
            context={
                "request": request,
                "current_user": admin_user,
                "room": room,
                "csrf_token": csrf,
                "active_page": "admin_rooms",
                "error_msg": error_text,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.post("/rooms/{room_id}/toggle-status")
async def admin_room_toggle_status(
    room_id: uuid.UUID,
    request: Request,
    csrf_token: str = Form(...),
    admin_user: User = Depends(require_admin),
    room_service: RoomService = Depends(get_room_service),
):
    await validate_csrf(request)
    room_service.toggle_room_status(room_id, admin_user)
    return RedirectResponse(url="/admin/rooms", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/reservations", response_class=HTMLResponse)
async def admin_reservations_list(
    request: Request,
    admin_user: User = Depends(require_admin),
    reservation_service: ReservationService = Depends(get_reservation_service),
    room_service: RoomService = Depends(get_room_service),
    user_service: UserService = Depends(get_user_service),
):
    all_res = reservation_service.list_all_reservations()

    enriched = []
    for r in all_res:
        room = room_service.room_repo.get_by_id(r.room_id)
        u = user_service.user_repo.get_by_id(r.user_id)
        enriched.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_name": u.name if u else "Desconocido",
            "user_email": u.email if u else "N/A",
            "room_name": room.name if room else "Sala Desconocida",
            "start_datetime": r.start_datetime,
            "end_datetime": r.end_datetime,
            "status": r.status,
            "cancelled_at": r.cancelled_at,
        })

    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request=request,
        name="admin/reservations.html",
        context={
            "request": request,
            "current_user": admin_user,
            "csrf_token": csrf_token,
            "reservations": enriched,
            "active_page": "admin_reservations",
        },
    )


@router.post("/reservations/{reservation_id}/cancel")
async def admin_cancel_reservation(
    reservation_id: uuid.UUID,
    request: Request,
    csrf_token: str = Form(...),
    admin_user: User = Depends(require_admin),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    await validate_csrf(request)
    reservation_service.cancel_reservation(reservation_id, admin_user)
    return RedirectResponse(url="/admin/reservations", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/users", response_class=HTMLResponse)
async def admin_users_list(
    request: Request,
    admin_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    users = user_service.list_all()
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "request": request,
            "current_user": admin_user,
            "csrf_token": csrf_token,
            "users": users,
            "active_page": "admin_users",
        },
    )


@router.get("/audit", response_class=HTMLResponse)
async def admin_audit_logs(
    request: Request,
    admin_user: User = Depends(require_admin),
    audit_service: AuditService = Depends(get_audit_service),
):
    logs = audit_service.list_events(limit=200)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request=request,
        name="admin/audit.html",
        context={
            "request": request,
            "current_user": admin_user,
            "csrf_token": csrf_token,
            "logs": logs,
            "active_page": "admin_audit",
        },
    )
