from __future__ import annotations

import pytest

from twobrain_rec_server.normalization.audit import NormalizationAuditError, build_audit_receipt


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("filename", "private-meeting.m4a"),
        ("object_key", "organizations/private/workspaces/private/object"),
        ("local_path", "/private/var/tmp/private-media"),
        ("ffmpeg_stderr", "Invalid data near private title"),
        ("transcript", "private spoken content"),
        ("summary", "private meeting summary"),
        ("credential", "secret-token"),
    ],
)
def test_normalization_audit_has_no_private_content_egress(key: str, value: str) -> None:
    with pytest.raises(NormalizationAuditError) as exc_info:
        build_audit_receipt(
            "playback_normalization_failed",
            {"reason_code": "corrupt_source", key: value},
        )
    assert value not in str(exc_info.value)


def test_unknown_event_type_fails_closed_without_echoing_input() -> None:
    event_type = "private-meeting-title"
    with pytest.raises(NormalizationAuditError) as exc_info:
        build_audit_receipt(event_type, {})
    assert event_type not in str(exc_info.value)
