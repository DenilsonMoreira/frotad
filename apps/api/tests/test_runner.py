from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from frotad.models.identity import AuditEvent, Role
from frotad.models.runner import FormAnswer, FormSubmission, PeriodValue
from frotad.schemas.forms import FieldCreate, FormCreate
from frotad.services import forms, runner
from frotad.services.tenancy import TenantContext


def headers(data, tenant=0):
    return {
        "X-Company-ID": str(data[0][tenant].id),
        "Authorization": f"Bearer token-{'ab'[tenant]}",
    }


def definition(db, data, types=None, concurrent=False, tenant=0):
    context = TenantContext(data[0][tenant].id, data[1][tenant].id, None, Role.OWNER)
    version = forms.create_form(db, context, FormCreate(code="CYCLE", name="Ciclo"))
    specs = types or [
        ("wait", "PERIOD", True),
        ("unload", "PERIOD", False),
        ("volume", "DECIMAL", True),
    ]
    for key, kind, required in specs:
        config = (
            {"status_key": key.upper(), "status_label": key, "allow_concurrent": concurrent}
            if kind == "PERIOD"
            else {}
        )
        if kind in ("SINGLE_SELECT", "MULTI_SELECT"):
            config = {"options": ["a", "b"]}
        forms.add_field(
            db,
            context,
            version.id,
            FieldCreate(key=key, label=key, field_type=kind, required=required, config=config),
        )
    result = forms.publish(db, context, version.id)
    return result, {f.key: str(f.id) for f in result.fields}


