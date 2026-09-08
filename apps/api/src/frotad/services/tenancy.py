from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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

    def require(self, capability: str) -> None:
        permissions = {
            Role.OWNER: {"fleet:read", "forms:read", "forms:write"},
            Role.ADMIN: {"fleet:read", "forms:read", "forms:write"},
            Role.MANAGER: {"fleet:read", "forms:read", "forms:write"},
            Role.DISPATCHER: {"fleet:read"},
            Role.MAINTENANCE: {"fleet:read"},
            Role.VIEWER: {"fleet:read", "forms:read"},
            Role.DRIVER: set(),
        }
        if capability not in permissions[self.role]:
            raise DomainError(403, "permission_denied")


def resolve_tenant(db: Session, token: str, company_id: UUID) -> TenantContext:
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
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.company_id == company_id,
            Membership.active.is_(True),
        )
    )
    if membership is None:
        raise DomainError(403, "membership_required")
    return TenantContext(company_id, user.id, membership.branch_id, membership.role)
