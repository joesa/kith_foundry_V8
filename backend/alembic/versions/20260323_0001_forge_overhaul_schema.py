"""forge overhaul: extend enums, add capability/secret/patch tables, saved idea expiry

Revision ID: 20260323_0001
Revises: 1d60040ced8c
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260323_0001"
down_revision: Union[str, Sequence[str], None] = "1d60040ced8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS(SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column)"
    ), {"table": table, "column": column})
    return result.scalar()


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table)"
    ), {"table": table})
    return result.scalar()


def upgrade() -> None:
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"

    if is_pg:
        for val in [
            "prd_generating", "prd_complete",
            "design_generating", "design_complete",
            "capability_gate", "secrets_pending", "build_complete",
        ]:
            op.execute(f"ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS '{val}'")

        for val in ["ciso", "synthesizer"]:
            op.execute(f"ALTER TYPE csuiterole ADD VALUE IF NOT EXISTS '{val}'")

    if not _column_exists("saved_ideas", "saved_expires_at"):
        op.add_column("saved_ideas", sa.Column("saved_expires_at", sa.DateTime(), nullable=True))
    if not _column_exists("saved_ideas", "uniqueness_degraded"):
        op.add_column("saved_ideas", sa.Column("uniqueness_degraded", sa.Boolean(), server_default="false", nullable=False))

    if not _table_exists("project_capability_choices"):
        op.create_table(
            "project_capability_choices",
            sa.Column("id", sa.String(), primary_key=True, index=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
            sa.Column("wants_database", sa.Boolean(), default=False, nullable=False),
            sa.Column("wants_auth", sa.Boolean(), default=False, nullable=False),
            sa.Column("wants_ai", sa.Boolean(), default=False, nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if not _table_exists("encrypted_user_secrets"):
        op.create_table(
            "encrypted_user_secrets",
            sa.Column("id", sa.String(), primary_key=True, index=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("label", sa.String(), nullable=False),
            sa.Column("encrypted_value", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("last_accessed_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )

    if not _table_exists("secret_access_audit"):
        op.create_table(
            "secret_access_audit",
            sa.Column("id", sa.String(), primary_key=True, index=True),
            sa.Column("secret_id", sa.String(), sa.ForeignKey("encrypted_user_secrets.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("accessed_by", sa.String(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if not _table_exists("code_patches"):
        op.create_table(
            "code_patches",
            sa.Column("id", sa.String(), primary_key=True, index=True),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("file_path", sa.String(), nullable=False),
            sa.Column("diff", sa.Text(), nullable=False),
            sa.Column("status", sa.String(), server_default="proposed", nullable=False),
            sa.Column("agent_role", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("applied_at", sa.DateTime(), nullable=True),
        )

    if not _table_exists("patch_validations"):
        op.create_table(
            "patch_validations",
            sa.Column("id", sa.String(), primary_key=True, index=True),
            sa.Column("patch_id", sa.String(), sa.ForeignKey("code_patches.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("validator", sa.String(), nullable=False),
            sa.Column("passed", sa.Boolean(), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("patch_validations")
    op.drop_table("code_patches")
    op.drop_table("secret_access_audit")
    op.drop_table("encrypted_user_secrets")
    op.drop_table("project_capability_choices")
    op.drop_column("saved_ideas", "uniqueness_degraded")
    op.drop_column("saved_ideas", "saved_expires_at")
