"""Compatibility and approval safety regressions; never live acceptance evidence."""

from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.research_platform.backend.app import create_app
from src.research_platform.config import Settings
from src.research_platform.database import Database, Run, Job
from src.research_platform.schemas import RunCreate
from src.research_platform.worker import Worker


def test_native_protocol_requires_approval_and_rejects_old_version():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RunCreate(profile="free_research", provider="groq", require_approval=False)
    with pytest.raises(ValidationError):
        RunCreate(execution_protocol=1)


def test_genuine_approval_binds_digest_and_old_run_cannot_resume(tmp_path):
    settings = replace(
        Settings(),
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
        artifact_root=tmp_path / "artifacts",
        checkpoint_path=tmp_path / "checkpoints.db",
    )
    db = Database(settings.database_url)
    with TestClient(create_app(settings, database=db)) as client:
        project = client.post(
            "/api/projects",
            json={
                "title": "Question-specific study",
                "question": "Does shortest-processing-time scheduling improve total completion time?",
            },
        ).json()
        response = client.post(
            f"/api/projects/{project['id']}/runs",
            json={"profile": "free_research", "provider": "groq", "model": "discovered-model"},
        )
        assert response.status_code == 201
        identifier = response.json()["id"]
        with db.sessions.begin() as session:
            run = session.get(Run, identifier)
            run.status, run.approval = "awaiting_approval", {"gate": "approval"}
            run.state = {"experiment_config": {"approval_digest": "a" * 64}}
            session.scalar(select(Job).where(Job.run_id == identifier)).status = "waiting"
        assert (
            client.post(f"/api/runs/{identifier}/approve", json={"approved": True}).status_code
            == 409
        )
        assert (
            client.post(
                f"/api/runs/{identifier}/approve",
                json={"approved": True, "approval_digest": "b" * 64},
            ).status_code
            == 409
        )
        assert (
            client.post(
                f"/api/runs/{identifier}/approve",
                json={"approved": True, "approval_digest": "a" * 64},
            ).status_code
            == 200
        )
        with db.sessions.begin() as session:
            run = session.get(Run, identifier)
            run.status = "paused"
            run.config = {**run.config, "execution_protocol": 1}
            session.scalar(select(Job).where(Job.run_id == identifier)).status = "waiting"
        assert client.post(f"/api/runs/{identifier}/resume").status_code == 409


def test_legacy_worker_cannot_claim_or_recover_native_jobs(tmp_path):
    settings = replace(
        Settings(),
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
        artifact_root=tmp_path / "artifacts",
        checkpoint_path=tmp_path / "checkpoints.db",
    )
    db = Database(settings.database_url)
    with TestClient(create_app(settings, database=db)) as client:
        project = client.post(
            "/api/projects",
            json={
                "title": "Version fence",
                "question": "Does shortest-processing-time scheduling reduce total completion time?",
            },
        ).json()
        run = client.post(
            f"/api/projects/{project['id']}/runs",
            json={"profile": "free_research", "provider": "groq", "model": "configured-model"},
        ).json()
        with db.sessions() as session:
            job = session.scalar(select(Job).where(Job.run_id == run["id"]))
            assert job.status == "queued_v2"
            # These are the exact status predicates used by old workers.
            assert session.scalar(select(Job).where(Job.status == "queued")) is None
        worker = Worker(settings, db)
        assert worker.claim()[0] == run["id"]
        with db.sessions.begin() as session:
            job = session.scalar(select(Job).where(Job.run_id == run["id"]))
            assert job.status == "running_v2"
            job.lease_until = 0
        with db.sessions() as session:
            assert (
                session.scalar(select(Job).where(Job.status == "running", Job.lease_until < 1))
                is None
            )
        assert worker.claim()[0] == run["id"]
