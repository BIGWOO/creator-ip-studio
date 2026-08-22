import httpx

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

