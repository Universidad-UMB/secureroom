"""PS-06: Protección contra SQL Injection (CA-06, RS-06, RS-07).

Objetivo: Comprobar que entradas con cargas maliciosas SQL no alteren las consultas.
"""

import unittest
from fastapi.testclient import TestClient

from app.audit.repository import in_memory_audit_repo
from app.auth.repository import in_memory_session_repo
from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.core.security import generate_csrf_token
from app.main import app
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestPS06SQLInjection(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_audit_repo.clear()
        in_memory_session_repo.clear()
        login_rate_limiter.reset_all()

        self.client = TestClient(app)
        user_service = UserService(in_memory_user_repo)
        self.user = user_service.register_user(
            UserCreate(name="Target User", email="target@test.com", password="Password2026!", password_confirmation="Password2026!")
        )

    def test_ps06_login_sqli_payloads_do_not_bypass_authentication(self):
        """Classic SQL Injection payloads in login form must be rejected as invalid credentials."""
        self.client.get("/login")
        anon = self.client.cookies.get("secureroom_csrf_anon")
        csrf = generate_csrf_token(anon)

        payloads = [
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT 1, 'admin', 'hash'--",
            "target@test.com' OR 1=1--",
            "'; DROP TABLE users;--",
        ]

        for payload in payloads:
            resp = self.client.post(
                "/login",
                data={"email": payload, "password": "anypassword", "csrf_token": csrf},
            )
            self.assertEqual(resp.status_code, 400)
            self.assertIn("Credenciales inválidas", resp.text)
            # Ensure no active session was created
            self.assertIsNone(self.client.cookies.get(settings.session_cookie_name))


if __name__ == "__main__":
    unittest.main()
