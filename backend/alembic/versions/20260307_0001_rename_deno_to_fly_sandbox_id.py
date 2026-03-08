"""rename deno_project_id to fly_sandbox_id

Revision ID: 20260307_0001
Revises: eba5a71728b5
Create Date: 2026-03-07
"""
from typing import Sequence, Union

from alembic import op


revision: str = '20260307_0001'
down_revision: Union[str, Sequence[str], None] = 'eba5a71728b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE projects RENAME COLUMN deno_project_id TO fly_sandbox_id")
    op.execute("DROP INDEX IF EXISTS ix_projects_deno_project_id")
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_fly_sandbox_id ON projects (fly_sandbox_id)")


def downgrade() -> None:
    op.execute("ALTER TABLE projects RENAME COLUMN fly_sandbox_id TO deno_project_id")
    op.execute("DROP INDEX IF EXISTS ix_projects_fly_sandbox_id")
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_deno_project_id ON projects (deno_project_id)")
