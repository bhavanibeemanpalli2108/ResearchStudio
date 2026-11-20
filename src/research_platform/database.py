"""SQLAlchemy storage shared by API and independent durable worker."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "rp_projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(180))
    question: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(120))
    objectives: Mapped[list] = mapped_column(JSON, default=list)
    references: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class Run(Base):
    __tablename__ = "rp_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("rp_projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    current_stage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    profile: Mapped[str] = mapped_column(String(30))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(180))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    approval: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    control: Mapped[str | None] = mapped_column(String(20), nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class Job(Base):
    __tablename__ = "rp_jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("rp_runs.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    heartbeat_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resume_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class WorkflowEvent(Base):
    __tablename__ = "rp_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rp_runs.id"), index=True)
    stage: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class Decision(Base):
    __tablename__ = "rp_decisions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("rp_runs.id"), index=True)
    stage: Mapped[str] = mapped_column(String(60))
    summary: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class Experiment(Base):
    __tablename__ = "rp_experiments"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rp_runs.id"), index=True)
    status: Mapped[str] = mapped_column(String(24))
    hypothesis: Mapped[str] = mapped_column(Text)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    logs: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_ids: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[str] = mapped_column(String(40), default=utcnow)
    finished_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Artifact(Base):
    __tablename__ = "rp_artifacts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rp_runs.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    kind: Mapped[str] = mapped_column(String(40))
    media_type: Mapped[str] = mapped_column(String(100))
    relative_path: Mapped[str] = mapped_column(String(500), unique=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class ModelUsage(Base):
    __tablename__ = "rp_model_usage"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("rp_runs.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(180))
    stage: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="reserved")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reserved_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow, index=True)


class ResearchItem(Base):
    __tablename__ = "rp_research_items"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rp_runs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    data: Mapped[dict] = mapped_column(JSON)


class GatewayGrant(Base):
    """Authorization only; all request accounting remains in ModelUsage."""

    __tablename__ = "rp_gateway_grants"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("rp_runs.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    allowed_models: Mapped[list] = mapped_column(JSON)
    max_output_tokens: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[float] = mapped_column(Float)
    revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class TraceReference(Base):
    __tablename__ = "rp_traces"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rp_runs.id"), index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


def as_dict(row: Base) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


class Database:
    def __init__(self, url: str) -> None:
        parsed = make_url(url)
        if (
            parsed.get_backend_name() == "sqlite"
            and parsed.database
            and parsed.database != ":memory:"
        ):
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 30}
            if parsed.get_backend_name() == "sqlite"
            else {},
            pool_pre_ping=True,
        )
        if parsed.get_backend_name() == "sqlite":

            @event.listens_for(self.engine, "connect")
            def sqlite_settings(connection: Any, _: Any) -> None:
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")

        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def migrate(self) -> None:
        from alembic import command
        from alembic.config import Config
        from .config import REPO_ROOT

        cfg = Config(str(REPO_ROOT / "apps/research_platform/backend/alembic.ini"))
        cfg.set_main_option(
            "script_location", str(REPO_ROOT / "apps/research_platform/backend/migrations")
        )
        with self.engine.begin() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
