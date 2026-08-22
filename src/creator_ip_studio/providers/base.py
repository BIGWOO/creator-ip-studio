from __future__ import annotations

from abc import ABC, abstractmethod

from creator_ip_studio.models import ProviderCapabilities


class Provider(ABC):
    @abstractmethod
    def health(self) -> ProviderCapabilities:
        raise NotImplementedError

