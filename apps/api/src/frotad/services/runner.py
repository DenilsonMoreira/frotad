from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select

from frotad.models import Branch, Company, Driver, Vehicle
from frotad.models.forms import FieldType, Form, FormField, FormVersion
from frotad.models.identity import Role
from frotad.models.runner import FormAnswer, FormSubmission, PeriodValue
from frotad.schemas.forms import FieldRead
from frotad.schemas.runner import AnswerRead, PeriodRead, SubmissionRead
from frotad.services.forms import audit, commit
from frotad.services.periods import period_duration_seconds
from frotad.services.tenancy import DomainError

SUPPORTED = {
    FieldType.TEXT,
    FieldType.INTEGER,
    FieldType.DECIMAL,
    FieldType.BOOLEAN,
    FieldType.DATE,
    FieldType.TIME,
    FieldType.DATETIME,
    FieldType.SINGLE_SELECT,
    FieldType.MULTI_SELECT,
    FieldType.VEHICLE_REFERENCE,
    FieldType.DRIVER_REFERENCE,
    FieldType.PERIOD,
}
VALUE_COLUMNS = (
    "value_text",
    "value_integer",
    "value_decimal",
    "value_boolean",
    "value_date",
    "value_time",
    "value_datetime",
    "value_json",
)


def now():
    return datetime.now(UTC)


def utc(value):
    # SQLite drops tzinfo. All stored timestamps have already been normalized to UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def scope(context, write=False):
    context.require("runner:write" if write else "runner:read")
    query = select(FormSubmission).where(FormSubmission.company_id == context.company_id)
    if context.branch_id is not None:
        query = query.where(FormSubmission.branch_id == context.branch_id)
    if context.role == Role.DRIVER:
        query = query.where(
            FormSubmission.driver_id.in_(
                select(Driver.id).where(
                    Driver.company_id == context.company_id,
                    Driver.user_id == context.user_id,
                    Driver.active.is_(True),
                )
            )
        )
    return query


def submission(db, context, submission_id, write=False):
    query = scope(context, write).where(FormSubmission.id == submission_id)
    if write:
        query = query.with_for_update()
    record = db.scalar(query)
    if record is None:
        raise DomainError(404, "not_found")
    return record


def require_draft(record):
    if record.status != "DRAFT":
        raise DomainError(409, "submitted_record_immutable")


def field(db, record, field_id):
    result = db.scalar(
        select(FormField).where(
            FormField.id == field_id, FormField.form_version_id == record.form_version_id
        )
    )
    if result is None:
        raise DomainError(404, "field_not_found")
    return result


def answers(db, record):
    return db.scalars(
        select(FormAnswer)
        .where(FormAnswer.submission_id == record.id, FormAnswer.company_id == record.company_id)
        .order_by(FormAnswer.field_id)
    ).all()


def periods(db, record):
    return db.execute(
        select(PeriodValue, FormAnswer.field_id)
        .join(FormAnswer, PeriodValue.answer_id == FormAnswer.id)
        .where(PeriodValue.submission_id == record.id, PeriodValue.company_id == record.company_id)
        .order_by(PeriodValue.start_at, PeriodValue.id)
    ).all()


def answer_value(answer):
    value = next(
        (getattr(answer, col) for col in VALUE_COLUMNS if getattr(answer, col) is not None), None
    )
    return utc(value) if isinstance(value, datetime) else value


def view(db, record):
    server_time = now()
    return SubmissionRead(
        id=record.id,
        form_version_id=record.form_version_id,
        form_name=db.get(FormVersion, record.form_version_id).name,
        fields=[
            FieldRead.model_validate(f)
            for f in db.scalars(
                select(FormField)
                .where(FormField.form_version_id == record.form_version_id)
                .order_by(FormField.position)
            ).all()
        ],
        vehicle_id=record.vehicle_id,
        driver_id=record.driver_id,
        branch_id=record.branch_id,
        timezone=record.timezone,
        status=record.status,
        started_at=utc(record.started_at),
        submitted_at=utc(record.submitted_at) if record.submitted_at else None,
        server_time=server_time,
        answers=[
            AnswerRead(field_id=a.field_id, value=answer_value(a)) for a in answers(db, record)
        ],
        periods=[
            PeriodRead(
                field_id=field_id,
                start_at=utc(p.start_at),
                end_at=utc(p.end_at) if p.end_at else None,
                duration_seconds=p.duration_seconds
                if p.end_at
                else period_duration_seconds(utc(p.start_at), None, now=server_time),
                status_key=p.status_key,
                status="ACTIVE" if p.end_at is None else "CLOSED",
            )
            for p, field_id in periods(db, record)
        ],
    )


