"""PS-01: Bloqueo de acceso administrativo no autorizado (CA-01, RS-01, RS-03, RS-10).

Objetivo: Comprobar que un visitante o usuario con rol USER no pueda ejecutar funciones administrativas.
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


class TestPS01AdminAccess(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_audit_repo.clear()
        in_memory_session_repo.clear()
        login_rate_limiter.reset_all()

        self.client = TestClient(app)
        audit_service = AuditService(in_memory_audit_repo)
        self.user_service = UserService(in_memory_user_repo)
        auth_service = AuthService(in_memory_user_repo, in_memory_session_repo, audit_service)

        self.user = self.user_service.register_user(
            UserCreate(name="Regular User", email="user@test.com", password="Password2026!", password_confirmation="Password2026!")
        )
        self.admin = self.user_service.create_admin_user("Admin User", "admin@test.com", "AdminPass2026!")

        _, self.user_session = auth_service.authenticate_and_login("user@test.com", "Password2026!")
        _, self.admin_session = auth_service.authenticate_and_login("admin@test.com", "AdminPass2026!")

    def test_ps01_unauthenticated_visitor_blocked_from_admin(self):
        """1. Visitante sin sesión es redirigido o rechazado (401/307)."""
        admin_routes = ["/admin", "/admin/rooms", "/admin/reservations", "/admin/users", "/admin/audit"]
        for route in admin_routes:
            resp = self.client.get(route, follow_redirects=False)
            self.assertIn(resp.status_code, [307, 401], f"Route {route} was not blocked for visitor")

    def test_ps01_regular_user_blocked_with_403_forbidden(self):
        """2. Usuario con rol USER recibe HTTP 403 Forbidden al acceder a rutas administrativas."""
        admin_routes = ["/admin", "/admin/rooms", "/admin/reservations", "/admin/users", "/admin/audit"]
        for route in admin_routes:
            resp = self.client.get(route, cookies={settings.session_cookie_name: self.user_session.id})
            self.assertEqual(resp.status_code, 403, f"Regular user was not denied with 403 on {route}")

    def test_ps01_admin_user_granted_access(self):
        """3. Usuario con rol ADMIN accede satisfactoriamente a las rutas administrativas."""
        admin_routes = ["/admin", "/admin/rooms", "/admin/reservations", "/admin/users", "/admin/audit"]
        for route in admin_routes:
            resp = self.client.get(route, cookies={settings.session_cookie_name: self.admin_session.id})
            self.assertEqual(resp.status_code, 200, f"Admin could not access {route}")


if __name__ == "__main__":
    unittest.main()
