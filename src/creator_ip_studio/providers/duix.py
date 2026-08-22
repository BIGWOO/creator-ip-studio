from __future__ import annotations

import uuid
from pathlib import Path

import httpx

from creator_ip_studio.models import ProviderCapabilities

from .base import Provider


class DuixProvider(Provider):
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> ProviderCapabilities:
        try:
            response = httpx.get(f"{self.base_url}/easy/query", params={"code": "healthcheck"}, timeout=self.timeout)
            healthy = response.status_code < 500
            detail = f"HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            healthy = False
            detail = str(exc)
        return ProviderCapabilities(
            name="duix",
            healthy=healthy,
            base_url=self.base_url,
            capabilities=["avatar-lip-sync"],
            requires_gpu=True,
            detail=detail,
        )

    def submit(self, audio: Path, video: Path) -> tuple[str, dict]:
        if not audio.is_file() or not video.is_file():
            raise FileNotFoundError("Duix requires existing audio and reference video")
        code = str(uuid.uuid4())
        payload = {
            "audio_url": audio.resolve().as_uri(),
            "video_url": video.resolve().as_uri(),
            "code": code,
            "chaofen": 0,
            "watermark_switch": 0,
            "pn": 1,
        }
        response = httpx.post(f"{self.base_url}/easy/submit", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return code, response.json()

    def status(self, code: str) -> dict:
        response = httpx.get(
            f"{self.base_url}/easy/query", params={"code": code}, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

