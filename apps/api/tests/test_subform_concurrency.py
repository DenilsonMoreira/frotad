from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from frotad.models import Company, User
from frotad.models.identity import Role
from frotad.models.runner import FormSubmission, SubmissionRelation
from frotad.schemas.forms import FieldCreate, FormCreate
from frotad.schemas.runner import SubmissionCreate
from frotad.services import forms, runner, subforms
from frotad.services.tenancy import DomainError, TenantContext


def prepare(engine):
    with Session(engine) as db:
        company, user = (
            Company(name="Test", slug="test"),
            User(name="Owner", email="subform@example.test"),
        )
        db.add_all([company, user])
        db.commit()
        ctx = TenantContext(company.id, user.id, None, Role.OWNER)
        child = forms.create_form(db, ctx, FormCreate(code="CHILD", name="Child"))
        forms.add_field(
            db, ctx, child.id, FieldCreate(key="v", label="Value", field_type="DECIMAL")
        )
        child = forms.publish(db, ctx, child.id)
        parent = forms.create_form(db, ctx, FormCreate(code="PARENT", name="Parent"))
        forms.add_field(
            db,
            ctx,
            parent.id,
            FieldCreate(
                key="children",
                label="Children",
                field_type="SUBFORM",
                config={"form_version_id": str(child.id)},
            ),
        )
        version = forms.publish(db, ctx, parent.id)
        parent = runner.create(db, ctx, SubmissionCreate(form_version_id=version.id))
        return ctx, parent, version.fields[0].id


@pytest.mark.parametrize("race", ["duplicate", "submit"])
def test_child_creation_is_serialized_with_parent(migrated_engine, race):
    if migrated_engine.dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL row locking")
    ctx, parent, field_id = prepare(migrated_engine)
    barrier, request_key = Barrier(2), uuid4()

    def operation(second):
        with Session(migrated_engine) as db:
            barrier.wait(timeout=10)
            try:
                if second and race == "submit":
                    return runner.submit(db, ctx, parent.id).status
                return subforms.create_child(db, ctx, parent.id, field_id, request_key).id
            except DomainError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(operation, second) for second in (False, True)]
        results = [f.result(timeout=20) for f in futures]
    with Session(migrated_engine) as db:
        relations = db.scalars(select(SubmissionRelation)).all()
        status = db.get(FormSubmission, parent.id).status
    if race == "duplicate":
        assert results[0] == results[1] and len(relations) == 1
    elif status == "SUBMITTED":
        assert len(relations) == 0 and "submitted_record_immutable" in results
    else:
        assert len(relations) == 1 and "unfinished_children" in results
