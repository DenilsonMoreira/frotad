from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from frotad.models import Company, User
from frotad.models.identity import AuditEvent, Role
from frotad.models.runner import PeriodValue
from frotad.schemas.forms import FieldCreate, FormCreate
from frotad.schemas.runner import SubmissionCreate
from frotad.services import forms, runner
from frotad.services.tenancy import DomainError, TenantContext


@pytest.mark.parametrize("concurrent,same_field", [(False, False), (True, False), (False, True)])
def test_simultaneous_period_starts(migrated_engine, concurrent, same_field):
    if migrated_engine.dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL row locks")
    with Session(migrated_engine) as db:
        company = Company(name="Test", slug="periods")
        user = User(name="Owner", email="period@example.test")
        db.add_all([company, user])
        db.commit()
        context = TenantContext(company.id, user.id, None, Role.OWNER)
        draft = forms.create_form(db, context, FormCreate(code="PERIOD", name="Period"))
        for key in ("wait", "unload"):
            forms.add_field(
                db,
                context,
                draft.id,
                FieldCreate(
                    key=key,
                    label=key,
                    field_type="PERIOD",
                    config={"status_key": key, "status_label": key, "allow_concurrent": concurrent},
                ),
            )
        version = forms.publish(db, context, draft.id)
        record = runner.create(db, context, SubmissionCreate(form_version_id=version.id))
    barrier = Barrier(2)

    def start(index):
        with Session(migrated_engine) as db:
            barrier.wait(timeout=10)
            try:
                runner.start_period(
                    db, context, record.id, version.fields[0 if same_field else index].id
                )
                return "ok"
            except DomainError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(start, i) for i in range(2)]
        results = [f.result(timeout=20) for f in futures]
    assert results.count("ok") == (2 if concurrent or same_field else 1)
    if not concurrent and not same_field:
        assert "active_period_conflict" in results
    with Session(migrated_engine) as db:
        expected = 2 if concurrent and not same_field else 1
        assert len(db.scalars(select(PeriodValue)).all()) == expected
        assert (
            len(db.scalars(select(AuditEvent).where(AuditEvent.action == "period.started")).all())
            == expected
        )
