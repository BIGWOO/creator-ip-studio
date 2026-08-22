from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from creator_ip_studio import database
from creator_ip_studio.api import app


def test_api_project_run_and_worker_lease(monkeypatch, tmp_path: Path):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(database, "ENGINE", test_engine)
    database.Base.metadata.create_all(test_engine)
    headers = {"X-Worker-Token": "local-development"}

    with TestClient(app) as client:
        project = client.post(
            "/v1/projects",
            json={
                "project_id": "episode-1",
                "title": "Episode 1",
                "narration": "A short test.",
                "target_seconds": 10,
            },
        )
        assert project.status_code == 201
        run = client.post("/v1/projects/episode-1/runs", json={"until": "preview"})
        assert run.status_code == 202

        worker = client.post(
            "/v1/workers/register",
            headers=headers,
            json={"name": "test-worker", "capabilities": ["cpu", "ffmpeg"]},
        )
        assert worker.status_code == 201
        lease = client.post(
            "/v1/workers/lease",
            headers=headers,
            json={"worker_id": worker.json()["worker_id"], "capabilities": ["cpu", "ffmpeg"]},
        )
        assert lease.status_code == 200
        assert lease.json()["lease"]["project_id"] == "episode-1"

