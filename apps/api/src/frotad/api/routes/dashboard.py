from datetime import date

from fastapi import APIRouter, Depends, Response

from frotad.api.dependencies import get_db, get_tenant
from frotad.schemas.dashboard import DashboardRead
from frotad.services import dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardRead)
def read(
    response: Response, day: date | None = None, db=Depends(get_db), context=Depends(get_tenant)
):
    response.headers["Cache-Control"] = "no-store"
    return dashboard.read(db, context, day)
