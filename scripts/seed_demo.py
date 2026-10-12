"""Optional seed script for populating demo rooms and users for academic presentation.

Completely separated from the production initialization flow (FASE 14).
"""

from app.audit.service import AuditService
from app.core.exceptions import ValidationError
from app.database.deps import (
    get_audit_repository,
    get_room_repository,
    get_user_repository,
)
from app.database.session import get_db
from app.rooms.schemas import RoomCreate
from app.rooms.service import RoomService
from app.users.schemas import UserCreate
from app.users.service import UserService


def seed():
    db_gen = get_db()
    db = next(db_gen)

    user_repo = get_user_repository(db)
    room_repo = get_room_repository(db)
    audit_repo = get_audit_repository(db)

    audit_service = AuditService(audit_repo)
    user_service = UserService(user_repo)
    room_service = RoomService(room_repo, audit_service)

    print("--- Inicializando datos de demostración para SecureRoom v1 ---")

    # 1. Create Admin
    try:
        admin = user_service.create_admin_user(
            name="Administrador Principal",
            email="admin@secureroom.local",
            password="AdminSecure2026!",
        )
        print(f"[OK] Admin creado: {admin.email}")
    except ValidationError:
        admin = user_service.get_by_email("admin@secureroom.local")
        print(f"[INFO] Admin ya existía: {admin.email}")

    # 2. Create Regular Demo User
    try:
        user = user_service.register_user(
            UserCreate(
                name="Usuario Demo",
                email="usuario@secureroom.local",
                password="UserSecure2026!",
                password_confirmation="UserSecure2026!",
            )
        )
        print(f"[OK] Usuario regular creado: {user.email}")
    except ValidationError:
        user = user_service.get_by_email("usuario@secureroom.local")
        print(f"[INFO] Usuario regular ya existía: {user.email}")

    # 3. Create Demo Rooms
    demo_rooms = [
        RoomCreate(
            name="Sala Magna de Consejo",
            location="Piso 4 - Torre Ejecutiva",
            capacity=24,
            description="Sala de conferencias principal con videoconferencia 4K, microfonía omnidireccional y pantalla interactiva.",
        ),
        RoomCreate(
            name="Laboratorio de Innovación A",
            location="Piso 2 - Ala Creativa",
            capacity=12,
            description="Espacio colaborativo con pizarras de cristal, proyector láser y mesas modulares.",
        ),
        RoomCreate(
            name="Sala de Reuniones Ágil 1",
            location="Piso 1 - Zona Coworking",
            capacity=6,
            description="Sala pequeña para reuniones tácticas, daily standups y entrevistas.",
        ),
        RoomCreate(
            name="Sala de Capacitación Técnica",
            location="Piso 3 - Auditorio Sur",
            capacity=40,
            description="Auditorio para talleres, formaciones y presentaciones grupales con sistema de audio dedicado.",
        ),
    ]

    for room_data in demo_rooms:
        existing_rooms = [r for r in room_service.list_all_rooms() if r.name == room_data.name]
        if not existing_rooms:
            created_room = room_service.create_room(room_data, admin)
            print(f"[OK] Sala creada: {created_room.name} (Capacidad: {created_room.capacity})")
        else:
            print(f"[INFO] Sala ya existía: {room_data.name}")

    print("--- Demostración sembrada con éxito ---")


if __name__ == "__main__":
    seed()
