from sqlalchemy import func, select

from frotad.models.forms import FieldType
from frotad.models.runner import SubmissionRelation
from frotad.schemas.runner import SubmissionCreate
from frotad.services import runner
from frotad.services.calculations import child_version
from frotad.services.forms import audit, commit
from frotad.services.tenancy import DomainError


def create_child(db, context, parent_id, field_id, request_key):
    parent = runner.submission(db, context, parent_id, write=True)
    field = runner.field(db, parent, field_id)
    if field.field_type != FieldType.SUBFORM:
        raise DomainError(422, "subform_field_required")
    existing = db.scalar(
        select(SubmissionRelation).where(
            SubmissionRelation.parent_submission_id == parent.id,
            SubmissionRelation.request_key == request_key,
            SubmissionRelation.company_id == context.company_id,
        )
    )
    if existing:
        if existing.relation_field_id != field_id:
            raise DomainError(409, "request_key_reused")
        return runner.get(db, context, existing.child_submission_id)
    runner.require_draft(parent)
    if db.scalar(
        select(SubmissionRelation.id).where(SubmissionRelation.child_submission_id == parent.id)
    ):
        raise DomainError(422, "nested_subforms_not_supported")
    count = db.scalar(
        select(func.count())
        .select_from(SubmissionRelation)
        .where(
            SubmissionRelation.parent_submission_id == parent.id,
            SubmissionRelation.company_id == context.company_id,
        )
    )
    if count >= 1000:
        raise DomainError(422, "child_limit_reached")
    version = child_version(db, context.company_id, field.config)
    child = runner.new_submission(
        db,
        context,
        SubmissionCreate(
            form_version_id=version.id,
            vehicle_id=parent.vehicle_id,
            driver_id=parent.driver_id,
            branch_id=parent.branch_id,
        ),
    )
    child.timezone = parent.timezone
    db.add(
        SubmissionRelation(
            company_id=context.company_id,
            parent_submission_id=parent.id,
            child_submission_id=child.id,
            parent_version_id=parent.form_version_id,
            relation_field_id=field.id,
            request_key=request_key,
        )
    )
    audit(db, context, parent.id, "submission.child_created")
    commit(db)
    return runner.view(db, child)
