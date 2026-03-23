"""
Project Brain Service — structured memory for each project.

Provides upsert/query helpers that agents call to record pages, components,
sections, features, and architectural decisions as they are generated.
Also provides embedding-based retrieval for context compression (Phase 4).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import (
    Project, ProjectDesignModeHistory,
    ProjectPage, ProjectComponent, ProjectSection, ProjectFeature,
    ProjectDecision, ProjectEmbedding,
    PageStatus, FeatureStatus, DecisionType, ContentType,
)


# ── Page helpers ───────────────────────────────────────────────────────────────

def upsert_page(
    db: Session,
    project_id: str,
    page_name: str,
    route: str,
    *,
    description: str | None = None,
    layout_json: dict | None = None,
    status: PageStatus = PageStatus.planned,
) -> ProjectPage:
    page = (
        db.query(ProjectPage)
        .filter_by(project_id=project_id, route=route)
        .first()
    )
    if page:
        page.page_name = page_name
        if description is not None:
            page.description = description
        if layout_json is not None:
            page.layout_json = layout_json
        page.status = status
        page.updated_at = datetime.utcnow()
    else:
        page = ProjectPage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            page_name=page_name,
            route=route,
            description=description,
            layout_json=layout_json,
            status=status,
        )
        db.add(page)
    db.flush()
    return page


# ── Component helpers ──────────────────────────────────────────────────────────

def upsert_component(
    db: Session,
    project_id: str,
    component_name: str,
    file_path: str,
    *,
    props_schema_json: dict | None = None,
    dependencies_json: list | None = None,
    description: str | None = None,
) -> ProjectComponent:
    comp = (
        db.query(ProjectComponent)
        .filter_by(project_id=project_id, file_path=file_path)
        .first()
    )
    if comp:
        comp.component_name = component_name
        if props_schema_json is not None:
            comp.props_schema_json = props_schema_json
        if dependencies_json is not None:
            comp.dependencies_json = dependencies_json
        if description is not None:
            comp.description = description
        comp.updated_at = datetime.utcnow()
    else:
        comp = ProjectComponent(
            id=str(uuid.uuid4()),
            project_id=project_id,
            component_name=component_name,
            file_path=file_path,
            props_schema_json=props_schema_json,
            dependencies_json=dependencies_json,
            description=description,
        )
        db.add(comp)
    db.flush()
    return comp


# ── Section helpers ────────────────────────────────────────────────────────────

def upsert_section(
    db: Session,
    page_id: str,
    section_name: str,
    *,
    section_type: str | None = None,
    description: str | None = None,
    component_refs_json: list | None = None,
    sort_order: int = 0,
) -> ProjectSection:
    sec = (
        db.query(ProjectSection)
        .filter_by(page_id=page_id, section_name=section_name)
        .first()
    )
    if sec:
        if section_type is not None:
            sec.section_type = section_type
        if description is not None:
            sec.description = description
        if component_refs_json is not None:
            sec.component_refs_json = component_refs_json
        sec.sort_order = sort_order
    else:
        sec = ProjectSection(
            id=str(uuid.uuid4()),
            page_id=page_id,
            section_name=section_name,
            section_type=section_type,
            description=description,
            component_refs_json=component_refs_json,
            sort_order=sort_order,
        )
        db.add(sec)
    db.flush()
    return sec


# ── Feature helpers ────────────────────────────────────────────────────────────

def upsert_feature(
    db: Session,
    project_id: str,
    feature_name: str,
    *,
    status: FeatureStatus = FeatureStatus.planned,
    description: str | None = None,
    files_json: list | None = None,
) -> ProjectFeature:
    feat = (
        db.query(ProjectFeature)
        .filter_by(project_id=project_id, feature_name=feature_name)
        .first()
    )
    if feat:
        feat.status = status
        if description is not None:
            feat.description = description
        if files_json is not None:
            feat.files_json = files_json
        feat.updated_at = datetime.utcnow()
    else:
        feat = ProjectFeature(
            id=str(uuid.uuid4()),
            project_id=project_id,
            feature_name=feature_name,
            status=status,
            description=description,
            files_json=files_json,
        )
        db.add(feat)
    db.flush()
    return feat


# ── Decision helpers ───────────────────────────────────────────────────────────

def add_decision(
    db: Session,
    project_id: str,
    decision_type: DecisionType,
    decision_json: dict,
    *,
    rationale: str | None = None,
    agent_role: str | None = None,
) -> ProjectDecision:
    dec = ProjectDecision(
        id=str(uuid.uuid4()),
        project_id=project_id,
        decision_type=decision_type,
        decision_json=decision_json,
        rationale=rationale,
        agent_role=agent_role,
    )
    db.add(dec)
    db.flush()
    return dec


def update_project_design_mode(
    db: Session,
    project_id: str,
    *,
    product_mode: str,
    style_mode: str,
    confidence: float | None,
    source: str,
    locked_by_user: bool | None = None,
    record_history: bool = True,
) -> Project:
    """Persist project-level design mode state and optional history."""
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise ValueError(f"Project not found: {project_id}")

    project.product_mode = product_mode
    project.style_mode = style_mode
    project.mode_confidence = confidence
    if locked_by_user is not None:
        project.design_mode_locked = locked_by_user
    project.updated_at = datetime.utcnow()

    if record_history:
        db.add(ProjectDesignModeHistory(
            id=str(uuid.uuid4()),
            project_id=project_id,
            product_mode=product_mode,
            style_mode=style_mode,
            confidence=confidence,
            source=source,
        ))

    db.flush()
    return project


def lock_project_design_mode(
    db: Session,
    project_id: str,
    *,
    product_mode: str,
    style_mode: str,
    confidence: float | None = None,
) -> Project:
    """Persist a user-selected design mode and lock it against auto-reclassification."""
    return update_project_design_mode(
        db,
        project_id,
        product_mode=product_mode,
        style_mode=style_mode,
        confidence=confidence,
        source="user",
        locked_by_user=True,
        record_history=True,
    )


def unlock_project_design_mode(db: Session, project_id: str) -> Project:
    """Unlock a project's design mode while preserving the last selected values."""
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise ValueError(f"Project not found: {project_id}")

    project.design_mode_locked = False
    project.updated_at = datetime.utcnow()
    db.flush()
    return project


