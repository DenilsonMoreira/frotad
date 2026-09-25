from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from frotad.db.session import SessionLocal
from frotad.services.tenancy import DomainError, resolve_tenant


def get_db():
    with SessionLocal() as db:
        yield db


def get_tenant(
    company_id: Annotated[UUID, Header(alias="X-Company-ID")],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))
    ],
    db=Depends(get_db),
):
    if credentials is None:
        raise DomainError(401, "authentication_required")
    return resolve_tenant(db, credentials.credentials, company_id)
