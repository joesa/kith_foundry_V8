"""normalize enum values for schema drift

Revision ID: 20260303_0002
Revises: 20260303_0001
Create Date: 2026-03-03
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260303_0002"
down_revision: Union[str, Sequence[str], None] = "20260303_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_enum_value(enum_name: str, value: str) -> None:
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")


def upgrade() -> None:
    # Keep enum catalogs aligned with current application enums.
    # This is idempotent and safe to run on existing environments.

    # ArtifactType additions introduced after initial schema rollout
    for value in [
        "market_analysis",
        "user_personas",
        "competitive_matrix",
        "roadmap",
        "monetization",
    ]:
        _add_enum_value("artifacttype", value)

    # Ensure full ProjectStatus catalog exists
    for value in [
        "ideation",
        "csuite_pending",
        "csuite_running",
        "csuite_complete",
        "building",
        "deployed",
    ]:
        _add_enum_value("projectstatus", value)

    # Ensure AgentStatus includes runtime values used by APIs
    for value in ["pending", "running", "complete", "error"]:
        _add_enum_value("agentstatus", value)

    # Ensure MockupStatus contains all generation states
    for value in ["pending", "generating", "complete", "error"]:
        _add_enum_value("mockupstatus", value)


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without type recreation,
    # so this migration is intentionally non-reversible.
    pass
