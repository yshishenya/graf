from __future__ import annotations

import json

import pytest

from tests.contract.test_ingest_openapi_contract import auth_headers
from twobrain_rec_server.admin.audit import assert_metadata_safe, sanitize_audit_metadata

FORBIDDEN_MARKERS = {
    "storage_object_key",
    "signed_url",
    "X-Amz",
    "/Users/",
    "session_token",
    "password",
    "secret",
    "transcript_text",
    "raw_audio",
}


def _dump_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_admin_audit_metadata_rejects_secret_and_content_markers() -> None:
    unsafe = {
        "storage_object_key": "workspace/private/object.wav",
        "note": "transcript_text must not leave the service",
    }

    with pytest.raises(ValueError, match="metadata"):
        assert_metadata_safe(unsafe)


def test_admin_audit_metadata_sanitizer_keeps_only_safe_fields() -> None:
    safe = sanitize_audit_metadata(
        {
            "role": "admin",
            "reason_code": "quota_viewed",
            "storage_object_key": "workspace/private/object.wav",
            "nested": {"signed_url": "https://example.invalid/X-Amz-Signature=private"},
        }
    )

    body = _dump_json(safe)
    assert safe["role"] == "admin"
    assert safe["reason_code"] == "quota_viewed"
    for marker in FORBIDDEN_MARKERS:
        assert marker not in body


def test_admin_overview_api_and_html_do_not_egress_private_markers(client) -> None:
    api_response = client.get("/api/v1/admin/overview", headers=auth_headers())
    html_response = client.get("/admin", headers=auth_headers())

    assert api_response.status_code in {200, 403, 503}
    assert html_response.status_code in {200, 403}
    body = _dump_json(api_response.json()) + html_response.text
    for marker in FORBIDDEN_MARKERS:
        assert marker not in body

