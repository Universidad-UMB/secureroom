"""PS-05: Invalidación y protección de sesión (CA-05, RS-08, RS-09).

Objetivo: Comprobar que una sesión cerrada no pueda reutilizarse y las cookies estén protegidas.
"""

import unittest
from fastapi.testclient import TestClient

from app.audit.repository import in_memory_audit_repo
from app.audit.service import AuditService
from app.auth.repository import in_memory_session_repo
from app.auth.service import AuthService
from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.core.security import generate_csrf_token
from app.main import app
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestPS05SessionInvalidation(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_audit_repo.clear()
        in_memory_session_repo.clear()
        login_rate_limiter.reset_all()

        self.client = TestClient(app)
        user_service = UserService(in_memory_user_repo)
        self.user = user_service.register_user(
            UserCreate(name="Session User", email="session@test.com", password="Password2026!", password_confirmation="Password2026!")
        )

    def test_ps05_cookie_flags_and_post_logout_invalidation(self):
        # 1. Login to inspect cookie
        self.client.get("/login")
        anon = self.client.cookies.get("secureroom_csrf_anon")
        csrf = generate_csrf_token(anon)

        resp_login = self.client.post(
            "/login",
            data={"email": "session@test.com", "password": "Password2026!", "csrf_token": csrf},
            follow_redirects=False,
        )
        self.assertEqual(resp_login.status_code, 303)

        # Cookie check
        raw_cookie_header = resp_login.headers.get("set-cookie", "")
        self.assertIn("HttpOnly", raw_cookie_header)
        self.assertIn("samesite=lax", raw_cookie_header.lower())

        session_id = self.client.cookies.get(settings.session_cookie_name)
        self.assertIsNotNone(session_id)

        # 2. Access dashboard works
        resp_valid = self.client.get("/dashboard")
        self.assertEqual(resp_valid.status_code, 200)

        # 3. Logout
        csrf_logout = generate_csrf_token(session_id)
        self.client.post(
            "/logout",
            data={"csrf_token": csrf_logout},
            follow_redirects=False,
        )

        # 4. Attempt to reuse old session token on protected route
        resp_after_logout = self.client.get(
            "/dashboard",
            cookies={settings.session_cookie_name: session_id},
            follow_redirects=False,
        )
        self.assertIn(resp_after_logout.status_code, [307, 401])


if __name__ == "__main__":
    unittest.main()
