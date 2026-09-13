from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from frotad.models import Company, Driver
from frotad.models.identity import AccessToken, Membership, Role, SystemAuditEvent, User
from frotad.services.auth import hash_password

PASSWORD = "Minha frase segura 123!"


def register(client, suffix="one", **extra):
    return client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Empresa {suffix}",
            "company_slug": f"empresa-{suffix}",
            "name": f"Admin {suffix}",
            "email": f"admin-{suffix}@example.test",
            "password": PASSWORD,
            **extra,
        },
    )


def headers(session):
    result = {"Authorization": f"Bearer {session['access_token']}"}
    if session["company_id"]:
        result["X-Company-ID"] = session["company_id"]
    return result


def test_register_login_logout_password_and_secrets(client, db):
    response = register(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "OWNER" and body["is_system_admin"] is False
    assert response.headers["cache-control"] == "no-store"
    user = db.scalar(select(User))
    assert PASSWORD not in user.password_hash
    assert db.scalar(select(AccessToken)).token_hash != body["access_token"]
    assert (
        client.get("/api/v1/auth/me", headers=headers(body)).json()["company_name"] == "Empresa one"
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": " ADMIN-ONE@example.test ", "password": PASSWORD}
    )
    assert login.status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers(body)).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers(body)).status_code == 401
    new = login.json()
    assert (
        client.post(
            "/api/v1/auth/password",
            headers=headers(new),
            json={"current_password": PASSWORD, "new_password": PASSWORD + " changed"},
        ).status_code
        == 204
    )
    assert client.get("/api/v1/auth/me", headers=headers(new)).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD + " changed"}
        ).status_code
        == 200
    )
    assert db.scalar(
        select(SystemAuditEvent.id).where(SystemAuditEvent.action == "auth.password_changed")
    )


def test_registration_is_atomic_and_cannot_escalate(client, db):
    assert register(client).status_code == 201
    assert register(client, "two", email="ADMIN-ONE@example.test").status_code == 409
    assert register(client, "three", company_slug="empresa-one").status_code == 409
    assert register(client, "four", is_system_admin=True).status_code == 422
    assert register(client, "five", role="ADMIN").status_code == 422
    assert register(client, "six", timezone="invalid").status_code == 422
    assert register(client, "seven", password="short").status_code == 422
    assert len(db.scalars(select(Company)).all()) == 1
    assert len(db.scalars(select(User)).all()) == 1


def test_company_users_isolation_and_admin_roles(client, db):
    one, two = register(client).json(), register(client, "two").json()
    h = headers(one)
    payload = {
        "name": "Motorista",
        "email": "driver@example.test",
        "password": PASSWORD,
        "role": "DRIVER",
    }
    result = client.post("/api/v1/users", headers=h, json=payload)
    assert result.status_code == 201, result.text
    member = result.json()
    assert len(client.get("/api/v1/users", headers=h).json()) == 2
    assert len(client.get("/api/v1/users", headers=headers(two)).json()) == 1
    assert db.scalar(select(Driver).where(Driver.name == "Motorista"))
    assert (
        client.patch(
            f"/api/v1/users/{member['id']}", headers=headers(two), json={"active": False}
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/users/{one['user']['id']}", headers=h, json={"active": False}
        ).status_code
        == 403
    )
    driver = client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": PASSWORD}
    ).json()
    assert client.get("/api/v1/users", headers=headers(driver)).status_code == 403
    assert (
        client.post(
            "/api/v1/forms", headers=headers(driver), json={"code": "NO", "name": "No"}
        ).status_code
        == 403
    )
    assert (
        client.patch(f"/api/v1/users/{member['id']}", headers=h, json={"active": False}).status_code
        == 204
    )
    assert client.get("/api/v1/dashboard", headers=headers(driver)).status_code == 403
    assert (
        client.post(
            "/api/v1/users",
            headers=h,
            json={**payload, "email": "owner@example.test", "role": "OWNER"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/users", headers=h, json={**payload, "email": two["user"]["email"]}
        ).status_code
        == 409
    )


def test_system_admin_is_separate_and_cannot_be_created_by_tenant(client, db):
    system = User(
        name="System",
        email="system@example.test",
        password_hash=hash_password(PASSWORD),
        is_system_admin=True,
    )
    db.add(system)
    db.commit()
    result = client.post("/api/v1/auth/login", json={"email": system.email, "password": PASSWORD})
    assert result.status_code == 200, result.text
    session = result.json()
    assert session["is_system_admin"] is True and session["company_id"] is None
    h = headers(session)
    payload = {
        "company_name": "Criada pelo sistema",
        "company_slug": "system-created",
        "name": "Admin empresa",
        "email": "company@example.test",
        "password": PASSWORD,
    }
    assert client.post("/api/v1/system/companies", headers=h, json=payload).status_code == 201
    assert client.get("/api/v1/system/companies", headers=h).json()[0]["slug"] == "system-created"
    owner = client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": PASSWORD}
    ).json()
    assert owner["is_system_admin"] is False
    assert (
        client.post(
            "/api/v1/forms",
            headers={**h, "X-Company-ID": owner["company_id"]},
            json={"code": "SYSTEM_FORM", "name": "Formulário da empresa"},
        ).status_code
        == 201
    )
    assert client.get("/api/v1/system/companies", headers=headers(owner)).status_code == 403
    assert (
        client.post("/api/v1/system/companies", headers=headers(owner), json=payload).status_code
        == 403
    )
    assert (
        client.get(
            "/api/v1/dashboard", headers={**h, "X-Company-ID": owner["company_id"]}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/users",
            headers=headers(owner),
            json={
                "name": "Escape",
                "email": "escape@example.test",
                "password": PASSWORD,
                "is_system_admin": True,
            },
        ).status_code
        == 422
    )


def test_lockout_and_only_admins_create_forms(client, db):
    owner = register(client).json()
    for _ in range(5):
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": owner["user"]["email"], "password": "incorrect"},
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": owner["user"]["email"], "password": PASSWORD}
        ).status_code
        == 401
    )
    user = db.scalar(select(User))
    user.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
        ).status_code
        == 200
    )
    membership = db.scalar(select(Membership))
    membership.role = Role.MANAGER
    db.commit()
    assert (
        client.post(
            "/api/v1/forms", headers=headers(owner), json={"code": "NO", "name": "No"}
        ).status_code
        == 403
    )
    membership.role = Role.ADMIN
    db.commit()
    assert (
        client.post(
            "/api/v1/forms", headers=headers(owner), json={"code": "YES", "name": "Yes"}
        ).status_code
        == 201
    )
