from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from frotad.models.identity import AuditEvent, Role
from frotad.models.runner import FormAnswer, SubmissionRelation
from frotad.schemas.forms import FieldCreate, FormCreate
from frotad.services import forms
from frotad.services.tenancy import DomainError, TenantContext


def headers(data, tenant=0):
    return {
        "X-Company-ID": str(data[0][tenant].id),
        "Authorization": f"Bearer token-{'ab'[tenant]}",
    }


def context(data, tenant=0):
    return TenantContext(data[0][tenant].id, data[1][tenant].id, None, Role.OWNER)


def build(db, data, tenant=0):
    ctx = context(data, tenant)
    child_versions = {}
    for code, key in [("FORM02", "volume_m3"), ("FORM03", "liters")]:
        version = forms.create_form(db, ctx, FormCreate(code=code, name=code))
        forms.add_field(
            db,
            ctx,
            version.id,
            FieldCreate(key=key, label=key, field_type="DECIMAL", required=True),
        )
        child_versions[code] = forms.publish(db, ctx, version.id)
    parent = forms.create_form(db, ctx, FormCreate(code="FORM01", name="Jornada"))
    for key in ["km_inicio", "km_fim"]:
        forms.add_field(db, ctx, parent.id, FieldCreate(key=key, label=key, field_type="INTEGER"))
    for code, key in [("FORM02", "viagens_registros"), ("FORM03", "abastecimentos")]:
        forms.add_field(
            db,
            ctx,
            parent.id,
            FieldCreate(
                key=key,
                label=key,
                field_type="SUBFORM",
                config={"form_version_id": str(child_versions[code].id)},
            ),
        )
    expressions = {
        "viagens": {"op": "count_children", "form_code": "FORM02"},
        "volume": {"op": "sum_children", "form_code": "FORM02", "field_key": "volume_m3"},
        "diesel": {"op": "sum_children", "form_code": "FORM03", "field_key": "liters"},
        "km_rodados": {"op": "subtract", "left": {"ref": "km_fim"}, "right": {"ref": "km_inicio"}},
        "liters_per_m3": {
            "op": "divide",
            "left": {"ref": "diesel"},
            "right": {"ref": "volume"},
            "zero_behavior": "null",
        },
    }
    for key, expression in expressions.items():
        forms.add_field(
            db,
            ctx,
            parent.id,
            FieldCreate(
                key=key, label=key, field_type="CALCULATED", config={"expression": expression}
            ),
        )
    return forms.publish(db, ctx, parent.id), child_versions


