"""Dependency injection providers for Repositories and Services."""

from fastapi import Depends
from app.audit.repository import (
    AuditRepository,
    SQLAlchemyAuditRepository,
    in_memory_audit_repo,
)
from app.audit.service import AuditService
from app.auth.repository import (
    SessionRepository,
    SQLAlchemySessionRepository,
    in_memory_session_repo,
)
from app.auth.service import AuthService
from app.database.base import HAS_SQLALCHEMY
from app.database.session import get_db
from app.reservations.repository import (
    ReservationRepository,
    SQLAlchemyReservationRepository,
    in_memory_reservation_repo,
)
from app.reservations.service import ReservationService
from app.rooms.repository import (
    RoomRepository,
    SQLAlchemyRoomRepository,
    in_memory_room_repo,
)
from app.rooms.service import RoomService
from app.users.repository import (
    UserRepository,
    SQLAlchemyUserRepository,
    in_memory_user_repo,
)
from app.users.service import UserService


def get_user_repository(db=Depends(get_db)) -> UserRepository:
    if HAS_SQLALCHEMY and hasattr(db, "query"):
        return SQLAlchemyUserRepository(db)
    return in_memory_user_repo


def get_session_repository(db=Depends(get_db)) -> SessionRepository:
    if HAS_SQLALCHEMY and hasattr(db, "query"):
        return SQLAlchemySessionRepository(db)
    return in_memory_session_repo


def get_audit_repository(db=Depends(get_db)) -> AuditRepository:
    if HAS_SQLALCHEMY and hasattr(db, "query"):
        return SQLAlchemyAuditRepository(db)
    return in_memory_audit_repo


def get_room_repository(db=Depends(get_db)) -> RoomRepository:
    if HAS_SQLALCHEMY and hasattr(db, "query"):
        return SQLAlchemyRoomRepository(db)
    return in_memory_room_repo


def get_reservation_repository(db=Depends(get_db)) -> ReservationRepository:
    if HAS_SQLALCHEMY and hasattr(db, "query"):
        return SQLAlchemyReservationRepository(db)
    return in_memory_reservation_repo


def get_audit_service(
    audit_repo: AuditRepository = Depends(get_audit_repository),
) -> AuditService:
    return AuditService(audit_repo)


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(user_repo)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuthService:
    return AuthService(user_repo, session_repo, audit_service)


def get_room_service(
    room_repo: RoomRepository = Depends(get_room_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> RoomService:
    return RoomService(room_repo, audit_service)


def get_reservation_service(
    reservation_repo: ReservationRepository = Depends(get_reservation_repository),
    room_repo: RoomRepository = Depends(get_room_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> ReservationService:
    return ReservationService(reservation_repo, room_repo, audit_service)
