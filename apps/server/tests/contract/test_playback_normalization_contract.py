from __future__ import annotations


def test_playback_read_contract_is_durable_and_has_no_repair_mutation(client) -> None:
    schema = client.get("/openapi.json").json()
    components = schema["components"]["schemas"]

    list_playback = components["MeetingListItem"]["properties"]["playback"]
    assert list_playback == {"$ref": "#/components/schemas/PlaybackPreparationState"}

    preparation = components["PlaybackPreparationState"]
    assert set(preparation["properties"]) == {
        "state",
        "reason_code",
        "label",
        "automatic_recovery",
        "can_play",
        "action",
    }
    assert preparation["properties"]["state"]["enum"] == [
        "preparing",
        "available",
        "unavailable",
        "deleting",
        "deleted",
    ]
    assert preparation["properties"]["action"]["const"] == "disabled"

    review = components["PlaybackReviewState"]["properties"]
    assert set(preparation["properties"]) <= set(review)
    assert review["can_play"]["type"] == "boolean"
    assert review["automatic_recovery"]["type"] == "boolean"

    playback_paths = {
        path: operations for path, operations in schema["paths"].items() if "playback" in path
    }
    assert set(playback_paths) == {"/api/v1/cabinet/meetings/{meeting_id}/playback"}
    assert set(playback_paths["/api/v1/cabinet/meetings/{meeting_id}/playback"]) == {"get"}
    operation = playback_paths["/api/v1/cabinet/meetings/{meeting_id}/playback"]["get"]
    range_parameter = next(
        parameter for parameter in operation["parameters"] if parameter["name"] == "Range"
    )
    assert range_parameter["in"] == "header"
    assert range_parameter["required"] is False
    responses = operation["responses"]
    assert {"200", "206", "416", "503"} <= set(responses)
    for status_code in ("200", "206"):
        assert responses[status_code]["content"]["audio/mp4"]["schema"] == {
            "type": "string",
            "format": "binary",
        }
        assert "Accept-Ranges" in responses[status_code]["headers"]
        assert "Content-Disposition" in responses[status_code]["headers"]
    assert "Content-Range" in responses["206"]["headers"]
    for status_code in ("416", "503"):
        assert responses[status_code]["content"]["application/problem+json"]["schema"] == {
            "$ref": "#/components/schemas/Problem"
        }

    source_roles = components["PlaybackReviewState"]["properties"]["included_sources"][
        "items"
    ]["enum"]
    assert "uploaded_media" in source_roles


def test_playback_reason_contract_contains_only_safe_stable_categories(client) -> None:
    schema = client.get("/openapi.json").json()
    reasons = schema["components"]["schemas"]["PlaybackPreparationState"]["properties"][
        "reason_code"
    ]["enum"]

    assert {
        "normalization_queued",
        "normalization_retry_wait",
        "reconciliation_pending",
        "canonical_artifact_missing",
        "canonical_ready",
        "unsupported_media",
        "corrupt_source",
        "source_missing",
        "meeting_deleting",
        "meeting_deleted",
    } <= set(reasons)
    forbidden_fragments = {
        "filename",
        "object_key",
        "storage_url",
        "ffmpeg",
        "credential",
        "transcript",
    }
    assert not any(fragment in reason for reason in reasons for fragment in forbidden_fragments)


def test_openapi_has_no_competing_normalization_source_or_repair_mutation(client) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    forbidden_path_fragments = (
        "/normalization",
        "/normalize",
        "/reprocess",
        "/backfill",
        "/playback/retry",
    )
    assert not any(
        fragment in path
        for path in paths
        for fragment in forbidden_path_fragments
    )
    assert "/api/v1/media-uploads" in paths
    assert "/api/v1/upload-sessions/{session_id}/finalize" in paths
    assert set(paths["/api/v1/cabinet/meetings/{meeting_id}/playback"]) == {"get"}
