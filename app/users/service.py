"""Service layer for User management and business rules."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.core.exceptions import ValidationError, ResourceNotFoundError
from app.core.security import hash_password, validate_password_strength
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def register_user(self, data: UserCreate) -> User:
        """Registers a new public user.

        Enforces:
        - RB-01: Public registration always assigns role 'USER'.
        - RB-02: Email uniqueness.
        - RS-02: Password hashed with Argon2id.
        - RS-05: Server controls role, is_active, and id.
        """
        existing = self.user_repo.get_by_email(data.email)
        if existing:
            raise ValidationError("El correo electrónico ya se encuentra registrado.")

        hashed = hash_password(data.password)

        new_user = User(
            id=uuid.uuid4(),
            name=data.name.strip(),
            email=data.email.strip().lower(),
            password_hash=hashed,
            role="USER",  # Strict server assignment (RB-01, RS-05)
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        return self.user_repo.create(new_user)

    def create_admin_user(self, name: str, email: str, password: str) -> User:
        """Creates an administrator account via controlled initialization script (RB-23)."""
        clean_email = email.strip().lower()
        clean_name = name.strip()

        if not clean_name:
            raise ValidationError("El nombre no puede estar vacío.")
        if not clean_email or "@" not in clean_email:
            raise ValidationError("El correo electrónico no es válido.")

        validate_password_strength(password)

        existing = self.user_repo.get_by_email(clean_email)
        if existing:
            raise ValidationError("El correo electrónico ya se encuentra registrado.")

        hashed = hash_password(password)

        admin_user = User(
            id=uuid.uuid4(),
            name=clean_name,
            email=clean_email,
            password_hash=hashed,
            role="ADMIN",  # Explicit admin creation (RB-23)
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        return self.user_repo.create(admin_user)

    def get_by_id(self, user_id: uuid.UUID) -> User:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("Usuario no encontrado.")
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        return self.user_repo.get_by_email(email.strip().lower())

    def list_all(self) -> List[User]:
        """Lists all registered users for administration (RF-06)."""
        return self.user_repo.list_all()
