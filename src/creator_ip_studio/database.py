from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .models import ProjectSpec, RunState
from .settings import settings


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    spec_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    until_stage: Mapped[str] = mapped_column(String(32), default="preview")
    required_capability: Mapped[str] = mapped_column(String(32), default="ffmpeg")
    lease_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    leased_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkerRecord(Base):
    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    capabilities_json: Mapped[str] = mapped_column(Text)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def engine():
    kwargs = {"pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(settings.database_url, **kwargs)


ENGINE = engine()


def init_database() -> None:
    Base.metadata.create_all(ENGINE)


def create_project(spec: ProjectSpec) -> ProjectRecord:
    now = datetime.now(UTC)
    record = ProjectRecord(
        id=spec.project_id,
        title=spec.title,
        spec_json=spec.model_dump_json(),
        created_at=now,
    )
    with Session(ENGINE) as session:
        session.merge(record)
        session.commit()
    return record


def create_run(project_id: str, until_stage: str) -> RunRecord:
    now = datetime.now(UTC)
    record = RunRecord(
        id=str(uuid.uuid4()),
        project_id=project_id,
        state=RunState.QUEUED,
        until_stage=until_stage,
        created_at=now,
        updated_at=now,
    )
    with Session(ENGINE) as session:
        if session.get(ProjectRecord, project_id) is None:
            raise KeyError(project_id)
        session.add(record)
        session.commit()
        session.refresh(record)
        session.expunge(record)
    return record


def register_worker(name: str, capabilities: list[str]) -> WorkerRecord:
    now = datetime.now(UTC)
    record = WorkerRecord(
        id=str(uuid.uuid4()),
        name=name,
        capabilities_json=json.dumps(capabilities),
        last_seen_at=now,
    )
    with Session(ENGINE) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        session.expunge(record)
    return record


def lease_run(worker_id: str, capabilities: list[str]) -> RunRecord | None:
    now = datetime.now(UTC)
    with Session(ENGINE) as session:
        worker = session.get(WorkerRecord, worker_id)
        if worker is None:
            raise KeyError(worker_id)
        worker.last_seen_at = now

        expired = session.scalars(
            select(RunRecord).where(
                RunRecord.state == RunState.LEASED,
                RunRecord.lease_expires_at < now,
            )
        ).all()
        for item in expired:
            item.state = RunState.QUEUED
            item.lease_id = None
            item.leased_by = None
            item.lease_expires_at = None

        query = (
            select(RunRecord)
            .where(RunRecord.state == RunState.QUEUED)
            .order_by(RunRecord.created_at)
            .with_for_update(skip_locked=True)
        )
        record = session.scalars(query).first()
        if record is None or record.required_capability not in capabilities:
            session.commit()
            return None
        record.state = RunState.LEASED
        record.lease_id = str(uuid.uuid4())
        record.leased_by = worker_id
        record.lease_expires_at = now + timedelta(seconds=settings.lease_seconds)
        record.updated_at = now
        session.commit()
        session.refresh(record)
        session.expunge(record)
        return record


def complete_run(
    run_id: str,
    *,
    worker_id: str,
    lease_id: str,
    success: bool,
    result: dict,
    error: str | None,
) -> RunRecord:
    with Session(ENGINE) as session:
        record = session.get(RunRecord, run_id)
        if record is None:
            raise KeyError(run_id)
        if record.leased_by != worker_id or record.lease_id != lease_id:
            raise PermissionError("lease does not match")
        record.state = RunState.SUCCEEDED if success else RunState.FAILED
        record.result_json = json.dumps(result, ensure_ascii=False)
        record.error = error
        record.updated_at = datetime.now(UTC)
        session.commit()
        session.refresh(record)
        session.expunge(record)
        return record


def get_run(run_id: str) -> RunRecord | None:
    with Session(ENGINE) as session:
        record = session.get(RunRecord, run_id)
        if record:
            session.expunge(record)
        return record


def get_project(project_id: str) -> ProjectSpec | None:
    with Session(ENGINE) as session:
        record = session.get(ProjectRecord, project_id)
        return ProjectSpec.model_validate_json(record.spec_json) if record else None


def list_runs(limit: int = 50) -> list[RunRecord]:
    with Session(ENGINE) as session:
        records = list(
            session.scalars(select(RunRecord).order_by(RunRecord.created_at.desc()).limit(limit))
        )
        for record in records:
            session.expunge(record)
        return records

