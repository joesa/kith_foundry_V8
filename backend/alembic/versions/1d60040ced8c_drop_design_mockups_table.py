"""drop design_mockups table

Revision ID: 1d60040ced8c
Revises: 20260316_0002
Create Date: 2026-03-14 02:41:55.724297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d60040ced8c'
down_revision: Union[str, Sequence[str], None] = '20260316_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('design_mockups')


def downgrade() -> None:
    op.create_table(
        'design_mockups',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('screen_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(), nullable=False, server_default='medium'),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('component_code', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
