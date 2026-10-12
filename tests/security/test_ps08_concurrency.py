"""PS-08: Concurrencia y prevención de doble reserva (CA-08, RS-14, FASE 4).

Objetivo: Comprobar que solicitudes concurrentes para la misma sala y horario solapado
garanticen como máximo una reserva válida (ACTIVE) y la otra sea rechazada.
"""

import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import uuid

from app.audit.repository import in_memory_audit_repo
from app.audit.service import AuditService
from app.core.exceptions import ReservationConflictError
from app.reservations.models import Reservation
from app.reservations.repository import in_memory_reservation_repo
from app.reservations.schemas import ReservationCreate
from app.reservations.service import ReservationService
from app.rooms.models import Room
from app.rooms.repository import in_memory_room_repo
from app.rooms.schemas import RoomCreate
from app.rooms.service import RoomService
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestPS08Concurrency(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_room_repo.clear()
        in_memory_reservation_repo.clear()
        in_memory_audit_repo.clear()

        audit_service = AuditService(in_memory_audit_repo)
        user_service = UserService(in_memory_user_repo)
        room_service = RoomService(in_memory_room_repo, audit_service)
        self.reservation_service = ReservationService(
            in_memory_reservation_repo, in_memory_room_repo, audit_service
        )

        self.admin = user_service.create_admin_user("Admin", "admin@test.com", "AdminPass2026!")
        self.user1 = user_service.register_user(
            UserCreate(name="User 1", email="user1@test.com", password="Password2026!", password_confirmation="Password2026!")
        )
        self.user2 = user_service.register_user(
            UserCreate(name="User 2", email="user2@test.com", password="Password2026!", password_confirmation="Password2026!")
        )
        self.room = room_service.create_room(
            RoomCreate(name="Contested Room", location="L1", capacity=10), self.admin
        )

    def test_ps08_concurrent_reservation_attempts_for_same_slot(self):
        """Simulates 10 concurrent threads attempting to reserve the exact same room and slot."""
        start = datetime.now(timezone.utc) + timedelta(days=5, hours=9)
        end = start + timedelta(hours=2)

        data = ReservationCreate(room_id=self.room.id, start_datetime=start, end_datetime=end)

        results = []
        errors = []

        def attempt_booking(user):
            try:
                res = self.reservation_service.create_reservation(data, user)
                results.append(res)
            except ReservationConflictError as e:
                errors.append(e)

        users = [self.user1, self.user2] * 5  # 10 attempts

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(attempt_booking, users))

        # Exactly ONE reservation must succeed!
        self.assertEqual(len(results), 1, f"Expected exactly 1 success, got {len(results)}")
        # All other 9 must fail with conflict error!
        self.assertEqual(len(errors), 9, f"Expected 9 conflict errors, got {len(errors)}")

        # Verify database has exactly 1 ACTIVE reservation for this room
        active_in_db = in_memory_reservation_repo.find_active_overlapping(self.room.id, start, end)
        self.assertEqual(len(active_in_db), 1)


if __name__ == "__main__":
    unittest.main()
