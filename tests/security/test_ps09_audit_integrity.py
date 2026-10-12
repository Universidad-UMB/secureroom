"""PS-09: Integridad de auditoría (CA-09, RS-10, RS-11).

Objetivo: Comprobar que los logs no se puedan modificar o borrar desde la aplicación,
y que usuarios normales no tengan acceso a los registros.
"""

import unittest
from fastapi.testclient import TestClient

from app.audit.repository import in_memory_audit_repo
from app.audit.service import AuditService
from app.auth.repository import in_memory_session_repo
from app.auth.service import AuthService
from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.main import app
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestPS09AuditIntegrity(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_audit_repo.clear()
        in_memory_session_repo.clear()
        login_rate_limiter.reset_all()

        self.client = TestClient(app)
        audit_service = AuditService(in_memory_audit_repo)
        user_service = UserService(in_memory_user_repo)
        auth_service = AuthService(in_memory_user_repo, in_memory_session_repo, audit_service)

        self.admin = user_service.create_admin_user("Admin", "admin@test.com", "AdminPass2026!")
        self.user = user_service.register_user(
            UserCreate(name="Regular User", email="user@test.com", password="Password2026!", password_confirmation="Password2026!")
        )

        _, self.admin_session = auth_service.authenticate_and_login("admin@test.com", "AdminPass2026!")
        _, self.user_session = auth_service.authenticate_and_login("user@test.com", "Password2026!")

        # Create sample audit event
        audit_service.log_event("TEST_ACTION", "TEST_RESOURCE", "123", self.admin.id, "SUCCESS")

    def test_ps09_user_denied_access_to_audit(self):
        """Usuario regular recibe 403 al intentar acceder a /admin/audit."""
        resp = self.client.get(
            "/admin/audit",
            cookies={settings.session_cookie_name: self.user_session.id},
        )
        self.assertEqual(resp.status_code, 403)

    def test_ps09_no_mutation_endpoints_exist_for_audit(self):
        """No existen endpoints POST, PUT, DELETE para alterar o borrar auditoría."""
        endpoints = [
            ("POST", "/admin/audit"),
            ("DELETE", "/admin/audit"),
            ("PUT", "/admin/audit"),
            ("DELETE", "/admin/audit/123"),
            ("POST", "/audit/delete"),
        ]

        for method, endpoint in endpoints:
            resp = self.client.request(
                method,
                endpoint,
                cookies={settings.session_cookie_name: self.admin_session.id},
            )
            # Must return 404 Not Found or 405 Method Not Allowed
            self.assertIn(resp.status_code, [404, 405], f"Mutating endpoint {method} {endpoint} should not exist!")


if __name__ == "__main__":
    unittest.main()
