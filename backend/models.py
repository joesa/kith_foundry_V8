from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, Boolean, DateTime,
    Float, Enum as SAEnum, JSON, create_engine, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import enum, os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is required. Set it in .env to your Nhost Postgres connection string (Dashboard → Settings → Database).")
# SQLAlchemy requires postgresql:// not postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
