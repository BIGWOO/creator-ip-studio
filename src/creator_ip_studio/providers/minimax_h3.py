from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Literal

import httpx

from creator_ip_studio.models import ProviderCapabilities

from .base import Provider

Preset = Literal["draft", "quality"]

REQUIRED_NODES = {
    "UNETLoader",
    "CLIPLoader",
    "VAELoader",
    "LoraLoaderModelOnly",
    "MiniMaxH3Director",
    "ApplyMiniMaxH3FirstBlockCache",
    "CreateVideo",
    "SaveVideo",
}

MODEL_FILES = {
    "fl2va": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
    "text": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "video_vae": "minimax_h3_video_vae_fp16.safetensors",
    "audio_vae": "minimax_h3_audio_vae_fp32.safetensors",
    "turbo": "minimax_h3_fl2v_lightx2v_turbo_4step_v0.1_comfy_resized_avg_rank_21_bf16.safetensors",
}


class MiniMaxH3Provider(Provider):
    """Pinned MiniMax H3 workflows served through ComfyUI's REST API."""

    def __init__(self, base_url: str, timeout: float = 30.0, poll_interval: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval

    def health(self) -> ProviderCapabilities:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                system = client.get(f"{self.base_url}/system_stats").raise_for_status().json()
                object_info = client.get(f"{self.base_url}/object_info").raise_for_status().json()
            missing = sorted(REQUIRED_NODES - set(object_info))
            devices = system.get("devices", [])
            device = devices[0].get("name", "unknown GPU") if devices else "no GPU"
            version = system.get("system", {}).get("comfyui_version", "unknown")
            healthy = not missing and bool(devices)
            detail = f"ComfyUI {version}; {device}"
            if missing:
                detail += f"; missing nodes: {', '.join(missing)}"
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            healthy = False
            detail = str(exc)
        return ProviderCapabilities(
            name="minimax-h3",
            healthy=healthy,
            base_url=self.base_url,
            capabilities=["text-to-video", "image-to-video", "video-with-audio"],
            requires_gpu=True,
            detail=detail,
        )

    @staticmethod
    def _output_prefix(value: str | None) -> str:
        prefix = value or f"creator-ip/{uuid.uuid4()}"
        path = PurePosixPath(prefix.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or not re.fullmatch(r"[A-Za-z0-9_./-]+", str(path)):
            raise ValueError("output_prefix must be a safe relative ComfyUI output path")
        return str(path)

    @staticmethod
    def _timeline(prompt: str, *, width: int, height: int, frames: int, fps: float) -> str:
        task = "t2v — 文生视频(Text to Video)"
        timeline = {
            "version": 4,
            "editMode": "global",
            "timelineMode": "gen_blank",
            "totalFrames": frames,
            "frameRate": fps,
            "width": width,
            "height": height,
            "refMaxSize": max(width, height),
            "output": {
                "mode": "fixed",
                "longEdge": max(width, height),
                "width": width,
                "height": height,
                "maxExportFrames": 0,
                "exportMode": "all",
                "audioMode": "generate",
                "continuityEnabled": False,
                "continuityOverlapFrames": 9,
            },
            "videoClips": [],
            "video": {"fileName": "", "videoFile": "", "subfolder": "", "type": "input", "frames": [], "frameMap": []},
            "global": {
                "taskType": task,
                "prompt": prompt,
                "refs": [],
                "referenceVideo": {},
                "continuousReference": False,
                "genImage": {"imageFile": ""},
            },
            "segments": [
                {
                    "id": "s0",
                    "start": 0,
                    "length": frames,
                    "frameCount": frames,
                    "prompt": "",
                    "taskType": "",
                    "refs": [],
                    "referenceVideo": {},
                }
            ],
            "runSelectEnabled": False,
            "runSelection": [],
        }
        return json.dumps(timeline, ensure_ascii=False, separators=(",", ":"))

    def workflow(
        self,
        prompt: str,
        *,
        preset: Preset = "quality",
        width: int = 864,
        height: int = 480,
        frames: int = 124,
        fps: float = 24.0,
        seed: int = 42,
        output_prefix: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if width < 256 or height < 256 or width % 16 or height % 16:
            raise ValueError("width and height must be at least 256 and divisible by 16")
        if not 9 <= frames <= 4096:
            raise ValueError("frames must be between 9 and 4096")
        if not 1 <= fps <= 60:
            raise ValueError("fps must be between 1 and 60")

        workflow: dict[str, dict[str, Any]] = {
            "1": {
                "class_type": "UNETLoader",
                "inputs": {"unet_name": MODEL_FILES["fl2va"], "weight_dtype": "default"},
            },
            "2": {
                "class_type": "CLIPLoader",
                "inputs": {"clip_name": MODEL_FILES["text"], "type": "minimax", "device": "default"},
            },
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": MODEL_FILES["video_vae"]}},
            "4": {"class_type": "VAELoader", "inputs": {"vae_name": MODEL_FILES["audio_vae"]}},
        }

        if preset == "quality":
            workflow["5"] = {
                "class_type": "ApplyMiniMaxH3FirstBlockCache",
                "inputs": {
                    "mode": "H3 Fast — 0.10 / max 2",
                    "threshold": 0.10,
                    "start_percent": 0.10,
                    "end_percent": 0.95,
                    "max_consecutive_hits": 2,
                    "temporal_guard": False,
                    "model": ["1", 0],
                },
            }
            model_ref = ["5", 0]
            steps = 25
            sampler = "res_multistep"
        elif preset == "draft":
            workflow["5"] = {
                "class_type": "LoraLoaderModelOnly",
                "inputs": {"model": ["1", 0], "lora_name": MODEL_FILES["turbo"], "strength_model": 0.75},
            }
            model_ref = ["5", 0]
            steps = 4
            sampler = "er_sde"
        else:
            raise ValueError(f"unsupported preset: {preset}")

        task = "t2v — 文生视频(Text to Video)"
        workflow["6"] = {
            "class_type": "MiniMaxH3Director",
            "inputs": {
                "task_type": task,
                "global_prompt": prompt.strip(),
                "bd_grp_sample": "采样设置",
                "cfg": 1.0,
                "seed": seed,
                "frame_rate": fps,
                "width": width,
                "height": height,
                "ref_max_size": max(width, height),
                "total_frames": frames,
                "timeline_data": self._timeline(prompt.strip(), width=width, height=height, frames=frames, fps=fps),
                "bd_grp_advanced": "高级采样",
                "steps": steps,
                "sampler": sampler,
                "scheduler": "simple",
                "shift_video": 12.0,
                "shift_audio": 3.0,
                "bd_grp_perf": "性能",
                "clear_vram_between_segments": True,
                "export_source_images": False,
                "model": model_ref,
                "video_vae": ["3", 0],
                "audio_vae": ["4", 0],
                "clip": ["2", 0],
            },
        }
        workflow["7"] = {
            "class_type": "CreateVideo",
            "inputs": {"images": ["6", 0], "fps": ["6", 2], "audio": ["6", 1]},
        }
        workflow["8"] = {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["7", 0],
                "filename_prefix": self._output_prefix(output_prefix),
                "format": "auto",
                "codec": "auto",
            },
        }
        return workflow

    def submit(self, workflow: dict[str, Any], *, client_id: str = "creator-ip-studio") -> str:
        response = httpx.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"ComfyUI rejected the workflow: {response.text[:4000]}") from exc
        prompt_id = response.json().get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt_id")
        return str(prompt_id)

    def status(self, prompt_id: str) -> dict[str, Any] | None:
        response = httpx.get(f"{self.base_url}/history/{prompt_id}", timeout=self.timeout)
        response.raise_for_status()
        return response.json().get(prompt_id)

    def wait(self, prompt_id: str, *, timeout_seconds: float = 1800) -> dict[str, Any]:
        started = time.monotonic()
        while time.monotonic() - started <= timeout_seconds:
            result = self.status(prompt_id)
            if result is not None:
                status = result.get("status", {})
                if status.get("completed") or status.get("status_str") == "success":
                    return result
                raise RuntimeError(f"ComfyUI prompt failed: {status}")
            time.sleep(self.poll_interval)
        raise TimeoutError(f"ComfyUI prompt {prompt_id} exceeded {timeout_seconds} seconds")

    @staticmethod
    def output_files(result: dict[str, Any]) -> list[dict[str, str]]:
        files: list[dict[str, str]] = []
        for output in result.get("outputs", {}).values():
            for key in ("images", "videos", "audio"):
                for item in output.get(key, []):
                    if isinstance(item, dict) and item.get("filename"):
                        files.append(
                            {
                                "filename": str(item["filename"]),
                                "subfolder": str(item.get("subfolder", "")),
                                "type": str(item.get("type", "output")),
                            }
                        )
        return files

    def download(self, output: dict[str, str], destination: Path) -> Path:
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream(
            "GET",
            f"{self.base_url}/view",
            params=output,
            timeout=httpx.Timeout(self.timeout, read=None),
        ) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        return destination
