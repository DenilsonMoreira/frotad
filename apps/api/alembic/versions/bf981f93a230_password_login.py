"""Password login and account lockout.

Revision ID: bf981f93a230
Revises: 2fa3d7f56571
"""

import sqlalchemy as sa

from alembic import op

revision = "bf981f93a230"
down_revision = "2fa3d7f56571"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "system_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("is_system_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("password_hash", sa.String(256), nullable=True))
    op.add_column(
        "users", sa.Column("failed_logins", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_table("system_audit_events")
    op.drop_column("users", "is_system_admin")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_logins")
    op.drop_column("users", "password_hash")
