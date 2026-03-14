"""add design_preferences JSON column to projects

Revision ID: 20260312_0001
Revises: 20260307_0001
Create Date: 2026-03-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260312_0001'
down_revision: Union[str, Sequence[str], None] = '20260307_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('design_preferences', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'design_preferences')
