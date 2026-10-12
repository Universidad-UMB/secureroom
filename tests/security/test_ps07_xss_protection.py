"""PS-07: Protección contra Cross-Site Scripting (XSS) (CA-07, RS-06, RS-08).

Objetivo: Comprobar que contenido malicioso HTML/JavaScript se renderice escapado en el navegador.
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
from app.reservations.repository import in_memory_reservation_repo
from app.rooms.repository import in_memory_room_repo
from app.rooms.schemas import RoomCreate
from app.rooms.service import RoomService
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestPS07XSSProtection(unittest.TestCase):
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
        self.room_service = RoomService(in_memory_room_repo, audit_service)
        auth_service = AuthService(in_memory_user_repo, in_memory_session_repo, audit_service)

        self.admin = user_service.create_admin_user("Admin", "admin@test.com", "AdminPass2026!")
        _, self.admin_session = auth_service.authenticate_and_login("admin@test.com", "AdminPass2026!")

    def test_ps07_html_tags_are_escaped_in_rendered_templates(self):
        xss_payload = "<script>alert('XSS_ATTACK')</script>"

        # Create room with script tag in name and description
        room = self.room_service.create_room(
            RoomCreate(
                name=xss_payload,
                location="<img src=x onerror=alert(1)>",
                capacity=10,
                description="<b>Bold</b> <script>document.cookie</script>",
            ),
            self.admin,
        )

        # Retrieve room list view
        resp = self.client.get(
            "/rooms",
            cookies={settings.session_cookie_name: self.admin_session.id},
        )
        self.assertEqual(resp.status_code, 200)

        # Raw script tags must NOT appear unescaped in HTML
        self.assertNotIn("<script>alert('XSS_ATTACK')</script>", resp.text)
        self.assertNotIn("<img src=x onerror=alert(1)>", resp.text)

        # Escaped versions must be present
        self.assertIn("&lt;script&gt;alert(&#39;XSS_ATTACK&#39;)&lt;/script&gt;", resp.text)


if __name__ == "__main__":
    unittest.main()
