"""Service layer for Room management."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.audit.service import AuditService
from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.rooms.models import Room
from app.rooms.repository import RoomRepository
from app.rooms.schemas import RoomCreate, RoomUpdate
from app.users.models import User


class RoomService:
    def __init__(self, room_repo: RoomRepository, audit_service: AuditService):
        self.room_repo = room_repo
        self.audit_service = audit_service

    def create_room(self, data: RoomCreate, admin_user: User) -> Room:
        """Creates a new room and records audit log (RF-09, RB-08, RS-10)."""
        if data.capacity <= 0:
            raise ValidationError("La capacidad de la sala debe ser mayor a cero.")

        new_room = Room(
            id=uuid.uuid4(),
            name=data.name,
            location=data.location,
            capacity=data.capacity,
            description=data.description,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        room = self.room_repo.create(new_room)

        self.audit_service.log_event(
            action="ROOM_CREATED",
            resource_type="ROOM",
            resource_id=str(room.id),
            user_id=admin_user.id,
            result="SUCCESS",
        )

        return room

    def update_room(self, room_id: uuid.UUID, data: RoomUpdate, admin_user: User) -> Room:
        """Updates room details (RF-10, RS-10)."""
        room = self.get_room(room_id)

        if data.capacity <= 0:
            raise ValidationError("La capacidad de la sala debe ser mayor a cero.")

        room.name = data.name
        room.location = data.location
        room.capacity = data.capacity
        room.description = data.description
        room.updated_at = datetime.now(timezone.utc)

        updated = self.room_repo.update(room)

        self.audit_service.log_event(
            action="ROOM_UPDATED",
            resource_type="ROOM",
            resource_id=str(room.id),
            user_id=admin_user.id,
            result="SUCCESS",
        )

        return updated

    def toggle_room_status(self, room_id: uuid.UUID, admin_user: User) -> Room:
        """Toggles room active state without physical deletion (RF-11, RB-07, RS-10)."""
        room = self.get_room(room_id)
        room.is_active = not room.is_active
        room.updated_at = datetime.now(timezone.utc)

        updated = self.room_repo.update(room)

        action = "ROOM_ENABLED" if updated.is_active else "ROOM_DISABLED"
        self.audit_service.log_event(
            action=action,
            resource_type="ROOM",
            resource_id=str(room.id),
            user_id=admin_user.id,
            result="SUCCESS",
        )

        return updated

    def get_room(self, room_id: uuid.UUID) -> Room:
        """Retrieves a room by ID or raises ResourceNotFoundError (RF-08)."""
        room = self.room_repo.get_by_id(room_id)
        if not room:
            raise ResourceNotFoundError("La sala solicitada no existe.")
        return room

    def list_active_rooms(self) -> List[Room]:
        """Lists active rooms for public/user view (RF-07, RB-06)."""
        return self.room_repo.list_active()

    def list_all_rooms(self) -> List[Room]:
        """Lists all rooms for administrative management (RF-07)."""
        return self.room_repo.list_all()
