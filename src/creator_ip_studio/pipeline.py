from __future__ import annotations

import asyncio
import json
import math
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .artifacts import LocalArtifactStore, sha256_file
from .config import resolve_profile
from .models import (
    ArtifactRef,
    ProjectSpec,
    QCCheck,
    QCReport,
    ResolvedProfile,
    StageManifest,
    StageState,
)


class PipelineError(RuntimeError):
    pass


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout)[-4000:]
        raise PipelineError(f"command failed ({result.returncode}): {' '.join(command[:3])}\n{tail}")
    return result


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump_json"):
        text = payload.model_dump_json(indent=2)
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    path.write_text(text + "\n", encoding="utf-8")


def _timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def _captions(narration: str, duration: float) -> str:
    phrases = [part.strip() for part in narration.replace("。", ".").split(".") if part.strip()]
    if not phrases:
        phrases = ["Creator IP Studio smoke test"]
    slot = duration / len(phrases)
    blocks = []
    for index, phrase in enumerate(phrases, start=1):
        start = (index - 1) * slot
        end = min(duration, index * slot - 0.05)
        blocks.append(f"{index}\n{_timestamp(start)} --> {_timestamp(end)}\n{phrase}\n")
    return "\n".join(blocks)


async def _edge_tts(narration: str, output: Path, voice: str, rate: str) -> None:
    try:
        import edge_tts
    except ImportError as exc:
        raise PipelineError("edge-tts is not installed; install the 'tts' extra") from exc
    communicate = edge_tts.Communicate(narration, voice=voice, rate=rate)
    await communicate.save(str(output))


def _probe(path: Path, cwd: Path) -> dict[str, Any]:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,width,height,codec_name",
            "-of",
            "json",
            str(path),
        ],
        cwd=cwd,
    )
    return json.loads(result.stdout)


def _duration(probe: dict[str, Any]) -> float:
    return float(probe.get("format", {}).get("duration", 0.0))


def _stage(
    *,
    name: str,
    started: datetime,
    start_clock: float,
    outputs: list[ArtifactRef],
    provider: str,
) -> StageManifest:
    now = datetime.now(UTC)
    return StageManifest(
        stage=name,
        state=StageState.SUCCEEDED,
        outputs=outputs,
        provider=provider,
        provider_version="1",
        started_at=started,
        completed_at=now,
        elapsed_seconds=round(time.monotonic() - start_clock, 3),
    )


