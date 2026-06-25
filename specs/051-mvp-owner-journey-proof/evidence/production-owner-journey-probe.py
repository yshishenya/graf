#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

FEATURE = "051-mvp-owner-journey-proof"
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://rec.2brain.pro").rstrip("/")
TIMEOUT_SECONDS = float(os.environ.get("OWNER_JOURNEY_PROBE_TIMEOUT", "15"))
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


def _get_json(path: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{PUBLIC_URL}{path}",
        headers={"Accept": "application/json", **(headers or {})},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body) if body else {}
            return {"ok": True, "http_status": response.status, "payload": payload}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "http_status": exc.code, "error": "http_error"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "http_status": None, "error": type(exc).__name__}


def _health() -> dict[str, Any]:
    live = _get_json("/api/v1/health/live")
    ready = _get_json("/api/v1/health/ready")
    return {
        "live": {"ok": live["ok"], "http_status": live["http_status"], "status": live.get("payload", {}).get("status")},
        "ready": {"ok": ready["ok"], "http_status": ready["http_status"], "status": ready.get("payload", {}).get("status")},
    }


def _owner_review() -> dict[str, Any]:
    cookie = os.environ.get("OWNER_SESSION_COOKIE")
    meeting_id = os.environ.get("OWNER_MEETING_ID")
    if not cookie or not meeting_id:
        return {
            "status": "blocked",
            "reason": "OWNER_SESSION_COOKIE and OWNER_MEETING_ID are required for owner review proof",
        }

    result = _get_json(f"/api/v1/cabinet/meetings/{meeting_id}", headers={"Cookie": cookie})
    if not result["ok"]:
        return {
            "status": "fail",
            "candidate_ref": "env:OWNER_MEETING_ID(redacted)",
            "http_status": result["http_status"],
            "error": result.get("error"),
        }

    payload = result["payload"]
    transcript = payload.get("transcript") or {}
    speakers = payload.get("speakers") or {}
    playback = payload.get("playback") or {}
    truth = payload.get("notes_action_truth") or {}
    outcome_states = {
        category: (truth.get(category) or {}).get("state", "missing") for category in OUTCOME_CATEGORIES
    }
    outcome_item_counts = {
        category: len((truth.get(category) or {}).get("items") or []) for category in OUTCOME_CATEGORIES
    }

    return {
        "status": "pass",
        "candidate_ref": "env:OWNER_MEETING_ID(redacted)",
        "http_status": result["http_status"],
        "meeting_status": payload.get("status"),
        "transcript_available": bool(transcript.get("available")),
        "transcript_segment_count": len(transcript.get("segments") or []),
        "speakers_available": bool(speakers.get("available")),
        "speaker_count": len(speakers.get("speakers") or []),
        "playback_available": bool(playback.get("available")),
        "playback_source_mode": playback.get("source_mode"),
        "outcome_source_basis": truth.get("source_basis"),
        "outcome_states": outcome_states,
        "outcome_item_counts": outcome_item_counts,
    }


def main() -> int:
    result = {
        "feature": FEATURE,
        "captured_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "public_url": PUBLIC_URL,
        "health": _health(),
        "owner_review": _owner_review(),
    }
    health_ok = result["health"]["live"]["status"] == "ok" and result["health"]["ready"]["status"] == "ready"
    result["overall_status"] = "pass" if health_ok and result["owner_review"]["status"] == "pass" else "blocked"
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if not health_ok:
        return 1
    if os.environ.get("OWNER_SESSION_COOKIE") and result["owner_review"]["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
