"""add project brain tables: pages, components, sections, features, decisions, embeddings

Revision ID: 20260316_0001
Revises: 20260313_0002
Create Date: 2026-03-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "20260316_0001"
down_revision = "20260313_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pgvector extension ─────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Enums ──────────────────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
          CREATE TYPE pagestatus AS ENUM ('planned','scaffolded','implemented','revised');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)
    op.execute("""
        DO $$ BEGIN
          CREATE TYPE featurestatus AS ENUM ('planned','in_progress','implemented','deferred');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)
    op.execute("""
        DO $$ BEGIN
          CREATE TYPE decisiontype AS ENUM ('layout','component','routing','styling','data_model','library','architecture');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)
    op.execute("""
        DO $$ BEGIN
          CREATE TYPE contenttype AS ENUM ('file','page','component','section','decision','message');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)

    # ── project_pages ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_pages (
            id          VARCHAR PRIMARY KEY,
            project_id  VARCHAR NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            page_name   VARCHAR NOT NULL,
            route       VARCHAR NOT NULL,
            description TEXT,
            layout_json JSONB,
            status      pagestatus NOT NULL DEFAULT 'planned',
            created_at  TIMESTAMP DEFAULT NOW(),
            updated_at  TIMESTAMP DEFAULT NOW(),
            UNIQUE (project_id, route)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_pp_project ON project_pages (project_id)")

    # ── project_components ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_components (
            id                  VARCHAR PRIMARY KEY,
            project_id          VARCHAR NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            component_name      VARCHAR NOT NULL,
            file_path           VARCHAR NOT NULL,
            props_schema_json   JSONB,
            dependencies_json   JSONB,
            description         TEXT,
            created_at          TIMESTAMP DEFAULT NOW(),
            updated_at          TIMESTAMP DEFAULT NOW(),
            UNIQUE (project_id, file_path)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_pc_project ON project_components (project_id)")

    # ── project_sections ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_sections (
            id                  VARCHAR PRIMARY KEY,
            page_id             VARCHAR NOT NULL REFERENCES project_pages(id) ON DELETE CASCADE,
            section_name        VARCHAR NOT NULL,
            section_type        VARCHAR,
            description         TEXT,
            component_refs_json JSONB,
            sort_order          INTEGER NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ps_page ON project_sections (page_id)")

    # ── project_features ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_features (
            id          VARCHAR PRIMARY KEY,
            project_id  VARCHAR NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            feature_name VARCHAR NOT NULL,
            status      featurestatus NOT NULL DEFAULT 'planned',
            description TEXT,
            files_json  JSONB,
            created_at  TIMESTAMP DEFAULT NOW(),
            updated_at  TIMESTAMP DEFAULT NOW(),
            UNIQUE (project_id, feature_name)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_pf_project ON project_features (project_id)")

    # ── project_decisions ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_decisions (
            id              VARCHAR PRIMARY KEY,
            project_id      VARCHAR NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            decision_type   decisiontype NOT NULL,
            decision_json   JSONB NOT NULL,
            rationale       TEXT,
            agent_role      VARCHAR,
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_pd_project ON project_decisions (project_id)")

    # ── project_embeddings ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS project_embeddings (
            id              VARCHAR PRIMARY KEY,
            project_id      VARCHAR NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            content_type    contenttype NOT NULL,
            content_ref_id  VARCHAR,
            content_text    TEXT NOT NULL,
            embedding       vector(1536),
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_pe_project ON project_embeddings (project_id)")
    # HNSW index for fast cosine similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pe_embedding
        ON project_embeddings
        USING hnsw (embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_embeddings")
    op.execute("DROP TABLE IF EXISTS project_decisions")
    op.execute("DROP TABLE IF EXISTS project_features")
    op.execute("DROP TABLE IF EXISTS project_sections")
    op.execute("DROP TABLE IF EXISTS project_components")
    op.execute("DROP TABLE IF EXISTS project_pages")
    op.execute("DROP TYPE IF EXISTS contenttype")
    op.execute("DROP TYPE IF EXISTS decisiontype")
    op.execute("DROP TYPE IF EXISTS featurestatus")
    op.execute("DROP TYPE IF EXISTS pagestatus")
    op.execute("DROP EXTENSION IF EXISTS vector")
