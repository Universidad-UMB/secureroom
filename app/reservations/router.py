"""User reservations and dashboard router."""

from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import get_current_user
from app.core.csrf import get_or_create_csrf_token, validate_csrf
from app.core.exceptions import (
    AuthorizationError,
    ReservationConflictError,
    ResourceNotFoundError,
    ValidationError,
)
from app.database.deps import get_reservation_service, get_room_service
from app.reservations.schemas import ReservationCreate
from app.reservations.service import ReservationService
from app.rooms.service import RoomService
from app.users.models import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
    room_service: RoomService = Depends(get_room_service),
):
    user_reservations = reservation_service.list_user_reservations(current_user.id)
    active_rooms = room_service.list_active_rooms()

    active_user_res = [r for r in user_reservations if r.status == "ACTIVE"]

    # Enrich with room name
    enriched_res = []
    for r in active_user_res:
        room = room_service.room_repo.get_by_id(r.room_id)
        enriched_res.append({
            "id": r.id,
            "room_id": r.room_id,
            "room_name": room.name if room else "Sala Desconocida",
            "start_datetime": r.start_datetime,
            "end_datetime": r.end_datetime,
            "status": r.status,
        })

    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        "user/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "csrf_token": csrf_token,
            "active_page": "dashboard",
            "active_reservations_count": len(active_user_res),
            "active_rooms_count": len(active_rooms),
            "next_reservations": enriched_res[:5],
        },
    )


@router.get("/reservations", response_class=HTMLResponse)
async def list_my_reservations(
    request: Request,
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
    room_service: RoomService = Depends(get_room_service),
):
    reservations = reservation_service.list_user_reservations(current_user.id)

    enriched = []
    for r in reservations:
        room = room_service.room_repo.get_by_id(r.room_id)
        enriched.append({
            "id": r.id,
            "room_name": room.name if room else "Sala Desconocida",
            "start_datetime": r.start_datetime,
            "end_datetime": r.end_datetime,
            "status": r.status,
            "cancelled_at": r.cancelled_at,
        })

    csrf_token = get_or_create_csrf_token(request)
    created = request.query_params.get("created")
    cancelled = request.query_params.get("cancelled")
    success_msg = None
    if created:
        success_msg = "Reserva creada exitosamente."
    elif cancelled:
        success_msg = "Reserva cancelada correctamente."

    return templates.TemplateResponse(
        "user/reservations_list.html",
        {
            "request": request,
            "current_user": current_user,
            "reservations": enriched,
            "csrf_token": csrf_token,
            "active_page": "reservations",
            "success_msg": success_msg,
            "error_msg": None,
        },
    )


@router.get("/reservations/new", response_class=HTMLResponse)
async def new_reservation_page(
    request: Request,
    room_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
):
    rooms = room_service.list_active_rooms()
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        "user/reservation_new.html",
        {
            "request": request,
            "current_user": current_user,
            "rooms": rooms,
            "selected_room_id": room_id,
            "csrf_token": csrf_token,
            "active_page": "new_reservation",
            "error_msg": None,
            "str": str,
        },
    )


@router.post("/reservations", response_class=HTMLResponse)
async def create_reservation_submit(
    request: Request,
    room_id: str = Form(...),
    start_datetime: str = Form(...),
    end_datetime: str = Form(...),
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
    room_service: RoomService = Depends(get_room_service),
):
    await validate_csrf(request)

    try:
        room_uuid = uuid.UUID(room_id)
        start_dt = datetime.fromisoformat(start_datetime)
        end_dt = datetime.fromisoformat(end_datetime)

        data = ReservationCreate(
            room_id=room_uuid,
            start_datetime=start_dt,
            end_datetime=end_dt,
        )

        reservation_service.create_reservation(data, current_user)
        return RedirectResponse(url="/reservations?created=1", status_code=status.HTTP_303_SEE_OTHER)

    except (ValueError, ValidationError, ReservationConflictError, ResourceNotFoundError) as err:
        rooms = room_service.list_active_rooms()
        csrf = get_or_create_csrf_token(request)
        error_text = err.message if hasattr(err, "message") else str(err)

        return templates.TemplateResponse(
            "user/reservation_new.html",
            {
                "request": request,
                "current_user": current_user,
                "rooms": rooms,
                "selected_room_id": room_id,
                "csrf_token": csrf,
                "active_page": "new_reservation",
                "error_msg": error_text,
                "default_start": start_datetime,
                "default_end": end_datetime,
                "str": str,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.post("/reservations/{reservation_id}/cancel")
async def cancel_reservation_submit(
    reservation_id: uuid.UUID,
    request: Request,
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    await validate_csrf(request)

    try:
        reservation_service.cancel_reservation(reservation_id, current_user)
        return RedirectResponse(url="/reservations?cancelled=1", status_code=status.HTTP_303_SEE_OTHER)
    except (AuthorizationError, ValidationError, ResourceNotFoundError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if isinstance(err, ValidationError) else status.HTTP_403_FORBIDDEN,
            detail=err.message,
        )


@router.get("/api/availability")
async def check_availability_api(
    room_id: uuid.UUID,
    start: str,
    end: str,
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    try:
        # Parse ISO datetimes
        start_clean = start.replace("Z", "+00:00")
        end_clean = end.replace("Z", "+00:00")
        start_dt = datetime.fromisoformat(start_clean)
        end_dt = datetime.fromisoformat(end_clean)

        is_avail = reservation_service.check_availability(
            room_id=room_id,
            start_datetime=start_dt,
            end_datetime=end_dt,
        )
        return JSONResponse({"available": is_avail})
    except Exception as err:
        return JSONResponse({"available": False, "error": str(err)}, status_code=400)
