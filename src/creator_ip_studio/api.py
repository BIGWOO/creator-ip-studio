from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .database import (
    complete_run,
    create_project,
    create_run,
    get_project,
    get_run,
    init_database,
    lease_run,
    list_runs,
    register_worker,
)
from .models import (
    ProjectSpec,
    RunComplete,
    RunCreate,
    WorkerLeaseRequest,
    WorkerRegistration,
)
from .settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="Creator IP Studio", version="0.1.0", lifespan=lifespan)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def worker_auth(x_worker_token: str = Header(default="")) -> None:
    if x_worker_token != settings.worker_token:
        raise HTTPException(status_code=401, detail="invalid worker token")


def _run_payload(record) -> dict:
    return {
        "id": record.id,
        "project_id": record.project_id,
        "state": record.state,
        "until": record.until_stage,
        "lease_id": record.lease_id,
        "leased_by": record.leased_by,
        "lease_expires_at": record.lease_expires_at,
        "result": json.loads(record.result_json or "{}"),
        "error": record.error,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"runs": [_run_payload(item) for item in list_runs()]},
    )


@app.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict:
    init_database()
    return {"status": "ready"}


@app.post("/v1/projects", status_code=201)
def projects_create(spec: ProjectSpec) -> dict:
    record = create_project(spec)
    return {"id": record.id, "title": record.title, "created_at": record.created_at}


@app.post("/v1/projects/{project_id}/runs", status_code=202)
def runs_create(project_id: str, body: RunCreate) -> dict:
    try:
        record = create_run(project_id, body.until)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc
    return _run_payload(record)


@app.get("/v1/runs/{run_id}")
def runs_get(run_id: str) -> dict:
    record = get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _run_payload(record)


@app.get("/v1/runs/{run_id}/artifacts")
def run_artifacts(run_id: str) -> dict:
    record = get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {"run_id": run_id, "artifacts": json.loads(record.result_json or "{}").get("artifacts", [])}


@app.post("/v1/runs/{run_id}/approvals")
def approve_run(run_id: str) -> dict:
    record = get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {"run_id": run_id, "accepted": True, "note": "approval recorded by caller"}


@app.post("/v1/workers/register", dependencies=[Depends(worker_auth)], status_code=201)
def workers_register(body: WorkerRegistration) -> dict:
    record = register_worker(body.name, body.capabilities)
    return {"worker_id": record.id, "capabilities": json.loads(record.capabilities_json)}


@app.post("/v1/workers/lease", dependencies=[Depends(worker_auth)])
def workers_lease(body: WorkerLeaseRequest) -> dict:
    try:
        record = lease_run(body.worker_id, body.capabilities)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="worker not found") from exc
    if record is None:
        return {"lease": None}
    spec = get_project(record.project_id)
    return {"lease": _run_payload(record), "project": spec.model_dump(mode="json") if spec else None}


@app.post("/v1/workers/{worker_id}/heartbeat", dependencies=[Depends(worker_auth)])
def worker_heartbeat(worker_id: str) -> dict:
    return {"worker_id": worker_id, "accepted": True}


@app.post("/v1/stages/{run_id}/complete", dependencies=[Depends(worker_auth)])
def stages_complete(run_id: str, body: RunComplete) -> dict:
    try:
        record = complete_run(
            run_id,
            worker_id=body.worker_id,
            lease_id=body.lease_id,
            success=body.success,
            result=body.result,
            error=body.error,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _run_payload(record)


def main() -> None:
    import uvicorn

    uvicorn.run("creator_ip_studio.api:app", host="0.0.0.0", port=8080)

