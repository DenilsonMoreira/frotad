import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from alembic import command
from frotad.api.dependencies import get_db
from frotad.core.config import settings
from frotad.main import app
from frotad.models import AccessToken, Branch, Company, Driver, Membership, User, Vehicle
from frotad.models.base import Base
from frotad.models.identity import Role


@pytest.fixture
def db():
    url = os.getenv("TEST_DATABASE_URL", "sqlite://")
    engine = create_engine(
        url,
        **(
            {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
            if url == "sqlite://"
            else {}
        ),
    )
    if engine.dialect.name == "sqlite":
        event.listen(
            engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON")
        )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def data(db):
    companies = [Company(name=name, slug=name) for name in ("alpha", "beta")]
    users = [User(name=name, email=f"{name}@example.test") for name in ("alice", "bob")]
    db.add_all(companies + users)
    db.flush()
    branches = [Branch(company_id=c.id, name="HQ") for c in companies]
    memberships = [
        Membership(company_id=c.id, user_id=u.id, role=Role.OWNER) for c, u in zip(companies, users)
    ]
    db.add_all(branches + memberships)
    db.flush()
    vehicles = [
        Vehicle(company_id=c.id, branch_id=b.id, fleet_number="001")
        for c, b in zip(companies, branches)
    ]
    drivers = [Driver(company_id=c.id, user_id=u.id, name=u.name) for c, u in zip(companies, users)]
    db.add_all(vehicles + drivers)
    for u, token in zip(users, ("token-a", "token-b")):
        db.add(
            AccessToken(
                user_id=u.id,
                token_hash=sha256(token.encode()).hexdigest(),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
    db.commit()
    return companies, users, branches, memberships, vehicles, drivers


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def migrated_engine(tmp_path):
    original = settings.database_url
    settings.database_url = os.getenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'forms.db'}")
    config = Config("alembic.ini")
    engine = create_engine(settings.database_url)
    command.upgrade(config, "head")
    try:
        yield engine
    finally:
        command.downgrade(config, "base")
        engine.dispose()
        settings.database_url = original
