import pytest
from pydantic import ValidationError

from creator_ip_studio.models import AvatarSpec, CanvasSpec, ProjectSpec


def test_avatar_requires_consent_manifest():
    with pytest.raises(ValidationError):
        AvatarSpec(enabled=True)


def test_avatar_accepts_consent_reference():
    avatar = AvatarSpec(enabled=True, consent_manifest="private://consent/subject-1")
    assert avatar.enabled


def test_canvas_limits_are_enforced():
    with pytest.raises(ValidationError):
        CanvasSpec(width=100, height=100)


def test_project_rejects_excessive_duration():
    with pytest.raises(ValidationError):
        ProjectSpec(project_id="x", title="x", narration="x", target_seconds=3601)

