from pathlib import Path

import yaml

from creator_ip_studio.config import deep_merge, init_workspace, resolve_profile


def test_deep_merge_preserves_unrelated_keys():
    assert deep_merge({"a": {"b": 1, "c": 2}}, {"a": {"b": 3}}) == {
        "a": {"b": 3, "c": 2}
    }


def test_init_is_idempotent_and_resolve_is_stable(tmp_path: Path):
    root = init_workspace(tmp_path)
    profile = root / "profiles" / "workspace.yaml"
    data = yaml.safe_load(profile.read_text(encoding="utf-8"))
    data["brand"] = {"name": "Test Brand"}
    profile.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    init_workspace(tmp_path)
    first = resolve_profile(tmp_path)
    second = resolve_profile(tmp_path)
    assert first.profile.brand["name"] == "Test Brand"
    assert first.sha256 == second.sha256
    assert len(first.sha256) == 64


def test_project_override_changes_hash(tmp_path: Path):
    root = init_workspace(tmp_path)
    base = resolve_profile(tmp_path)
    override = root / "projects" / "vertical.yaml"
    override.write_text("canvas:\n  width: 720\n  height: 1280\n", encoding="utf-8")
    vertical = resolve_profile(tmp_path, project_config=override)
    assert vertical.profile.canvas.width == 720
    assert vertical.sha256 != base.sha256

