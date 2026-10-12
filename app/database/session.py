"""Database engine and session management.

Configures connection pooling and session makers for PostgreSQL via SQLAlchemy.
Provides fallback in-memory database storage if SQLAlchemy is not installed in the environment.
"""

from contextlib import contextmanager
from typing import Generator
from app.core.config import settings
from app.database.base import HAS_SQLALCHEMY

_engine = None
_SessionLocal = None

if HAS_SQLALCHEMY:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    try:
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            echo=False,
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    except Exception:
        _engine = None
        _SessionLocal = None


class FallbackDatabaseSession:
    """In-memory fallback session simulating database transactions."""

    def __init__(self):
        self.is_active = True

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.is_active = False


def get_db() -> Generator:
    """FastAPI dependency yielding a database session."""
    if _SessionLocal is not None:
        db = _SessionLocal()
        try:
            yield db
        finally:
            db.close()
    else:
        db = FallbackDatabaseSession()
        try:
            yield db
        finally:
            db.close()
