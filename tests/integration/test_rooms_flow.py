"""Integration tests for room browsing, creation and status toggling."""

import unittest
from fastapi.testclient import TestClient

from app.audit.repository import in_memory_audit_repo
from app.auth.repository import in_memory_session_repo
from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.core.security import generate_csrf_token
from app.main import app
from app.reservations.repository import in_memory_reservation_repo
from app.rooms.repository import in_memory_room_repo
from app.rooms.schemas import RoomCreate
from app.rooms.service import RoomService
from app.users.repository import in_memory_user_repo
from app.users.service import UserService


class TestRoomsFlow(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_room_repo.clear()
        in_memory_reservation_repo.clear()
        in_memory_audit_repo.clear()
        in_memory_session_repo.clear()
        login_rate_limiter.reset_all()

        self.client = TestClient(app)
        user_service = UserService(in_memory_user_repo)
        self.admin = user_service.create_admin_user("Admin", "admin@test.com", "AdminPass123!")

        # Create session for admin
        from app.auth.service import AuthService
        from app.audit.service import AuditService
        auth_service = AuthService(in_memory_user_repo, in_memory_session_repo, AuditService(in_memory_audit_repo))
        _, session = auth_service.authenticate_and_login("admin@test.com", "AdminPass123!")
        self.admin_session_id = session.id

    def test_admin_create_and_toggle_room(self):
        csrf = generate_csrf_token(self.admin_session_id)
        # Create room via admin POST
        resp = self.client.post(
            "/admin/rooms",
            data={
                "name": "Integration Room",
                "location": "3rd Floor",
                "capacity": "15",
                "description": "Smart Board equipped",
                "csrf_token": csrf,
            },
            cookies={settings.session_cookie_name: self.admin_session_id},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 303)

        # Check room appears in active rooms
        resp_rooms = self.client.get(
            "/rooms",
            cookies={settings.session_cookie_name: self.admin_session_id},
        )
        self.assertEqual(resp_rooms.status_code, 200)
        self.assertIn("Integration Room", resp_rooms.text)


if __name__ == "__main__":
    unittest.main()
