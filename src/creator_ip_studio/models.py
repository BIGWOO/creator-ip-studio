from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunState(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    REUSED = "reused"


class CanvasSpec(StrictModel):
    width: int = Field(default=1280, ge=320, le=7680)
    height: int = Field(default=720, ge=320, le=4320)
    fps: int = Field(default=30, ge=15, le=120)
    background: str = "#17152b"


class VoiceSpec(StrictModel):
    provider: Literal["tone", "edge", "external"] = "tone"
    name: str = "zh-TW-HsiaoChenNeural"
    rate: str = "+0%"


class CaptionSpec(StrictModel):
    enabled: bool = True
    safe_bottom: int = Field(default=80, ge=0, le=1000)


class AvatarSpec(StrictModel):
    enabled: bool = False
    provider: Literal["duix", "external"] = "duix"
    consent_manifest: str | None = None

    @model_validator(mode="after")
    def require_consent(self) -> AvatarSpec:
        if self.enabled and not self.consent_manifest:
            raise ValueError("avatar.enabled requires consent_manifest")
        return self


class WorkspaceProfile(StrictModel):
    contract_version: Literal["1.0"] = "1.0"
    profile_id: str = "default"
    language: str = "zh-TW"
    voice: VoiceSpec = Field(default_factory=VoiceSpec)
    canvas: CanvasSpec = Field(default_factory=CanvasSpec)
    captions: CaptionSpec = Field(default_factory=CaptionSpec)
    visuals: dict[str, Any] = Field(default_factory=lambda: {"provider": "builtin"})
    avatar: AvatarSpec = Field(default_factory=AvatarSpec)
    delivery: dict[str, Any] = Field(
        default_factory=lambda: {"include_manifest": True, "include_qc": True}
    )
    brand: dict[str, Any] = Field(default_factory=dict)


class RuntimeProfile(StrictModel):
    contract_version: Literal["1.0"] = "1.0"
    mode: Literal["cpu", "nvidia", "cloud"] = "cpu"
    workspace_root: str
    artifact_root: str
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ResolvedProfile(StrictModel):
    contract_version: Literal["1.0"] = "1.0"
    profile: WorkspaceProfile
    runtime: RuntimeProfile
    sources: list[str]
    sha256: str
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectSpec(StrictModel):
    project_id: str
    title: str
    source: str | None = None
    narration: str
    language: str = "zh-TW"
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    target_seconds: int = Field(default=20, ge=5, le=3600)
    profile_id: str = "workspace"
    use_avatar: bool = False


class ArtifactRef(StrictModel):
    uri: str
    media_type: str
    size: int = Field(ge=0)
    sha256: str
    source_stage: str


class StageManifest(StrictModel):
    contract_version: Literal["1.0"] = "1.0"
    stage: str
    state: StageState
    inputs: list[ArtifactRef] = Field(default_factory=list)
    outputs: list[ArtifactRef] = Field(default_factory=list)
    provider: str
    provider_version: str
    started_at: datetime
    completed_at: datetime | None = None
    elapsed_seconds: float | None = None
    error: str | None = None


class QCCheck(StrictModel):
    name: str
    passed: bool
    measured: Any = None
    expected: Any = None
    message: str = ""


class QCReport(StrictModel):
    contract_version: Literal["1.0"] = "1.0"
    passed: bool
    checks: list[QCCheck]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProviderCapabilities(StrictModel):
    name: str
    healthy: bool
    base_url: HttpUrl | None = None
    capabilities: list[str]
    requires_gpu: bool = False
    requires_payment: bool = False
    detail: str = ""


class WorkerRegistration(StrictModel):
    name: str
    capabilities: list[str]


class WorkerLeaseRequest(StrictModel):
    worker_id: str
    capabilities: list[str]


class RunCreate(StrictModel):
    until: Literal["preview", "delivery"] = "preview"


class RunComplete(StrictModel):
    worker_id: str
    lease_id: str
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

