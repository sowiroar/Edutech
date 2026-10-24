from copy import deepcopy

import pytest
from pydantic import ValidationError
from test_contract import event

from viva_metrics.contract import Event


def sample():
    return dict(
        character="LIRA",
        model_sha256="a" * 64,
        measurement_scope="live-call-acoustic",
        window_ms=10000,
        sample_count=10,
        fps=30,
        fps_min=29,
        render_submission_ms=2,
        first_frame_ms=1200,
        model_bytes=4666084,
        texture_bytes_estimate=39000000,
        geometry_bytes=3600000,
        page_js_heap_bytes=None,
        triangles=75781,
        draw_calls=15,
        width=1280,
        height=720,
        mouth_available=True,
        lip_shapes_available=True,
        playback_status="silent",
        analysed_frames=300,
        speech_frames=150,
        onset_observations=2,
        close_observations=2,
        acoustic_onset_to_pose_max_ms=0,
        silence_to_rest_max_ms=67,
    )


def packet():
    row = event("avatar_quality_sample", sample())
    row.update(schema_version=2, source="browser")
    return row


@pytest.mark.parametrize("character", ["LIRA", "NEXO", "ELIAN", "NOA", "NOVA", "ATLAS"])
def test_family_avatar_quality_preserves_character_identity(character):
    row = packet()
    row["payload"]["character"] = character
    assert Event.model_validate(row).payload["character"] == character


def test_avatar_quality_has_bounded_numeric_data_and_no_audio():
    row = packet()
    parsed = Event.model_validate(row)
    assert parsed.payload["acoustic_onset_to_pose_max_ms"] == 0
    assert parsed.payload["page_js_heap_bytes"] is None
    for field, value in [
        ("fps", -1),
        ("fps", float("nan")),
        ("model_sha256", "no"),
        ("audio", "pcm"),
        ("text", "sensitive"),
        ("measurement_scope", "preview"),
    ]:
        bad = deepcopy(row)
        bad["payload"][field] = value
        with pytest.raises(ValidationError):
            Event.model_validate(bad)


def test_avatar_quality_requires_v2_and_unknown_is_not_zero():
    row = packet()
    row["schema_version"] = 1
    with pytest.raises(ValidationError):
        Event.model_validate(row)
    row["schema_version"] = 2
    row["payload"].update(
        onset_observations=0,
        close_observations=0,
        acoustic_onset_to_pose_max_ms=None,
        silence_to_rest_max_ms=None,
    )
    assert Event.model_validate(row).payload["silence_to_rest_max_ms"] is None


@pytest.mark.parametrize(
    "patch",
    [
        {"onset_observations": 0},
        {"close_observations": 0},
        {"speech_frames": 301},
        {"fps_min": 31},
    ],
)
def test_avatar_quality_rejects_inconsistent_coverage(patch):
    row = packet()
    row["payload"].update(patch)
    with pytest.raises(ValidationError):
        Event.model_validate(row)
