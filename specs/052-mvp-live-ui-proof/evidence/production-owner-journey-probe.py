#!/usr/bin/env python3
from __future__ import annotations

import http.client
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

FEATURE = "052-mvp-live-ui-proof"
OUTCOME_CATEGORIES = [
    "summary",
    "key_points",
    "decisions",
    "action_items",
    "followups",
    "risks",
    "questions",
    "evidence",
]


def _configuration() -> tuple[str, float]:
    origin = os.environ.get("PUBLIC_URL", "https://rec.2brain.pro")
    parsed = urllib.parse.urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or "?" in origin
        or "#" in origin
        or "\\" in origin
        or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in origin)
    ):
        raise ValueError("invalid_configuration")
    if parsed.port is not None and parsed.port == 0:
        raise ValueError("invalid_configuration")
    timeout = float(os.environ.get("OWNER_JOURNEY_PROBE_TIMEOUT", "15"))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("invalid_configuration")
    return origin.removesuffix("/"), timeout


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Cookies must never follow even a same-origin redirect.
        return None


def _get_json(path: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        origin, timeout = _configuration()
    except (ValueError, OverflowError):
        return {"ok": False, "http_status": None, "error": "invalid_configuration"}
    try:
        request = urllib.request.Request(
            f"{origin}{path}",
            headers={"Accept": "application/json", **(headers or {})},
            method="GET",
        )
        with urllib.request.build_opener(_NoRedirect()).open(
            request, timeout=timeout
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if not 200 <= response.status < 300:
                return {
                    "ok": False,
                    "http_status": response.status,
                    "error": "request_failed",
                }
            return {"ok": True, "http_status": response.status, "payload": payload}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "http_status": exc.code, "error": "request_failed"}
    except (
        OSError,
        ValueError,
        UnicodeError,
        OverflowError,
        http.client.HTTPException,
        RecursionError,
    ):
        return {"ok": False, "http_status": None, "error": "request_failed"}


def _request_ok(result: dict[str, Any]) -> bool:
    status = result.get("http_status")
    return (
        result.get("ok") is True
        and isinstance(status, int)
        and not isinstance(status, bool)
        and 200 <= status < 300
    )


def _health() -> dict[str, Any]:
    health = {}
    for name, expected in (("live", "ok"), ("ready", "ready")):
        response = _get_json(f"/api/v1/health/{name}")
        payload = response.get("payload")
        passed = (
            _request_ok(response)
            and isinstance(payload, dict)
            and payload.get("status") == expected
        )
        health[name] = {
            "ok": passed,
            "http_status": response["http_status"],
            "status": expected if passed else None,
        }
    return health


def _object(value):
    if not isinstance(value, dict):
        raise ValueError("schema_mismatch")
    return value


def _objects(value):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("schema_mismatch")
    return value


def _enum(value, allowed):
    if not isinstance(value, str) or value not in allowed:
        raise ValueError("schema_mismatch")
    return value


def _flag(value):
    if not isinstance(value, bool):
        raise ValueError("schema_mismatch")
    return value


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("schema_mismatch")
    return value


def _interval(segment):
    start, end = _number(segment["start_seconds"]), _number(segment["end_seconds"])
    if start > end:
        raise ValueError("schema_mismatch")
    return end > start


def _owner_access(access):
    access = _object(access)
    state = _enum(
        access["state"], {"owner", "team", "shared", "denied", "unavailable", "deleted"}
    )
    can_view = _flag(access["can_view"])
    full = _flag(access["can_view_full_meeting"])
    scope = _enum(access["content_scope"], {"full_meeting", "summary_only"})
    return state == "owner" and can_view and full and scope == "full_meeting"


def _review_metadata(payload):
    payload = _object(payload)
    access = _owner_access(payload["access"])
    meeting = _object(payload["meeting"])
    if not isinstance(meeting["meeting_id"], str):
        raise ValueError("schema_mismatch")
    candidate = UUID(meeting["meeting_id"])
    state = _enum(
        meeting["status"],
        {
            "ready",
            "local_only",
            "uploading",
            "submitted",
            "processing",
            "partial",
            "blocked",
            "failed",
            "unavailable",
            "deleted_future",
        },
    )
    if meeting.get("access") is not None:
        nested_access = _owner_access(meeting["access"])
        access = access and nested_access
    transcript = _object(payload["transcript"])
    transcript_available = _flag(transcript["available"])
    segments = _objects(transcript["segments"])
    for segment in segments:
        _interval(segment)
        _flag(segment["seekable"])
        if segment["seek_seconds"] is not None:
            _number(segment["seek_seconds"])
    speakers = _object(payload["speakers"])
    speakers_available = _flag(speakers["available"])
    lanes = _objects(speakers["speakers"])
    interval_count, positive_intervals = 0, 0
    for lane in lanes:
        for segment in _objects(lane["segments"]):
            positive_intervals += _interval(segment)
            interval_count += 1
    playback = _object(payload["playback"])
    playback_available = _flag(playback["available"])
    can_play = _flag(playback["can_play"])
    playback_state = _enum(
        playback["state"],
        {"preparing", "available", "unavailable", "deleting", "deleted"},
    )
    source = _enum(playback["source_mode"], {"none", "stored_review_m4a"})
    duration = playback["duration_seconds"]
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise ValueError("schema_mismatch")
    seek_count = sum(
        segment["seekable"]
        and segment["seek_seconds"] is not None
        and segment["seek_seconds"] <= duration
        for segment in segments
    )
    truth = _object(payload["notes_action_truth"])
    basis = _enum(
        truth["source_basis"],
        {
            "stored_output",
            "processing_status",
            "transcript_only",
            "policy_deferral",
            "not_supported",
            "blocked",
        },
    )
    states, counts, impacts = {}, {}, {}
    outcomes_ready = basis == "stored_output"
    for name in OUTCOME_CATEGORIES:
        category = _object(truth[name])
        states[name] = _enum(
            category["state"],
            {
                "available",
                "not_found",
                "not_inferable",
                "processing",
                "blocked",
                "unavailable",
                "deferred",
                "unsafe",
            },
        )
        impacts[name] = _enum(
            category["readiness_impact"],
            {"closes_gap", "keeps_gap_open", "non_blocking"},
        )
        counts[name] = len(_objects(category["items"]))
        protocol = category.get("protocol")
        if protocol is not None:
            _object(protocol)
        category_ready = (
            impacts[name] == "closes_gap"
            and (
                states[name] == "available"
                and counts[name] > 0
                or states[name] in {"not_found", "not_inferable"}
                and counts[name] == 0
            )
            or name == "risks"
            and states[name] == "unavailable"
            and impacts[name] == "non_blocking"
            and counts[name] == 0
            and isinstance(protocol, dict)
        )
        outcomes_ready = outcomes_ready and category_ready
    metadata = {
        "meeting_status": state,
        "transcript_available": transcript_available,
        "transcript_segment_count": len(segments),
        "speakers_available": speakers_available,
        "speaker_count": len(lanes),
        "speaker_interval_count": interval_count,
        "seek_target_count": seek_count,
        "playback_available": playback_available,
        "playback_source_mode": source,
        "playback_state": playback_state,
        "outcome_source_basis": basis,
        "outcome_states": states,
        "outcome_item_counts": counts,
        "outcome_readiness_impacts": impacts,
    }
    ready = (
        transcript_available
        and len(segments) > 0
        and speakers_available
        and len(lanes) > 0
        and positive_intervals > 0
        and seek_count > 0
        and playback_available
        and can_play
        and playback_state == "available"
        and source == "stored_review_m4a"
        and outcomes_ready
    )
    return candidate, access, ready, metadata


def _owner_review() -> dict[str, Any]:
    try:
        _configuration()
    except (ValueError, OverflowError):
        return {"status": "fail", "reason": "invalid_configuration"}
    cookie = os.environ.get("OWNER_SESSION_COOKIE")
    meeting_id = os.environ.get("OWNER_MEETING_ID")
    if not cookie or not meeting_id:
        return {"status": "blocked", "reason": "owner_context_missing"}
    try:
        requested = UUID(meeting_id)
    except ValueError:
        return {"status": "fail", "reason": "invalid_configuration"}
    result = _get_json(
        f"/api/v1/cabinet/meetings/{requested}", headers={"Cookie": cookie}
    )
    safe = {
        "candidate_ref": "env:OWNER_MEETING_ID(redacted)",
        "http_status": result["http_status"],
    }
    if not _request_ok(result):
        return {**safe, "status": "fail", "reason": "request_failed"}
    try:
        candidate, owner, ready, metadata = _review_metadata(result["payload"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return {**safe, "status": "fail", "reason": "schema_mismatch"}
    if candidate != requested:
        return {**safe, "status": "fail", "reason": "candidate_mismatch"}
    if not owner:
        status, reason = "blocked", "owner_access_unproven"
    elif metadata["meeting_status"] != "ready":
        status, reason = "blocked", "meeting_not_ready"
    elif not ready:
        status, reason = "blocked", "review_metadata_incomplete"
    else:
        status, reason = "pass", "review_metadata_available"
    return {**safe, **metadata, "status": status, "reason": reason}


def main() -> int:
    result = {
        "feature": FEATURE,
        "captured_at": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "proof_scope": "owner_review_api_metadata",
        "owner_journey_status": "unproven",
        "health": _health(),
        "owner_review": _owner_review(),
    }
    health_ok = all(observation["ok"] for observation in result["health"].values())
    result["overall_status"] = (
        "fail"
        if not health_ok or result["owner_review"]["status"] == "fail"
        else "pass"
        if result["owner_review"]["status"] == "pass"
        else "blocked"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["overall_status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
