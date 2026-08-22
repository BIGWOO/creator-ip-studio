from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _command(
    name: str,
    args: list[str] | None = None,
    *,
    candidates: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    executable = next(
        (path for candidate in (candidates or (name,)) if (path := shutil.which(candidate))),
        None,
    )
    if not executable:
        return {"name": name, "ok": False, "detail": "not found"}
    try:
        result = subprocess.run(
            [executable, *(args or ["--version"])],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        detail = (result.stdout or result.stderr).strip().splitlines()
        return {
            "name": name,
            "ok": result.returncode == 0,
            "path": executable,
            "detail": detail[0] if detail else f"exit {result.returncode}",
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"name": name, "ok": False, "path": executable, "detail": str(exc)}


def inspect_environment(mode: str = "cpu", workspace: Path | None = None) -> dict[str, Any]:
    root = (workspace or Path.cwd()).resolve()
    checks = [
        _command("git"),
        _command("python", candidates=("python", "python3")),
        _command("uv"),
        _command("ffmpeg", ["-version"]),
        _command("ffprobe", ["-version"]),
        _command("docker", ["version", "--format", "{{.Server.Version}}"]),
        _command("node"),
    ]
    if mode in {"nvidia", "cloud"}:
        checks.append(
            _command(
                "nvidia-smi",
                ["--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            )
        )
    usage = shutil.disk_usage(root.anchor or root)
    required = {"git", "python", "ffmpeg", "ffprobe"}
    if mode in {"nvidia", "cloud"}:
        required.add("nvidia-smi")
    by_name = {item["name"]: item for item in checks}
    missing = [name for name in sorted(required) if not by_name.get(name, {}).get("ok")]
    return {
        "ok": not missing,
        "mode": mode,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "workspace": str(root),
        "disk_free_gb": round(usage.free / (1024**3), 2),
        "checks": checks,
        "missing_required": missing,
        "environment": {
            "wsl_distro": os.getenv("WSL_DISTRO_NAME"),
            "container": Path("/.dockerenv").exists(),
        },
    }


def main() -> int:
    report = inspect_environment()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1
