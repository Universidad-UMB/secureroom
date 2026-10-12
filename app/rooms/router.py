"""User rooms router (list active rooms and view details)."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import get_current_user
from app.core.csrf import get_or_create_csrf_token
from app.core.exceptions import ResourceNotFoundError
from app.database.deps import get_room_service
from app.rooms.service import RoomService
from app.users.models import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/rooms", response_class=HTMLResponse)
async def list_active_rooms(
    request: Request,
    current_user: User = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
):
    rooms = room_service.list_active_rooms()
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request=request,
        name="user/rooms_list.html",
        context={
            "request": request,
            "current_user": current_user,
            "rooms": rooms,
            "csrf_token": csrf_token,
            "active_page": "rooms",
        },
    )


@router.get("/rooms/{room_id}", response_class=HTMLResponse)
async def room_detail(
    room_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    room_service: RoomService = Depends(get_room_service),
):
    try:
        room = room_service.get_room(room_id)
    except ResourceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala no encontrada.")

    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request=request,
        name="user/room_detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "room": room,
            "csrf_token": csrf_token,
            "active_page": "rooms",
        },
    )
