from __future__ import annotations

from typing import Any

from twobrain_rec_server.meeting_detection.redaction import forbidden_content_findings


def build_meeting_detection_admin_model(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidates": [_safe_candidate(row) for row in review.get("candidates", [])],
        "target_health": review.get("target_health", []),
        "registry_versions": review.get("registry_versions", []),
        "counts": review.get("counts", {}),
    }


def _safe_candidate(row: dict[str, Any]) -> dict[str, Any]:
    safe = dict(row)
    for key in ("bundle_id", "display_name", "signing_team_id"):
        value = safe.get(key)
        if isinstance(value, str) and forbidden_content_findings(value):
            safe[key] = "[redacted]"
    return safe
