"""
One-shot data migration: Nhost Postgres → Northflank Postgres.
Exports via Hasura run_sql, imports via psycopg2 with ON CONFLICT DO NOTHING.

Tables migrated (in dependency order):
  users → ideas → projects → csuite_analyses → artifacts
"""
import os, json, psycopg2, httpx
from dotenv import load_dotenv

load_dotenv()

# ── Source: Nhost via Hasura ──────────────────────────────────────────────────
NHOST_GRAPHQL_URL = os.getenv("NHOST_GRAPHQL_URL", "").rstrip("/")
NHOST_ADMIN_SECRET = os.getenv("NHOST_ADMIN_SECRET", "")
hasura_base = NHOST_GRAPHQL_URL.replace(".graphql.", ".hasura.")
HASURA_URL = f"{hasura_base}/v2/query"
HASURA_HEADERS = {
    "x-hasura-admin-secret": NHOST_ADMIN_SECRET,
    "Content-Type": "application/json",
}

# ── Destination: Northflank Postgres ─────────────────────────────────────────
NF_DATABASE_URL = os.getenv("DATABASE_URL", "")


def hasura_sql(sql: str) -> list[list]:
    resp = httpx.post(
        HASURA_URL,
        json={"type": "run_sql", "args": {"sql": sql}},
        headers=HASURA_HEADERS,
        timeout=30,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Hasura error: {data}")
    return data.get("result", [])


def _coerce(v):
    """Convert Hasura string NULLs to Python None."""
    return None if v == "NULL" else v


def rows_to_dicts(rows: list[list]) -> list[dict]:
    if len(rows) < 2:
        return []
    cols = rows[0]
    return [dict(zip(cols, [_coerce(c) for c in row])) for row in rows[1:]]


def nf_conn():
    return psycopg2.connect(NF_DATABASE_URL, connect_timeout=15)


# ── Migration helpers ─────────────────────────────────────────────────────────

def migrate_users(cur):
    rows = rows_to_dicts(hasura_sql("SELECT id, email, created_at, last_login FROM users;"))
    inserted = 0
    for r in rows:
        cur.execute(
            """
            INSERT INTO users (id, email, created_at, last_login)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (r["id"], r["email"], r.get("created_at"), r.get("last_login")),
        )
        inserted += cur.rowcount
    print(f"  users:           {inserted}/{len(rows)} inserted")


def migrate_ideas(cur):
    rows = rows_to_dicts(hasura_sql(
        "SELECT id, user_id, name, content, score, source::text, is_used, created_at FROM ideas;"
    ))
    inserted = 0
    for r in rows:
        content = r["content"]
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                pass
        cur.execute(
            """
            INSERT INTO ideas (id, user_id, name, content, score, source, is_used, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                r["id"], r["user_id"], r["name"],
                json.dumps(content) if isinstance(content, dict) else content,
                r.get("score"), r["source"], r.get("is_used", False), r.get("created_at"),
            ),
        )
        inserted += cur.rowcount
    print(f"  ideas:           {inserted}/{len(rows)} inserted")


def migrate_projects(cur):
    rows = rows_to_dicts(hasura_sql(
        """SELECT id, user_id, name, description, target_audience, problem_statement,
                  status::text, fly_sandbox_id, preview_url, auto_save_enabled,
                  design_preferences, product_mode, style_mode,
                  mode_confidence, design_mode_locked, idea_id,
                  created_at, updated_at
           FROM projects;"""
    ))
    inserted = 0
    for r in rows:
        dp = r.get("design_preferences")
        if isinstance(dp, str):
            try:
                dp = json.loads(dp)
            except Exception:
                dp = None
        cur.execute(
            """
            INSERT INTO projects (
                id, user_id, name, description, target_audience, problem_statement,
                status, fly_sandbox_id, preview_url, auto_save_enabled,
                design_preferences, product_mode, style_mode,
                mode_confidence, design_mode_locked, idea_id,
                created_at, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                r["id"], r["user_id"], r["name"],
                r.get("description"), r.get("target_audience"), r.get("problem_statement"),
                r.get("status", "ideation"),
                r.get("fly_sandbox_id"), r.get("preview_url"),
                r.get("auto_save_enabled", True),
                json.dumps(dp) if dp is not None else None,
                r.get("product_mode"), r.get("style_mode"),
                r.get("mode_confidence"), r.get("design_mode_locked", False),
                r.get("idea_id"),
                r.get("created_at"), r.get("updated_at"),
            ),
        )
        inserted += cur.rowcount
    print(f"  projects:        {inserted}/{len(rows)} inserted")


def migrate_csuite_analyses(cur):
    rows = rows_to_dicts(hasura_sql(
        """SELECT id, project_id, agent_role::text, analysis, score,
                  status::text, error_message, created_at, completed_at
           FROM csuite_analyses;"""
    ))
    inserted = 0
    for r in rows:
        analysis = r.get("analysis")
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except Exception:
                pass
        cur.execute(
            """
            INSERT INTO csuite_analyses (
                id, project_id, agent_role, analysis, score,
                status, error_message, created_at, completed_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                r["id"], r["project_id"], r["agent_role"],
                json.dumps(analysis) if isinstance(analysis, dict) else analysis,
                r.get("score"), r.get("status", "pending"),
                r.get("error_message"), r.get("created_at"), r.get("completed_at"),
            ),
        )
        inserted += cur.rowcount
    print(f"  csuite_analyses: {inserted}/{len(rows)} inserted")


def migrate_artifacts(cur):
    rows = rows_to_dicts(hasura_sql(
        """SELECT id, project_id, artifact_type::text, title, content,
                  status::text, created_at, updated_at
           FROM artifacts;"""
    ))
    inserted = 0
    for r in rows:
        content = r.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                pass
        cur.execute(
            """
            INSERT INTO artifacts (
                id, project_id, artifact_type, title, content,
                status, created_at, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                r["id"], r["project_id"], r["artifact_type"], r["title"],
                json.dumps(content) if isinstance(content, dict) else content,
                r.get("status", "pending"),
                r.get("created_at"), r.get("updated_at"),
            ),
        )
        inserted += cur.rowcount
    print(f"  artifacts:       {inserted}/{len(rows)} inserted")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Connecting to Northflank Postgres...")
    conn = nf_conn()
    conn.autocommit = False
    cur = conn.cursor()
    try:
        print("Migrating data...")
        migrate_users(cur)
        migrate_ideas(cur)
        migrate_projects(cur)
        migrate_csuite_analyses(cur)
        migrate_artifacts(cur)
        conn.commit()
        print("Migration complete ✓")
    except Exception as e:
        conn.rollback()
        print(f"Migration FAILED, rolled back: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
