"""
Embedding Service — text-to-vector conversion for semantic retrieval.

Uses litellm to call embedding models (OpenAI text-embedding-3-small by default).
Stores embeddings via brain_service into the project_embeddings table (pgvector).
"""
from __future__ import annotations

import os
import asyncio
from typing import Any

import litellm

from sqlalchemy.orm import Session
from models import ContentType
from brain_service import store_embedding, search_similar

# ── Configuration ──────────────────────────────────────────────────────────────

# Default embedding model — 1536 dimensions, matches our pgvector schema.
DEFAULT_EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "text-embedding-3-small"
)

# Max tokens per embedding call (text-embedding-3-small supports 8191).
# We chunk content that exceeds this.
_MAX_CHUNK_CHARS = 24_000  # ~6k tokens, safe for embedding models


# ── Core embedding functions ───────────────────────────────────────────────────

async def embed_text(
    text: str,
    *,
    model: str | None = None,
) -> list[float]:
    """Generate a 1536-dim embedding vector for a text string."""
    model = model or DEFAULT_EMBEDDING_MODEL

    # Truncate if necessary — embedding models have input limits
    truncated = text[:_MAX_CHUNK_CHARS] if len(text) > _MAX_CHUNK_CHARS else text

    response = await litellm.aembedding(
        model=model,
        input=[truncated],
    )
    return response.data[0]["embedding"]


async def embed_texts(
    texts: list[str],
    *,
    model: str | None = None,
    batch_size: int = 20,
) -> list[list[float]]:
    """Generate embeddings for multiple texts in batches.

    Returns a list of embedding vectors in the same order as input texts.
    """
    model = model or DEFAULT_EMBEDDING_MODEL
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = [
            t[:_MAX_CHUNK_CHARS] if len(t) > _MAX_CHUNK_CHARS else t
            for t in texts[i:i + batch_size]
        ]
        response = await litellm.aembedding(
            model=model,
            input=batch,
        )
        all_embeddings.extend(entry["embedding"] for entry in response.data)

    return all_embeddings


# ── File embedding helpers ─────────────────────────────────────────────────────

async def embed_and_store_file(
    db: Session,
    project_id: str,
    file_path: str,
    content: str,
    *,
    model: str | None = None,
) -> str | None:
    """Generate embedding for a source file and store in project_embeddings.

    Returns the embedding row id, or None if embedding failed.
    """
    if not content or not content.strip():
        return None

    # Build a contextual string: include file path for semantic relevance
    embed_text_str = f"File: {file_path}\n\n{content}"

    try:
        embedding = await embed_text(embed_text_str, model=model)
        row_id = store_embedding(
            db, project_id,
            content_type=ContentType.file,
            content_text=embed_text_str[:10_000],  # cap stored text
            embedding=embedding,
            content_ref_id=file_path,
        )
        return row_id
    except Exception as e:
        print(f"[embedding] Failed to embed file {file_path}: {e}")
        return None


async def embed_and_store_component(
    db: Session,
    project_id: str,
    component_name: str,
    description: str,
    file_path: str | None = None,
    *,
    model: str | None = None,
) -> str | None:
    """Generate embedding for a component summary and store."""
    text = f"Component: {component_name}"
    if file_path:
        text += f" ({file_path})"
    text += f"\n{description}"

    try:
        embedding = await embed_text(text, model=model)
        return store_embedding(
            db, project_id,
            content_type=ContentType.component,
            content_text=text[:10_000],
            embedding=embedding,
            content_ref_id=file_path or component_name,
        )
    except Exception as e:
        print(f"[embedding] Failed to embed component {component_name}: {e}")
        return None


async def embed_and_store_decision(
    db: Session,
    project_id: str,
    decision_id: str,
    decision_text: str,
    *,
    model: str | None = None,
) -> str | None:
    """Generate embedding for an architectural decision."""
    try:
        embedding = await embed_text(decision_text, model=model)
        return store_embedding(
            db, project_id,
            content_type=ContentType.decision,
            content_text=decision_text[:10_000],
            embedding=embedding,
            content_ref_id=decision_id,
        )
    except Exception as e:
        print(f"[embedding] Failed to embed decision {decision_id}: {e}")
        return None


