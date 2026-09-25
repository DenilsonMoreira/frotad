import json
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from frotad.models.forms import Form, FormField, FormStatus, FormVersion
from frotad.models.identity import AuditEvent
from frotad.schemas.forms import FieldCreate, FieldRead, FormCreate, VersionRead
from frotad.services.tenancy import DomainError, TenantContext


def audit(db, context, entity_id, action):
    db.add(
        AuditEvent(
            company_id=context.company_id,
            actor_user_id=context.user_id,
            entity_id=entity_id,
            action=action,
            occurred_at=datetime.now(UTC),
        )
    )


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "form_conflict") from None


def fields(db, version_id):
    return db.scalars(
        select(FormField)
        .where(FormField.form_version_id == version_id)
        .order_by(FormField.position, FormField.id)
    ).all()


def view(db, version):
    return VersionRead(
        id=version.id,
        form_id=version.form_id,
        version=version.version,
        name=version.name,
        description=version.description,
        published_at=version.published_at,
        schema_hash=version.schema_hash,
        fields=[FieldRead.model_validate(f) for f in fields(db, version.id)],
    )


def scoped_version(db: Session, context: TenantContext, version_id: UUID, write=False):
    context.require("forms:write" if write else "forms:read")
    # Lock the root before the version in every write path, including clone/publish.
    form_query = (
        select(Form)
        .join(FormVersion)
        .where(FormVersion.id == version_id, Form.company_id == context.company_id)
    )
    if write:
        form_query = form_query.with_for_update(of=Form)
    form = db.scalar(form_query)
    if form is None:
        raise DomainError(404, "not_found")
    query = select(FormVersion).where(FormVersion.id == version_id, FormVersion.form_id == form.id)
    if write:
        query = query.with_for_update()
    return form, db.scalar(query)


def require_draft(version):
    if version.published_at is not None:
        raise DomainError(409, "published_version_immutable")


def create_form(db, context, payload: FormCreate):
    context.require("forms:write")
    form = Form(company_id=context.company_id, **payload.model_dump())
    db.add(form)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "form_code_exists") from None
    version = FormVersion(
        form_id=form.id,
        version=1,
        name=form.name,
        description=form.description,
        created_by=context.user_id,
    )
    db.add(version)
    db.flush()
    audit(db, context, form.id, "form.created")
    commit(db)
    return view(db, version)


def get_version(db, context, version_id):
    _, version = scoped_version(db, context, version_id)
    return view(db, version)


def add_field(db, context, version_id, payload: FieldCreate):
    _, version = scoped_version(db, context, version_id, write=True)
    require_draft(version)
    existing = fields(db, version.id)
    if len(existing) >= 200:
        raise DomainError(422, "field_limit_reached")
    if any(field.key == payload.key for field in existing):
        raise DomainError(409, "field_key_exists")
    field = FormField(form_version_id=version.id, position=len(existing), **payload.model_dump())
    db.add(field)
    audit(db, context, version.id, "form.field_added")
    commit(db)
    return view(db, version)


def reorder_fields(db, context, version_id, field_ids):
    _, version = scoped_version(db, context, version_id, write=True)
    require_draft(version)
    existing = {field.id: field for field in fields(db, version.id)}
    if len(field_ids) != len(existing) or set(field_ids) != set(existing):
        raise DomainError(422, "reorder_requires_all_fields")
    for position, field_id in enumerate(field_ids):
        existing[field_id].position = position
    audit(db, context, version.id, "form.fields_reordered")
    commit(db)
    return view(db, version)


def publish(db, context, version_id):
    form, version = scoped_version(db, context, version_id, write=True)
    require_draft(version)
    definition = fields(db, version.id)
    if not definition:
        raise DomainError(422, "empty_form")
    snapshot = {
        "name": version.name,
        "description": version.description,
        "fields": [
            {
                "key": f.key,
                "label": f.label,
                "field_type": f.field_type.value,
                "position": f.position,
                "required": f.required,
                "config": f.config,
            }
            for f in definition
        ],
    }
    version.schema_hash = sha256(
        json.dumps(
            snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()
    version.published_at = datetime.now(UTC)
    form.status = FormStatus.PUBLISHED
    audit(db, context, version.id, "form.published")
    commit(db)
    return view(db, version)


def clone_version(db, context, version_id):
    form, source = scoped_version(db, context, version_id, write=True)
    if source.published_at is None:
        raise DomainError(409, "published_source_required")
    if db.scalar(
        select(FormVersion.id).where(
            FormVersion.form_id == form.id, FormVersion.published_at.is_(None)
        )
    ):
        raise DomainError(409, "draft_already_exists")
    number = (
        db.scalar(select(func.max(FormVersion.version)).where(FormVersion.form_id == form.id)) + 1
    )
    version = FormVersion(
        form_id=form.id,
        version=number,
        name=source.name,
        description=source.description,
        created_by=context.user_id,
    )
    db.add(version)
    db.flush()
    for field in fields(db, source.id):
        db.add(
            FormField(
                form_version_id=version.id,
                key=field.key,
                label=field.label,
                field_type=field.field_type,
                position=field.position,
                required=field.required,
                config=deepcopy(field.config),
            )
        )
    audit(db, context, version.id, "form.version_created")
    commit(db)
    return view(db, version)
