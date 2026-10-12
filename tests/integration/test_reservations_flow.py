"""Integration tests for reservation creation, availability check, and cancellation."""

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
from app.reservations.repository import in_memory_reservation_repo
from app.rooms.models import Room
from app.rooms.repository import in_memory_room_repo
from app.rooms.schemas import RoomCreate
from app.rooms.service import RoomService
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestReservationsFlow(unittest.TestCase):
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

        self.admin = user_service.create_admin_user("Admin", "admin@test.com", "AdminPass123!")
        self.user = user_service.register_user(
            UserCreate(name="User", email="user@test.com", password="UserPass123!", password_confirmation="UserPass123!")
        )
        self.room = room_service.create_room(
            RoomCreate(name="Reservations Test Room", location="Floor 2", capacity=8), self.admin
        )

        _, session = auth_service.authenticate_and_login("user@test.com", "UserPass123!")
        self.user_session_id = session.id

    def test_create_and_cancel_reservation_flow(self):
        csrf = generate_csrf_token(self.user_session_id)
        start = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT10:00")
        end = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT11:00")

        # Submit new reservation
        resp = self.client.post(
            "/reservations",
            data={
                "room_id": str(self.room.id),
                "start_datetime": start,
                "end_datetime": end,
                "csrf_token": csrf,
            },
            cookies={settings.session_cookie_name: self.user_session_id},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 303)

        # Check in my reservations
        resp_list = self.client.get(
            "/reservations",
            cookies={settings.session_cookie_name: self.user_session_id},
        )
        self.assertEqual(resp_list.status_code, 200)
        self.assertIn("Reservations Test Room", resp_list.text)

        # Get reservation ID from database
        all_res = in_memory_reservation_repo.list_by_user(self.user.id)
        self.assertEqual(len(all_res), 1)
        res_id = all_res[0].id

        # Cancel reservation
        resp_cancel = self.client.post(
            f"/reservations/{res_id}/cancel",
            data={"csrf_token": csrf},
            cookies={settings.session_cookie_name: self.user_session_id},
            follow_redirects=False,
        )
        self.assertEqual(resp_cancel.status_code, 303)

        # Status updated to CANCELLED
        updated_res = in_memory_reservation_repo.get_by_id(res_id)
        self.assertEqual(updated_res.status, "CANCELLED")


if __name__ == "__main__":
    unittest.main()
