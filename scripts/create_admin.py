"""Script for creating the initial administrator account (RB-23, RS-03).

Usage:
  python -m scripts.create_admin --name "Admin Name" --email "admin@secureroom.local" --password "AdminPass123!"
Or run interactively.
"""

import argparse
import getpass
import sys

from app.database.deps import get_user_repository
from app.database.session import get_db
from app.users.service import UserService
from app.core.exceptions import ValidationError


def main():
    parser = argparse.ArgumentParser(description="Create an initial SecureRoom administrator.")
    parser.add_argument("--name", help="Admin full name")
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--password", help="Admin password (min 10 chars)")
    args = parser.parse_args()

    name = args.name
    email = args.email
    password = args.password

    if not name:
        name = input("Nombre completo del administrador: ").strip()
    if not email:
        email = input("Correo electrónico: ").strip()
    if not password:
        password = getpass.getpass("Contraseña (mínimo 10 caracteres): ")

    db_gen = get_db()
    db = next(db_gen)
    user_repo = get_user_repository(db)
    user_service = UserService(user_repo)

    try:
        admin_user = user_service.create_admin_user(name=name, email=email, password=password)
        print(f"\n[OK] Administrador creado exitosamente:")
        print(f"     ID: {admin_user.id}")
        print(f"     Nombre: {admin_user.name}")
        print(f"     Correo: {admin_user.email}")
        print(f"     Rol: {admin_user.role}")
    except ValidationError as err:
        print(f"\n[ERROR] No se pudo crear el administrador: {err.message}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass


if __name__ == "__main__":
    main()
