"""add project-level design mode persistence and history

Revision ID: 20260316_0002
Revises: 20260316_0001
Create Date: 2026-03-16 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "20260316_0002"
down_revision = "20260316_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("product_mode", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("style_mode", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("mode_confidence", sa.Numeric(5, 4), nullable=True))
    op.add_column(
        "projects",
        sa.Column("design_mode_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "project_design_mode_history",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_mode", sa.Text(), nullable=False),
        sa.Column("style_mode", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index(
        "ix_project_design_mode_history_project",
        "project_design_mode_history",
        ["project_id"],
    )

    op.alter_column("projects", "design_mode_locked", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_project_design_mode_history_project", table_name="project_design_mode_history")
    op.drop_table("project_design_mode_history")
    op.drop_column("projects", "design_mode_locked")
    op.drop_column("projects", "mode_confidence")
    op.drop_column("projects", "style_mode")
    op.drop_column("projects", "product_mode")
