"""add is_super_admin to users table

Revision ID: 20260313_0002
Revises: 20260315_0001
Create Date: 2026-03-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "20260313_0002"
down_revision = "20260313_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_super_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_super_admin")
