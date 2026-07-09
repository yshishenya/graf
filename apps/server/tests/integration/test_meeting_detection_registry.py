from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.contract.test_meeting_detection_api_contract import meeting_detection_payload
from tests.fakes.auth_contexts import ORG_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import (
    AdminAuditEvent,
    MeetingDetectionCandidate,
    MeetingDetectionReviewAction,
    MeetingTargetRegistryEntry,
    MeetingTargetRegistryVersion,
    Workspace,
)
from twobrain_rec_server.meeting_detection.registry import (
    load_packaged_seed_registry,
    registry_entries,
    registry_etag,
)

TELEMETRY_PATH = "/api/v1/desktop/meeting-detection/telemetry"
ADMIN_REVIEW_PATH = "/api/v1/admin/meeting-detection"
REGISTRY_PATH = "/api/v1/desktop/meeting-detection/target-registry"
FOREIGN_WORKSPACE_ID = UUID("92000000-0000-0000-0000-000000000092")


def _create_candidate(client, key: str) -> dict:
    telemetry = client.post(
        TELEMETRY_PATH,
        headers=auth_headers() | {"Idempotency-Key": key},
        json=meeting_detection_payload(),
    )
    assert telemetry.status_code == 201
    review = client.get(ADMIN_REVIEW_PATH, headers=auth_headers())
    assert review.status_code == 200
    return review.json()["candidates"][0]


def _create_diagnostic_draft(client, candidate_id: str) -> dict:
    response = client.post(
        f"{ADMIN_REVIEW_PATH}/candidates/{candidate_id}/add-diagnostic-only-draft",
        headers=auth_headers(),
        json={
            "target_id": "example_vks",
            "display_name": "Example VKS",
            "market": "russia",
            "reason_code": "candidate_runtime_observed",
        },
    )
    assert response.status_code == 200
    return response.json()["registry_draft"]


def test_registry_fetch_seeds_published_registry_and_supports_etag_cache(client) -> None:
    response = client.get(REGISTRY_PATH, headers=auth_headers())
    body = response.json()
    etag = response.headers["etag"]

    async def load_seed_rows() -> tuple[str | None, int]:
        async with client.app_state["sessionmaker"]() as db:
            row = await db.scalar(
                select(MeetingTargetRegistryVersion).where(
                    MeetingTargetRegistryVersion.source == "packaged_seed"
                )
            )
            entries = (await db.scalars(select(MeetingTargetRegistryEntry))).all()
            return row.status if row else None, len(entries)

    seed_status, entry_count = asyncio.run(load_seed_rows())
    target_ids = {target["id"] for target in body["targets"]}

    assert response.status_code == 200
    assert body["registryVersion"] == "2026.07.08.1"
    assert body["etag"] == etag.strip('"')
    assert body["nonTargetRules"] == []
    assert {"zoom", "yandex_telemost"}.issubset(target_ids)
    assert response.headers["cache-control"] == "private, max-age=86400"
    assert response.headers["x-graf-registry-version"] == "2026.07.08.1"
    assert seed_status == "published"
    assert entry_count == len(body["targets"])

    cached = client.get(REGISTRY_PATH, headers=auth_headers() | {"If-None-Match": etag})
    assert cached.status_code == 304
    assert cached.text == ""


def test_admin_can_publish_diagnostic_draft_and_desktop_fetches_it(client) -> None:
    candidate = _create_candidate(client, "meeting-detection:registry-publish")
    draft = _create_diagnostic_draft(client, candidate["candidate_id"])

    publish = client.post(
        f"{ADMIN_REVIEW_PATH}/registry-drafts/{draft['registry_version_id']}/publish",
        headers=auth_headers(),
        json={"reason_code": "candidate_runtime_observed"},
    )
    registry = client.get(REGISTRY_PATH, headers=auth_headers())
    targets = {target["id"]: target for target in registry.json()["targets"]}

    async def load_publish_evidence() -> tuple[str | None, str | None, bool]:
        async with client.app_state["sessionmaker"]() as db:
            review_action = await db.scalar(
                select(MeetingDetectionReviewAction).where(
                    MeetingDetectionReviewAction.action == "publish_registry_version"
                )
            )
            audit_event = await db.scalar(
                select(AdminAuditEvent).where(AdminAuditEvent.action == "publish_registry_version")
            )
            entry = await db.scalar(
                select(MeetingTargetRegistryEntry).where(
                    MeetingTargetRegistryEntry.target_id == "example_vks"
                )
            )
            return (
                review_action.next_state if review_action else None,
                audit_event.outcome if audit_event else None,
                entry is not None,
            )

    review_state, audit_outcome, entry_exists = asyncio.run(load_publish_evidence())

    assert publish.status_code == 200
    assert publish.json()["status"] == "published"
    assert registry.status_code == 200
    assert registry.headers["x-graf-registry-version"] == publish.json()["registry_version"]
    assert targets["example_vks"]["mode"] == "diagnostic_only"
    assert targets["example_vks"]["mode"] != "prompt_enabled"
    assert targets["zoom"]["mode"] == "prompt_enabled"
    assert review_state == "published"
    assert audit_outcome == "completed"
    assert entry_exists is True


