"""Integration tests for administrative supervisor views and audit logs."""

import unittest
from fastapi.testclient import TestClient

from app.audit.repository import in_memory_audit_repo
from app.audit.service import AuditService
from app.auth.repository import in_memory_session_repo
from app.auth.service import AuthService
from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.main import app
from app.reservations.repository import in_memory_reservation_repo
from app.rooms.repository import in_memory_room_repo
from app.users.repository import in_memory_user_repo
from app.users.service import UserService


class TestAdminFlow(unittest.TestCase):
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
        auth_service = AuthService(in_memory_user_repo, in_memory_session_repo, audit_service)

        self.admin = user_service.create_admin_user("Admin Super", "admin_super@test.com", "AdminPass123!")
        _, session = auth_service.authenticate_and_login("admin_super@test.com", "AdminPass123!")
        self.admin_session_id = session.id

    def test_admin_dashboard_and_audit_access(self):
        cookies = {settings.session_cookie_name: self.admin_session_id}

        # Dashboard access
        resp_dash = self.client.get("/admin", cookies=cookies)
        self.assertEqual(resp_dash.status_code, 200)
        self.assertIn("Panel de Control Administrativo", resp_dash.text)

        # Users list access
        resp_users = self.client.get("/admin/users", cookies=cookies)
        self.assertEqual(resp_users.status_code, 200)
        self.assertIn("admin_super@test.com", resp_users.text)

        # Audit logs access
        resp_audit = self.client.get("/admin/audit", cookies=cookies)
        self.assertEqual(resp_audit.status_code, 200)
        self.assertIn("Registro de Auditoría de Seguridad", resp_audit.text)


if __name__ == "__main__":
    unittest.main()
