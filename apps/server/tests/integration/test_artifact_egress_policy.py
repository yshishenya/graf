from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    add_retained_playback_m4a,
    add_workspace_user,
    audit_events,
    auth_headers_for,
    grant_meeting_to_user,
    replace_retained_audio_with_test_wav,
    set_artifact_policy,
)
from twobrain_rec_server.cabinet import egress as egress_module


class DownloadStreamingOnlyStorage:
    def __init__(self, delegate: object) -> None:
        self.delegate = delegate

    def get_bytes(self, _object_key: str) -> bytes:
        raise AssertionError("audio download must not load full audio objects into memory")

    async def get_bytes_async(self, _object_key: str) -> bytes:
        raise AssertionError("audio download must not load full audio objects into memory")

    def iter_object(self, object_key: str, *, offset: int = 0, length: int | None = None):
        return self.delegate.iter_object(object_key, offset=offset, length=length)

    def stat_object(self, object_key: str):
        return self.delegate.stat_object(object_key)

    async def stat_object_async(self, object_key: str):
        return await self.delegate.stat_object_async(object_key)


class DownloadReaderFailingStorage(DownloadStreamingOnlyStorage):
    def iter_object(self, _object_key: str, *, offset: int = 0, length: int | None = None):
        raise RuntimeError("storage backend unavailable")


def test_allowed_transcript_download_is_server_mediated_and_audited(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(
        client,
        seeds.ready_id,
        transcript_download="allowed",
        package_export="allowed",
    )

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "attachment;" in response.headers["content-disposition"]
    assert SAFE_TRANSCRIPT_TEXT in response.text
    assert "storage_object_key" not in response.text
    event_types = [event.event_type for event in audit_events(client, seeds.ready_id)]
    assert event_types == ["download_requested", "download_completed"]


def test_blocked_artifact_download_fails_closed_and_records_denied_audit(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.artifact_class) for event in events] == [
        ("download_denied", "denied", "audio")
    ]


def test_owner_default_audio_download_returns_stored_m4a_without_policy(client) -> None:
    seeds = seed_cabinet_meetings(client)
    m4a_body = add_retained_playback_m4a(
        client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A owner default"
    )

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.content == m4a_body
    assert [event.event_type for event in audit_events(client, seeds.ready_id)] == [
        "download_requested",
        "download_stream_prepared",
    ]


def test_owner_default_audio_download_returns_stored_m4a_for_workspace_default_disabled(
    client,
) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(
        client,
        seeds.ready_id,
        audio_download="disabled",
        policy_source="workspace_default",
    )
    m4a_body = add_retained_playback_m4a(
        client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A workspace default"
    )

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.content == m4a_body


def test_explicit_audio_download_deny_remains_blocked_for_owner(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(
        client,
        seeds.ready_id,
        audio_download="disabled",
        policy_source="meeting_override",
    )
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A explicit deny")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert "content-disposition" not in response.headers
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.artifact_class) for event in events] == [
        ("download_denied", "denied", "audio")
    ]


def test_owner_default_audio_download_remains_owner_only_for_permitted_non_owner(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    grant_meeting_to_user(client, seeds.ready_id)
    set_artifact_policy(
        client,
        seeds.ready_id,
        audio_download="disabled",
        policy_source="workspace_default",
    )
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A non owner")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers_for(),
    )

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert "content-disposition" not in response.headers
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.artifact_class) for event in events] == [
        ("download_denied", "denied", "audio")
    ]


def test_owner_default_audio_download_requires_stored_playback_artifact(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "artifact_unavailable"
    assert response.content != b"\x00"
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.policy_reason) for event in events] == [
        ("download_denied", "denied", "missing_playback_artifact")
    ]


