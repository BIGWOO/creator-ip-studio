from __future__ import annotations

import hashlib
from pathlib import Path

from .models import ArtifactRef


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LocalArtifactStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative: str | Path) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("artifact path escapes configured root")
        return candidate

    def ref(self, path: Path, *, media_type: str, stage: str) -> ArtifactRef:
        path = path.resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError("artifact is outside configured root")
        return ArtifactRef(
            uri=path.as_uri(),
            media_type=media_type,
            size=path.stat().st_size,
            sha256=sha256_file(path),
            source_stage=stage,
        )

