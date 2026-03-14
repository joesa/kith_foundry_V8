from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, Boolean, DateTime,
    Float, Enum as SAEnum, JSON, create_engine, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime
import asyncio
import enum, os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # For local development, fall back to a file-based SQLite DB so `python main.py`
    # works without requiring an external Postgres instance. In production
    # require `DATABASE_URL` to be set explicitly.
    if os.getenv("ENVIRONMENT", "development") != "production":
        sqlite_path = os.path.join(os.path.dirname(__file__), "dev.db")
        DATABASE_URL = f"sqlite:///{sqlite_path}"
        print("[models] WARNING: DATABASE_URL not set — using local SQLite for development:", DATABASE_URL)
    else:
        raise ValueError("DATABASE_URL is required. Set it in .env to your Nhost Postgres connection string (Dashboard → Settings → Database).")
# SQLAlchemy requires postgresql:// not postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── PgBouncer support ─────────────────────────────────────────────────────────
# Set PGBOUNCER=true in the environment (fly-backend.toml [env]) to route
# connections through Nhost's built-in PgBouncer (port 6543, transaction
# mode).  This lets us run many Fly machines without exceeding Postgres
# max_connections: each machine's workers share a tiny pool that PgBouncer
# multiplexes, instead of each worker claiming 60 long-lived connections.
_is_pgbouncer = os.getenv("PGBOUNCER", "").lower() in ("1", "true", "yes")
if _is_pgbouncer and DATABASE_URL.startswith("postgresql"):
    # Switch to port 6543 (Nhost PgBouncer) if still on direct Postgres port 5432
    import re as _re
    DATABASE_URL = _re.sub(r":5432/", ":6543/", DATABASE_URL)
    # Mark the connection as going through pgbouncer so asyncpg disables
    # prepared-statement caching (required for transaction-mode pooling).
    if "pgbouncer=true" not in DATABASE_URL:
        DATABASE_URL += ("&" if "?" in DATABASE_URL else "?") + "pgbouncer=true"

# Use generous connection pool for high-throughput production workloads.
# With PgBouncer in transaction mode, each worker only needs a small pool
# (PgBouncer does the real multiplexing).  Without it, keep the larger pool.
# SQLite (dev fallback) does not support pool args, so skip them entirely.
if DATABASE_URL.startswith("postgresql"):
    _pool_kwargs = (
        dict(pool_size=2, max_overflow=3, pool_recycle=300, pool_pre_ping=True)
        if _is_pgbouncer else
        dict(pool_size=20, max_overflow=40, pool_recycle=300, pool_pre_ping=True)
    )
else:
    _pool_kwargs = dict(pool_pre_ping=True)

