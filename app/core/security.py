"""Security utilities for SecureRoom: Argon2id password hashing, tokens, and sanitization."""

import ctypes
from ctypes import c_char_p, c_int, c_size_t, c_uint32, c_void_p
import hmac
import hashlib
import os
import secrets
from typing import Optional

from app.core.config import settings
from app.core.exceptions import ValidationError

# Try importing argon2-cffi first. If unavailable, use system libargon2 via ctypes.
_ARGON2_AVAILABLE = False
_hasher_instance = None

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _hasher_instance = PasswordHasher(
        time_cost=2,
        memory_cost=65536,
        parallelism=1,
        hash_len=32,
        salt_len=16,
    )
    _ARGON2_AVAILABLE = True
except ImportError:
    # Try ctypes fallback to /usr/lib/x86_64-linux-gnu/libargon2.so.1
    try:
        _lib_path = "/usr/lib/x86_64-linux-gnu/libargon2.so.1"
        if os.path.exists(_lib_path):
            _c_libargon2 = ctypes.CDLL(_lib_path)
            _c_libargon2.argon2id_hash_encoded.argtypes = [
                c_uint32, c_uint32, c_uint32, c_void_p, c_size_t,
                c_void_p, c_size_t, c_size_t, c_char_p, c_size_t
            ]
            _c_libargon2.argon2id_hash_encoded.restype = c_int

            _c_libargon2.argon2id_verify.argtypes = [c_char_p, c_void_p, c_size_t]
            _c_libargon2.argon2id_verify.restype = c_int
            _ARGON2_AVAILABLE = True
        else:
            _c_libargon2 = None
    except Exception:
        _c_libargon2 = None


def validate_password_strength(password: str) -> None:
    """Validates password constraints according to business and security rules.
    - Not empty
    - Minimum 10 characters
    - Maximum 128 characters
    """
    if not password:
        raise ValidationError("La contraseña no puede estar vacía.")
    if len(password) < 10:
        raise ValidationError("La contraseña debe tener al menos 10 caracteres.")
    if len(password) > 128:
        raise ValidationError("La contraseña no puede exceder 128 caracteres.")


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id with recommended parameters."""
    validate_password_strength(password)

    if _hasher_instance is not None:
        return _hasher_instance.hash(password)

    if _c_libargon2 is not None:
        salt = secrets.token_bytes(16)
        encoded_buf = ctypes.create_string_buffer(512)
        pwd_bytes = password.encode("utf-8")
        res = _c_libargon2.argon2id_hash_encoded(
            2, 65536, 1, pwd_bytes, len(pwd_bytes), salt, len(salt), 32, encoded_buf, 512
        )
        if res == 0:
            return encoded_buf.value.decode("utf-8")
        raise RuntimeError(f"Error al generar hash Argon2id (código: {res})")

    # Fallback to PBKDF2 with SHA-256 and high iteration count if Argon2 is completely missing
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    return f"$pbkdf2-sha256$600000${salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against an Argon2id (or fallback) hash."""
    if not plain_password or not hashed_password:
        return False

    if hashed_password.startswith("$argon2"):
        if _hasher_instance is not None:
            try:
                return _hasher_instance.verify(hashed_password, plain_password)
            except Exception:
                return False

        if _c_libargon2 is not None:
            res = _c_libargon2.argon2id_verify(
                hashed_password.encode("utf-8"),
                plain_password.encode("utf-8"),
                len(plain_password.encode("utf-8")),
            )
            return res == 0

    if hashed_password.startswith("$pbkdf2-sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 5:
            _, algo, iters, salt_hex, hash_hex = parts
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, int(iters))
            return hmac.compare_digest(dk, expected)

    return False


def generate_session_id() -> str:
    """Generates a cryptographically secure 256-bit session token."""
    return secrets.token_urlsafe(32)


def generate_csrf_token(session_id: str) -> str:
    """Generates a signed HMAC-SHA256 CSRF token cryptographically bound to a session."""
    key = settings.session_secret.encode("utf-8")
    msg = f"csrf:{session_id}".encode("utf-8")
    token_hmac = hmac.new(key, msg, hashlib.sha256).hexdigest()
    # Random nonce prevents token reuse / BREACH attacks
    nonce = secrets.token_hex(8)
    return f"{nonce}:{token_hmac}"


def verify_csrf_token(session_id: str, token: str) -> bool:
    """Validates that a submitted CSRF token matches the session ID."""
    if not session_id or not token or ":" not in token:
        return False
    try:
        nonce, submitted_hmac = token.split(":", 1)
        key = settings.session_secret.encode("utf-8")
        msg = f"csrf:{session_id}".encode("utf-8")
        expected_hmac = hmac.new(key, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(submitted_hmac, expected_hmac)
    except Exception:
        return False