def create(client, data, version, tenant=0):
    result = client.post(
        "/api/v1/submissions",
        headers=headers(data, tenant),
        json={
            "form_version_id": str(version.id),
            "vehicle_id": str(data[4][tenant].id),
            "driver_id": str(data[5][tenant].id),
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_complete_cycle_server_time_and_audit(client, db, data, monkeypatch):
    version, fields = definition(db, data)
    start = datetime(2026, 9, 9, 12, tzinfo=UTC)
    monkeypatch.setattr(runner, "now", lambda: start)
    record = create(client, data, version)
    path = f"/api/v1/submissions/{record['id']}"
    h = headers(data)
    period_path = path + f"/periods/{fields['wait']}"
    assert client.post(period_path + "/finish", headers=h).status_code == 409
    first = client.post(period_path + "/start", headers=h)
    assert first.status_code == 200, first.text
    assert first.json()["form_name"] == "Ciclo"
    assert {f["id"] for f in first.json()["fields"]} == set(fields.values())
    assert first.json()["periods"][0]["status"] == "ACTIVE"
    assert first.json()["periods"][0]["start_at"] == "2026-09-09T12:00:00Z"
    assert db.query(PeriodValue).one().duration_seconds is None
    monkeypatch.setattr(runner, "now", lambda: start + timedelta(seconds=125))
    active = client.get(path, headers=h).json()
    assert active["periods"][0]["duration_seconds"] == 125
    assert client.post(path + "/submit", headers=h).status_code == 409
    assert (
        client.post(period_path + "/start", headers=h).json()["periods"][0]["start_at"]
        == first.json()["periods"][0]["start_at"]
    )
    assert client.post(path + f"/periods/{fields['unload']}/start", headers=h).status_code == 409
    closed = client.post(period_path + "/finish", headers=h).json()["periods"][0]
    assert closed["duration_seconds"] == 125 and closed["status"] == "CLOSED"
    monkeypatch.setattr(runner, "now", lambda: start + timedelta(hours=5))
    assert client.post(period_path + "/finish", headers=h).json()["periods"][0] == closed
    assert client.post(period_path + "/start", headers=h).status_code == 409
    assert client.post(path + "/submit", headers=h).status_code == 422
    saved = client.put(path + f"/answers/{fields['volume']}", headers=h, json={"value": "8.1250"})
    assert saved.status_code == 200, saved.text
    answer = db.query(FormAnswer).filter_by(field_id=version.fields[2].id).one()
    assert answer.value_decimal == Decimal("8.1250") and answer.value_text is None
    submitted = client.post(path + "/submit", headers=h)
    assert submitted.status_code == 200 and submitted.json()["status"] == "SUBMITTED"
    assert (
        client.post(path + "/submit", headers=h).json()["submitted_at"]
        == submitted.json()["submitted_at"]
    )
    assert (
        client.put(
            path + f"/answers/{fields['volume']}", headers=h, json={"value": "9"}
        ).status_code
        == 409
    )
    events = [a.action for a in db.query(AuditEvent).all()]
    assert events.count("period.started") == 1 and events.count("period.ended") == 1
    assert events.count("form.submitted") == 1


def test_timestamp_injection_and_period_bypass(client, db, data):
    version, fields = definition(db, data)
    record = create(client, data, version)
    path = f"/api/v1/submissions/{record['id']}"
    assert (
        client.post(
            path + f"/periods/{fields['wait']}/start",
            headers=headers(data),
            json={"start_at": "2000-01-01T00:00:00Z"},
        ).status_code
        == 422
    )
    assert (
        client.put(
            path + f"/answers/{fields['wait']}",
            headers=headers(data),
            json={"value": {"start_at": "x"}},
        ).status_code
        == 422
    )
    assert db.query(PeriodValue).count() == 0


def test_concurrency_can_be_enabled(client, db, data):
    version, fields = definition(db, data, concurrent=True)
    record = create(client, data, version)
    for key in ("wait", "unload"):
        response = client.post(
            f"/api/v1/submissions/{record['id']}/periods/{fields[key]}/start", headers=headers(data)
        )
        assert response.status_code == 200, response.text
    assert len(response.json()["periods"]) == 2


@pytest.mark.parametrize(
    "method,suffix,payload",
    [
        ("get", "", None),
        ("post", "/submit", {}),
        ("put", "/answers/volume", {"value": "8"}),
        ("post", "/periods/wait/start", {}),
        ("post", "/periods/wait/finish", {}),
    ],
)
def test_runner_tenant_isolation(client, db, data, method, suffix, payload):
    version, fields = definition(db, data)
    record = create(client, data, version)
    suffix = suffix.replace("volume", fields["volume"]).replace("wait", fields["wait"])
    response = client.request(
        method,
        f"/api/v1/submissions/{record['id']}" + suffix,
        headers=headers(data, 1),
        json=payload,
    )
    assert response.status_code == 404
    assert client.get("/api/v1/submissions", headers=headers(data, 1)).json() == []


def test_foreign_references_and_draft_version(client, db, data):
    version, fields = definition(db, data)
    for key, value in [
        ("vehicle_id", str(data[4][1].id)),
        ("driver_id", str(data[5][1].id)),
        ("branch_id", str(data[2][1].id)),
    ]:
        assert (
            client.post(
                "/api/v1/submissions",
                headers=headers(data),
                json={"form_version_id": str(version.id), key: value},
            ).status_code
            == 404
        )
    assert (
        client.post(
            "/api/v1/submissions",
            headers=headers(data, 1),
            json={"form_version_id": str(version.id)},
        ).status_code
        == 404
    )
    context = TenantContext(data[0][0].id, data[1][0].id, None, Role.OWNER)
    draft = forms.clone_version(db, context, version.id)
    assert (
        client.post(
            "/api/v1/submissions", headers=headers(data), json={"form_version_id": str(draft.id)}
        ).status_code
        == 409
    )


def test_driver_assignment_and_branch_scope(client, db, data):
    version, fields = definition(db, data)
    assigned = create(client, data, version)
    other = client.post(
        "/api/v1/submissions", headers=headers(data), json={"form_version_id": str(version.id)}
    ).json()
    data[3][0].role = Role.DRIVER
    db.commit()
    h = headers(data)
    assert client.get(f"/api/v1/submissions/{assigned['id']}", headers=h).status_code == 200
    assert client.get(f"/api/v1/submissions/{other['id']}", headers=h).status_code == 404
    assert (
        client.post(
            f"/api/v1/submissions/{assigned['id']}/periods/{fields['wait']}/start", headers=h
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/submissions", headers=h, json={"form_version_id": str(version.id)}
        ).status_code
        == 403
    )
    data[3][0].role = Role.MANAGER
    data[3][0].branch_id = data[2][0].id
    db.commit()
    assert client.get(f"/api/v1/submissions/{other['id']}", headers=h).status_code == 404
    assert len(client.get("/api/v1/submissions", headers=h).json()) == 1


@pytest.mark.parametrize(
    "kind,value,column",
    [
        ("TEXT", "ok", "value_text"),
        ("INTEGER", 0, "value_integer"),
        ("DECIMAL", "2.3400", "value_decimal"),
        ("BOOLEAN", False, "value_boolean"),
        ("DATE", "2026-09-09", "value_date"),
        ("TIME", "14:20:00", "value_time"),
        ("DATETIME", "2026-09-09T10:00:00-03:00", "value_datetime"),
        ("SINGLE_SELECT", "a", "value_text"),
        ("MULTI_SELECT", ["a", "b"], "value_json"),
    ],
)
def test_typed_answers(client, db, data, kind, value, column):
    version, fields = definition(db, data, types=[("answer", kind, True)])
    record = create(client, data, version)
    path = f"/api/v1/submissions/{record['id']}"
    response = client.put(
        path + f"/answers/{fields['answer']}", headers=headers(data), json={"value": value}
    )
    assert response.status_code == 200, response.text
    assert getattr(db.query(FormAnswer).one(), column) is not None
    if kind == "DATETIME":
        assert response.json()["answers"][0]["value"] == "2026-09-09T13:00:00Z"
    assert client.post(path + "/submit", headers=headers(data)).status_code == 200


@pytest.mark.parametrize(
    "kind,value",
    [
        ("INTEGER", True),
        ("INTEGER", 1.2),
        ("DECIMAL", 2.34),
        ("DECIMAL", "NaN"),
        ("DECIMAL", "1.00001"),
        ("BOOLEAN", "yes"),
        ("DATE", "yesterday"),
        ("DATETIME", "2026-09-09T10:00:00"),
        ("SINGLE_SELECT", "c"),
        ("MULTI_SELECT", ["a", "a"]),
    ],
)
def test_invalid_answers(client, db, data, kind, value):
    version, fields = definition(db, data, types=[("answer", kind, True)])
    record = create(client, data, version)
    response = client.put(
        f"/api/v1/submissions/{record['id']}/answers/{fields['answer']}",
        headers=headers(data),
        json={"value": value},
    )
    assert response.status_code == 422
    assert db.query(FormAnswer).count() == 0


def test_foreign_field_and_database_tenant_constraints(client, db, data):
    version, fields = definition(db, data)
    foreign, foreign_fields = definition(db, data, tenant=1)
    record = create(client, data, version)
    assert (
        client.put(
            f"/api/v1/submissions/{record['id']}/answers/{foreign_fields['volume']}",
            headers=headers(data),
            json={"value": "1"},
        ).status_code
        == 404
    )
    submission = db.query(FormSubmission).one()
    submission.vehicle_id = data[4][1].id
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_mixed_period_config_respects_exclusive_field(client, db, data):
    context = TenantContext(data[0][0].id, data[1][0].id, None, Role.OWNER)
    version = forms.create_form(db, context, FormCreate(code="MIXED", name="Mixed"))
    for key, concurrent in [("shared", True), ("exclusive", False)]:
        forms.add_field(
            db,
            context,
            version.id,
            FieldCreate(
                key=key,
                label=key,
                field_type="PERIOD",
                config={"status_key": key, "status_label": key, "allow_concurrent": concurrent},
            ),
        )
    version = forms.publish(db, context, version.id)
    for first, second in [(0, 1), (1, 0)]:
        record = create(client, data, version)
        prefix = f"/api/v1/submissions/{record['id']}/periods/"
        assert (
            client.post(
                prefix + str(version.fields[first].id) + "/start", headers=headers(data)
            ).status_code
            == 200
        )
        assert (
            client.post(
                prefix + str(version.fields[second].id) + "/start", headers=headers(data)
            ).status_code
            == 409
        )


def test_server_clock_reversal_does_not_close_period(client, db, data, monkeypatch):
    version, fields = definition(db, data)
    record = create(client, data, version)
    current = datetime(2026, 9, 9, 12, tzinfo=UTC)
    monkeypatch.setattr(runner, "now", lambda: current)
    path = f"/api/v1/submissions/{record['id']}/periods/{fields['wait']}"
    client.post(path + "/start", headers=headers(data))
    monkeypatch.setattr(runner, "now", lambda: current - timedelta(seconds=1))
    assert client.post(path + "/finish", headers=headers(data)).status_code == 409
    assert db.query(PeriodValue).one().end_at is None