engine = create_engine(DATABASE_URL, **_pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Async engine (asyncpg) for non-blocking DB access in async handlers ───────
if DATABASE_URL.startswith("postgresql"):
    _async_connect_args = (
        {"prepared_statement_cache_size": 0}  # required for PgBouncer transaction mode
        if _is_pgbouncer else {}
    )
    _async_pool_kwargs = (
        dict(pool_size=2, max_overflow=3, pool_recycle=300, pool_pre_ping=True)
        if _is_pgbouncer else
        dict(pool_size=20, max_overflow=40, pool_recycle=300, pool_pre_ping=True)
    )
    _ASYNC_DATABASE_URL = (
        DATABASE_URL
        # Strip pgbouncer=true param — asyncpg doesn't understand it; we handle
        # prepared-statement caching via connect_args instead.
        .replace("&pgbouncer=true", "").replace("?pgbouncer=true", "")
        .replace("postgresql://", "postgresql+asyncpg://")
        .replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    )
    _async_engine = create_async_engine(
        _ASYNC_DATABASE_URL,
        connect_args=_async_connect_args,
        **_async_pool_kwargs,
    )
    AsyncSessionLocal = async_sessionmaker(_async_engine, expire_on_commit=False, class_=AsyncSession)
else:
    # SQLite dev fallback — async engine not available without aiosqlite.
    # get_async_db() will raise if called, but module import succeeds.
    _async_engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """FastAPI dependency — yields an AsyncSession (non-blocking, asyncpg)."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Async DB requires PostgreSQL (DATABASE_URL must start with postgresql://).")
    async with AsyncSessionLocal() as session:
        yield session


async def run_db(fn):
    """Run a synchronous DB operation in a thread pool.

    Usage::

        result = await run_db(lambda db: db.query(Project).filter(...).first())

    A fresh SessionLocal is created inside the thread and closed after ``fn``
    returns, so the caller must not access ORM objects outside the lambda or
    convert them to plain dicts / primitives first.
    """
    def _wrapper():
        db = SessionLocal()
        try:
            return fn(db)
        finally:
            db.close()
    return await asyncio.to_thread(_wrapper)


# ── Enums ────────────────────────────────────────────────────────────────────

class ProjectStatus(str, enum.Enum):
    ideation = "ideation"
    csuite_pending = "csuite_pending"
    csuite_running = "csuite_running"
    csuite_complete = "csuite_complete"
    building = "building"
    deployed = "deployed"


class IdeaSource(str, enum.Enum):
    unique_gen = "unique_gen"
    questionnaire = "questionnaire"
    user_prompt = "user_prompt"


class CSuiteRole(str, enum.Enum):
    ceo = "ceo"
    cto = "cto"
    cfo = "cfo"
    cmo = "cmo"
    cpo = "cpo"
    coo = "coo"
    cdo = "cdo"


class AgentStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    error = "error"


class ArtifactType(str, enum.Enum):
    exec_summary = "exec_summary"
    product_requirements = "product_requirements"
    tech_architecture = "tech_architecture"
    design_tokens = "design_tokens"
    design_system = "design_system"
    design_components = "design_components"
    financial_model = "financial_model"
    gtm_plan = "gtm_plan"
    api_docs = "api_docs"
    bootstrap_prompt = "bootstrap_prompt"
    market_analysis = "market_analysis"
    user_personas = "user_personas"
    competitive_matrix = "competitive_matrix"
    roadmap = "roadmap"
    monetization = "monetization"


class MockupStatus(str, enum.Enum):
    pending = "pending"
    generating = "generating"
    complete = "complete"
    approved = "approved"
    error = "error"


class MockupPriority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


# ── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)  # Supabase auth.users.id (UUID string)
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    is_super_admin = Column(Boolean, default=False, nullable=False, server_default="false")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    ideas = relationship("Idea", back_populates="user", cascade="all, delete-orphan")
    provider_keys = relationship("ProviderKey", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True)  # UUID string
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    problem_statement = Column(Text, nullable=True)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.ideation, nullable=False)
    fly_sandbox_id = Column(String, nullable=True, index=True)
    preview_url = Column(String, nullable=True)
    auto_save_enabled = Column(Boolean, default=True)
    design_preferences = Column(JSON, nullable=True)  # {theme, style, color_preference, ...}
    idea_id = Column(String, ForeignKey("ideas.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    idea = relationship("Idea", back_populates="project", foreign_keys=[idea_id])
    files = relationship("File", back_populates="project", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="project", cascade="all, delete-orphan")
    csuite_analyses = relationship("CSuiteAnalysis", back_populates="project", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    design_mockups = relationship("DesignMockup", back_populates="project", cascade="all, delete-orphan")
    pages = relationship("ProjectPage", back_populates="project", cascade="all, delete-orphan")
    components = relationship("ProjectComponent", back_populates="project", cascade="all, delete-orphan")
    features = relationship("ProjectFeature", back_populates="project", cascade="all, delete-orphan")
    decisions = relationship("ProjectDecision", back_populates="project", cascade="all, delete-orphan")
    embeddings = relationship("ProjectEmbedding", back_populates="project", cascade="all, delete-orphan")


class Idea(Base):
    __tablename__ = "ideas"
    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    content = Column(JSON, nullable=False)  # Full idea details as structured JSON
    score = Column(Integer, nullable=True)
    source = Column(SAEnum(IdeaSource), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ideas")
    project = relationship("Project", back_populates="idea", foreign_keys=[Project.idea_id])


class IdeaQuestionnaireResponse(Base):
    __tablename__ = "idea_questionnaire_responses"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    responses = Column(JSON, nullable=False)  # All Q&A as structured JSON
    created_at = Column(DateTime, default=datetime.utcnow)


class GeneratedIdeaGlobal(Base):
    """Track every unique idea ever generated globally, for dedup."""
    __tablename__ = "generated_ideas_global"
    id = Column(String, primary_key=True, index=True)
    idea_hash = Column(String, unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    claimed_by = Column(String, ForeignKey("users.id"), nullable=True, index=True)  # user who started building
    claimed_at = Column(DateTime, nullable=True)  # when they started building
    created_at = Column(DateTime, default=datetime.utcnow)


class SavedIdea(Base):
    """Ideas saved by users for later. Not exclusive until claimed (built)."""
    __tablename__ = "saved_ideas"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    content = Column(JSON, nullable=False)  # Full idea details
    score = Column(Integer, nullable=True)
    source = Column(SAEnum(IdeaSource), nullable=False)
    idea_hash = Column(String, nullable=True, index=True)  # links to GeneratedIdeaGlobal
    is_claimed = Column(Boolean, default=False)  # True = user started building, idea is exclusive
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class CSuiteAnalysis(Base):
    __tablename__ = "csuite_analyses"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    agent_role = Column(SAEnum(CSuiteRole), nullable=False)
    analysis = Column(JSON, nullable=True)  # Structured analysis result
    score = Column(Integer, nullable=True)
    status = Column(SAEnum(AgentStatus), default=AgentStatus.pending, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="csuite_analyses")

    __table_args__ = (
        UniqueConstraint("project_id", "agent_role", name="uq_project_agent"),
    )


class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    artifact_type = Column(SAEnum(ArtifactType), nullable=False)
    title = Column(String, nullable=False)
    content = Column(JSON, nullable=True)  # Structured content or large text
    status = Column(SAEnum(AgentStatus), default=AgentStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="artifacts")

    __table_args__ = (
        UniqueConstraint("project_id", "artifact_type", name="uq_project_artifact"),
    )


class DesignMockup(Base):
    __tablename__ = "design_mockups"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    screen_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(SAEnum(MockupPriority), default=MockupPriority.medium, nullable=False)
    prompt = Column(Text, nullable=True)  # Mini-prompt for generating this screen
    component_code = Column(Text, nullable=True)  # Generated React component code
    status = Column(SAEnum(MockupStatus), default=MockupStatus.pending, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="design_mockups")


class File(Base):
    __tablename__ = "files"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    file_path = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="files")

    __table_args__ = (
        UniqueConstraint("project_id", "file_path", name="uq_project_filepath"),
    )


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="messages")


class ProviderKey(Base):
    __tablename__ = "provider_keys"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)  # nullable for legacy global keys
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    base_url = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="provider_keys")


class ModelRouting(Base):
    """Per-user, per-task model routing config."""
    __tablename__ = "model_routings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    task_type = Column(String, nullable=False)  # "code_gen", "csuite", "design", "ideation"
    provider_id = Column(Integer, ForeignKey("provider_keys.id"), nullable=True)
    model_id = Column(String, nullable=True)  # e.g. "gemini-2.5-flash", "anthropic/claude-sonnet-4-6"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
    provider = relationship("ProviderKey")
    __table_args__ = (
        UniqueConstraint("user_id", "task_type", name="uq_user_task_routing"),
    )


# ── Billing / Subscription ────────────────────────────────────────────────────

class SubscriptionTier(str, enum.Enum):
    free = "free"
    indie = "indie"
    pro = "pro"
    team = "team"
    enterprise = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    canceled = "canceled"
    unpaid = "unpaid"


class Subscription(Base):
    """One active (or cancelled) subscription row per user."""
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    tier = Column(SAEnum(SubscriptionTier), default=SubscriptionTier.free, nullable=False)
    status = Column(SAEnum(SubscriptionStatus), default=SubscriptionStatus.active, nullable=False)
    # Stripe identifiers
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    stripe_price_id = Column(String, nullable=True)
    # Billing period
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    # Optional team seats (for team/enterprise tiers)
    seat_count = Column(Integer, default=1, nullable=False)
    # BYOK discount applied?
    byok_discount_applied = Column(Boolean, default=False)
    # Annual plan?
    is_annual = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="subscription")


class UsageRecord(Base):
    """
    Tracks billable usage per user per calendar month.
    One row per user+month; columns for each usage type.
    """
    __tablename__ = "usage_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    # Billing month: YYYY-MM (e.g. "2026-03")
    billing_month = Column(String(7), nullable=False, index=True)
    csuite_runs = Column(Integer, default=0, nullable=False)
    design_screens = Column(Integer, default=0, nullable=False)
    artifact_sets = Column(Integer, default=0, nullable=False)
    project_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "billing_month", name="uq_user_billing_month"),
    )


class UsagePack(Base):
    """
    One-time purchased usage packs added on top of plan limits.
    pack_type: 'csuite_runs' | 'design_screens'
    pack_size: 25 for C-Suite runs, 50 for design screens
    """
    __tablename__ = "usage_packs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    pack_type = Column(String, nullable=False)   # 'csuite_runs' | 'design_screens'
    pack_size = Column(Integer, nullable=False)   # 25 or 50
    remaining = Column(Integer, nullable=False)   # decrements as used
    stripe_payment_intent = Column(String, nullable=True)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # None = never expires


# ── Project Brain ──────────────────────────────────────────────────────────────

class PageStatus(str, enum.Enum):
    planned = "planned"
    scaffolded = "scaffolded"
    implemented = "implemented"
    revised = "revised"


class FeatureStatus(str, enum.Enum):
    planned = "planned"
    in_progress = "in_progress"
    implemented = "implemented"
    deferred = "deferred"


class DecisionType(str, enum.Enum):
    layout = "layout"
    component = "component"
    routing = "routing"
    styling = "styling"
    data_model = "data_model"
    library = "library"
    architecture = "architecture"


class ContentType(str, enum.Enum):
    file = "file"
    page = "page"
    component = "component"
    section = "section"
    decision = "decision"
    message = "message"


class ProjectPage(Base):
    __tablename__ = "project_pages"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    page_name = Column(String, nullable=False)
    route = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    layout_json = Column(JSON, nullable=True)
    status = Column(SAEnum(PageStatus), default=PageStatus.planned, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="pages")
    sections = relationship("ProjectSection", back_populates="page", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "route", name="uq_project_route"),
    )


class ProjectComponent(Base):
    __tablename__ = "project_components"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    component_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    props_schema_json = Column(JSON, nullable=True)
    dependencies_json = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="components")

    __table_args__ = (
        UniqueConstraint("project_id", "file_path", name="uq_project_component_path"),
    )


class ProjectSection(Base):
    __tablename__ = "project_sections"
    id = Column(String, primary_key=True, index=True)
    page_id = Column(String, ForeignKey("project_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    section_name = Column(String, nullable=False)
    section_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    component_refs_json = Column(JSON, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)

    page = relationship("ProjectPage", back_populates="sections")


class ProjectFeature(Base):
    __tablename__ = "project_features"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_name = Column(String, nullable=False)
    status = Column(SAEnum(FeatureStatus), default=FeatureStatus.planned, nullable=False)
    description = Column(Text, nullable=True)
    files_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="features")

    __table_args__ = (
        UniqueConstraint("project_id", "feature_name", name="uq_project_feature"),
    )


class ProjectDecision(Base):
    __tablename__ = "project_decisions"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    decision_type = Column(SAEnum(DecisionType), nullable=False)
    decision_json = Column(JSON, nullable=False)
    rationale = Column(Text, nullable=True)
    agent_role = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="decisions")


class ProjectEmbedding(Base):
    __tablename__ = "project_embeddings"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    content_type = Column(SAEnum(ContentType), nullable=False)
    content_ref_id = Column(String, nullable=True)
    content_text = Column(Text, nullable=False)
    # embedding column is vector(1536) — managed via raw SQL in migration;
    # SQLAlchemy reads/writes are handled via brain_service using pgvector helpers
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="embeddings")

