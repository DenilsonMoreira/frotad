import secrets
from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac, sha256
from hmac import compare_digest

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from frotad.models import Company, Driver
from frotad.models.identity import AccessToken, Membership, Role, SystemAuditEvent, User
from frotad.schemas.auth import CompanyRead, LoginRead, SessionRead, UserRead
from frotad.services.forms import audit
from frotad.services.runner import utc
from frotad.services.tenancy import DomainError, TenantContext

ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_hex(32)
    digest = pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password, encoded):
    # Missing accounts perform the same expensive derivation to limit timing disclosure.
    encoded = encoded or f"pbkdf2_sha256${ITERATIONS}${'00' * 32}${'00' * 32}"
    _, iterations, salt, digest = encoded.split("$")
    candidate = pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return compare_digest(candidate, digest)


def save(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "registration_conflict") from None


def session(db, user, company_id=None):
    member = db.scalar(
        select(Membership)
        .where(
            Membership.user_id == user.id,
            Membership.active.is_(True),
            *([Membership.company_id == company_id] if company_id else []),
        )
        .order_by(Membership.created_at, Membership.id)
        .limit(1)
    )
    if member is None and not user.is_system_admin:
        raise DomainError(403, "membership_required")
    company = (
        db.get(Company, member.company_id)
        if member
        else (db.get(Company, company_id) if company_id else None)
    )
    if company_id is not None and company is None:
        raise DomainError(404, "not_found")
    return SessionRead(
        company_id=company.id if company else None,
        company_name=company.name if company else None,
        is_system_admin=user.is_system_admin,
        user=UserRead(
            id=user.id,
            name=user.name,
            email=user.email,
            role=member.role if member else None,
            active=True,
        ),
    )


def security_event(db, user_id, action):
    db.add(SystemAuditEvent(actor_user_id=user_id, action=action, occurred_at=datetime.now(UTC)))


def issue(db, user, membership):
    token = secrets.token_urlsafe(48)
    expires = datetime.now(UTC) + timedelta(hours=8)
    db.add(
        AccessToken(
            user_id=user.id, token_hash=sha256(token.encode()).hexdigest(), expires_at=expires
        )
    )
    security_event(db, user.id, "auth.login")
    result = LoginRead(
        **session(db, user, membership.company_id if membership else None).model_dump(),
        access_token=token,
        expires_at=expires,
    )
    save(db)
    return result


def create_company(db, payload, actor=None):
    if db.scalar(select(User.id).where(func.lower(User.email) == payload.email)):
        raise DomainError(409, "registration_conflict")
    company = Company(
        name=payload.company_name, slug=payload.company_slug, timezone=payload.timezone
    )
    user = User(
        name=payload.name, email=payload.email, password_hash=hash_password(payload.password)
    )
    try:
        db.add_all([company, user])
        db.flush()
        membership = Membership(company_id=company.id, user_id=user.id, role=Role.OWNER)
        db.add(membership)
        db.flush()
        context = TenantContext(company.id, actor.id if actor else user.id, None, Role.OWNER)
        audit(db, context, company.id, "company.created")
        audit(db, context, user.id, "user.created")
        return user, membership
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "registration_conflict") from None


def register(db, payload):
    user, membership = create_company(db, payload)
    return issue(db, user, membership)


def require_system_admin(user):
    if not user.is_system_admin:
        raise DomainError(403, "system_admin_required")


def company_read(company):
    return CompanyRead(
        id=company.id, name=company.name, slug=company.slug, timezone=company.timezone
    )


def list_companies(db, user, offset=0, limit=50):
    require_system_admin(user)
    return [
        company_read(c)
        for c in db.scalars(
            select(Company).order_by(Company.name, Company.id).offset(offset).limit(limit)
        )
    ]


def register_company(db, user, payload):
    require_system_admin(user)
    _, membership = create_company(db, payload, actor=user)
    company = db.get(Company, membership.company_id)
    save(db)
    return company_read(company)


