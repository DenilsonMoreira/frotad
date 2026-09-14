from uuid import UUID

from fastapi import APIRouter, Depends, Query

from frotad.api.dependencies import get_db, get_tenant
from frotad.schemas.forms import FieldCreate, FormCreate, FormSummary, ReorderFields, VersionRead
from frotad.services import forms

router = APIRouter(tags=["forms"])


@router.get("/forms", response_model=list[FormSummary])
def listing(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    context=Depends(get_tenant),
):
    return forms.list_forms(db, context, offset, limit)


@router.post("/forms", response_model=VersionRead, status_code=201)
def create(payload: FormCreate, db=Depends(get_db), context=Depends(get_tenant)):
    return forms.create_form(db, context, payload)


@router.get("/form-versions/{version_id}", response_model=VersionRead)
def read(version_id: UUID, db=Depends(get_db), context=Depends(get_tenant)):
    return forms.get_version(db, context, version_id)


@router.post("/form-versions/{version_id}/fields", response_model=VersionRead, status_code=201)
def add(version_id: UUID, payload: FieldCreate, db=Depends(get_db), context=Depends(get_tenant)):
    return forms.add_field(db, context, version_id, payload)


@router.put("/form-versions/{version_id}/field-order", response_model=VersionRead)
def reorder(
    version_id: UUID, payload: ReorderFields, db=Depends(get_db), context=Depends(get_tenant)
):
    return forms.reorder_fields(db, context, version_id, payload.field_ids)


@router.post("/form-versions/{version_id}/publish", response_model=VersionRead)
def publish(version_id: UUID, db=Depends(get_db), context=Depends(get_tenant)):
    return forms.publish(db, context, version_id)


@router.post("/form-versions/{version_id}/clone", response_model=VersionRead, status_code=201)
def clone(version_id: UUID, db=Depends(get_db), context=Depends(get_tenant)):
    return forms.clone_version(db, context, version_id)