def reference(db, context, model, record_id):
    if record_id is None:
        return None
    obj = db.scalar(
        select(model).where(model.id == record_id, model.company_id == context.company_id)
    )
    if obj is None or (hasattr(obj, "active") and not obj.active):
        raise DomainError(404, "reference_not_found")
    return obj


def create(db, context, payload):
    context.require("runner:create")
    version = db.scalar(
        select(FormVersion)
        .join(Form)
        .where(FormVersion.id == payload.form_version_id, Form.company_id == context.company_id)
    )
    if version is None:
        raise DomainError(404, "not_found")
    if version.published_at is None:
        raise DomainError(409, "published_version_required")
    definitions = db.scalars(select(FormField).where(FormField.form_version_id == version.id)).all()
    if any(f.field_type not in SUPPORTED for f in definitions):
        raise DomainError(422, "unsupported_runner_field")
    if any(
        f.config.get("capture_location_on_start") or f.config.get("capture_location_on_end")
        for f in definitions
    ):
        raise DomainError(422, "location_capture_not_implemented")
    vehicle = reference(db, context, Vehicle, payload.vehicle_id)
    reference(db, context, Driver, payload.driver_id)
    branch_id = payload.branch_id or (vehicle.branch_id if vehicle else None) or context.branch_id
    branch = reference(db, context, Branch, branch_id)
    if context.branch_id is not None and branch_id != context.branch_id:
        raise DomainError(403, "branch_scope_required")
    if vehicle and vehicle.branch_id != branch_id:
        raise DomainError(422, "vehicle_branch_mismatch")
    company = db.get(Company, context.company_id)
    record = FormSubmission(
        company_id=context.company_id,
        form_id=version.form_id,
        form_version_id=version.id,
        vehicle_id=payload.vehicle_id,
        driver_id=payload.driver_id,
        branch_id=branch_id,
        timezone=(branch.timezone if branch else None) or company.timezone,
        created_by=context.user_id,
        started_at=now(),
    )
    db.add(record)
    db.flush()
    audit(db, context, record.id, "submission.created")
    commit(db)
    return view(db, record)


def get(db, context, submission_id):
    return view(db, submission(db, context, submission_id))


