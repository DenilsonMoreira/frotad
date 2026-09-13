from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from frotad.models.company import Company
from frotad.models.identity import AccessToken, Membership, Role, User


class DomainError(Exception):
    def __init__(self, status: int, code: str):
        self.status = status
        self.code = code


@dataclass(frozen=True)
class TenantContext:
    company_id: UUID
    user_id: UUID
    branch_id: UUID | None
    role: Role
    system_form_admin: bool = False

    def require(self, capability: str) -> None:
        # System administrators may explicitly manage a company's definitions,
        # without gaining access to its submissions, fleet or users implicitly.
        if self.system_form_admin:
            if capability not in {"forms:read", "forms:write"}:
                raise DomainError(403, "permission_denied")
            return
        permissions = {
            Role.OWNER: {
                "users:manage",
                "fleet:read",
                "forms:read",
                "forms:write",
                "runner:read",
                "runner:write",
                "runner:create",
            },
            Role.ADMIN: {
                "users:manage",
                "fleet:read",
                "forms:read",
                "forms:write",
                "runner:read",
                "runner:write",
                "runner:create",
            },
            Role.MANAGER: {
                "fleet:read",
                "forms:read",
                "runner:read",
                "runner:write",
                "runner:create",
            },
            Role.DISPATCHER: {"fleet:read", "runner:read", "runner:write", "runner:create"},
            Role.MAINTENANCE: {"fleet:read"},
            Role.VIEWER: {"fleet:read", "forms:read", "runner:read"},
            Role.DRIVER: {"runner:read", "runner:write"},
        }
        if capability not in permissions[self.role]:
            raise DomainError(403, "permission_denied")


def resolve_user(db: Session, token: str) -> User:
    user = db.scalar(
        select(User)
        .join(AccessToken)
        .where(
            AccessToken.token_hash == sha256(token.encode()).hexdigest(),
            AccessToken.expires_at > datetime.now(UTC),
            AccessToken.revoked.is_(False),
            User.status == "ACTIVE",
        )
    )
    if user is None:
        raise DomainError(401, "invalid_credentials")
    return user


def resolve_tenant(db: Session, token: str, company_id: UUID) -> TenantContext:
    user = resolve_user(db, token)
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.company_id == company_id,
            Membership.active.is_(True),
        )
    )
    if membership is None:
        if user.is_system_admin and db.get(Company, company_id) is not None:
            return TenantContext(company_id, user.id, None, Role.ADMIN, system_form_admin=True)
        raise DomainError(403, "membership_required")
    return TenantContext(company_id, user.id, membership.branch_id, membership.role)