def create(client, data, version, tenant=0):
    response = client.post(
        "/api/v1/submissions",
        headers=headers(data, tenant),
        json={
            "form_version_id": str(version.id),
            "vehicle_id": str(data[4][tenant].id),
            "driver_id": str(data[5][tenant].id),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def field_id(record, key):
    return next(f["id"] for f in record["fields"] if f["key"] == key)


def value(record, key):
    field = field_id(record, key)
    result = next(a["value"] for a in record["answers"] if a["field_id"] == field)
    return Decimal(result) if result is not None else None


def child(client, data, parent, key, request_key=None, tenant=0):
    return client.post(
        f"/api/v1/submissions/{parent['id']}/subforms/{field_id(parent, key)}/children",
        headers=headers(data, tenant),
        json={"request_key": str(request_key or uuid4())},
    )


def write(client, data, record, key, answer):
    response = client.put(
        f"/api/v1/submissions/{record['id']}/answers/{field_id(record, key)}",
        headers=headers(data),
        json={"value": answer},
    )
    assert response.status_code == 200, response.text
    return response.json()


def submit(client, data, record):
    return client.post(f"/api/v1/submissions/{record['id']}/submit", headers=headers(data))


def test_form01_form02_form03_and_frozen_results(client, db, data):
    version, _ = build(db, data)
    parent = create(client, data, version)
    assert value(parent, "viagens") == 0 and value(parent, "liters_per_m3") is None
    parent = write(client, data, parent, "km_inicio", 100)
    parent = write(client, data, parent, "km_fim", 160)
    assert value(parent, "km_rodados") == 60
    for key, answer_key, amount in [
        ("viagens_registros", "volume_m3", "8"),
        ("viagens_registros", "volume_m3", "12"),
        ("abastecimentos", "liters", "50"),
    ]:
        response = child(client, data, parent, key)
        assert response.status_code == 201, response.text
        record = response.json()
        assert (
            record["vehicle_id"] == parent["vehicle_id"]
            and record["driver_id"] == parent["driver_id"]
        )
        write(client, data, record, answer_key, amount)
        assert submit(client, data, parent).status_code == 409
        assert submit(client, data, record).status_code == 200
    result = submit(client, data, parent)
    assert result.status_code == 200, result.text
    frozen = result.json()
    assert value(frozen, "viagens") == 2
    assert value(frozen, "volume") == 20
    assert value(frozen, "diesel") == 50
    assert value(frozen, "liters_per_m3") == Decimal("2.5000")
    assert len(frozen["children"]) == 3
    snapshot = (
        db.query(FormAnswer)
        .filter_by(
            submission_id=UUID(parent["id"]), field_id=UUID(field_id(parent, "liters_per_m3"))
        )
        .one()
    )
    assert snapshot.value_decimal == Decimal("2.5000")
    assert child(client, data, parent, "viagens_registros").status_code == 409
    assert submit(client, data, parent).json()["answers"] == frozen["answers"]
    assert db.query(AuditEvent).filter_by(action="submission.child_created").count() == 3


def test_drafts_and_unrelated_children_not_aggregated(client, db, data):
    version, children = build(db, data)
    parent = create(client, data, version)
    unrelated = create(client, data, children["FORM02"])
    write(client, data, unrelated, "volume_m3", "999")
    submit(client, data, unrelated)
    draft = child(client, data, parent, "viagens_registros").json()
    write(client, data, draft, "volume_m3", "8")
    current = client.get(f"/api/v1/submissions/{parent['id']}", headers=headers(data)).json()
    assert value(current, "viagens") == 0 and value(current, "volume") == 0


def test_child_idempotency_and_driver_permissions(client, db, data):
    version, _ = build(db, data)
    parent = create(client, data, version)
    data[3][0].role = Role.DRIVER
    db.commit()
    request_key = uuid4()
    first = child(client, data, parent, "viagens_registros", request_key)
    repeated = child(client, data, parent, "viagens_registros", request_key)
    assert first.status_code == 201 and first.json()["id"] == repeated.json()["id"]
    assert db.query(SubmissionRelation).count() == 1
    assert child(client, data, parent, "abastecimentos", request_key).status_code == 409
    assert child(client, data, parent, "viagens_registros", tenant=1).status_code == 404


def test_cross_tenant_binding_and_database_relationships(client, db, data):
    version, children = build(db, data)
    other, _ = build(db, data, tenant=1)
    draft = forms.clone_version(db, context(data, 1), other.id)
    with pytest.raises(DomainError) as error:
        forms.add_field(
            db,
            context(data, 1),
            draft.id,
            FieldCreate(
                key="foreign",
                label="Foreign",
                field_type="SUBFORM",
                config={"form_version_id": str(children["FORM02"].id)},
            ),
        )
    assert error.value.status == 404
    parent = create(client, data, version)
    foreign = create(client, data, other, tenant=1)
    record = child(client, data, parent, "viagens_registros")
    assert record.status_code == 201
    relation = db.query(SubmissionRelation).one()
    relation.child_submission_id = UUID(foreign["id"])
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.parametrize(
    "expression",
    [
        {"ref": "missing"},
        {"ref": "text"},
        {"op": "count_children", "form_code": "MISSING"},
    ],
)
def test_invalid_references_block_publication(db, data, expression):
    ctx = context(data)
    version = forms.create_form(db, ctx, FormCreate(code="INVALID", name="Invalid"))
    forms.add_field(db, ctx, version.id, FieldCreate(key="text", label="Text", field_type="TEXT"))
    forms.add_field(
        db,
        ctx,
        version.id,
        FieldCreate(
            key="calc", label="Calc", field_type="CALCULATED", config={"expression": expression}
        ),
    )
    with pytest.raises(DomainError):
        forms.publish(db, ctx, version.id)


def test_cycles_and_derived_field_writes_are_rejected(client, db, data):
    ctx = context(data)
    version = forms.create_form(db, ctx, FormCreate(code="CYCLE", name="Cycle"))
    for key, ref in [("a", "b"), ("b", "a")]:
        forms.add_field(
            db,
            ctx,
            version.id,
            FieldCreate(
                key=key, label=key, field_type="CALCULATED", config={"expression": {"ref": ref}}
            ),
        )
    with pytest.raises(DomainError) as error:
        forms.publish(db, ctx, version.id)
    assert error.value.code == "cyclic_or_deep_calculation"
    parent_version, _ = build(db, data)
    parent = create(client, data, parent_version)
    for key in ("viagens", "viagens_registros"):
        response = client.put(
            f"/api/v1/submissions/{parent['id']}/answers/{field_id(parent, key)}",
            headers=headers(data),
            json={"value": "9"},
        )
        assert response.status_code == 422


def test_draft_source_and_nested_subforms_rejected(db, data):
    version, _ = build(db, data)
    ctx = context(data)
    target = forms.create_form(db, ctx, FormCreate(code="OTHER", name="Other"))
    with pytest.raises(DomainError) as error:
        forms.add_field(
            db,
            ctx,
            target.id,
            FieldCreate(
                key="nested",
                label="Nested",
                field_type="SUBFORM",
                config={"form_version_id": str(version.id)},
            ),
        )
    assert error.value.code == "nested_subforms_not_supported"
    with pytest.raises(DomainError) as error:
        forms.add_field(
            db,
            ctx,
            target.id,
            FieldCreate(
                key="draft",
                label="Draft",
                field_type="SUBFORM",
                config={"form_version_id": str(target.id)},
            ),
        )
    assert error.value.code == "subform_version_must_be_published"


def test_zero_denominator_is_frozen_as_null(client, db, data):
    version, _ = build(db, data)
    parent = create(client, data, version)
    submitted = submit(client, data, parent)
    assert submitted.status_code == 200, submitted.text
    assert value(submitted.json(), "liters_per_m3") is None
    assert value(submitted.json(), "volume") == 0


def test_subform_keeps_published_child_version(client, db, data):
    version, versions = build(db, data)
    ctx = context(data)
    draft = forms.clone_version(db, ctx, versions["FORM02"].id)
    forms.add_field(db, ctx, draft.id, FieldCreate(key="later", label="Later", field_type="TEXT"))
    forms.publish(db, ctx, draft.id)
    parent = create(client, data, version)
    response = child(client, data, parent, "viagens_registros")
    assert response.json()["form_version_id"] == str(versions["FORM02"].id)
    assert "later" not in {f["key"] for f in response.json()["fields"]}


def test_overflow_rolls_back_answer(client, db, data):
    ctx = context(data)
    version = forms.create_form(db, ctx, FormCreate(code="OVERFLOW", name="Overflow"))
    forms.add_field(
        db, ctx, version.id, FieldCreate(key="input", label="Input", field_type="DECIMAL")
    )
    forms.add_field(
        db,
        ctx,
        version.id,
        FieldCreate(
            key="calc",
            label="Calc",
            field_type="CALCULATED",
            config={
                "expression": {"op": "multiply", "left": {"ref": "input"}, "right": {"const": 2}}
            },
        ),
    )
    version = forms.publish(db, ctx, version.id)
    record = create(client, data, version)
    record = write(client, data, record, "input", "2")
    response = client.put(
        f"/api/v1/submissions/{record['id']}/answers/{field_id(record, 'input')}",
        headers=headers(data),
        json={"value": "99999999999999"},
    )
    assert response.status_code == 422
    current = client.get(f"/api/v1/submissions/{record['id']}", headers=headers(data)).json()
    assert value(current, "input") == 2 and value(current, "calc") == 4
