from __future__ import annotations

import socket
import time
from pathlib import Path

import httpx

from .config import init_workspace
from .models import ProjectSpec
from .pipeline import run_project
from .settings import settings


def main() -> None:
    capabilities = [item.strip() for item in settings.worker_capabilities.split(",") if item.strip()]
    headers = {"X-Worker-Token": settings.worker_token}
    workspace = Path(settings.workspace)
    init_workspace(workspace, mode="nvidia" if "nvidia" in capabilities else "cpu")
    with httpx.Client(base_url=settings.api_url, headers=headers, timeout=30.0) as client:
        registration = client.post(
            "/v1/workers/register",
            json={"name": socket.gethostname(), "capabilities": capabilities},
        )
        registration.raise_for_status()
        worker_id = registration.json()["worker_id"]
        while True:
            response = client.post(
                "/v1/workers/lease",
                json={"worker_id": worker_id, "capabilities": capabilities},
            )
            response.raise_for_status()
            body = response.json()
            lease = body.get("lease")
            if not lease:
                time.sleep(2)
                continue
            success = True
            error = None
            result = {}
            try:
                spec = ProjectSpec.model_validate(body["project"])
                result = run_project(workspace, spec, profile_id=spec.profile_id)
            except Exception as exc:  # worker must report failures to the control plane
                success = False
                error = f"{type(exc).__name__}: {exc}"
            complete = client.post(
                f"/v1/stages/{lease['id']}/complete",
                json={
                    "worker_id": worker_id,
                    "lease_id": lease["lease_id"],
                    "success": success,
                    "result": result,
                    "error": error,
                },
            )
            complete.raise_for_status()

