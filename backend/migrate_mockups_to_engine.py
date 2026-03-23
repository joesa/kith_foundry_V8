#!/usr/bin/env python3
"""Phase 2 — One-time migration: backfill engine design artifacts from approved mockups.

For each project that has DesignMockup rows with status='approved' but no
engine-generated design_system artifact, this script extracts the CSS :root
tokens from the approved mockup HTML and persists them as design_tokens
artifacts so the engine-first code paths have data to work with.

Usage:
    cd backend
    PYTHONPATH=. /home/joe/miniconda3/envs/kith_venv/bin/python migrate_mockups_to_engine.py [--dry-run]
"""
import re
import sys
import uuid
from datetime import datetime

from sqlalchemy import text
from models import SessionLocal

_PALETTE_VAR_PAT = re.compile(
    r'^\s*(--(?:bg|background|surface|primary|secondary|accent|cta|text|muted|border|color'
    r'|font(?:-family|-size|-weight|-display|-scale)?|foreground|line-height|letter-spacing)'
    r'[^:]*\s*:[^;]+;)',
    re.IGNORECASE | re.MULTILINE,
)


def _extract_root_css(html: str) -> str | None:
    """Pull :root { ... } from an HTML mockup's inline styles."""
    m = re.search(r':root\s*\{([^}]+)\}', html, re.DOTALL)
    if not m:
        return None
    lines = [v.group(1).strip() for v in _PALETTE_VAR_PAT.finditer(m.group(1))]
    if not lines:
        return None
    return ":root {\n  " + "\n  ".join(lines) + "\n}"


def migrate(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        # Find distinct project IDs that have at least one approved mockup
        rows = db.execute(
            text("SELECT DISTINCT project_id FROM design_mockups WHERE status = 'approved'")
        ).fetchall()
        project_ids = [r[0] for r in rows]
        print(f"Found {len(project_ids)} project(s) with approved mockups")

        migrated = 0
        skipped_engine = 0
        skipped_nodata = 0

        for pid in project_ids:
            # Check if an engine-generated design_system artifact already exists
            ds_row = db.execute(text(
                "SELECT content FROM artifacts "
                "WHERE project_id = :pid AND artifact_type = 'design_system' AND status = 'complete'"
            ), {"pid": pid}).fetchone()

            if ds_row and ds_row[0]:
                content = ds_row[0]
                if isinstance(content, dict) and content.get("design_tokens"):
                    print(f"  [{pid[:8]}] SKIP — engine design_system already exists")
                    skipped_engine += 1
                    continue

            # Get the approved mockups, north-star first (by sort_order)
            mockup_rows = db.execute(text(
                "SELECT screen_name, description, priority, component_code FROM design_mockups "
                "WHERE project_id = :pid AND status = 'approved' AND component_code IS NOT NULL "
                "ORDER BY sort_order"
            ), {"pid": pid}).fetchall()

            # Extract CSS tokens from the first mockup with a :root block
            css_contract = None
            source_screen = None
            for m in mockup_rows:
                css_contract = _extract_root_css(m[3] or "")
                if css_contract:
                    source_screen = m[0]
                    break

            if not css_contract:
                print(f"  [{pid[:8]}] SKIP — no :root tokens found in {len(mockup_rows)} approved mockup(s)")
                skipped_nodata += 1
                continue

            # Check if design_tokens artifact already has CSS data
            dt_row = db.execute(text(
                "SELECT id, content FROM artifacts "
                "WHERE project_id = :pid AND artifact_type = 'design_tokens' AND status = 'complete'"
            ), {"pid": pid}).fetchone()

            if dt_row and dt_row[1]:
                dt_content = dt_row[1]
                dt_css = dt_content.get("css") if isinstance(dt_content, dict) else None
                if dt_css and dt_css.strip():
                    print(f"  [{pid[:8]}] SKIP — design_tokens artifact already has CSS")
                    skipped_engine += 1
                    continue

            now = datetime.utcnow()

            if dry_run:
                print(f"  [{pid[:8]}] WOULD migrate — {len(mockup_rows)} screens, tokens from '{source_screen}'")
                print(f"    CSS preview: {css_contract[:120]}...")
                migrated += 1
                continue

            # Persist design_tokens artifact
            import json
            token_content = json.dumps({"css": css_contract, "source": "migrated_from_mockups"})
            if dt_row:
                db.execute(text(
                    "UPDATE artifacts SET content = CAST(:content AS jsonb), status = 'complete', "
                    "updated_at = :now WHERE id = :aid"
                ), {"content": token_content, "now": now, "aid": dt_row[0]})
            else:
                new_id = str(uuid.uuid4())
                db.execute(text(
                    "INSERT INTO artifacts (id, project_id, artifact_type, title, content, status, created_at, updated_at) "
                    "VALUES (:id, :pid, 'design_tokens', 'Design Tokens', CAST(:content AS jsonb), 'complete', :now, :now)"
                ), {"id": new_id, "pid": pid, "content": token_content, "now": now})

            db.commit()
            migrated += 1
            print(f"  [{pid[:8]}] MIGRATED — tokens from '{source_screen}', {len(mockup_rows)} screens")

        print(f"\nDone: {migrated} migrated, {skipped_engine} skipped (engine exists), {skipped_nodata} skipped (no data)")

    finally:
        db.close()


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("=== DRY RUN — no changes will be written ===\n")
    migrate(dry_run=dry)
