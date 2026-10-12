"""Reservation service enforcing domain and business rules (RB-06, RB-09 to RB-20, RS-04, RS-14)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.audit.service import AuditService
from app.core.exceptions import (
    AuthorizationError,
    ReservationConflictError,
    ResourceNotFoundError,
    ValidationError,
)
from app.reservations.models import Reservation
from app.reservations.repository import ReservationRepository
from app.reservations.schemas import ReservationCreate
from app.rooms.repository import RoomRepository
from app.users.models import User


class ReservationService:
    def __init__(
        self,
        reservation_repo: ReservationRepository,
        room_repo: RoomRepository,
        audit_service: AuditService,
    ):
        self.reservation_repo = reservation_repo
        self.room_repo = room_repo
        self.audit_service = audit_service

    def create_reservation(
        self, data: ReservationCreate, current_user: User
    ) -> Reservation:
        """Creates a new reservation.

        Enforces:
        - RB-06: Only active rooms can be reserved.
        - RB-09 / RS-05: User is set strictly from authenticated session.
        - RB-10: start_datetime < end_datetime.
        - RB-11: start_datetime must be in the future.
        - RB-12 / RS-14: No overlapping active reservations for the same room.
        - RB-14: Initial status is always 'ACTIVE'.
        """
        room = self.room_repo.get_by_id(data.room_id)
        if not room:
            raise ResourceNotFoundError("La sala seleccionada no existe.")

        if not room.is_active:
            raise ValidationError("No es posible reservar una sala inactiva.")

        # Validate start < end (RB-10)
        if data.start_datetime >= data.end_datetime:
            raise ValidationError("La hora de inicio debe ser anterior a la de finalización.")

        # Validate future start time (RB-11)
        now = datetime.now(timezone.utc)
        start_utc = (
            data.start_datetime
            if data.start_datetime.tzinfo is not None
            else data.start_datetime.replace(tzinfo=timezone.utc)
        )
        if start_utc < now:
            raise ValidationError("No se pueden crear reservas en el pasado.")

        new_reservation = Reservation(
            id=uuid.uuid4(),
            user_id=current_user.id,  # Server-assigned owner (RB-09, RS-05)
            room_id=data.room_id,
            start_datetime=data.start_datetime,
            end_datetime=data.end_datetime,
            status="ACTIVE",  # Server-assigned status (RB-14, RS-05)
            created_at=datetime.now(timezone.utc),
            cancelled_at=None,
            cancelled_by=None,
        )

        # Atomic insertion with concurrency lock (RS-14, CA-08, FASE 4)
        persisted = self.reservation_repo.create_atomic(new_reservation)

        self.audit_service.log_event(
            action="RESERVATION_CREATED",
            resource_type="RESERVATION",
            resource_id=str(persisted.id),
            user_id=current_user.id,
            result="SUCCESS",
        )

        return persisted

    def check_availability(
        self, room_id: uuid.UUID, start_datetime: datetime, end_datetime: datetime
    ) -> bool:
        """Checks if room is active and free during the specified window (RF-13, RB-18)."""
        room = self.room_repo.get_by_id(room_id)
        if not room or not room.is_active:
            return False

        if start_datetime >= end_datetime:
            return False

        overlapping = self.reservation_repo.find_active_overlapping(
            room_id=room_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        return len(overlapping) == 0

    def get_by_id(self, reservation_id: uuid.UUID) -> Reservation:
        res = self.reservation_repo.get_by_id(reservation_id)
        if not res:
            raise ResourceNotFoundError("La reserva no fue encontrada.")
        return res

    def list_user_reservations(self, user_id: uuid.UUID) -> List[Reservation]:
        """Lists only reservations belonging to the requesting user (RB-20, RS-04)."""
        return self.reservation_repo.list_by_user(user_id)

    def list_all_reservations(self) -> List[Reservation]:
        """Lists all reservations for administrative view (RF-21)."""
        return self.reservation_repo.list_all()

    def cancel_reservation(
        self, reservation_id: uuid.UUID, current_user: User
    ) -> Reservation:
        """Cancels a reservation.

        Enforces:
        - RB-15: Logical cancellation (status=CANCELLED, cancelled_at=now, cancelled_by=current_user).
        - RB-16: Regular user can only cancel their own reservation (RS-04, CA-02).
        - RB-17: Admin can cancel any active reservation.
        - RB-19: A cancelled reservation cannot be re-cancelled.
        """
        reservation = self.get_by_id(reservation_id)

        # RB-19: Already cancelled check
        if reservation.status == "CANCELLED":
            raise ValidationError("La reserva ya se encuentra cancelada.")

        # Ownership authorization check (RS-04, RB-16, RB-17, CA-02)
        if current_user.role != "ADMIN" and reservation.user_id != current_user.id:
            self.audit_service.log_event(
                action="RESERVATION_CANCEL_DENIED",
                resource_type="RESERVATION",
                resource_id=str(reservation.id),
                user_id=current_user.id,
                result="FORBIDDEN",
            )
            raise AuthorizationError("No tiene permisos para cancelar esta reserva.")

        reservation.status = "CANCELLED"
        reservation.cancelled_at = datetime.now(timezone.utc)
        reservation.cancelled_by = current_user.id

        updated = self.reservation_repo.update(reservation)

        self.audit_service.log_event(
            action="RESERVATION_CANCELLED",
            resource_type="RESERVATION",
            resource_id=str(updated.id),
            user_id=current_user.id,
            result="SUCCESS",
        )

        return updated
