"""PS-03: Protección contra manipulación de parámetros (CA-03, RS-03, RS-04, RS-05, RS-06).

Objetivo: Comprobar que el cliente no pueda asignar roles, propietario o estado directamente.
"""

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
from app.rooms.repository import in_memory_room_repo
from app.rooms.schemas import RoomCreate
from app.rooms.service import RoomService
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestPS03ParameterTampering(unittest.TestCase):
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

        self.admin = user_service.create_admin_user("Admin", "admin@test.com", "AdminPass2026!")
        self.user_victim = user_service.register_user(
            UserCreate(name="Victim", email="victim@test.com", password="Password2026!", password_confirmation="Password2026!")
        )
        self.room = room_service.create_room(
            RoomCreate(name="Tamper Room", location="Floor 1", capacity=10), self.admin
        )

    def test_ps03_registration_role_tampering_ignored(self):
        """1. Atacante envía role=ADMIN en registro público -> Se asigna estrictamente USER (RB-01, RS-05)."""
        self.client.get("/register")
        anon_cookie = self.client.cookies.get("secureroom_csrf_anon")
        csrf = generate_csrf_token(anon_cookie)

        resp = self.client.post(
            "/register",
            data={
                "name": "Attacker",
                "email": "attacker@test.com",
                "password": "AttackerPass2026!",
                "password_confirmation": "AttackerPass2026!",
                "role": "ADMIN",  # Tampered parameter
                "csrf_token": csrf,
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 303)

        created_user = in_memory_user_repo.get_by_email("attacker@test.com")
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.role, "USER", "Attacker managed to escalate role via parameter tampering!")

    def test_ps03_reservation_owner_and_status_tampering(self):
        """2. Atacante envía user_id=<Victim> y status=CANCELLED al crear reserva -> Servidor fija dueño y ACTIVE."""
        # Login as attacker
        auth_service = AuthService(in_memory_user_repo, in_memory_session_repo, AuditService(in_memory_audit_repo))
        user_service = UserService(in_memory_user_repo)
        attacker = user_service.register_user(
            UserCreate(name="Attacker", email="attacker2@test.com", password="Password2026!", password_confirmation="Password2026!")
        )
        _, session = auth_service.authenticate_and_login("attacker2@test.com", "Password2026!")

        csrf = generate_csrf_token(session.id)
        start = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT14:00")
        end = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT15:00")

        resp = self.client.post(
            "/reservations",
            data={
                "room_id": str(self.room.id),
                "start_datetime": start,
                "end_datetime": end,
                "user_id": str(self.user_victim.id),  # Tampering attempt
                "status": "CANCELLED",                 # Tampering attempt
                "csrf_token": csrf,
            },
            cookies={settings.session_cookie_name: session.id},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 303)

        # Check created reservation in database
        res_list = in_memory_reservation_repo.list_all()
        created_res = res_list[0]
        self.assertEqual(created_res.user_id, attacker.id, "Owner was forged to victim!")
        self.assertEqual(created_res.status, "ACTIVE", "Status was forged!")


if __name__ == "__main__":
    unittest.main()