def run_project(
    workspace: Path,
    spec: ProjectSpec,
    *,
    profile_id: str = "workspace",
) -> dict[str, Any]:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise PipelineError("ffmpeg and ffprobe are required")

    resolved: ResolvedProfile = resolve_profile(workspace, profile_id=profile_id)
    project = (workspace.resolve() / "projects" / spec.project_id).resolve()
    if workspace.resolve() not in project.parents:
        raise PipelineError("project id escapes workspace")
    audio_dir = project / "audio" / "output"
    render_dir = project / "renders"
    delivery_dir = project / "delivery"
    pipeline_dir = project / ".pipeline"
    for path in (audio_dir, render_dir, delivery_dir, pipeline_dir):
        path.mkdir(parents=True, exist_ok=True)
    store = LocalArtifactStore(workspace / "projects")

    _write_json(project / "project.json", spec)
    _write_json(pipeline_dir / "resolved-profile.json", resolved)
    (pipeline_dir / "resolved-profile.sha256").write_text(resolved.sha256 + "\n", encoding="utf-8")

    stage_manifests: list[StageManifest] = []
    narration = spec.narration.strip()
    if not narration:
        raise PipelineError("narration must not be empty")

    started = datetime.now(UTC)
    clock = time.monotonic()
    audio_path: Path
    if resolved.profile.voice.provider == "edge":
        audio_path = audio_dir / "narration_master.mp3"
        asyncio.run(
            _edge_tts(
                narration,
                audio_path,
                resolved.profile.voice.name,
                resolved.profile.voice.rate,
            )
        )
        audio_duration = _duration(_probe(audio_path, project))
        provider = "edge-tts"
    else:
        audio_path = audio_dir / "narration_master.wav"
        audio_duration = float(spec.target_seconds)
        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=220:sample_rate=48000:duration={audio_duration}",
                "-af",
                "volume=0.025",
                "-c:a",
                "pcm_s16le",
                str(audio_path),
            ],
            cwd=project,
        )
        provider = "builtin-tone"
    audio_ref = store.ref(audio_path, media_type="audio/wav", stage="audio")
    stage_manifests.append(
        _stage(name="audio", started=started, start_clock=clock, outputs=[audio_ref], provider=provider)
    )

    started = datetime.now(UTC)
    clock = time.monotonic()
    captions_path = project / "captions.srt"
    captions_path.write_text(_captions(narration, audio_duration), encoding="utf-8")
    captions_ref = store.ref(captions_path, media_type="application/x-subrip", stage="captions")
    stage_manifests.append(
        _stage(
            name="captions",
            started=started,
            start_clock=clock,
            outputs=[captions_ref],
            provider="builtin",
        )
    )

    started = datetime.now(UTC)
    clock = time.monotonic()
    canvas = resolved.profile.canvas
    base_video = render_dir / "base.mp4"
    video_source = (
        f"color=c=0x{canvas.background.lstrip('#')}:"
        f"s={canvas.width}x{canvas.height}:r={canvas.fps}:d={audio_duration}"
    )
    video_filter = (
        "drawtext=text='Creator IP Studio':fontcolor=white:fontsize=54:"
        "x=(w-text_w)/2:y=h*0.28,"
        "drawtext=text='Reproducible video smoke test':fontcolor=0xB9B4FF:fontsize=30:"
        "x=(w-text_w)/2:y=h*0.40,"
        "subtitles=captions.srt:force_style='FontName=Noto Sans CJK TC,FontSize=22,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00111111,BorderStyle=1,Outline=2,"
        "Alignment=2,MarginV=70'"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            video_source,
            "-i",
            str(audio_path),
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(base_video),
        ],
        cwd=project,
    )
    video_ref = store.ref(base_video, media_type="video/mp4", stage="render")
    stage_manifests.append(
        _stage(
            name="render",
            started=started,
            start_clock=clock,
            outputs=[video_ref],
            provider="ffmpeg",
        )
    )

    started = datetime.now(UTC)
    clock = time.monotonic()
    probe = _probe(base_video, project)
    streams = probe.get("streams", [])
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})
    measured_duration = _duration(probe)
    checks = [
        QCCheck(
            name="duration",
            passed=math.isclose(measured_duration, audio_duration, abs_tol=max(0.2, 1 / canvas.fps)),
            measured=round(measured_duration, 3),
            expected=round(audio_duration, 3),
        ),
        QCCheck(
            name="resolution",
            passed=(video_stream.get("width"), video_stream.get("height"))
            == (canvas.width, canvas.height),
            measured=[video_stream.get("width"), video_stream.get("height")],
            expected=[canvas.width, canvas.height],
        ),
        QCCheck(name="video_track", passed=bool(video_stream), measured=video_stream.get("codec_name")),
        QCCheck(name="audio_track", passed=bool(audio_stream), measured=audio_stream.get("codec_name")),
        QCCheck(name="captions", passed=captions_path.stat().st_size > 0),
        QCCheck(name="profile_hash", passed=len(resolved.sha256) == 64, measured=resolved.sha256),
    ]
    qc = QCReport(passed=all(check.passed for check in checks), checks=checks)
    qc_path = project / "qc-report.json"
    _write_json(qc_path, qc)
    qc_ref = store.ref(qc_path, media_type="application/json", stage="qc")
    stage_manifests.append(
        _stage(name="qc", started=started, start_clock=clock, outputs=[qc_ref], provider="ffprobe")
    )
    if not qc.passed:
        raise PipelineError(f"quality checks failed; see {qc_path}")

    delivered_video = delivery_dir / f"{spec.project_id}.mp4"
    delivered_captions = delivery_dir / f"{spec.project_id}.srt"
    shutil.copy2(base_video, delivered_video)
    shutil.copy2(captions_path, delivered_captions)
    cover = delivery_dir / f"{spec.project_id}-cover.jpg"
    _run(
        ["ffmpeg", "-y", "-ss", "1", "-i", str(base_video), "-frames:v", "1", str(cover)],
        cwd=project,
    )
    delivery = {
        "project": spec.model_dump(mode="json"),
        "resolved_profile_sha256": resolved.sha256,
        "artifacts": [
            store.ref(delivered_video, media_type="video/mp4", stage="delivery").model_dump(mode="json"),
            store.ref(delivered_captions, media_type="application/x-subrip", stage="delivery").model_dump(mode="json"),
            store.ref(cover, media_type="image/jpeg", stage="delivery").model_dump(mode="json"),
        ],
        "publishing": {
            "title": spec.title,
            "description": f"Generated by Creator IP Studio. Profile {resolved.sha256[:12]}.",
            "status": "requires-human-review",
        },
    }
    delivery_manifest = delivery_dir / "manifest.json"
    _write_json(delivery_manifest, delivery)
    for manifest in stage_manifests:
        _write_json(pipeline_dir / f"stage-{manifest.stage}.json", manifest)
    _write_json(pipeline_dir / "stages.json", [m.model_dump(mode="json") for m in stage_manifests])

    return {
        "project_id": spec.project_id,
        "project_dir": str(project),
        "video": str(delivered_video),
        "cover": str(cover),
        "captions": str(delivered_captions),
        "manifest": str(delivery_manifest),
        "qc": str(qc_path),
        "profile_sha256": resolved.sha256,
        "video_sha256": sha256_file(delivered_video),
    }

