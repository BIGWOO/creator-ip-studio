from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Annotated

import typer

from .config import init_workspace, resolve_profile
from .doctor import inspect_environment
from .models import ProjectSpec
from .pipeline import run_project
from .providers import DuixProvider, MiniMaxH3Provider, MoneyPrinterProvider
from .smoke import run_smoke

app = typer.Typer(no_args_is_help=True, help="Creator IP Studio control CLI")
project_app = typer.Typer(no_args_is_help=True, help="Create and run video projects")
provider_app = typer.Typer(no_args_is_help=True, help="Inspect optional providers")
app.add_typer(project_app, name="project")
app.add_typer(provider_app, name="provider")


def _print(payload) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


@app.command()
def doctor(
    mode: Annotated[str, typer.Option(help="cpu, nvidia, or cloud")] = "cpu",
    workspace: Annotated[Path | None, typer.Option()] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON")] = False,
) -> None:
    report = inspect_environment(mode, workspace)
    if json_output:
        _print(report)
    else:
        typer.echo(f"Creator IP Studio doctor: {'PASS' if report['ok'] else 'NEEDS ATTENTION'}")
        for item in report["checks"]:
            typer.echo(f"  [{'OK' if item['ok'] else '--'}] {item['name']}: {item['detail']}")
        typer.echo(f"  Free disk: {report['disk_free_gb']} GB")
    if not report["ok"]:
        raise typer.Exit(1)


@app.command("init")
def init_command(
    workspace: Annotated[Path, typer.Option(help="Workspace directory")],
    mode: Annotated[str, typer.Option(help="cpu, nvidia, or cloud")] = "cpu",
) -> None:
    root = init_workspace(workspace, mode=mode)
    _print({"workspace": str(workspace.resolve()), "config_root": str(root), "mode": mode})


@app.command()
def resolve(
    workspace: Annotated[Path, typer.Option()],
    profile_id: Annotated[str, typer.Option()] = "workspace",
    project_config: Annotated[Path | None, typer.Option()] = None,
) -> None:
    _print(resolve_profile(workspace, profile_id=profile_id, project_config=project_config).model_dump(mode="json"))


@app.command()
def smoke(
    workspace: Annotated[Path, typer.Option()] = Path("workspace"),
    duration: Annotated[int, typer.Option(min=5, max=120)] = 20,
) -> None:
    _print(run_smoke(workspace, duration=duration))


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "video-project"


@project_app.command("create")
def project_create(
    title: Annotated[str, typer.Option(prompt=True)],
    narration_file: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    workspace: Annotated[Path, typer.Option()] = Path("workspace"),
    project_id: Annotated[str | None, typer.Option()] = None,
    target_seconds: Annotated[int, typer.Option(min=5, max=3600)] = 60,
) -> None:
    init_workspace(workspace)
    spec = ProjectSpec(
        project_id=project_id or _slug(title),
        title=title,
        source=str(narration_file.resolve()),
        narration=narration_file.read_text(encoding="utf-8"),
        target_seconds=target_seconds,
    )
    target = workspace.resolve() / ".creator-ip" / "projects" / f"{spec.project_id}.json"
    target.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    _print({"project": spec.model_dump(mode="json"), "spec_path": str(target)})


@app.command()
def run(
    project: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    workspace: Annotated[Path, typer.Option()] = Path("workspace"),
) -> None:
    spec = ProjectSpec.model_validate_json(project.read_text(encoding="utf-8"))
    _print(run_project(workspace, spec, profile_id=spec.profile_id))


@provider_app.command("check")
def provider_check(
    name: Annotated[str, typer.Argument(help="moneyprinter, duix, or minimax-h3")],
    base_url: Annotated[str | None, typer.Option()] = None,
) -> None:
    if name == "moneyprinter":
        provider = MoneyPrinterProvider(base_url or os.getenv("MPT_BASE_URL", "http://127.0.0.1:8081"))
    elif name == "duix":
        provider = DuixProvider(base_url or os.getenv("DUIX_BASE_URL", "http://127.0.0.1:8383"))
    elif name == "minimax-h3":
        provider = MiniMaxH3Provider(base_url or os.getenv("MINIMAX_H3_BASE_URL", "http://127.0.0.1:8188"))
    else:
        raise typer.BadParameter("provider must be moneyprinter, duix, or minimax-h3")
    report = provider.health()
    _print(report.model_dump(mode="json"))
    if not report.healthy:
        raise typer.Exit(1)


@provider_app.command("h3-generate")
def h3_generate(
    prompt: Annotated[str, typer.Option(prompt=True)],
    output: Annotated[Path, typer.Option()] = Path("minimax-h3-output.mp4"),
    preset: Annotated[str, typer.Option(help="draft or quality")] = "draft",
    width: Annotated[int, typer.Option()] = 512,
    height: Annotated[int, typer.Option()] = 288,
    frames: Annotated[int, typer.Option()] = 39,
    seed: Annotated[int, typer.Option()] = 42,
    timeout_seconds: Annotated[int, typer.Option()] = 1800,
    base_url: Annotated[str | None, typer.Option()] = None,
) -> None:
    if preset not in {"draft", "quality"}:
        raise typer.BadParameter("preset must be draft or quality")
    provider = MiniMaxH3Provider(base_url or os.getenv("MINIMAX_H3_BASE_URL", "http://127.0.0.1:8188"))
    workflow = provider.workflow(
        prompt,
        preset=preset,
        width=width,
        height=height,
        frames=frames,
        seed=seed,
    )
    prompt_id = provider.submit(workflow)
    result = provider.wait(prompt_id, timeout_seconds=timeout_seconds)
    files = provider.output_files(result)
    videos = [item for item in files if item["filename"].lower().endswith((".mp4", ".webm", ".mov"))]
    if not videos:
        raise RuntimeError(f"ComfyUI prompt {prompt_id} completed without a video output")
    target = provider.download(videos[0], output)
    _print({"prompt_id": prompt_id, "preset": preset, "output": str(target), "source": videos[0]})


if __name__ == "__main__":
    app()
