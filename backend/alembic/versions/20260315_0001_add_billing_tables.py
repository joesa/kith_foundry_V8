"""add billing tables: subscriptions, usage_records, usage_packs

Revision ID: 20260315_0001
Revises: 20260312_0001
Create Date: 2026-03-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "20260315_0001"
down_revision = "20260312_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
          CREATE TYPE subscriptiontier AS ENUM ('free','indie','pro','team','enterprise');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)
    op.execute("""
        DO $$ BEGIN
          CREATE TYPE subscriptionstatus AS ENUM ('active','trialing','past_due','canceled','unpaid');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id                      SERIAL PRIMARY KEY,
            user_id                 VARCHAR NOT NULL UNIQUE REFERENCES users(id),
            tier                    subscriptiontier NOT NULL DEFAULT 'free',
            status                  subscriptionstatus NOT NULL DEFAULT 'active',
            stripe_customer_id      VARCHAR,
            stripe_subscription_id  VARCHAR,
            stripe_price_id         VARCHAR,
            current_period_start    TIMESTAMP,
            current_period_end      TIMESTAMP,
            seat_count              INTEGER NOT NULL DEFAULT 1,
            byok_discount_applied   BOOLEAN NOT NULL DEFAULT FALSE,
            is_annual               BOOLEAN NOT NULL DEFAULT FALSE,
            created_at              TIMESTAMP DEFAULT NOW(),
            updated_at              TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_subscriptions_id ON subscriptions (id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_subscriptions_user_id ON subscriptions (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sub_cust ON subscriptions (stripe_customer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sub_stripe ON subscriptions (stripe_subscription_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_records (
            id              SERIAL PRIMARY KEY,
            user_id         VARCHAR NOT NULL REFERENCES users(id),
            billing_month   VARCHAR(7) NOT NULL,
            csuite_runs     INTEGER NOT NULL DEFAULT 0,
            design_screens  INTEGER NOT NULL DEFAULT 0,
            artifact_sets   INTEGER NOT NULL DEFAULT 0,
            project_count   INTEGER NOT NULL DEFAULT 0,
            updated_at      TIMESTAMP DEFAULT NOW(),
            UNIQUE (user_id, billing_month)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_records_id ON usage_records (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_user ON usage_records (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_month ON usage_records (billing_month)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_packs (
            id                      SERIAL PRIMARY KEY,
            user_id                 VARCHAR NOT NULL REFERENCES users(id),
            pack_type               VARCHAR NOT NULL,
            pack_size               INTEGER NOT NULL,
            remaining               INTEGER NOT NULL,
            stripe_payment_intent   VARCHAR,
            purchased_at            TIMESTAMP DEFAULT NOW(),
            expires_at              TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_packs_id ON usage_packs (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_packs_user ON usage_packs (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS usage_packs")
    op.execute("DROP TABLE IF EXISTS usage_records")
    op.execute("DROP TABLE IF EXISTS subscriptions")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")