def login(db, payload):
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email).with_for_update())
    valid = verify_password(payload.password, user.password_hash if user else None)
    clock = datetime.now(UTC)
    if user is None:
        raise DomainError(401, "invalid_credentials")
    locked = user.locked_until is not None and utc(user.locked_until) > clock
    if not valid or user.status != "ACTIVE" or locked:
        if not locked:
            user.failed_logins = (0 if user.locked_until else user.failed_logins) + 1
            user.locked_until = clock + timedelta(minutes=5) if user.failed_logins >= 5 else None
            save(db)
        raise DomainError(401, "invalid_credentials")
    membership = db.scalar(
        select(Membership)
        .where(Membership.user_id == user.id, Membership.active.is_(True))
        .order_by(Membership.created_at, Membership.id)
        .limit(1)
    )
    if membership is None and not user.is_system_admin:
        raise DomainError(401, "invalid_credentials")
    user.failed_logins = 0
    user.locked_until = None
    return issue(db, user, membership)


def logout(db, user, token):
    db.execute(
        update(AccessToken)
        .where(
            AccessToken.user_id == user.id,
            AccessToken.token_hash == sha256(token.encode()).hexdigest(),
        )
        .values(revoked=True)
    )
    security_event(db, user.id, "auth.logout")
    save(db)


def require_admin(context):
    context.require("users:manage")
    if context.branch_id:
        raise DomainError(403, "company_admin_required")


def list_users(db, context, offset=0, limit=50):
    require_admin(context)
    return [
        UserRead(id=u.id, name=u.name, email=u.email, role=m.role, active=m.active)
        for u, m in db.execute(
            select(User, Membership)
            .join(Membership)
            .where(Membership.company_id == context.company_id)
            .order_by(User.name, User.id)
            .offset(offset)
            .limit(limit)
        )
    ]


def create_user(db, context, payload):
    require_admin(context)
    if payload.role == Role.OWNER or (payload.role == Role.ADMIN and context.role != Role.OWNER):
        raise DomainError(403, "role_not_assignable")
    if db.scalar(select(User.id).where(func.lower(User.email) == payload.email)):
        raise DomainError(409, "registration_conflict")
    user = User(
        name=payload.name, email=payload.email, password_hash=hash_password(payload.password)
    )
    try:
        db.add(user)
        db.flush()
        db.add(Membership(company_id=context.company_id, user_id=user.id, role=payload.role))
        db.flush()
        if payload.role == Role.DRIVER:
            db.add(Driver(company_id=context.company_id, user_id=user.id, name=user.name))
        audit(db, context, user.id, "user.created")
        save(db)
    except IntegrityError:
        db.rollback()
        raise DomainError(409, "registration_conflict") from None
    return UserRead(id=user.id, name=user.name, email=user.email, role=payload.role, active=True)


def set_active(db, context, user_id, active):
    require_admin(context)
    member = db.scalar(
        select(Membership)
        .where(Membership.company_id == context.company_id, Membership.user_id == user_id)
        .with_for_update()
    )
    if member is None:
        raise DomainError(404, "not_found")
    if (
        user_id == context.user_id
        or member.role == Role.OWNER
        or (member.role == Role.ADMIN and context.role != Role.OWNER)
    ):
        raise DomainError(403, "protected_membership")
    member.active = active
    audit(db, context, user_id, "membership.activated" if active else "membership.deactivated")
    save(db)


def change_password(db, identity, payload):
    user = db.scalar(select(User).where(User.id == identity.id).with_for_update())
    if not verify_password(payload.current_password, user.password_hash):
        raise DomainError(401, "invalid_credentials")
    user.password_hash = hash_password(payload.new_password)
    db.execute(update(AccessToken).where(AccessToken.user_id == user.id).values(revoked=True))
    security_event(db, user.id, "auth.password_changed")
    save(db)
