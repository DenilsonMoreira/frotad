"""Trusted host-only provisioning: python -m frotad.system_admin --email EMAIL --name NAME."""

import argparse
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy import func, select

from frotad.db.session import SessionLocal
from frotad.models.identity import User
from frotad.schemas.auth import UserCreate
from frotad.services.auth import hash_password, save, security_event


def main():
    parser = argparse.ArgumentParser(description="Provisionar administrador do sistema FrotaD")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass("Senha (15 a 128 caracteres): ")
    if password != getpass("Confirme a senha: "):
        parser.error("As senhas não coincidem")
    try:
        payload = UserCreate(name=args.name, email=args.email, password=password)
    except ValidationError:
        parser.error("Confira nome, e-mail e senha de 15 a 128 caracteres.")
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(func.lower(User.email) == payload.email)):
            parser.error(
                "A conta já existe. O comando não promove nem substitui contas existentes."
            )
        user = User(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(password),
            is_system_admin=True,
        )
        db.add(user)
        db.flush()
        security_event(db, user.id, "system_admin.provisioned")
        save(db)
    print("Administrador do sistema criado. Acesse a tela de login.")


if __name__ == "__main__":
    main()
