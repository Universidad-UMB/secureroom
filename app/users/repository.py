"""Repository layer for User persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional
import threading
import uuid

from app.database.base import HAS_SQLALCHEMY
from app.users.models import User


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def create(self, user: User) -> User:
        pass

    @abstractmethod
    def list_all(self) -> List[User]:
        pass


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, db_session):
        self.db = db_session

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.lower()).first()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_all(self) -> List[User]:
        return self.db.query(User).order_by(User.created_at.desc()).all()


class InMemoryUserRepository(UserRepository):
    """Thread-safe in-memory repository for tests and offline execution."""

    def __init__(self):
        self._lock = threading.Lock()
        self._users_by_id = {}
        self._users_by_email = {}

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        with self._lock:
            return self._users_by_id.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        with self._lock:
            return self._users_by_email.get(email.lower())

    def create(self, user: User) -> User:
        with self._lock:
            if user.id is None:
                user.id = uuid.uuid4()
            self._users_by_id[user.id] = user
            self._users_by_email[user.email.lower()] = user
            return user

    def list_all(self) -> List[User]:
        with self._lock:
            return sorted(
                list(self._users_by_id.values()),
                key=lambda u: getattr(u, "created_at", None) or 0,
                reverse=True,
            )

    def clear(self):
        with self._lock:
            self._users_by_id.clear()
            self._users_by_email.clear()


# Global singleton instance for in-memory mode
in_memory_user_repo = InMemoryUserRepository()
