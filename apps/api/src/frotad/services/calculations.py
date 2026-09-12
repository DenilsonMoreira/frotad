from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from frotad.models.forms import FieldType, Form, FormField, FormVersion
from frotad.models.runner import FormAnswer, FormSubmission, SubmissionRelation
from frotad.services import formulas
from frotad.services.tenancy import DomainError

NUMERIC = {FieldType.INTEGER, FieldType.DECIMAL, FieldType.CALCULATED}


def definitions(db, version_id):
    return db.scalars(select(FormField).where(FormField.form_version_id == version_id)).all()


def child_version(db, company_id, config):
    version = db.scalar(
        select(FormVersion)
        .join(Form)
        .where(FormVersion.id == UUID(config["form_version_id"]), Form.company_id == company_id)
    )
    if version is None:
        raise DomainError(404, "subform_version_not_found")
    if version.published_at is None:
        raise DomainError(422, "subform_version_must_be_published")
    if any(f.field_type == FieldType.SUBFORM for f in definitions(db, version.id)):
        raise DomainError(422, "nested_subforms_not_supported")
    return version


def validate_definition(db, company_id, fields):
    by_key = {f.key: f for f in fields}
    children = {}
    dependencies = {}
    for f in fields:
        if f.field_type == FieldType.SUBFORM:
            version = child_version(db, company_id, f.config)
            code = db.get(Form, version.form_id).code
            if code in children:
                raise DomainError(422, "duplicate_subform_code")
            children[code] = {field.key: field for field in definitions(db, version.id)}
    for f in fields:
        if f.field_type != FieldType.CALCULATED:
            continue
        refs, aggregates = formulas.validate(f.config["expression"])
        if any(key not in by_key or by_key[key].field_type not in NUMERIC for key in refs):
            raise DomainError(422, "invalid_numeric_reference")
        for node in aggregates:
            target = children.get(node["form_code"])
            if target is None:
                raise DomainError(422, "unbound_child_aggregation")
            if node["op"] == "sum_children" and (
                node["field_key"] not in target
                or target[node["field_key"]].field_type not in NUMERIC
            ):
                raise DomainError(422, "invalid_child_numeric_reference")
        dependencies[f.key] = refs
    depths, visiting = {}, set()

    def walk(key):
        if key in visiting:
            raise DomainError(422, "cyclic_or_deep_calculation")
        if key in depths:
            return depths[key]
        if key not in dependencies:
            return 0
        visiting.add(key)
        depth = 1 + max((walk(dependency) for dependency in dependencies[key]), default=0)
        visiting.remove(key)
        if depth > 32:
            raise DomainError(422, "cyclic_or_deep_calculation")
        depths[key] = depth
        return depth

    for key in dependencies:
        walk(key)


def child_records(db, record):
    return db.execute(
        select(SubmissionRelation, FormSubmission)
        .join(FormSubmission, SubmissionRelation.child_submission_id == FormSubmission.id)
        .where(
            SubmissionRelation.parent_submission_id == record.id,
            SubmissionRelation.company_id == record.company_id,
            FormSubmission.company_id == record.company_id,
        )
    ).all()


def values(db, record):
    fields = definitions(db, record.form_version_id)
    by_key = {f.key: f for f in fields}
    existing = {
        a.field_id: a
        for a in db.scalars(
            select(FormAnswer).where(
                FormAnswer.submission_id == record.id, FormAnswer.company_id == record.company_id
            )
        ).all()
    }
    calculated = [f for f in fields if f.field_type == FieldType.CALCULATED]
    if record.status == "SUBMITTED":
        return {
            f.id: existing[f.id].value_decimal if f.id in existing else None for f in calculated
        }
    if not calculated:
        return {}
    # Only finalized children feed the parent's operational totals.
    children = [
        (rel, child) for rel, child in child_records(db, record) if child.status == "SUBMITTED"
    ]
    child_ids = [child.id for _, child in children]
    child_answers = (
        db.execute(
            select(
                FormAnswer.submission_id,
                FormField.key,
                FormAnswer.value_integer,
                FormAnswer.value_decimal,
            )
            .join(FormField, FormField.id == FormAnswer.field_id)
            .where(
                FormAnswer.submission_id.in_(child_ids), FormAnswer.company_id == record.company_id
            )
        ).all()
        if child_ids
        else []
    )
    child_data = {}
    for child_id, key, integer, decimal in child_answers:
        child_data[(child_id, key)] = (
            decimal if decimal is not None else (Decimal(integer) if integer is not None else None)
        )
    codes = {
        f.id: db.get(Form, child_version(db, record.company_id, f.config).form_id).code
        for f in fields
        if f.field_type == FieldType.SUBFORM
    }
    cache, visiting = {}, set()

    def aggregate(node):
        selected = [
            child.id
            for relation, child in children
            if codes[relation.relation_field_id] == node["form_code"]
        ]
        if node["op"] == "count_children":
            return Decimal(len(selected))
        return sum(
            (child_data.get((child_id, node["field_key"])) or Decimal(0) for child_id in selected),
            Decimal(0),
        )

    def resolve(key):
        if key in cache:
            return cache[key]
        if key in visiting or len(visiting) >= 33:
            raise ValueError("cyclic calculation")
        visiting.add(key)
        field = by_key[key]
        if field.field_type == FieldType.CALCULATED:
            result = formulas.evaluate(field.config["expression"], resolve, aggregate)
        else:
            answer = existing.get(field.id)
            result = (
                None
                if answer is None
                else (
                    answer.value_decimal
                    if answer.value_decimal is not None
                    else Decimal(answer.value_integer)
                    if answer.value_integer is not None
                    else None
                )
            )
        visiting.remove(key)
        cache[key] = result
        return result

    try:
        return {f.id: resolve(f.key) for f in calculated}
    except ValueError:
        raise DomainError(422, "calculation_out_of_range") from None


def prepare_submit(db, record):
    children = child_records(db, record)
    if any(child.status != "SUBMITTED" for _, child in children):
        raise DomainError(409, "unfinished_children")
    return values(db, record), {rel.relation_field_id for rel, _ in children}