def test_allowed_audio_download_returns_stored_m4a_review_artifact(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A download")

    original_storage = client.app.state.storage
    client.app.state.storage = DownloadStreamingOnlyStorage(client.app_state["storage"])
    try:
        response = client.get(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
            headers=auth_headers(),
        )
    finally:
        client.app.state.storage = original_storage

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mp4")
    assert response.headers["content-length"] == str(len(m4a_body))
    assert 'filename="meeting-review.m4a"' in response.headers["content-disposition"]
    assert response.content == m4a_body
    events = audit_events(client, seeds.ready_id)
    assert [event.event_type for event in events] == [
        "download_requested",
        "download_stream_prepared",
    ]
    assert events[-1].outcome == "prepared"
    assert events[-1].metadata_json == {
        "artifact_class": "audio",
        "byte_length": len(m4a_body),
        "outcome": "prepared",
        "source_mode": "stored_review_m4a",
        "stream_state": "prepared",
    }


def test_audio_download_ignores_stale_processing_result_when_playback_is_available(
    client, monkeypatch
) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    m4a_body = add_retained_playback_m4a(
        client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A stale result"
    )

    async def stale_result(*_args, **_kwargs) -> bool:
        return False

    monkeypatch.setattr(egress_module, "_processing_result_is_current", stale_result)
    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.content == m4a_body


def test_allowed_audio_download_rejects_stale_storage_size_before_serving_headers(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    m4a_body = add_retained_playback_m4a(client, seeds.ready_id, b"0123456789abcdef")
    object_key = f"tests/cabinet/{seeds.ready_id}/meeting-review.m4a"
    client.app_state["storage"].objects[object_key] = m4a_body[:-1]

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "audio_unavailable"
    assert [
        (event.event_type, event.outcome, event.policy_reason)
        for event in audit_events(client, seeds.ready_id)
    ] == [
        ("download_requested", "allowed", "policy_allowed"),
        ("download_denied", "denied", "storage_object_size_mismatch"),
    ]


def test_allowed_audio_download_requires_stored_m4a_review_artifact(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    replace_retained_audio_with_test_wav(client, seeds.ready_id)

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "artifact_unavailable"
    events = audit_events(client, seeds.ready_id)
    assert [(event.event_type, event.outcome, event.policy_reason) for event in events] == [
        ("download_denied", "denied", "missing_playback_artifact")
    ]


def test_allowed_audio_download_reports_storage_unavailable_when_stored_m4a_object_is_missing(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A stale")
    client.app_state["storage"].delete_object(f"tests/cabinet/{seeds.ready_id}/meeting-review.m4a")

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    assert [(event.event_type, event.outcome, event.policy_reason) for event in audit_events(client, seeds.ready_id)] == [
        ("download_requested", "allowed", "policy_allowed"),
        ("download_denied", "denied", "storage_unavailable"),
    ]


def test_allowed_audio_download_reports_storage_unavailable_when_reader_is_missing(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A storage")
    original_storage = client.app.state.storage
    client.app.state.storage = object()
    try:
        response = client.get(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
            headers=auth_headers(),
        )
    finally:
        client.app.state.storage = original_storage

    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    assert [(event.event_type, event.outcome, event.policy_reason) for event in audit_events(client, seeds.ready_id)] == [
        ("download_requested", "allowed", "policy_allowed"),
        ("download_denied", "denied", "storage_unavailable"),
    ]


def test_allowed_audio_download_audits_storage_reader_failure(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A storage")
    original_storage = client.app.state.storage
    client.app.state.storage = DownloadReaderFailingStorage(client.app_state["storage"])
    try:
        response = client.get(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
            headers=auth_headers(),
        )
    finally:
        client.app.state.storage = original_storage

    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    assert [(event.event_type, event.outcome, event.policy_reason) for event in audit_events(client, seeds.ready_id)] == [
        ("download_requested", "allowed", "policy_allowed"),
        ("download_denied", "denied", "storage_unavailable"),
    ]


def test_export_package_includes_allowed_artifacts_and_excludes_unavailable_ones(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(
        client,
        seeds.ready_id,
        transcript_download="allowed",
        summary_download="allowed",
        package_export="allowed",
    )

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/exports",
        headers=auth_headers(),
        json={"artifact_classes": ["transcript", "summary"]},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["included_artifacts"] == ["transcript"]
    assert payload["excluded_artifacts"] == [
        {"artifact_class": "summary", "policy_reason": "Summary notes are not available yet."}
    ]
    assert [event.event_type for event in audit_events(client, seeds.ready_id)] == [
        "export_requested",
        "export_completed",
    ]


def test_package_export_policy_blocks_direct_export_even_when_transcript_is_allowed(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(
        client,
        seeds.ready_id,
        transcript_download="allowed",
        package_export="disabled",
    )

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/exports",
        headers=auth_headers(),
        json={"artifact_classes": ["transcript"]},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "export_unavailable"
    assert [(event.event_type, event.outcome, event.artifact_class) for event in audit_events(client, seeds.ready_id)] == [
        ("export_denied", "denied", "package")
    ]


def test_ready_export_package_download_returns_manifest_without_storage_urls(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, transcript_download="allowed", package_export="allowed")
    created = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/exports",
        headers=auth_headers(),
        json={"artifact_classes": ["transcript"]},
    )
    export_id = created.json()["export_id"]

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/exports/{export_id}/download",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "included_artifacts" in response.text
    assert "storage_object_key" not in response.text
    assert [event.event_type for event in audit_events(client, seeds.ready_id)] == [
        "export_requested",
        "export_completed",
        "export_completed",
    ]


def test_activity_endpoint_returns_only_metadata_not_artifact_content(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, transcript_download="allowed")
    client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers(),
    )

    activity = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/activity",
        headers=auth_headers(),
    )

    assert activity.status_code == 200
    body = activity.text
    assert "metadata_only" in body
    assert SAFE_TRANSCRIPT_TEXT not in body
    assert "download_completed" in body


def test_activity_endpoint_accepts_stream_prepared_audio_events(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A activity")
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed")

    downloaded = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/audio",
        headers=auth_headers(),
    )
    activity = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/activity",
        headers=auth_headers(),
    )

    assert downloaded.status_code == 200
    assert activity.status_code == 200
    assert activity.json()["items"][0]["event_type"] == "download_stream_prepared"
    assert activity.json()["items"][0]["outcome"] == "prepared"
