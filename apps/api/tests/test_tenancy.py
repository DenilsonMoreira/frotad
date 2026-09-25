import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from alembic import command
from frotad.models import AccessToken, Membership, Vehicle
from frotad.models.base import Base
from frotad.models.identity import Role


def headers(company, token="token-a"):
    return {"X-Company-ID": str(company.id), "Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("resource,index", [("vehicles", 4), ("drivers", 5)])
def test_isolation(client, data, resource, index):
    for n, token in enumerate(("token-a", "token-b")):
        h = headers(data[0][n], token)
        response = client.get(f"/api/v1/{resource}", headers=h)
        assert response.status_code == 200
        assert [r["id"] for r in response.json()] == [str(data[index][n].id)]
        assert (
            client.get(f"/api/v1/{resource}/{data[index][1 - n].id}", headers=h).status_code == 404
        )
        assert client.get(f"/api/v1/{resource}/{data[index][n].id}", headers=h).status_code == 200


def test_forged_tenant_and_missing_identity(client, data):
    assert client.get("/api/v1/vehicles", headers=headers(data[0][1])).status_code == 403
    for token in ("bad", ""):
        assert client.get("/api/v1/vehicles", headers=headers(data[0][0], token)).status_code == 401
    assert (
        client.get("/api/v1/vehicles", headers={"X-Company-ID": str(data[0][0].id)}).status_code
        == 401
    )
    assert (
        client.get("/api/v1/vehicles", headers={"Authorization": "Bearer token-a"}).status_code
        == 422
    )


@pytest.mark.parametrize(
    "change", ["revoked", "expired", "inactive_user", "inactive_membership", "driver"]
)
def test_revocation_permissions(client, db, data, change):
    token = db.query(AccessToken).filter_by(user_id=data[1][0].id).one()
    if change == "revoked":
        token.revoked = True
    if change == "expired":
        token.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    if change == "inactive_user":
        data[1][0].status = "DISABLED"
    if change == "inactive_membership":
        data[3][0].active = False
    if change == "driver":
        data[3][0].role = Role.DRIVER
    db.commit()
    response = client.get("/api/v1/vehicles", headers=headers(data[0][0]))
    assert response.status_code == (403 if change in ("inactive_membership", "driver") else 401)


def test_branch_scope(client, db, data):
    data[3][0].branch_id = data[2][0].id
    extra = Vehicle(company_id=data[0][0].id, fleet_number="002")
    db.add(extra)
    db.commit()
    h = headers(data[0][0])
    assert len(client.get("/api/v1/vehicles", headers=h).json()) == 1
    assert client.get(f"/api/v1/vehicles/{extra.id}", headers=h).status_code == 404
    assert client.get("/api/v1/drivers", headers=h).status_code == 403


@pytest.mark.parametrize("kind", ["vehicle", "driver", "membership"])
def test_database_rejects_cross_tenant_links(db, data, kind):
    if kind == "vehicle":
        data[4][0].branch_id = data[2][1].id
    if kind == "driver":
        data[5][0].user_id = data[1][1].id
    if kind == "membership":
        data[3][0].branch_id = data[2][1].id
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_errors_and_request_id(client, data):
    response = client.get(f"/api/v1/vehicles/{uuid4()}", headers=headers(data[0][0]))
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert client.get("/api/v1/vehicles?limit=101", headers=headers(data[0][0])).status_code == 422


def test_migration_roundtrip(tmp_path):
    from frotad.core.config import settings

    original = settings.database_url
    settings.database_url = os.getenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'migration.db'}")
    config = Config("alembic.ini")
    engine = create_engine(settings.database_url)
    try:
        command.upgrade(config, "head")
        assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())
        command.check(config)
        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
        command.upgrade(config, "head")
        command.downgrade(config, "base")
    finally:
        settings.database_url = original
        engine.dispose()


def test_bootstrap_audits_membership(db, monkeypatch, capsys):
    from contextlib import contextmanager

    from frotad import bootstrap
    from frotad.models.identity import AuditEvent

    @contextmanager
    def transaction():
        yield db
        db.commit()

    class Sessions:
        begin = staticmethod(transaction)

    monkeypatch.setattr(bootstrap, "SessionLocal", Sessions)
    monkeypatch.setattr(
        "sys.argv",
        [
            "bootstrap",
            "--company",
            "Test",
            "--slug",
            "test",
            "--name",
            "Owner",
            "--email",
            "owner@example.test",
        ],
    )
    bootstrap.main()
    output = capsys.readouterr().out
    audit = db.query(AuditEvent).one()
    membership = db.query(Membership).one()
    assert audit.entity_id == membership.id
    assert audit.company_id == membership.company_id
    assert audit.action == "membership.owner_created"
    token = output.split("expires in 8h): ")[1].strip()
    assert db.query(AccessToken).one().token_hash == sha256(token.encode()).hexdigest()


def test_validation_reports_path_without_input(client, data):
    response = client.get("/api/v1/vehicles?limit=101", headers=headers(data[0][0]))
    assert response.json()["error"]["fields"][0]["path"] == ["query", "limit"]
    assert "input" not in response.json()["error"]["fields"][0]
