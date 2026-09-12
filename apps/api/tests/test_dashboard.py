from datetime import UTC, datetime, timedelta

from test_runner import create, definition, headers

from frotad.models.identity import Role
from frotad.services import dashboard, runner


def test_live_isolation_permissions_and_server_duration(client, db, data, monkeypatch):
    clock = datetime(2026, 9, 12, 12, tzinfo=UTC)
    monkeypatch.setattr(runner, "now", lambda: clock - timedelta(days=2))
    monkeypatch.setattr(dashboard, "now", lambda: clock)
    for tenant in (0, 1):
        version, fields = definition(db, data, tenant=tenant)
        record = create(client, data, version, tenant=tenant)
        assert (
            client.post(
                f"/api/v1/submissions/{record['id']}/periods/{fields['wait']}/start",
                headers=headers(data, tenant),
            ).status_code
            == 200
        )
    result = client.get("/api/v1/dashboard", headers=headers(data))
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    body = result.json()
    assert body["company"] == "alpha"
    assert len(body["active"]) == 1
    assert body["active"][0]["driver"] == "alice"
    assert body["active"][0]["elapsed_seconds"] == 172800
    assert body["active_vehicles"] == 1
    assert body["metrics"]["liters_per_m3"] is None
    assert (
        client.get("/api/v1/dashboard", headers={"X-Company-ID": str(data[0][0].id)}).status_code
        == 401
    )
    data[3][0].role = Role.MAINTENANCE
    db.commit()
    assert client.get("/api/v1/dashboard", headers=headers(data)).status_code == 403
    data[3][0].role = Role.DRIVER
    db.commit()
    assert len(client.get("/api/v1/dashboard", headers=headers(data)).json()["active"]) == 1
    data[5][0].active = False
    db.commit()
    assert client.get("/api/v1/dashboard", headers=headers(data)).json()["active"] == []


def test_local_day_totals_mapping_and_draft_exclusion(client, db, data, monkeypatch):
    data[0][0].settings = {
        "dashboard": {
            "cycle_form": "CYCLE",
            "volume_field": "volume",
            "fuel_form": "CYCLE",
            "fuel_field": "diesel",
            "target_liters_per_m3": "2.5",
        }
    }
    db.commit()
    version, fields = definition(
        db, data, types=[("volume", "DECIMAL", False), ("diesel", "DECIMAL", False)]
    )
    clock = datetime(2026, 9, 12, 2, 59, tzinfo=UTC)
    monkeypatch.setattr(runner, "now", lambda: clock)
    monkeypatch.setattr(dashboard, "now", lambda: clock)
    for volume, diesel, submitted in [("8", "20", True), ("2", "10", True), ("999", "999", False)]:
        record = create(client, data, version)
        path = f"/api/v1/submissions/{record['id']}"
        for key, value in [("volume", volume), ("diesel", diesel)]:
            assert (
                client.put(
                    path + f"/answers/{fields[key]}", headers=headers(data), json={"value": value}
                ).status_code
                == 200
            )
        if submitted:
            assert client.post(path + "/submit", headers=headers(data)).status_code == 200
    body = client.get("/api/v1/dashboard", headers=headers(data)).json()
    assert body["metrics"] == {
        "day": "2026-09-11",
        "missing_measurements": 0,
        "trips": 2,
        "volume_m3": "10.0000",
        "diesel_liters": "30.0000",
        "liters_per_m3": "3.0000",
    }
    assert len(body["trend"]) == 7
    assert body["target_liters_per_m3"] == "2.5"
    next_day = client.get("/api/v1/dashboard?day=2026-09-12", headers=headers(data)).json()
    assert next_day["metrics"]["trips"] == 0
    assert next_day["metrics"]["liters_per_m3"] is None
    data[3][0].branch_id = data[2][0].id
    db.commit()
    # Assigned vehicle inherits this branch, so it remains visible.
    assert client.get("/api/v1/dashboard", headers=headers(data)).json()["metrics"]["trips"] == 2


def test_missing_measurement_disables_ratio(client, db, data):
    data[0][0].settings = {"dashboard": {"cycle_form": "CYCLE", "volume_field": "volume"}}
    db.commit()
    version, _ = definition(db, data, types=[("volume", "DECIMAL", False)])
    record = create(client, data, version)
    assert (
        client.post(f"/api/v1/submissions/{record['id']}/submit", headers=headers(data)).status_code
        == 200
    )
    body = client.get("/api/v1/dashboard", headers=headers(data)).json()
    assert body["metrics"]["missing_measurements"] == 1
    assert body["metrics"]["liters_per_m3"] is None
    assert client.get("/api/v1/dashboard", headers=headers(data, 1)).json()["metrics"]["trips"] == 0
