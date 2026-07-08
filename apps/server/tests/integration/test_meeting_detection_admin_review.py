from __future__ import annotations

import asyncio

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.contract.test_meeting_detection_api_contract import meeting_detection_payload
from twobrain_rec_server.db.models import (
    AdminAuditEvent,
    MeetingDetectionNonTargetRule,
    MeetingDetectionReviewAction,
    MeetingTargetRegistryVersion,
)

TELEMETRY_PATH = "/api/v1/desktop/meeting-detection/telemetry"
ADMIN_REVIEW_PATH = "/api/v1/admin/meeting-detection"


def _create_candidate(client, key: str) -> dict:
    response = client.post(
        TELEMETRY_PATH,
        headers=auth_headers() | {"Idempotency-Key": key},
        json=meeting_detection_payload(),
    )
    assert response.status_code == 201
    review = client.get(ADMIN_REVIEW_PATH, headers=auth_headers())
    assert review.status_code == 200
    return review.json()["candidates"][0]


def test_synthetic_candidate_appears_in_admin_review_page(client) -> None:
    _create_candidate(client, "meeting-detection:admin-page")

    response = client.get("/admin/meeting-detection", headers=auth_headers())

    assert response.status_code == 200
    assert "Example VKS" in response.text
    assert "ru.example.vks" in response.text
    assert "yandex_telemost" in response.text


def test_mark_non_target_writes_review_action_admin_audit_and_rule(client) -> None:
    candidate = _create_candidate(client, "meeting-detection:admin-non-target")
    response = client.post(
        f"{ADMIN_REVIEW_PATH}/candidates/{candidate['candidate_id']}/mark-non-target",
        headers=auth_headers(),
        json={"reason_code": "admin_marked_non_target"},
    )

    async def load_rows() -> tuple[str | None, str | None, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            review_action = await db.scalar(select(MeetingDetectionReviewAction))
            audit_event = await db.scalar(
                select(AdminAuditEvent).where(AdminAuditEvent.action == "mark_non_target")
            )
            non_target_rule = await db.scalar(select(MeetingDetectionNonTargetRule))
            return (
                review_action.action if review_action else None,
                audit_event.outcome if audit_event else None,
                non_target_rule.rule_value if non_target_rule else None,
            )

    action, audit_outcome, rule_value = asyncio.run(load_rows())

    assert response.status_code == 200
    assert action == "mark_non_target"
    assert audit_outcome == "completed"
    assert rule_value == "ru.example.vks"


def test_add_diagnostic_draft_never_enables_prompt_mode(client) -> None:
    candidate = _create_candidate(client, "meeting-detection:admin-diagnostic")
    response = client.post(
        f"{ADMIN_REVIEW_PATH}/candidates/{candidate['candidate_id']}/add-diagnostic-only-draft",
        headers=auth_headers(),
        json={
            "target_id": "example_vks",
            "display_name": "Example VKS",
            "market": "russia",
            "reason_code": "candidate_runtime_observed",
        },
    )

    async def load_draft() -> MeetingTargetRegistryVersion | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(MeetingTargetRegistryVersion).where(
                    MeetingTargetRegistryVersion.status == "draft"
                )
            )

    draft = asyncio.run(load_draft())

    assert response.status_code == 200
    assert draft is not None
    target = next(target for target in draft.document_json["targets"] if target["id"] == "example_vks")
    assert target["mode"] == "diagnostic_only"
    assert target["mode"] != "prompt_enabled"
    assert len(draft.document_json["targets"]) > 1


def test_merge_candidate_rejects_unknown_target_id(client) -> None:
    candidate = _create_candidate(client, "meeting-detection:admin-merge-missing-target")

    response = client.post(
        f"{ADMIN_REVIEW_PATH}/candidates/{candidate['candidate_id']}/merge",
        headers=auth_headers(),
        json={"target_id": "missing_target", "reason_code": "same_target"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "meeting_detection_target_not_found"
