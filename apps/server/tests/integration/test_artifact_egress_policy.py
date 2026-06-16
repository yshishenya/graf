from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import audit_events, set_artifact_policy


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
