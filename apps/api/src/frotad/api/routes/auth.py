from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response

from frotad.api.dependencies import get_db, get_tenant, get_user
from frotad.schemas.auth import (
    CompanyRead,
    Login,
    LoginRead,
    PasswordChange,
    Register,
    SessionRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from frotad.services import auth

router = APIRouter(tags=["identity"])


@router.get("/system/companies", response_model=list[CompanyRead])
def companies(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(get_user),
):
    response.headers["Cache-Control"] = "no-store"
    return auth.list_companies(db, user, offset, limit)


@router.post("/system/companies", response_model=CompanyRead, status_code=201)
def create_company(payload: Register, db=Depends(get_db), user=Depends(get_user)):
    return auth.register_company(db, user, payload)


@router.post("/auth/register", response_model=LoginRead, status_code=201)
def register(payload: Register, response: Response, db=Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return auth.register(db, payload)


@router.post("/auth/login", response_model=LoginRead)
def login(payload: Login, response: Response, db=Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return auth.login(db, payload)


@router.get("/auth/me", response_model=SessionRead)
def me(
    response: Response,
    company_id: UUID | None = Header(None, alias="X-Company-ID"),
    db=Depends(get_db),
    user=Depends(get_user),
):
    response.headers["Cache-Control"] = "no-store"
    return auth.session(db, user, company_id)


@router.post("/auth/logout", status_code=204)
def logout(authorization: str = Header(), db=Depends(get_db), user=Depends(get_user)):
    auth.logout(db, user, authorization.split(" ", 1)[1])


@router.post("/auth/password", status_code=204)
def password(payload: PasswordChange, db=Depends(get_db), user=Depends(get_user)):
    auth.change_password(db, user, payload)


@router.get("/users", response_model=list[UserRead])
def users(
    response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    context=Depends(get_tenant),
):
    response.headers["Cache-Control"] = "no-store"
    return auth.list_users(db, context, offset, limit)


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db=Depends(get_db), context=Depends(get_tenant)):
    return auth.create_user(db, context, payload)


@router.patch("/users/{user_id}", status_code=204)
def update_user(
    user_id: UUID, payload: UserUpdate, db=Depends(get_db), context=Depends(get_tenant)
):
    auth.set_active(db, context, user_id, payload.active)
