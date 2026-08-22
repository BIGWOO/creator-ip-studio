from __future__ import annotations

import hashlib
import json
import shutil
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from .models import ResolvedProfile, RuntimeProfile, WorkspaceProfile


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def config_root(workspace: Path) -> Path:
    return workspace.resolve() / ".creator-ip"


def init_workspace(workspace: Path, *, mode: str = "cpu") -> Path:
    workspace = workspace.resolve()
    root = config_root(workspace)
    for relative in (
        "profiles",
        "projects",
        "resolved",
        "assets/voice",
        "assets/avatar",
        "assets/character",
        "assets/logo",
        "assets/music",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (workspace / "projects").mkdir(parents=True, exist_ok=True)

    template_root = files("creator_ip_studio.templates")
    profile_target = root / "profiles" / "workspace.yaml"
    runtime_target = root / "runtime.local.yaml"
    if not profile_target.exists():
        shutil.copyfile(template_root / "default-profile.yaml", profile_target)
        data = _load_yaml(profile_target)
        data["profile_id"] = "workspace"
        _dump_yaml(profile_target, data)
    if not runtime_target.exists():
        shutil.copyfile(template_root / "runtime.local.example.yaml", runtime_target)
        runtime = _load_yaml(runtime_target)
        runtime.update(
            {
                "mode": mode,
                "workspace_root": workspace.as_posix(),
                "artifact_root": (workspace / "projects").as_posix(),
            }
        )
        _dump_yaml(runtime_target, runtime)
    return root


def resolve_profile(
    workspace: Path,
    *,
    profile_id: str = "workspace",
    project_config: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> ResolvedProfile:
    root = config_root(workspace)
    profile_path = root / "profiles" / f"{profile_id}.yaml"
    runtime_path = root / "runtime.local.yaml"
    if not profile_path.is_file() or not runtime_path.is_file():
        raise FileNotFoundError(f"incomplete config root: {root}")

    defaults = _load_yaml(Path(str(files("creator_ip_studio.templates") / "default-profile.yaml")))
    data = deep_merge(defaults, _load_yaml(profile_path))
    sources = ["builtin:default-profile", str(profile_path)]
    if project_config:
        data = deep_merge(data, _load_yaml(project_config))
        sources.append(str(project_config))
    if cli_overrides:
        data = deep_merge(data, cli_overrides)
        sources.append("cli")

    profile = WorkspaceProfile.model_validate(data)
    runtime = RuntimeProfile.model_validate(_load_yaml(runtime_path))
    canonical = json.dumps(
        {"profile": profile.model_dump(mode="json"), "runtime": runtime.model_dump(mode="json")},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    resolved = ResolvedProfile(
        profile=profile,
        runtime=runtime,
        sources=sources + [str(runtime_path)],
        sha256=digest,
    )
    target = root / "resolved" / f"{profile_id}-{digest[:12]}.json"
    target.write_text(resolved.model_dump_json(indent=2), encoding="utf-8")
    return resolved