# ── Project-level operations ───────────────────────────────────────────────────

async def reindex_project(
    db: Session,
    project_id: str,
    files: dict[str, str],
    *,
    model: str | None = None,
    progress_callback: Any = None,
) -> dict:
    """Re-embed all project files and brain entities.

    Args:
        files: dict of {file_path: content} for all project source files.
        progress_callback: optional async callable(step, total, message)

    Returns:
        {"files_indexed": int, "components_indexed": int, "errors": int}
    """
    from models import ProjectComponent, ProjectDecision

    stats = {"files_indexed": 0, "components_indexed": 0, "decisions_indexed": 0, "errors": 0}
    total_items = len(files)

    # ── Index source files ──────────────────────────────────────────────
    file_paths = list(files.keys())
    file_contents = list(files.values())
    embed_texts_list = [
        f"File: {fp}\n\n{content}" for fp, content in zip(file_paths, file_contents)
        if content and content.strip()
    ]
    valid_paths = [
        fp for fp, content in zip(file_paths, file_contents)
        if content and content.strip()
    ]

    if embed_texts_list:
        try:
            embeddings = await embed_texts(embed_texts_list, model=model)
            for fp, emb, etxt in zip(valid_paths, embeddings, embed_texts_list):
                try:
                    store_embedding(
                        db, project_id,
                        content_type=ContentType.file,
                        content_text=etxt[:10_000],
                        embedding=emb,
                        content_ref_id=fp,
                    )
                    stats["files_indexed"] += 1
                except Exception as e:
                    print(f"[reindex] File store error {fp}: {e}")
                    stats["errors"] += 1
        except Exception as e:
            print(f"[reindex] Batch embed error: {e}")
            stats["errors"] += len(embed_texts_list)

    if progress_callback:
        await progress_callback(stats["files_indexed"], total_items, "Files indexed")

    # ── Index components from brain ─────────────────────────────────────
    components = db.query(ProjectComponent).filter_by(project_id=project_id).all()
    for comp in components:
        text = f"Component: {comp.component_name}"
        if comp.file_path:
            text += f" ({comp.file_path})"
        if comp.description:
            text += f"\n{comp.description}"
        if comp.props_schema_json:
            text += f"\nProps: {str(comp.props_schema_json)[:500]}"

        try:
            emb = await embed_text(text, model=model)
            store_embedding(
                db, project_id,
                content_type=ContentType.component,
                content_text=text[:10_000],
                embedding=emb,
                content_ref_id=comp.file_path or comp.component_name,
            )
            stats["components_indexed"] += 1
        except Exception as e:
            print(f"[reindex] Component embed error {comp.component_name}: {e}")
            stats["errors"] += 1

    # ── Index recent decisions ──────────────────────────────────────────
    decisions = (
        db.query(ProjectDecision)
        .filter_by(project_id=project_id)
        .order_by(ProjectDecision.created_at.desc())
        .limit(50)
        .all()
    )
    for dec in decisions:
        text = f"Decision ({dec.decision_type.value if dec.decision_type else 'unknown'}): "
        if dec.rationale:
            text += dec.rationale + "\n"
        if dec.decision_json:
            text += str(dec.decision_json)[:1000]

        try:
            emb = await embed_text(text, model=model)
            store_embedding(
                db, project_id,
                content_type=ContentType.decision,
                content_text=text[:10_000],
                embedding=emb,
                content_ref_id=dec.id,
            )
            stats["decisions_indexed"] += 1
        except Exception as e:
            print(f"[reindex] Decision embed error {dec.id}: {e}")
            stats["errors"] += 1

    db.commit()
    print(f"[reindex] Project {project_id}: {stats}")
    return stats


# ── Semantic search wrapper ────────────────────────────────────────────────────

async def search_relevant(
    db: Session,
    project_id: str,
    query: str,
    *,
    top_k: int = 10,
    model: str | None = None,
) -> list[dict]:
    """Search for embeddings most relevant to a user query.

    Returns list of {id, content_type, content_ref_id, content_text, similarity}.
    """
    try:
        query_embedding = await embed_text(query, model=model)
        return search_similar(db, project_id, query_embedding, top_k=top_k)
    except Exception as e:
        print(f"[embedding] Semantic search failed: {e}")
        return []