def test_non_target_rules_are_exported_in_registry_without_secret_content(client) -> None:
    before = client.get(REGISTRY_PATH, headers=auth_headers())
    candidate = _create_candidate(client, "meeting-detection:registry-non-target")

    mark = client.post(
        f"{ADMIN_REVIEW_PATH}/candidates/{candidate['candidate_id']}/mark-non-target",
        headers=auth_headers(),
        json={"reason_code": "admin_marked_non_target"},
    )
    after = client.get(REGISTRY_PATH, headers=auth_headers())
    rules = after.json()["nonTargetRules"]

    assert mark.status_code == 200
    assert after.status_code == 200
    assert after.headers["etag"] != before.headers["etag"]
    assert rules == [
        {
            "platform": "macos",
            "ruleKind": "bundle_id",
            "ruleValue": "ru.example.vks",
            "reasonCode": "admin_marked_non_target",
        }
    ]
    assert "passcode" not in str(after.json()).lower()
    assert "audio" not in str(after.json()).lower()


def test_registry_and_candidate_queries_ignore_foreign_workspace_rows(client) -> None:
    async def seed_foreign_rows() -> None:
        document = deepcopy(load_packaged_seed_registry())
        document["registryVersion"] = "2026.07.08.99"
        document["generatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        document["targets"].append(
            {
                "id": "foreign_workspace_vks",
                "displayName": "Foreign Workspace VKS",
                "market": "russia",
                "platform": "macos",
                "targetFamily": "native_app",
                "nativeBundleIds": ["ru.foreign.vks"],
                "mode": "diagnostic_only",
                "evidence": "runtime_start_verified",
                "requiredSignals": ["macos_sensor_indicators_mic"],
            }
        )
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Workspace(
                    id=FOREIGN_WORKSPACE_ID,
                    organization_id=ORG_ID,
                    slug="foreign-meeting-detection",
                    name="Foreign Meeting Detection",
                )
            )
            registry = MeetingTargetRegistryVersion(
                workspace_id=FOREIGN_WORKSPACE_ID,
                registry_version=document["registryVersion"],
                schema_version=1,
                status="published",
                source="foreign_test",
                published_at=datetime.now(UTC),
                document_json=document,
                etag=registry_etag(document),
            )
            db.add(registry)
            await db.flush()
            for entry in registry_entries(document):
                db.add(MeetingTargetRegistryEntry(registry_version_id=registry.id, **entry))
            db.add(
                MeetingDetectionCandidate(
                    workspace_id=FOREIGN_WORKSPACE_ID,
                    platform="macos",
                    candidate_kind="unknown_native_app",
                    state="new",
                    bundle_id="ru.foreign.vks",
                    display_name="Foreign Workspace VKS",
                    candidate_score=10,
                    candidate_reasons_json=["stable_mic_duration"],
                    suppression_reasons_json=[],
                    stable_observation_count=4,
                )
            )
            await db.commit()

    asyncio.run(seed_foreign_rows())

    registry = client.get(REGISTRY_PATH, headers=auth_headers())
    review = client.get(ADMIN_REVIEW_PATH, headers=auth_headers())
    target_ids = {target["id"] for target in registry.json()["targets"]}
    candidate_bundles = {candidate["bundle_id"] for candidate in review.json()["candidates"]}

    assert registry.status_code == 200
    assert review.status_code == 200
    assert "foreign_workspace_vks" not in target_ids
    assert "ru.foreign.vks" not in candidate_bundles
    assert registry.json()["registryVersion"] == "2026.07.08.1"
    assert WORKSPACE_ID != FOREIGN_WORKSPACE_ID
