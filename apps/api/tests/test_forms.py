from uuid import uuid4

import pytest

from frotad.models.identity import AuditEvent, Role


def headers(company, token="token-a"):
    return {"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)}


def create(client, data, code="FORM01", tenant=0):
    h = headers(data[0][tenant], ("token-a", "token-b")[tenant])
    response = client.post("/api/v1/forms", headers=h, json={"code": code, "name": "Jornada"})
    assert response.status_code == 201, response.text
    return h, response.json()


def add(client, h, version, key="km_inicio", field_type="INTEGER", config=None):
    return client.post(
        f"/api/v1/form-versions/{version['id']}/fields",
        headers=h,
        json={"key": key, "label": key, "field_type": field_type, "config": config or {}},
    )


def test_lifecycle_and_immutability(client, data, db):
    h, draft = create(client, data)
    path = f"/api/v1/form-versions/{draft['id']}"
    first = add(client, h, draft).json()["fields"][0]
    second = add(client, h, draft, "km_fim").json()["fields"][1]
    response = client.put(
        path + "/field-order", headers=h, json={"field_ids": [second["id"], first["id"]]}
    )
    assert response.status_code == 200
    assert [f["key"] for f in response.json()["fields"]] == ["km_fim", "km_inicio"]
    published = client.post(path + "/publish", headers=h)
    assert published.status_code == 200
    snapshot = published.json()
    assert snapshot["published_at"] and len(snapshot["schema_hash"]) == 64
    assert add(client, h, draft, "extra").status_code == 409
    assert client.put(path + "/field-order", headers=h, json={"field_ids": []}).status_code == 409
    assert client.post(path + "/publish", headers=h).status_code == 409
    clone = client.post(path + "/clone", headers=h)
    assert clone.status_code == 201
    new = clone.json()
    assert new["version"] == 2 and new["published_at"] is None and new["schema_hash"] is None
    assert {f["id"] for f in new["fields"]}.isdisjoint(f["id"] for f in snapshot["fields"])
    assert add(client, h, new, "extra").status_code == 201
    assert client.get(path, headers=h).json() == snapshot
    assert client.post(path + "/clone", headers=h).status_code == 409
    actions = {event.action for event in db.query(AuditEvent).all()}
    assert {
        "form.created",
        "form.published",
        "form.version_created",
        "form.fields_reordered",
    } <= actions


@pytest.mark.parametrize(
    "method,suffix,payload",
    [
        ("get", "", None),
        ("post", "/publish", None),
        ("post", "/clone", None),
        ("post", "/fields", {"key": "x", "label": "X", "field_type": "TEXT"}),
        ("put", "/field-order", {"field_ids": []}),
    ],
)
def test_cross_tenant_versions(client, data, method, suffix, payload):
    _, version = create(client, data)
    response = client.request(
        method,
        f"/api/v1/form-versions/{version['id']}{suffix}",
        headers=headers(data[0][1], "token-b"),
        json=payload,
    )
    assert response.status_code == 404


def test_codes_unique_within_tenant(client, data):
    h, _ = create(client, data)
    assert (
        client.post(
            "/api/v1/forms", headers=h, json={"code": "FORM01", "name": "Duplicate"}
        ).status_code
        == 409
    )
    create(client, data, tenant=1)
    assert (
        client.post(
            "/api/v1/forms",
            headers=h,
            json={"code": "X", "name": "X", "company_id": str(data[0][1].id)},
        ).status_code
        == 422
    )


def test_invalid_lifecycle_and_reorder_are_atomic(client, data):
    h, version = create(client, data)
    path = f"/api/v1/form-versions/{version['id']}"
    assert client.post(path + "/publish", headers=h).status_code == 422
    assert client.post(path + "/clone", headers=h).status_code == 409
    result = add(client, h, version).json()
    field_id = result["fields"][0]["id"]
    assert add(client, h, version).status_code == 409
    for ids in ([], [str(uuid4())], [field_id, field_id]):
        assert (
            client.put(path + "/field-order", headers=h, json={"field_ids": ids}).status_code == 422
        )
        assert client.get(path, headers=h).json() == result


@pytest.mark.parametrize(
    "kind,config",
    [
        ("PERIOD", {}),
        ("PERIOD", {"status_key": "WAIT", "status_label": "Wait", "script": "bad"}),
        ("TEXT", {"javascript": "bad"}),
        ("SINGLE_SELECT", {"options": ["a", "a"]}),
        ("SINGLE_SELECT", {"options": []}),
        ("PHOTO", {"policy": "ALWAYS"}),
        ("CALCULATED", {"formula": "eval(x)"}),
    ],
)
def test_invalid_field_config(client, data, kind, config):
    h, version = create(client, data)
    assert add(client, h, version, field_type=kind, config=config).status_code == 422


def test_period_config_is_copied(client, data):
    h, version = create(client, data)
    config = {"status_key": "WAIT", "status_label": "Aguardando"}
    response = add(client, h, version, field_type="PERIOD", config=config)
    assert response.status_code == 201
    assert response.json()["fields"][0]["config"]["allow_concurrent"] is False


@pytest.mark.parametrize("role", [Role.VIEWER, Role.DRIVER, Role.DISPATCHER])
def test_write_permissions(client, data, db, role):
    data[3][0].role = role
    db.commit()
    response = client.post(
        "/api/v1/forms", headers=headers(data[0][0]), json={"code": "X", "name": "X"}
    )
    assert response.status_code == 403
