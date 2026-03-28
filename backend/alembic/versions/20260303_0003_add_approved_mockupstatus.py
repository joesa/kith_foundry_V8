"""add approved value to mockupstatus enum

Revision ID: 20260303_0003
Revises: 20260303_0002
Create Date: 2026-03-03
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260303_0003"
down_revision: Union[str, Sequence[str], None] = "20260303_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    result = bind.execute(text("SELECT 1 FROM pg_type WHERE typname = 'mockupstatus'"))
    if result.fetchone():
        op.execute("ALTER TYPE mockupstatus ADD VALUE IF NOT EXISTS 'approved'")


def downgrade() -> None:
    pass
