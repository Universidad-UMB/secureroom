"""Unit tests for SecureRoom business rules (RB-01 through RB-24)."""

import unittest
from datetime import datetime, timezone, timedelta
import uuid

from app.audit.repository import in_memory_audit_repo
from app.audit.service import AuditService
from app.core.exceptions import (
    AuthorizationError,
    ReservationConflictError,
    ValidationError,
)
from app.reservations.repository import in_memory_reservation_repo
from app.reservations.schemas import ReservationCreate
from app.reservations.service import ReservationService
from app.rooms.models import Room
from app.rooms.repository import in_memory_room_repo
from app.rooms.schemas import RoomCreate
from app.rooms.service import RoomService
from app.users.models import User
from app.users.repository import in_memory_user_repo
from app.users.schemas import UserCreate
from app.users.service import UserService


class TestBusinessRules(unittest.TestCase):
    def setUp(self):
        in_memory_user_repo.clear()
        in_memory_room_repo.clear()
        in_memory_reservation_repo.clear()
        in_memory_audit_repo.clear()

        self.audit_service = AuditService(in_memory_audit_repo)
        self.user_service = UserService(in_memory_user_repo)
        self.room_service = RoomService(in_memory_room_repo, self.audit_service)
        self.reservation_service = ReservationService(
            in_memory_reservation_repo, in_memory_room_repo, self.audit_service
        )

        self.admin = self.user_service.create_admin_user("Admin", "admin@test.com", "AdminPassword123!")
        self.user = self.user_service.register_user(
            UserCreate(name="User", email="user@test.com", password="UserPassword123!", password_confirmation="UserPassword123!")
        )

    def test_rb01_public_registration_always_assigns_user_role(self):
        """RB-01: Public register always assigns role USER."""
        self.assertEqual(self.user.role, "USER")

    def test_rb02_email_uniqueness(self):
        """RB-02: Email must be unique."""
        with self.assertRaises(ValidationError):
            self.user_service.register_user(
                UserCreate(name="Dupe", email="user@test.com", password="AnotherPassword123!", password_confirmation="AnotherPassword123!")
            )

    def test_rb06_cannot_reserve_inactive_room(self):
        """RB-06: Only active rooms allow reservations."""
        room = self.room_service.create_room(
            RoomCreate(name="Inactive Room", location="Floor 1", capacity=10), self.admin
        )
        self.room_service.toggle_room_status(room.id, self.admin)
        self.assertFalse(room.is_active)

        start = datetime.now(timezone.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)

        with self.assertRaises(ValidationError):
            self.reservation_service.create_reservation(
                ReservationCreate(room_id=room.id, start_datetime=start, end_datetime=end),
                self.user,
            )

    def test_rb08_room_capacity_must_be_positive(self):
        """RB-08: Room capacity must be greater than zero."""
        with self.assertRaises(Exception):
            self.room_service.create_room(
                RoomCreate(name="Zero Cap", location="L1", capacity=0), self.admin
            )

    def test_rb10_start_must_be_before_end(self):
        """RB-10: Start datetime must be before end datetime."""
        room = self.room_service.create_room(
            RoomCreate(name="Room 1", location="L1", capacity=5), self.admin
        )
        start = datetime.now(timezone.utc) + timedelta(days=1, hours=2)
        end = datetime.now(timezone.utc) + timedelta(days=1, hours=1)

        with self.assertRaises(Exception):
            self.reservation_service.create_reservation(
                ReservationCreate(room_id=room.id, start_datetime=start, end_datetime=end),
                self.user,
            )

    def test_rb11_reservation_must_be_future(self):
        """RB-11: New reservations must be in the future."""
        room = self.room_service.create_room(
            RoomCreate(name="Room 2", location="L1", capacity=5), self.admin
        )
        past_start = datetime.now(timezone.utc) - timedelta(hours=2)
        past_end = datetime.now(timezone.utc) - timedelta(hours=1)

        with self.assertRaises(Exception):
            self.reservation_service.create_reservation(
                ReservationCreate(room_id=room.id, start_datetime=past_start, end_datetime=past_end),
                self.user,
            )

    def test_rb12_and_rb13_overlapping_and_consecutive_reservations(self):
        """RB-12 & RB-13: Overlapping active reservations blocked, consecutive allowed."""
        room = self.room_service.create_room(
            RoomCreate(name="Room 3", location="L1", capacity=5), self.admin
        )
        base = datetime.now(timezone.utc) + timedelta(days=1)
        r1_start = base.replace(hour=10, minute=0, second=0, microsecond=0)
        r1_end = base.replace(hour=11, minute=0, second=0, microsecond=0)

        # Create first reservation: 10:00 - 11:00
        res1 = self.reservation_service.create_reservation(
            ReservationCreate(room_id=room.id, start_datetime=r1_start, end_datetime=r1_end),
            self.user,
        )
        self.assertEqual(res1.status, "ACTIVE")

        # Conflict 1: exact same time (10:00 - 11:00)
        with self.assertRaises(ReservationConflictError):
            self.reservation_service.create_reservation(
                ReservationCreate(room_id=room.id, start_datetime=r1_start, end_datetime=r1_end),
                self.user,
            )

        # Conflict 2: partial overlap (10:30 - 11:30)
        with self.assertRaises(ReservationConflictError):
            self.reservation_service.create_reservation(
                ReservationCreate(
                    room_id=room.id,
                    start_datetime=base.replace(hour=10, minute=30, second=0, microsecond=0),
                    end_datetime=base.replace(hour=11, minute=30, second=0, microsecond=0),
                ),
                self.user,
            )

        # RB-13: Consecutive reservation immediately following (11:00 - 12:00) allowed!
        r2_start = base.replace(hour=11, minute=0, second=0, microsecond=0)
        r2_end = base.replace(hour=12, minute=0, second=0, microsecond=0)
        res2 = self.reservation_service.create_reservation(
            ReservationCreate(room_id=room.id, start_datetime=r2_start, end_datetime=r2_end),
            self.user,
        )
        self.assertEqual(res2.status, "ACTIVE")

    def test_rb16_and_rb17_cancellation_ownership_and_admin(self):
        """RB-16 & RB-17: User can only cancel own reservation; Admin can cancel any."""
        user_b = self.user_service.register_user(
            UserCreate(name="User B", email="user_b@test.com", password="UserPassword123!", password_confirmation="UserPassword123!")
        )
        room = self.room_service.create_room(
            RoomCreate(name="Room 4", location="L1", capacity=5), self.admin
        )
        start = datetime.now(timezone.utc) + timedelta(days=2)
        end = start + timedelta(hours=1)

        res_a = self.reservation_service.create_reservation(
            ReservationCreate(room_id=room.id, start_datetime=start, end_datetime=end),
            self.user,
        )

        # User B cannot cancel User A's reservation (RB-16, RS-04)
        with self.assertRaises(AuthorizationError):
            self.reservation_service.cancel_reservation(res_a.id, user_b)

        # Admin CAN cancel User A's reservation (RB-17)
        cancelled = self.reservation_service.cancel_reservation(res_a.id, self.admin)
        self.assertEqual(cancelled.status, "CANCELLED")
        self.assertEqual(cancelled.cancelled_by, self.admin.id)

        # RB-19: A cancelled reservation cannot be re-cancelled
        with self.assertRaises(ValidationError):
            self.reservation_service.cancel_reservation(res_a.id, self.admin)


if __name__ == "__main__":
    unittest.main()
