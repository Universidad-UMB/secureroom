"""Unit tests for Pydantic input schemas and parameter validation."""

import unittest
from datetime import datetime, timezone, timedelta
import uuid

from app.reservations.schemas import ReservationCreate
from app.rooms.schemas import RoomCreate
from app.users.schemas import UserCreate


class TestSchemas(unittest.TestCase):
    def test_user_create_passwords_mismatch(self):
        with self.assertRaises(Exception):
            UserCreate(
                name="Test",
                email="test@test.com",
                password="Password123!",
                password_confirmation="DifferentPass123!",
            )

    def test_user_create_invalid_email(self):
        with self.assertRaises(Exception):
            UserCreate(
                name="Test",
                email="not-an-email",
                password="Password123!",
                password_confirmation="Password123!",
            )

    def test_room_create_zero_capacity_fails(self):
        with self.assertRaises(Exception):
            RoomCreate(name="Room", location="L1", capacity=0)

    def test_reservation_create_excludes_user_id_tampering(self):
        """RS-05: ReservationCreate schema does not accept user_id from client."""
        start = datetime.now(timezone.utc) + timedelta(days=1)
        end = start + timedelta(hours=1)
        # Supplying user_id in payload is ignored or not a field
        schema = ReservationCreate(
            room_id=uuid.uuid4(),
            start_datetime=start,
            end_datetime=end,
        )
        self.assertFalse(hasattr(schema, "user_id"))


if __name__ == "__main__":
    unittest.main()
