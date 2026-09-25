from uuid import UUID

from fastapi import APIRouter, Depends, Query

from frotad.api.dependencies import get_db, get_tenant
from frotad.schemas.runner import AnswerWrite, EmptyCommand, SubmissionCreate, SubmissionRead
from frotad.services import runner

router = APIRouter(tags=["runner"])


@router.post("/submissions", response_model=SubmissionRead, status_code=201)
def create(payload: SubmissionCreate, db=Depends(get_db), context=Depends(get_tenant)):
    return runner.create(db, context, payload)


@router.get("/submissions", response_model=list[SubmissionRead])
def listing(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    context=Depends(get_tenant),
):
    return runner.list_submissions(db, context, offset, limit)


@router.get("/submissions/{submission_id}", response_model=SubmissionRead)
def read(submission_id: UUID, db=Depends(get_db), context=Depends(get_tenant)):
    return runner.get(db, context, submission_id)


@router.put("/submissions/{submission_id}/answers/{field_id}", response_model=SubmissionRead)
def answer(
    submission_id: UUID,
    field_id: UUID,
    payload: AnswerWrite,
    db=Depends(get_db),
    context=Depends(get_tenant),
):
    return runner.save_answer(db, context, submission_id, field_id, payload.value)


@router.post("/submissions/{submission_id}/periods/{field_id}/start", response_model=SubmissionRead)
def start(
    submission_id: UUID,
    field_id: UUID,
    payload: EmptyCommand = EmptyCommand(),
    db=Depends(get_db),
    context=Depends(get_tenant),
):
    return runner.start_period(db, context, submission_id, field_id)


@router.post(
    "/submissions/{submission_id}/periods/{field_id}/finish", response_model=SubmissionRead
)
def finish(
    submission_id: UUID,
    field_id: UUID,
    payload: EmptyCommand = EmptyCommand(),
    db=Depends(get_db),
    context=Depends(get_tenant),
):
    return runner.finish_period(db, context, submission_id, field_id)


@router.post("/submissions/{submission_id}/submit", response_model=SubmissionRead)
def submit(
    submission_id: UUID,
    payload: EmptyCommand = EmptyCommand(),
    db=Depends(get_db),
    context=Depends(get_tenant),
):
    return runner.submit(db, context, submission_id)
