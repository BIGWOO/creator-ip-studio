import httpx
from pathlib import Path

from creator_ip_studio.providers.duix import DuixProvider
from creator_ip_studio.providers.moneyprinter import MoneyPrinterProvider


def test_moneyprinter_health_failure_is_reported(monkeypatch):
    def fail(*_args, **_kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", fail)
    report = MoneyPrinterProvider("http://127.0.0.1:9999").health()
    assert not report.healthy
    assert "offline" in report.detail


def test_duix_health_exposes_gpu_capability(monkeypatch):
    class Response:
        status_code = 200

    monkeypatch.setattr(httpx, "get", lambda *_args, **_kwargs: Response())
    report = DuixProvider("http://127.0.0.1:8383").health()
    assert report.healthy
    assert report.requires_gpu


def test_duix_submit_uses_shared_container_paths(monkeypatch, tmp_path: Path):
    audio = tmp_path / "narration.wav"
    video = tmp_path / "reference.mp4"
    audio.write_bytes(b"audio")
    video.write_bytes(b"video")
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 10000}

    def post(*_args, **kwargs):
        captured.update(kwargs["json"])
        return Response()

    monkeypatch.setattr(httpx, "post", post)
    DuixProvider("http://127.0.0.1:8383").submit(audio, video)

    assert captured["audio_url"] == str(audio.resolve())
    assert captured["video_url"] == str(video.resolve())
    assert not captured["audio_url"].startswith("file:")