def list_submissions(db, context, offset, limit):
    records = db.scalars(
        scope(context)
        .order_by(FormSubmission.started_at.desc(), FormSubmission.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [view(db, record) for record in records]


def typed_value(db, context, record, definition, value):
    kind = definition.field_type
    if kind not in SUPPORTED or kind == FieldType.PERIOD:
        raise DomainError(
            422, "use_period_commands" if kind == FieldType.PERIOD else "unsupported_runner_field"
        )
    if value is None:
        return {}
    try:
        if kind == FieldType.INTEGER:
            if type(value) is not int or not -(2**31) <= value < 2**31:
                raise ValueError()
            return {"value_integer": value}
        if kind == FieldType.DECIMAL:
            if type(value) not in (str, int):
                raise ValueError()
            number = Decimal(value)
            if (
                not number.is_finite()
                or abs(number) >= Decimal("100000000000000")
                or number != number.quantize(Decimal("0.0001"))
            ):
                raise ValueError()
            return {"value_decimal": number}
        if kind == FieldType.BOOLEAN:
            if type(value) is not bool:
                raise ValueError()
            return {"value_boolean": value}
        if kind == FieldType.MULTI_SELECT:
            if (
                not isinstance(value, list)
                or any(type(v) is not str for v in value)
                or len(set(value)) != len(value)
            ):
                raise ValueError()
            if not set(value) <= set(definition.config["options"]):
                raise ValueError()
            return {"value_json": value}
        if type(value) is not str or len(value) > 10000:
            raise ValueError()
        if kind == FieldType.DATE:
            return {"value_date": date.fromisoformat(value)}
        if kind == FieldType.TIME:
            parsed = time.fromisoformat(value)
            if parsed.tzinfo is not None:
                raise ValueError()
            return {"value_time": parsed}
        if kind == FieldType.DATETIME:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                raise ValueError()
            return {"value_datetime": parsed.astimezone(UTC)}
        if kind == FieldType.SINGLE_SELECT and value not in definition.config["options"]:
            raise ValueError()
        if kind in (FieldType.VEHICLE_REFERENCE, FieldType.DRIVER_REFERENCE):
            obj = reference(
                db, context, Vehicle if kind == FieldType.VEHICLE_REFERENCE else Driver, UUID(value)
            )
            if (
                kind == FieldType.VEHICLE_REFERENCE
                and record.branch_id is not None
                and obj.branch_id != record.branch_id
            ):
                raise DomainError(422, "vehicle_branch_mismatch")
            if context.role == Role.DRIVER and (
                obj.id
                != (record.vehicle_id if kind == FieldType.VEHICLE_REFERENCE else record.driver_id)
            ):
                raise DomainError(403, "assigned_reference_required")
            value = str(obj.id)
        return {"value_text": value}
    except ValueError, TypeError, InvalidOperation:
        raise DomainError(422, "invalid_answer_value") from None


def get_answer(db, record, field_id):
    return db.scalar(
        select(FormAnswer).where(
            FormAnswer.submission_id == record.id,
            FormAnswer.company_id == record.company_id,
            FormAnswer.field_id == field_id,
        )
    )


def new_answer(record, field_id):
    return FormAnswer(
        submission_id=record.id,
        company_id=record.company_id,
        form_version_id=record.form_version_id,
        field_id=field_id,
    )


def save_answer(db, context, submission_id, field_id, value):
    record = submission(db, context, submission_id, write=True)
    require_draft(record)
    definition = field(db, record, field_id)
    values = typed_value(db, context, record, definition, value)
    answer = get_answer(db, record, field_id) or new_answer(record, field_id)
    for col in VALUE_COLUMNS:
        setattr(answer, col, values.get(col))
    db.add(answer)
    audit(db, context, record.id, "submission.answer_saved")
    commit(db)
    return view(db, record)


def start_period(db, context, submission_id, field_id):
    record = submission(db, context, submission_id, write=True)
    require_draft(record)
    definition = field(db, record, field_id)
    if definition.field_type != FieldType.PERIOD:
        raise DomainError(422, "period_field_required")
    existing = periods(db, record)
    for period, existing_field_id in existing:
        if existing_field_id == field_id:
            if period.end_at is None:
                return view(db, record)
            raise DomainError(409, "period_already_closed")
    concurrent = definition.config.get("allow_concurrent", False)
    if any(p.end_at is None and (not concurrent or not p.allow_concurrent) for p, _ in existing):
        raise DomainError(409, "active_period_conflict")
    answer = new_answer(record, field_id)
    db.add(answer)
    db.flush()
    db.add(
        PeriodValue(
            company_id=context.company_id,
            submission_id=record.id,
            answer_id=answer.id,
            start_at=now(),
            status_key=definition.config["status_key"],
            allow_concurrent=concurrent,
        )
    )
    audit(db, context, record.id, "period.started")
    commit(db)
    return view(db, record)


def finish_period(db, context, submission_id, field_id):
    record = submission(db, context, submission_id, write=True)
    definition = field(db, record, field_id)
    if definition.field_type != FieldType.PERIOD:
        raise DomainError(422, "period_field_required")
    period = next((p for p, f in periods(db, record) if f == field_id), None)
    if period is None:
        raise DomainError(409, "period_not_started")
    if period.end_at is not None:
        return view(db, record)
    require_draft(record)
    end = now()
    if end < utc(period.start_at):
        raise DomainError(409, "server_clock_before_start")
    period.end_at = end
    period.duration_seconds = period_duration_seconds(utc(period.start_at), end)
    audit(db, context, record.id, "period.ended")
    commit(db)
    return view(db, record)


def submit(db, context, submission_id):
    record = submission(db, context, submission_id, write=True)
    if record.status == "SUBMITTED":
        return view(db, record)
    running = periods(db, record)
    if any(p.end_at is None for p, _ in running):
        raise DomainError(409, "active_periods_remaining")
    closed = {field_id for p, field_id in running}
    provided = {
        a.field_id
        for a in answers(db, record)
        if any(
            getattr(a, col) is not None
            and getattr(a, col) != []
            and (not isinstance(getattr(a, col), str) or getattr(a, col).strip())
            for col in VALUE_COLUMNS
        )
    }
    required = db.scalars(
        select(FormField).where(
            FormField.form_version_id == record.form_version_id, FormField.required.is_(True)
        )
    ).all()
    if any(
        f.id not in (closed if f.field_type == FieldType.PERIOD else provided) for f in required
    ):
        raise DomainError(422, "required_answers_missing")
    record.status = "SUBMITTED"
    record.submitted_at = now()
    audit(db, context, record.id, "form.submitted")
    commit(db)
    return view(db, record)
