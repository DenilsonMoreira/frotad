from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from frotad.models import Company, User
from frotad.models.forms import FormField, FormVersion
from frotad.models.identity import Role
from frotad.schemas.forms import FieldCreate, FormCreate
from frotad.services import forms
from frotad.services.tenancy import DomainError, TenantContext


def published(engine):
    with Session(engine) as db:
        company = Company(name="Test", slug="test")
        user = User(name="Owner", email="owner@example.test")
        db.add_all([company, user])
        db.commit()
        context = TenantContext(company.id, user.id, None, Role.OWNER)
        draft = forms.create_form(db, context, FormCreate(code="TEST", name="Test"))
        forms.add_field(db, context, draft.id, FieldCreate(key="a", label="A", field_type="TEXT"))
        version = forms.publish(db, context, draft.id)
        return context, version


def test_database_guards_published_content(migrated_engine):
    context, version = published(migrated_engine)
    field_id = version.fields[0].id
    for statement in (
        update(FormVersion).where(FormVersion.id == version.id).values(name="Changed"),
        update(FormVersion).where(FormVersion.id == version.id).values(published_at=None),
        delete(FormVersion).where(FormVersion.id == version.id),
        update(FormField).where(FormField.id == field_id).values(label="Changed"),
        delete(FormField).where(FormField.id == field_id),
    ):
        with Session(migrated_engine) as db:
            with pytest.raises(IntegrityError):
                db.execute(statement)
                db.commit()
    with Session(migrated_engine) as db:
        db.add(
            FormField(
                form_version_id=version.id, key="new", label="New", field_type="TEXT", position=1
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
    with Session(migrated_engine) as db:
        clone = forms.clone_version(db, context, version.id)
        assert clone.version == 2
        assert forms.get_version(db, context, version.id).schema_hash == version.schema_hash


def test_concurrent_clone_creates_exactly_one_draft(migrated_engine):
    if migrated_engine.dialect.name != "postgresql":
        pytest.skip("row locking is tested on PostgreSQL")
    context, version = published(migrated_engine)
    barrier = Barrier(2)

    def clone():
        with Session(migrated_engine) as db:
            barrier.wait(timeout=10)
            try:
                return forms.clone_version(db, context, version.id).version
            except DomainError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(clone) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert sorted(map(str, results)) == ["2", "draft_already_exists"]


def test_publish_and_add_are_serialized(migrated_engine):
    if migrated_engine.dialect.name != "postgresql":
        pytest.skip("row locking is tested on PostgreSQL")
    context, version = published(migrated_engine)
    with Session(migrated_engine) as db:
        draft = forms.clone_version(db, context, version.id)
    barrier = Barrier(2)

    def operation(publish):
        with Session(migrated_engine) as db:
            barrier.wait(timeout=10)
            try:
                if publish:
                    return forms.publish(db, context, draft.id)
                return forms.add_field(
                    db, context, draft.id, FieldCreate(key="b", label="B", field_type="TEXT")
                )
            except DomainError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        publisher = executor.submit(operation, True)
        editor = executor.submit(operation, False)
        snapshot = publisher.result(timeout=20)
        edit = editor.result(timeout=20)
    with Session(migrated_engine) as db:
        current = forms.get_version(db, context, draft.id)
        assert current == snapshot
        assert len(current.fields) == (1 if edit == "published_version_immutable" else 2)
