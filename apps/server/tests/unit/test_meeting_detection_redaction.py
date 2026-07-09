import pytest

from twobrain_rec_server.meeting_detection.redaction import (
    MeetingDetectionRedactionError,
    assert_metadata_only,
    forbidden_content_findings,
)


def test_metadata_only_payload_with_safe_reason_codes_passes() -> None:
    assert_metadata_only(
        {
            "schemaVersion": 1,
            "targetRollups": [
                {
                    "targetId": "yandex_telemost",
                    "outcomes": {"observed": 2, "prompted": 1},
                    "reasonCodes": ["stable_mic_duration"],
                }
            ],
            "resourceRollup": {"parserRestartCount": 0, "uploadAttemptCount": 1},
        }
    )


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({"meetingUrl": "https://telemost.yandex.ru/j/secret"}, "forbidden_key"),
        ({"attendeeEmail": "person@example.com"}, "forbidden_key"),
        ({"metadata": "authorization: bearer token"}, "forbidden_marker"),
        ({"host": "192.168.1.10"}, "raw_ip"),
        ({"path": "/Users/alice/Library/Logs/private.log"}, "home_path"),
    ],
)
def test_forbidden_content_findings_report_reason(payload: dict[str, object], reason: str) -> None:
    findings = forbidden_content_findings(payload)

    assert any(finding.reason == reason for finding in findings)


def test_assert_metadata_only_raises_with_compact_reason() -> None:
    with pytest.raises(MeetingDetectionRedactionError) as error:
        assert_metadata_only({"notes": "raw_audio sample"})

    assert "forbidden_marker" in str(error.value)
