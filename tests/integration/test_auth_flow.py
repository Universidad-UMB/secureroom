"""Integration tests for authentication flows (Register, Login, Session, Logout)."""

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
from app.users.repository import in_memory_user_repo


class TestAuthFlow(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_room_repo.clear()
        in_memory_reservation_repo.clear()
        in_memory_audit_repo.clear()
        in_memory_session_repo.clear()
        login_rate_limiter.reset_all()
        self.client = TestClient(app)

    def test_short_password_returns_friendly_validation_message(self):
        self.client.get("/register")
        anon_cookie = self.client.cookies.get("secureroom_csrf_anon")
        csrf_token = generate_csrf_token(anon_cookie)

        response = self.client.post(
            "/register",
            data={
                "name": "Integration User",
                "email": "short-password@test.com",
                "password": "heidy10",
                "password_confirmation": "heidy10",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("La contraseña debe tener al menos 10 caracteres.", response.text)
        self.assertNotIn("pydantic.dev", response.text)

    def test_full_registration_and_login_flow(self):
        """User registers, logs in, accesses dashboard, and logs out."""
        # 1. Get register page
        self.client.get("/register")
        anon_cookie = self.client.cookies.get("secureroom_csrf_anon")
        self.assertIsNotNone(anon_cookie)
        csrf_token = generate_csrf_token(anon_cookie)

        # 2. Submit valid registration
        resp_reg = self.client.post(
            "/register",
            data={
                "name": "Integration User",
                "email": "integration@test.com",
                "password": "IntegrationPassword2026!",
                "password_confirmation": "IntegrationPassword2026!",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(resp_reg.status_code, 303)
        self.assertIn("/login?registered=1", resp_reg.headers["location"])

        # 3. Submit login with client's active anon cookie
        anon_cookie_login = self.client.cookies.get("secureroom_csrf_anon")
        csrf_login = generate_csrf_token(anon_cookie_login)

        resp_login = self.client.post(
            "/login",
            data={
                "email": "integration@test.com",
                "password": "IntegrationPassword2026!",
                "csrf_token": csrf_login,
            },
            follow_redirects=False,
        )
        self.assertEqual(resp_login.status_code, 303)
        self.assertEqual(resp_login.headers["location"], "/dashboard")

        # Session cookie must be set
        session_cookie = self.client.cookies.get(settings.session_cookie_name)
        self.assertIsNotNone(session_cookie)

        # 4. Access dashboard with session
        resp_dash = self.client.get("/dashboard")
        self.assertEqual(resp_dash.status_code, 200)
        self.assertIn("Integration User", resp_dash.text)

        # 5. Logout
        csrf_logout = generate_csrf_token(session_cookie)
        resp_logout = self.client.post(
            "/logout",
            data={"csrf_token": csrf_logout},
            follow_redirects=False,
        )
        self.assertEqual(resp_logout.status_code, 303)

        # Session must be deleted server-side
        self.assertIsNone(in_memory_session_repo.get_by_id(session_cookie))

        # Re-accessing dashboard must redirect to login
        resp_retry = self.client.get("/dashboard", follow_redirects=False)
        self.assertIn(resp_retry.status_code, [307, 401])


if __name__ == "__main__":
    unittest.main()
