from __future__ import annotations

from datetime import UTC, datetime


def custody_read_model_fixture(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "state": "partial_uploaded",
        "upload_state": "partial_uploaded",
        "processing_state": "pending_processing",
        "owner": "product_automatic",
        "retry_class": "automatic",
        "normal_user_action": "none",
        "display_priority": 5,
        "review_available": False,
        "review_desktop_url": None,
        "safe_incident_available": False,
        "retention_deadline": datetime(2026, 7, 3, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        "copy_key": "custody.uploading",
        "metadata_safety": "metadata_only",
    }
    payload.update(overrides)
    return payload


def custody_problem_extension_fixture(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "custody_owner": "workspace_admin",
        "retry_class": "paused_until_admin_action",
        "normal_user_action": "copy_safe_report",
        "metadata_safety": "metadata_only",
    }
    payload.update(overrides)
    return payload
