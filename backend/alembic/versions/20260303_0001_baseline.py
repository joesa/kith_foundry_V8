"""baseline schema checkpoint

Revision ID: 20260303_0001
Revises:
Create Date: 2026-03-03
"""

from typing import Sequence, Union

from alembic import op
from models import Base

revision: str = "20260303_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
