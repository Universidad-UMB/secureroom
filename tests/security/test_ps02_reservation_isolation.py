"""PS-02: Aislamiento de reservas entre usuarios / IDOR (CA-02, RS-04, RS-05, RS-10).

Objetivo: Comprobar que un usuario no pueda consultar ni cancelar reservas de otro usuario.
"""

import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.audit.repository import in_memory_audit_repo
from app.audit.service import AuditService
from app.auth.repository import in_memory_session_repo
from app.auth.service import AuthService
from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.core.security import generate_csrf_token
from app.main import app
from app.reservations.models import Reservation
from app.reservations.repository import in_memory_reservation_repo
from app.reservations.schemas import ReservationCreate
from app.reservations.service import ReservationService
from app.rooms.repository import in_memory_room_repo
from app.rooms.schemas import RoomCreate
from app.rooms.service import RoomService
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestPS02ReservationIsolation(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_room_repo.clear()
        in_memory_reservation_repo.clear()
        in_memory_audit_repo.clear()
        in_memory_session_repo.clear()
        login_rate_limiter.reset_all()

        self.client = TestClient(app)
        audit_service = AuditService(in_memory_audit_repo)
        user_service = UserService(in_memory_user_repo)
        room_service = RoomService(in_memory_room_repo, audit_service)
        auth_service = AuthService(in_memory_user_repo, in_memory_session_repo, audit_service)
        self.reservation_service = ReservationService(
            in_memory_reservation_repo, in_memory_room_repo, audit_service
        )

        self.admin = user_service.create_admin_user("Admin", "admin@test.com", "AdminPass2026!")
        self.user_a = user_service.register_user(
            UserCreate(name="User A", email="user_a@test.com", password="Password2026!", password_confirmation="Password2026!")
        )
        self.user_b = user_service.register_user(
            UserCreate(name="User B", email="user_b@test.com", password="Password2026!", password_confirmation="Password2026!")
        )
        self.room = room_service.create_room(
            RoomCreate(name="Private Room", location="Floor 2", capacity=6), self.admin
        )

        _, self.session_a = auth_service.authenticate_and_login("user_a@test.com", "Password2026!")
        _, self.session_b = auth_service.authenticate_and_login("user_b@test.com", "Password2026!")

        # Create active reservation owned by User B
        start_b = datetime.now(timezone.utc) + timedelta(days=2)
        end_b = start_b + timedelta(hours=1)
        self.res_b = self.reservation_service.create_reservation(
            ReservationCreate(room_id=self.room.id, start_datetime=start_b, end_datetime=end_b),
            self.user_b,
        )

    def test_ps02_user_a_cannot_view_user_b_reservations(self):
        """User A querying /reservations does NOT see User B's reservation."""
        resp = self.client.get(
            "/reservations",
            cookies={settings.session_cookie_name: self.session_a.id},
        )
        self.assertEqual(resp.status_code, 200)
        # Reservation B must not appear in User A's list
        self.assertNotIn(str(self.res_b.id), resp.text)

    def test_ps02_user_a_cannot_cancel_user_b_reservation(self):
        """User A attempting to POST cancel User B's reservation is rejected with 403 Forbidden."""
        csrf_a = generate_csrf_token(self.session_a.id)

        resp = self.client.post(
            f"/reservations/{self.res_b.id}/cancel",
            data={"csrf_token": csrf_a},
            cookies={settings.session_cookie_name: self.session_a.id},
        )
        self.assertEqual(resp.status_code, 403)

        # Confirm reservation B remains ACTIVE
        check_b = in_memory_reservation_repo.get_by_id(self.res_b.id)
        self.assertEqual(check_b.status, "ACTIVE")


if __name__ == "__main__":
    unittest.main()
