"""Reservation repository with robust concurrency locking (RS-14, CA-08, FASE 4)."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import threading
import uuid

from app.core.exceptions import ReservationConflictError
from app.reservations.models import Reservation
from app.rooms.models import Room


class ReservationRepository(ABC):
    @abstractmethod
    def get_by_id(self, reservation_id: uuid.UUID) -> Optional[Reservation]:
        pass

    @abstractmethod
    def list_all(self) -> List[Reservation]:
        pass

    @abstractmethod
    def list_by_user(self, user_id: uuid.UUID) -> List[Reservation]:
        pass

    @abstractmethod
    def find_active_overlapping(
        self,
        room_id: uuid.UUID,
        start_datetime: datetime,
        end_datetime: datetime,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> List[Reservation]:
        pass

    @abstractmethod
    def create_atomic(self, reservation: Reservation) -> Reservation:
        pass

    @abstractmethod
    def update(self, reservation: Reservation) -> Reservation:
        pass


class SQLAlchemyReservationRepository(ReservationRepository):
    def __init__(self, db_session):
        self.db = db_session

    def get_by_id(self, reservation_id: uuid.UUID) -> Optional[Reservation]:
        return self.db.query(Reservation).filter(Reservation.id == reservation_id).first()

    def list_all(self) -> List[Reservation]:
        return (
            self.db.query(Reservation)
            .order_by(Reservation.start_datetime.desc())
            .all()
        )

    def list_by_user(self, user_id: uuid.UUID) -> List[Reservation]:
        return (
            self.db.query(Reservation)
            .filter(Reservation.user_id == user_id)
            .order_by(Reservation.start_datetime.desc())
            .all()
        )

    def find_active_overlapping(
        self,
        room_id: uuid.UUID,
        start_datetime: datetime,
        end_datetime: datetime,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> List[Reservation]:
        query = (
            self.db.query(Reservation)
            .filter(
                Reservation.room_id == room_id,
                Reservation.status == "ACTIVE",
                Reservation.start_datetime < end_datetime,
                Reservation.end_datetime > start_datetime,
            )
        )
        if exclude_id:
            query = query.filter(Reservation.id != exclude_id)
        return query.all()

    def create_atomic(self, reservation: Reservation) -> Reservation:
        """Atomically locks the target Room row using SELECT ... FOR UPDATE,
        re-verifies that no overlapping active reservation exists, and persists.
        Ensures strict serialization and prevents double-booking race conditions (RS-14, CA-08).
        """
        # 1. Acquire row-level lock on the room
        room = (
            self.db.query(Room)
            .filter(Room.id == reservation.room_id)
            .with_for_update()
            .first()
        )
        if not room:
            raise ReservationConflictError("La sala no existe.")

        # 2. Check for active overlaps within the locked transaction
        overlapping = self.find_active_overlapping(
            room_id=reservation.room_id,
            start_datetime=reservation.start_datetime,
            end_datetime=reservation.end_datetime,
        )
        if overlapping:
            self.db.rollback()
            raise ReservationConflictError("Existe una reserva activa solapada para esta sala.")

        # 3. Insert and commit
        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)
        return reservation

    def update(self, reservation: Reservation) -> Reservation:
        self.db.commit()
        self.db.refresh(reservation)
        return reservation


class InMemoryReservationRepository(ReservationRepository):
    """Thread-safe in-memory repository implementing atomic reservation locking."""

    def __init__(self):
        self._lock = threading.RLock()
        self._reservations = {}

    def get_by_id(self, reservation_id: uuid.UUID) -> Optional[Reservation]:
        with self._lock:
            return self._reservations.get(reservation_id)

    def list_all(self) -> List[Reservation]:
        with self._lock:
            return sorted(
                list(self._reservations.values()),
                key=lambda r: getattr(r, "start_datetime", None) or 0,
                reverse=True,
            )

    def list_by_user(self, user_id: uuid.UUID) -> List[Reservation]:
        with self._lock:
            user_res = [r for r in self._reservations.values() if r.user_id == user_id]
            return sorted(
                user_res,
                key=lambda r: getattr(r, "start_datetime", None) or 0,
                reverse=True,
            )

    def find_active_overlapping(
        self,
        room_id: uuid.UUID,
        start_datetime: datetime,
        end_datetime: datetime,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> List[Reservation]:
        with self._lock:
            results = []
            for r in self._reservations.values():
                if r.room_id != room_id:
                    continue
                if r.status != "ACTIVE":
                    continue
                if exclude_id and r.id == exclude_id:
                    continue
                # Overlap check: start < existing_end AND end > existing_start
                # Ensure comparable datetimes (naive or aware)
                r_start = r.start_datetime
                r_end = r.end_datetime
                if (r_start.tzinfo is None) != (end_datetime.tzinfo is None):
                    # Align to timezone-naive UTC for comparison if mismatched
                    r_start = r_start.replace(tzinfo=None)
                    r_end = r_end.replace(tzinfo=None)
                    start_cmp = start_datetime.replace(tzinfo=None)
                    end_cmp = end_datetime.replace(tzinfo=None)
                else:
                    start_cmp = start_datetime
                    end_cmp = end_datetime

                if start_cmp < r_end and end_cmp > r_start:
                    results.append(r)
            return results

    def create_atomic(self, reservation: Reservation) -> Reservation:
        with self._lock:
            overlaps = self.find_active_overlapping(
                room_id=reservation.room_id,
                start_datetime=reservation.start_datetime,
                end_datetime=reservation.end_datetime,
            )
            if overlaps:
                raise ReservationConflictError("Existe una reserva activa solapada para esta sala.")

            if reservation.id is None:
                reservation.id = uuid.uuid4()
            self._reservations[reservation.id] = reservation
            return reservation

    def update(self, reservation: Reservation) -> Reservation:
        with self._lock:
            self._reservations[reservation.id] = reservation
            return reservation

    def clear(self):
        with self._lock:
            self._reservations.clear()


in_memory_reservation_repo = InMemoryReservationRepository()
