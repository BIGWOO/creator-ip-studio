from __future__ import annotations

import httpx

from creator_ip_studio.models import ProviderCapabilities

from .base import Provider


class MoneyPrinterProvider(Provider):
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> ProviderCapabilities:
        try:
            response = httpx.get(f"{self.base_url}/docs", timeout=self.timeout, follow_redirects=True)
            healthy = response.status_code < 500
            detail = f"HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            healthy = False
            detail = str(exc)
        return ProviderCapabilities(
            name="moneyprinter",
            healthy=healthy,
            base_url=self.base_url,
            capabilities=["stock-media", "tts", "llm", "video"],
            detail=detail,
        )

