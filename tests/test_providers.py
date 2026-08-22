from pathlib import Path

import httpx

from creator_ip_studio.providers.duix import DuixProvider
from creator_ip_studio.providers.minimax_h3 import REQUIRED_NODES, MiniMaxH3Provider
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


def test_minimax_h3_health_validates_gpu_and_required_nodes(monkeypatch):
    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return self

        def json(self):
            return self.payload

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, url):
            if url.endswith("/system_stats"):
                return Response(
                    {
                        "system": {"comfyui_version": "0.31.0"},
                        "devices": [{"name": "NVIDIA GeForce RTX 3090"}],
                    }
                )
            return Response({name: {} for name in REQUIRED_NODES})

    monkeypatch.setattr(httpx, "Client", Client)
    report = MiniMaxH3Provider("http://127.0.0.1:8188").health()

    assert report.healthy
    assert report.requires_gpu
    assert "RTX 3090" in report.detail


def test_minimax_h3_workflow_has_distinct_draft_and_quality_paths():
    provider = MiniMaxH3Provider("http://127.0.0.1:8188")
    quality = provider.workflow("A calm studio shot", preset="quality", width=512, height=288, frames=39)
    draft = provider.workflow("A calm studio shot", preset="draft", width=512, height=288, frames=39)

    assert quality["5"]["class_type"] == "ApplyMiniMaxH3FirstBlockCache"
    assert quality["6"]["inputs"]["steps"] == 25
    assert quality["6"]["inputs"]["sampler"] == "res_multistep"
    assert draft["5"]["class_type"] == "LoraLoaderModelOnly"
    assert draft["6"]["inputs"]["steps"] == 4
    assert draft["6"]["inputs"]["sampler"] == "er_sde"


def test_minimax_h3_workflow_rejects_unsafe_output_prefix():
    provider = MiniMaxH3Provider("http://127.0.0.1:8188")

    try:
        provider.workflow("test", width=512, height=288, frames=39, output_prefix="../escape")
    except ValueError as exc:
        assert "safe relative" in str(exc)
    else:
        raise AssertionError("unsafe ComfyUI output prefix was accepted")


def test_minimax_h3_extracts_comfyui_video_outputs():
    result = {
        "outputs": {
            "8": {
                "images": [
                    {
                        "filename": "clip_00001_.mp4",
                        "subfolder": "creator-ip",
                        "type": "output",
                    }
                ]
            }
        }
    }

    assert MiniMaxH3Provider.output_files(result) == [
        {"filename": "clip_00001_.mp4", "subfolder": "creator-ip", "type": "output"}
    ]
