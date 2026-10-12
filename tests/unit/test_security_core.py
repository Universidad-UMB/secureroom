"""Unit tests for security core components: Argon2id, CSRF, Session, Rate Limiter."""

import unittest
from datetime import datetime, timezone, timedelta
import uuid

from app.core.rate_limiter import login_rate_limiter
from app.core.security import (
    hash_password,
    verify_password,
    generate_csrf_token,
    verify_csrf_token,
    validate_password_strength,
)
from app.core.session import SessionData
from app.core.exceptions import ValidationError


class TestSecurityCore(unittest.TestCase):
    def setUp(self):
        login_rate_limiter.reset_all()

    def test_argon2id_hashing_and_verification(self):
        """RS-02: Password must be hashed with Argon2id and verified correctly."""
        password = "SecurePassword2026!"
        pwd_hash = hash_password(password)

        self.assertTrue(verify_password(password, pwd_hash))
        self.assertFalse(verify_password("WrongPassword123!", pwd_hash))
        self.assertFalse(verify_password("", pwd_hash))

    def test_password_strength_constraints(self):
        """Enforces minimum length of 10 characters."""
        with self.assertRaises(ValidationError):
            validate_password_strength("short9ch")
        with self.assertRaises(ValidationError):
            validate_password_strength("")
        # 10 chars is valid
        validate_password_strength("valid10chr")

    def test_csrf_generation_and_validation(self):
        """HMAC-bound CSRF token validation."""
        session_id = "session_crypto_token_abcdef12345"
        token = generate_csrf_token(session_id)

        self.assertTrue(verify_csrf_token(session_id, token))
        self.assertFalse(verify_csrf_token("different_session", token))
        self.assertFalse(verify_csrf_token(session_id, "corrupted_token"))
        self.assertFalse(verify_csrf_token(session_id, ""))

    def test_session_expiration_logic(self):
        """RS-08: Expired sessions must report is_expired=True."""
        now = datetime.now(timezone.utc)
        active_session = SessionData(
            session_id="s1",
            user_id=uuid.uuid4(),
            expires_at=now + timedelta(hours=1),
        )
        self.assertFalse(active_session.is_expired)

        expired_session = SessionData(
            session_id="s2",
            user_id=uuid.uuid4(),
            expires_at=now - timedelta(seconds=1),
        )
        self.assertTrue(expired_session.is_expired)

    def test_login_rate_limiter(self):
        """CA-04: Failed attempts trigger temporary lockout."""
        key = "127.0.0.1:target@test.com"

        for i in range(4):
            is_locked, _ = login_rate_limiter.record_failure(key)
            self.assertFalse(is_locked)

        # 5th failure triggers lockout
        is_locked, remaining = login_rate_limiter.record_failure(key)
        self.assertTrue(is_locked)
        self.assertGreater(remaining, 0)

        locked_check, _ = login_rate_limiter.is_locked(key)
        self.assertTrue(locked_check)


if __name__ == "__main__":
    unittest.main()
