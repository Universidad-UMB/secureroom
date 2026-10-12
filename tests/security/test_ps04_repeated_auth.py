"""PS-04: Resistencia a intentos repetidos de autenticación (CA-04, RS-01, RS-02, RS-10, RS-12).

Objetivo: Comprobar que múltiples intentos inválidos queden trazados y activen rate limiting.
"""

import unittest
from fastapi.testclient import TestClient

from app.audit.repository import in_memory_audit_repo
from app.audit.service import AuditService
from app.auth.repository import in_memory_session_repo
from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.core.security import generate_csrf_token
from app.main import app
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestPS04RepeatedAuth(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_audit_repo.clear()
        in_memory_session_repo.clear()
        login_rate_limiter.reset_all()

        self.client = TestClient(app)
        user_service = UserService(in_memory_user_repo)
        self.user = user_service.register_user(
            UserCreate(name="Target User", email="target@test.com", password="CorrectPassword123!", password_confirmation="CorrectPassword123!")
        )

    def test_ps04_failed_login_audited_and_rate_limited(self):
        # Obtain anon CSRF cookie
        self.client.get("/login")
        anon_cookie = self.client.cookies.get("secureroom_csrf_anon")
        csrf = generate_csrf_token(anon_cookie)

        # Send 5 failed attempts
        for i in range(5):
            resp = self.client.post(
                "/login",
                data={"email": "target@test.com", "password": f"WrongPass{i}", "csrf_token": csrf},
            )
            self.assertEqual(resp.status_code, 400)
            self.assertIn("Credenciales inválidas", resp.text)

        # 6th attempt should be blocked by rate limiter
        resp_blocked = self.client.post(
            "/login",
            data={"email": "target@test.com", "password": "WrongPasswordX", "csrf_token": csrf},
        )
        self.assertEqual(resp_blocked.status_code, 400)
        self.assertIn("Demasiados intentos fallidos", resp_blocked.text)

        # Check audit logs recorded LOGIN_FAILED events
        audit_events = in_memory_audit_repo.list_all()
        login_fails = [ev for ev in audit_events if ev.action == "LOGIN_FAILED"]
        self.assertGreaterEqual(len(login_fails), 5)


if __name__ == "__main__":
    unittest.main()
