from pathlib import Path

import pytest

from creator_ip_studio.artifacts import LocalArtifactStore


def test_store_rejects_path_escape(tmp_path: Path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    with pytest.raises(ValueError, match="escapes"):
        store.resolve("../private.txt")


def test_store_builds_content_addressed_reference(tmp_path: Path):
    store = LocalArtifactStore(tmp_path)
    artifact = store.resolve("result.txt")
    artifact.write_text("hello", encoding="utf-8")
    ref = store.ref(artifact, media_type="text/plain", stage="test")
    assert ref.size == 5
    assert len(ref.sha256) == 64
    assert ref.uri.startswith("file:")

