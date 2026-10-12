"""Test fixtures and test client configuration for SecureRoom tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.users.repository import in_memory_user_repo
from app.rooms.repository import in_memory_room_repo
from app.reservations.repository import in_memory_reservation_repo
from app.audit.repository import in_memory_audit_repo
from app.auth.repository import in_memory_session_repo
from app.core.rate_limiter import login_rate_limiter


def reset_test_databases():
    """Resets all in-memory repository states between tests."""
    in_memory_user_repo.clear()
    in_memory_room_repo.clear()
    in_memory_reservation_repo.clear()
    in_memory_audit_repo.clear()
    in_memory_session_repo.clear()
    login_rate_limiter.reset_all()


def get_test_client():
    return TestClient(app)
