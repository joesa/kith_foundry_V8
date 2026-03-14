"""add performance indexes for hot query paths

Revision ID: 20260313_0001
Revises: 20260315_0001
Create Date: 2026-03-13 00:00:00.000000

Five indexes covering the highest-frequency query patterns:

1. projects(user_id, updated_at DESC)
   - Every "list my projects" load. Without this Postgres sorts the full
     user's project set after an index scan on user_id alone.

2. messages(project_id, created_at ASC)
   - Fetched on every WS reconnect to rebuild chat history. Messages grow
     linearly; sorted scan without the composite index degrades at scale.

3. csuite_analyses(project_id, status)
   - "How many analyses are still running?" counted on every C-Suite start.
     The existing project_id index can't filter on status efficiently.

4. provider_keys(user_id, is_active, is_default)
   - Model resolution does user_id + is_active filter + is_default sort on
     every LLM call. Fired for every WS message.

5. usage_packs(user_id, pack_type) WHERE remaining > 0
   - Partial index: only rows that still have quota. Billing checks happen
     on every C-Suite run and design generation.
"""
from alembic import op

revision = "20260313_0001"
down_revision = "20260315_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Project listing sorted by recency
    op.create_index(
        "ix_projects_user_updated",
        "projects",
        ["user_id", op.f("updated_at")],
        postgresql_ops={"updated_at": "DESC"},
    )

    # 2. Message history ordered by time
    op.create_index(
        "ix_messages_project_created",
        "messages",
        ["project_id", "created_at"],
    )

    # 3. C-Suite active analysis count
    op.create_index(
        "ix_csuite_analyses_project_status",
        "csuite_analyses",
        ["project_id", "status"],
    )

    # 4. Provider/model resolution
    op.create_index(
        "ix_provider_keys_user_active_default",
        "provider_keys",
        ["user_id", "is_active", "is_default"],
    )

    # 5. Billing pack quota (partial — only rows with remaining units)
    op.create_index(
        "ix_usage_packs_user_type_remaining",
        "usage_packs",
        ["user_id", "pack_type"],
        postgresql_where="remaining > 0",
    )


def downgrade() -> None:
    op.drop_index("ix_usage_packs_user_type_remaining", table_name="usage_packs")
    op.drop_index("ix_provider_keys_user_active_default", table_name="provider_keys")
    op.drop_index("ix_csuite_analyses_project_status", table_name="csuite_analyses")
    op.drop_index("ix_messages_project_created", table_name="messages")
    op.drop_index("ix_projects_user_updated", table_name="projects")
