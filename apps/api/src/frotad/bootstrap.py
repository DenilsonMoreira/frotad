"""Trusted operator bootstrap: python -m frotad.bootstrap --help."""

import argparse
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from zoneinfo import ZoneInfo

from frotad.db.session import SessionLocal
from frotad.models import AccessToken, Company, Membership, User
from frotad.models.identity import AuditEvent, Role


def main():
    parser = argparse.ArgumentParser(description="Create a company and its first owner")
    parser.add_argument("--company", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--timezone", default="America/Fortaleza")
    args = parser.parse_args()
    ZoneInfo(args.timezone)
    token = token_urlsafe(32)
    with SessionLocal.begin() as db:
        company = Company(name=args.company, slug=args.slug, timezone=args.timezone)
        user = User(name=args.name, email=args.email.strip().lower())
        db.add_all([company, user])
        db.flush()
        db.add(Membership(company_id=company.id, user_id=user.id, role=Role.OWNER))
        db.add(
            AccessToken(
                user_id=user.id,
                token_hash=sha256(token.encode()).hexdigest(),
                expires_at=datetime.now(UTC) + timedelta(hours=8),
            )
        )
        db.flush()
        membership = db.query(Membership).filter_by(company_id=company.id, user_id=user.id).one()
        db.add(
            AuditEvent(
                company_id=company.id,
                actor_user_id=user.id,
                entity_id=membership.id,
                action="membership.owner_created",
                occurred_at=datetime.now(UTC),
            )
        )
        company_id = company.id
    print(f"X-Company-ID: {company_id}")
    print(f"Bearer token (shown once; expires in 8h): {token}")


if __name__ == "__main__":
    main()
