from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from frotad.models.fleet import Driver, Vehicle
from frotad.services.tenancy import DomainError, TenantContext


def fleet_query(context: TenantContext, model):
    context.require("fleet:read")
    query = select(model).where(model.company_id == context.company_id)
    if context.branch_id is not None:
        if model is Driver:
            # Driver branch assignments are not implemented yet: fail closed.
            raise DomainError(403, "branch_driver_scope_unavailable")
        query = query.where(Vehicle.branch_id == context.branch_id)
    return query


def list_records(db: Session, context: TenantContext, model, offset: int, limit: int):
    return db.scalars(
        fleet_query(context, model).order_by(model.id).offset(offset).limit(limit)
    ).all()


def get_record(db: Session, context: TenantContext, model, record_id: UUID):
    record = db.scalar(fleet_query(context, model).where(model.id == record_id))
    if record is None:
        raise DomainError(404, "not_found")
    return record
