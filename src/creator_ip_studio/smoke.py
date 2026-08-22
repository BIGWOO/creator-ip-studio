from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .config import init_workspace
from .models import ProjectSpec
from .pipeline import run_project

SMOKE_TEXT = (
    "Creator IP Studio turns a repeatable idea into a versioned production workflow. "
    "This test verifies audio, captions, rendering, quality checks, and delivery artifacts. "
    "The result can be reproduced locally or on a compatible cloud worker."
)


def run_smoke(workspace: Path, *, duration: int = 20) -> dict:
    init_workspace(workspace)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    spec = ProjectSpec(
        project_id=f"smoke-{stamp}",
        title="Creator IP Studio smoke test",
        narration=SMOKE_TEXT,
        language="en",
        target_seconds=duration,
    )
    return run_project(workspace, spec)


def main() -> int:
    result = run_smoke(Path("workspace"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