def list_project_design_mode_history(db: Session, project_id: str, *, limit: int = 25) -> list[dict[str, Any]]:
    rows = (
        db.query(ProjectDesignModeHistory)
        .filter_by(project_id=project_id)
        .order_by(ProjectDesignModeHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "productMode": row.product_mode,
            "styleMode": row.style_mode,
            "confidence": float(row.confidence) if row.confidence is not None else None,
            "source": row.source,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


# ── Context assembly ──────────────────────────────────────────────────────────

def get_project_brain_context(db: Session, project_id: str) -> dict[str, Any]:
    """Return a structured summary of the project brain for LLM context injection."""
    project = db.query(Project).filter_by(id=project_id).first()
    pages = db.query(ProjectPage).filter_by(project_id=project_id).all()
    components = db.query(ProjectComponent).filter_by(project_id=project_id).all()
    features = db.query(ProjectFeature).filter_by(project_id=project_id).all()
    decisions = (
        db.query(ProjectDecision)
        .filter_by(project_id=project_id)
        .order_by(ProjectDecision.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "designMode": {
            "productMode": project.product_mode if project else None,
            "styleMode": project.style_mode if project else None,
            "confidence": float(project.mode_confidence) if project and project.mode_confidence is not None else None,
            "lockedByUser": bool(project.design_mode_locked) if project else False,
        },
        "pages": [
            {
                "id": p.id,
                "name": p.page_name,
                "route": p.route,
                "status": p.status.value if p.status else None,
                "description": p.description,
                "sections": [
                    {
                        "name": s.section_name,
                        "type": s.section_type,
                        "sort_order": s.sort_order,
                        "component_refs": s.component_refs_json,
                    }
                    for s in sorted(
                        (db.query(ProjectSection).filter_by(page_id=p.id).all()),
                        key=lambda s: s.sort_order,
                    )
                ],
            }
            for p in pages
        ],
        "components": [
            {
                "name": c.component_name,
                "file_path": c.file_path,
                "props_schema": c.props_schema_json,
                "dependencies": c.dependencies_json,
                "description": c.description,
            }
            for c in components
        ],
        "features": [
            {
                "name": f.feature_name,
                "status": f.status.value if f.status else None,
                "description": f.description,
                "files": f.files_json,
            }
            for f in features
        ],
        "recent_decisions": [
            {
                "type": d.decision_type.value if d.decision_type else None,
                "decision": d.decision_json,
                "rationale": d.rationale,
                "agent_role": d.agent_role,
            }
            for d in decisions
        ],
    }


# ── Embedding helpers (Phase 4 preparation) ───────────────────────────────────

def store_embedding(
    db: Session,
    project_id: str,
    content_type: ContentType,
    content_text: str,
    embedding: list[float],
    *,
    content_ref_id: str | None = None,
) -> str:
    """Store a text + pre-computed embedding vector. Returns the row id."""
    row_id = str(uuid.uuid4())
    # Use raw SQL for the vector column since SQLAlchemy doesn't natively
    # handle pgvector types without an extra extension package.
    db.execute(
        text("""
            INSERT INTO project_embeddings (id, project_id, content_type, content_ref_id, content_text, embedding, created_at)
            VALUES (:id, :project_id, :content_type, :ref_id, :content_text, CAST(:embedding AS vector), NOW())
            ON CONFLICT (id) DO UPDATE SET
                content_text = EXCLUDED.content_text,
                embedding    = EXCLUDED.embedding
        """),
        {
            "id": row_id,
            "project_id": project_id,
            "content_type": content_type.value,
            "ref_id": content_ref_id,
            "content_text": content_text,
            "embedding": str(embedding),  # pgvector accepts '[0.1, 0.2, ...]'
        },
    )
    db.flush()
    return row_id


def search_similar(
    db: Session,
    project_id: str,
    query_embedding: list[float],
    *,
    top_k: int = 10,
) -> list[dict]:
    """Return the top-k most similar embeddings for a project by cosine distance."""
    rows = db.execute(
        text("""
            SELECT id, content_type, content_ref_id, content_text,
                   1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
            FROM project_embeddings
            WHERE project_id = :pid
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT :topk
        """),
        {
            "pid": project_id,
            "qvec": str(query_embedding),
            "topk": top_k,
        },
    ).fetchall()

    return [
        {
            "id": r.id,
            "content_type": r.content_type,
            "content_ref_id": r.content_ref_id,
            "content_text": r.content_text,
            "similarity": float(r.similarity),
        }
        for r in rows
    ]


# ── Embedding count helper ─────────────────────────────────────────────────────

def has_embeddings(db: Session, project_id: str) -> bool:
    """Check whether a project has any stored embeddings."""
    row = db.execute(
        text("SELECT COUNT(*) FROM project_embeddings WHERE project_id = :pid"),
        {"pid": project_id},
    ).scalar()
    return (row or 0) > 0


def embedding_count(db: Session, project_id: str) -> int:
    """Return the number of stored embeddings for a project."""
    return db.execute(
        text("SELECT COUNT(*) FROM project_embeddings WHERE project_id = :pid"),
        {"pid": project_id},
    ).scalar() or 0


def delete_project_embeddings(db: Session, project_id: str) -> int:
    """Delete all embeddings for a project (for re-indexing). Returns count deleted."""
    result = db.execute(
        text("DELETE FROM project_embeddings WHERE project_id = :pid"),
        {"pid": project_id},
    )
    db.flush()
    return result.rowcount or 0
