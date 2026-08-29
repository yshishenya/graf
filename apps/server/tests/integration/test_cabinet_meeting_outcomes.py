from __future__ import annotations

import asyncio
import importlib
import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.cabinet import (
    FOREIGN_DEVICE_ID,
    FOREIGN_ORG_ID,
    FOREIGN_USER_ID,
    FOREIGN_WORKSPACE_ID,
    SAFE_TRANSCRIPT_TEXT,
    create_outcome_ready_meeting,
)
from twobrain_rec_server.cabinet import queries
from twobrain_rec_server.cabinet.egress import current_outcome_set
from twobrain_rec_server.db.models import (
    MediaRevision,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
    SummaryTemplate,
)
from twobrain_rec_server.outcomes.store import OUTCOME_GENERATOR_VERSION
from twobrain_rec_server.outcomes.templates import BUILT_IN_BY_KEY


def _service_module():
    try:
        return importlib.import_module("twobrain_rec_server.outcomes.service")
    except ModuleNotFoundError as exc:
        raise AssertionError("outcome service module is missing") from exc


def test_summary_type_catalog_is_versioned_ordered_and_has_orthogonal_state(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-type-catalog")

    response = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-types",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["catalog_version"] == "graf-summary-types-v1"
    entries = payload["entries"]
    assert [entry["template_key"] for entry in entries[:4]] == [
        "graf-auto-v1",
        "graf-outline-v1",
        "graf-meeting-minutes-v1",
        "graf-project-sync-v1",
    ]
    assert all(entry["catalog_version"] == payload["catalog_version"] for entry in entries)
    assert all("my_actions" not in entry and "private_self" not in entry for entry in entries)
    assert {entry["generation_state"] for entry in entries} <= {
        "idle",
        "preparing",
        "updating",
        "blocked",
        "deferred",
        "error",
        "ambiguous",
        "no_supported_content",
    }


def test_ready_summary_type_read_is_saved_and_does_not_require_ai_dependencies(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-type-read-ready")
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))

    response = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-auto-v1",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["catalog_entry"]["result_state"] == "ready"
    assert payload["catalog_entry"]["source_state"] == "current"
    assert payload["outcome_set_id"]
    assert payload["items"]
    assert "my_actions" not in payload and "private_self" not in payload
    assert payload["schema_version"] == 1
    assert payload["meeting_id"] == str(meeting_id)
    assert payload["template_key"] == "graf-auto-v1"
    assert payload["event_id"]
    assert payload["current_outcome_set_id"] == payload["outcome_set_id"]
    assert payload["copy_capability"]["kind"] == "summary"
    assert payload["copy_capability"]["authorized"] is True
    assert payload["copy_capability"]["outcome_set_id"] == payload["outcome_set_id"]
    assert payload["copy_capability"]["displayed_revision"] == payload["outcome_set_id"]
    assert payload["copy_capability"]["outcome_content_hash"]
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["etag"] == (
        f'"sum-{meeting_id}-graf-auto-v1-v{payload["state_version"]}"'
    )

    processing = client.get(
        f"/api/v1/meetings/{meeting_id}/processing",
        headers=auth_headers(),
    )
    assert processing.status_code == 200
    assert processing.json()["summary_status"] == "available"
    assert processing.json()["artifacts"]["summary"] == {
        "state": "available",
        "visible": True,
    }

    cached = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-auto-v1",
        headers=auth_headers() | {"If-None-Match": response.headers["etag"]},
    )
    assert cached.status_code == 304
    assert cached.text == ""
    assert cached.headers["cache-control"] == "private, no-store"


def test_processing_status_does_not_promote_hash_mismatched_published_outcome(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-processing-hash-mismatch")
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))

    async def tamper_source_hash() -> None:
        async with client.app_state["sessionmaker"]() as db:
            outcome = await db.scalar(
                select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == meeting_id)
            )
            assert outcome is not None
            outcome.source_result_hash = "tampered-source-hash"
            await db.commit()

    asyncio.run(tamper_source_hash())
    processing = client.get(
        f"/api/v1/meetings/{meeting_id}/processing",
        headers=auth_headers(),
    )

    assert processing.status_code == 200
    assert processing.json()["summary_status"] != "available"
    assert processing.json()["artifacts"]["summary"]["visible"] is False


def test_retired_builtin_summary_remains_readable_but_cannot_be_ensured(
    client, monkeypatch
) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-type-retired-builtin")
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))
    monkeypatch.delitem(BUILT_IN_BY_KEY, "graf-auto-v1")

    read = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-auto-v1",
        headers=auth_headers(),
    )
    assert read.status_code == 200
    assert read.json()["catalog_entry"]["availability_state"] == "retired"
    assert read.json()["catalog_entry"]["result_state"] == "ready"

    ensure = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-auto-v1/ensure",
        headers=auth_headers(),
        json={"schema_version": 1, "idempotency_key": "retired-summary-type-0001"},
    )
    assert ensure.status_code == 409
    assert ensure.json()["code"] == "summary_type_unavailable"


def test_source_revision_marks_every_saved_type_stale_without_cross_slot_generation(
    client,
) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-source-revision-three-types")

    async def seed() -> tuple[dict[str, UUID], UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            active_keys = (
                "graf-auto-v1",
                "graf-outline-v1",
                "graf-meeting-minutes-v1",
            )
            current_ids: dict[str, UUID] = {}
            for index, template_key in enumerate(active_keys):
                outcome = MeetingOutcomeSet(
                    id=uuid4(),
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=result.media_revision_id,
                    processing_result_id=result.id,
                    status="available",
                    summary_state="available",
                    source_kind="db_fixture",
                    generator_kind="db_fixture",
                    generator_version=f"fixture-old-{index}",
                    source_result_hash=result.source_result_hash,
                    source_fingerprint=f"result:{result.id}",
                    content_hash=f"summary-hash-{index}",
                    template_key=template_key,
                    template_version=1,
                    revision_state="accepted",
                )
                db.add(outcome)
                await db.flush()
                current_ids[template_key] = outcome.id
                db.add(
                    MeetingSummarySlot(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        template_key=template_key,
                        current_outcome_set_id=outcome.id,
                        current_binding_class="verified_complete",
                        is_meeting_default=index == 0,
                        default_resolution_source="explicit_meeting" if index == 0 else None,
                        default_resolution_version="source-revision-test-v1" if index == 0 else None,
                        default_resolved_at=datetime(2026, 8, 24, tzinfo=UTC)
                        if index == 0
                        else None,
                    )
                )

            retired_template = SummaryTemplate(
                id=uuid4(),
                workspace_id=meeting.workspace_id,
                owner_user_id=meeting.created_by_user_id,
                template_key="personal-retired-v1",
                kind="personal",
                name="Архивный личный формат",
                purpose="Тестовый архивный формат",
                sections_json=["summary"],
                output_language="ru",
                detail_level="standard",
                version=1,
                status="archived",
            )
            db.add(retired_template)
            await db.flush()
            retired_outcome = MeetingOutcomeSet(
                id=uuid4(),
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                status="available",
                summary_state="available",
                source_kind="db_fixture",
                generator_kind="db_fixture",
                generator_version="fixture-old-retired",
                source_result_hash=result.source_result_hash,
                source_fingerprint=f"result:{result.id}",
                content_hash="summary-hash-retired",
                template_id=retired_template.id,
                template_key=retired_template.template_key,
                template_version=1,
                revision_state="accepted",
            )
            db.add(retired_outcome)
            await db.flush()
            db.add(
                MeetingSummarySlot(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key=retired_template.template_key,
                    current_outcome_set_id=retired_outcome.id,
                    current_binding_class="verified_complete",
                )
            )
            newer = ProcessingResult(
                id=uuid4(),
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                mediascribe_job_id=result.mediascribe_job_id,
                processing_workflow_id=result.processing_workflow_id,
                result_version=result.result_version + 1,
                status="imported",
                transcript_status=result.transcript_status,
                diarization_status=result.diarization_status,
                summary_status=result.summary_status,
                language=result.language,
                segment_count=result.segment_count,
                diarization_segment_count=result.diarization_segment_count,
                source_result_hash="source-revision-new-hash",
                imported_at=datetime.now(UTC),
            )
            db.add(newer)
            await db.commit()
            return current_ids, retired_outcome.id, newer.id

    current_ids, retired_id, newer_result_id = asyncio.run(seed())
    for template_key, current_id in current_ids.items():
        response = client.get(
            f"/api/v1/cabinet/meetings/{meeting_id}/summaries/{template_key}",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["catalog_entry"]["source_state"] == "stale"
        assert payload["current_outcome_set_id"] == str(current_id)
        assert payload["outcome_set_id"] == str(current_id)

    retired = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summaries/personal-retired-v1",
        headers=auth_headers(),
    )
    assert retired.status_code == 200
    assert retired.json()["catalog_entry"]["availability_state"] == "retired"
    assert retired.json()["outcome_set_id"] == str(retired_id)

    retired_ensure = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summaries/personal-retired-v1/ensure",
        headers=auth_headers(),
        json={"schema_version": 1, "idempotency_key": "retired-source-test-001"},
    )
    assert retired_ensure.status_code == 409
    assert retired_ensure.json()["code"] == "summary_type_unavailable"

    unsaved = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summaries/unknown-unsaved-v1/ensure",
        headers=auth_headers(),
        json={"schema_version": 1, "idempotency_key": "unsaved-source-test-001"},
    )
    assert unsaved.status_code == 404
    assert unsaved.json()["code"] == "summary_type_not_found"

    capability = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/content-exports",
        headers=auth_headers(),
    )
    assert capability.status_code == 200
    assert capability.json()["processing_result_id"] == str(newer_result_id)
    assert capability.json()["summary"]["reason"] == "stored_summary_revision_stale"

    async def read_slots() -> dict[str, UUID | None]:
        async with client.app_state["sessionmaker"]() as db:
            rows = (
                await db.scalars(
                    select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id)
                )
            ).all()
            return {row.template_key: row.current_outcome_set_id for row in rows}

    assert asyncio.run(read_slots()) == {
        **current_ids,
        "personal-retired-v1": retired_id,
    }


def test_ensure_missing_summary_type_is_one_click_and_idempotent(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-type-ensure")
    temporal = FakeTemporalClient()
    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = temporal
    url = f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-meeting-minutes-v1/ensure"
    headers = auth_headers()
    body = {"schema_version": 1, "idempotency_key": "ensure-summary-type-0001"}

    first = client.post(url, headers=headers, json=body)
    second = client.post(url, headers=headers, json=body)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["catalog_entry"]["template_key"] == "graf-meeting-minutes-v1"
    assert first.json()["catalog_entry"]["result_state"] == "absent"
    assert first.json()["catalog_entry"]["generation_state"] in {"preparing", "updating"}
    assert first.json()["state_version"] >= 2
    assert first.json()["event_id"]
    assert first.headers["etag"] == (
        f'"sum-{meeting_id}-graf-meeting-minutes-v1-v{first.json()["state_version"]}"'
    )
    assert len(temporal.starts) == 1


def test_refresh_current_summary_type_is_slot_scoped_and_idempotent(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-type-refresh")
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))
    temporal = FakeTemporalClient()
    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = temporal
    read_url = f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-auto-v1"
    current = client.get(read_url, headers=auth_headers()).json()["current_outcome_set_id"]
    refresh_url = f"{read_url}/refresh"
    body = {
        "schema_version": 1,
        "idempotency_key": "refresh-summary-type-0001",
        "expected_current_outcome_set_id": current,
        "template_id": None,
        "template_version": 1,
        "generation_options": {},
    }

    first = client.post(refresh_url, headers=auth_headers(), json=body)
    second = client.post(refresh_url, headers=auth_headers(), json=body)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["current_outcome_set_id"] == current
    assert second.json()["current_outcome_set_id"] == current
    assert first.json()["catalog_entry"]["generation_state"] in {"updating", "preparing"}
    assert second.json()["catalog_entry"]["generation_state"] in {"updating", "preparing"}
    assert len(temporal.starts) == 1

    stale = {
        **body,
        "idempotency_key": "refresh-summary-type-stale-0001",
        "expected_current_outcome_set_id": str(UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")),
    }
    conflict = client.post(refresh_url, headers=auth_headers(), json=stale)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "summary_revision_conflict"
    assert len(temporal.starts) == 1

    deprecated = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/"
        f"{UUID('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee')}/preview",
        headers=auth_headers(),
    )
    assert deprecated.status_code == 410
    assert deprecated.json()["code"] == "summary_candidate_deprecated"


def test_summary_state_matrix_preserves_current_result_and_advances_version(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-state-matrix")
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))

    async def seed_attempt() -> tuple[UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            attempt = MeetingOutcomeGenerationAttempt(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                status="blocked_dependency",
                provider_kind="test",
                generator_version="test-state-matrix",
                template_key="graf-auto-v1",
                template_version=1,
                failure_code="summary_generation_unavailable",
            )
            db.add(attempt)
            await db.commit()
            return meeting.workspace_id, attempt.id

    _, attempt_id = asyncio.run(seed_attempt())
    url = f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-auto-v1"

    blocked = client.get(url, headers=auth_headers())
    assert blocked.status_code == 200
    blocked_payload = blocked.json()
    assert blocked_payload["catalog_entry"]["result_state"] == "ready"
    assert blocked_payload["catalog_entry"]["generation_state"] == "blocked"
    assert blocked_payload["catalog_entry"]["next_action"] == "wait"
    assert blocked_payload["catalog_entry"]["retryable"] is False

    async def update_attempt(*, status: str, failure_code: str) -> None:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(MeetingOutcomeGenerationAttempt, attempt_id)
            assert attempt is not None
            attempt.status = status
            attempt.failure_code = failure_code
            await db.commit()

    asyncio.run(update_attempt(status="failed", failure_code="summary_provider_outcome_ambiguous"))
    ambiguous = client.get(url, headers=auth_headers()).json()
    assert ambiguous["catalog_entry"]["result_state"] == "ready"
    assert ambiguous["catalog_entry"]["generation_state"] == "ambiguous"
    assert ambiguous["catalog_entry"]["next_action"] == "wait"
    assert ambiguous["catalog_entry"]["retryable"] is False

    asyncio.run(update_attempt(status="failed", failure_code="failed_pre_egress"))
    retry_safe = client.get(url, headers=auth_headers()).json()
    assert retry_safe["catalog_entry"]["generation_state"] == "error"
    assert retry_safe["catalog_entry"]["next_action"] == "retry_safe"
    assert retry_safe["catalog_entry"]["retryable"] is True
    assert retry_safe["outcome_set_id"] == blocked_payload["outcome_set_id"]
    assert retry_safe["state_version"] > blocked_payload["state_version"]

    asyncio.run(update_attempt(status="failed", failure_code="no_eligible_items"))
    no_supported_content = client.get(url, headers=auth_headers()).json()
    assert no_supported_content["catalog_entry"]["generation_state"] == "no_supported_content"
    assert no_supported_content["catalog_entry"]["next_action"] == "switch_type"
    assert no_supported_content["catalog_entry"]["retryable"] is False

    asyncio.run(update_attempt(status="failed", failure_code="summary_generation_unavailable"))
    deferred = client.get(url, headers=auth_headers()).json()
    assert deferred["catalog_entry"]["generation_state"] == "deferred"
    assert deferred["catalog_entry"]["next_action"] == "wait"
    assert deferred["catalog_entry"]["retryable"] is False


def test_missing_type_distinguishes_transcript_failure_and_empty_source(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-source-states")
    url = f"/api/v1/cabinet/meetings/{meeting_id}/summaries/graf-outline-v1"

    async def update_source(*, transcript_status: str, segment_count: int) -> None:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            result.transcript_status = transcript_status
            result.segment_count = segment_count
            await db.commit()

    asyncio.run(update_source(transcript_status="failed", segment_count=4))
    failed = client.get(url, headers=auth_headers()).json()["catalog_entry"]
    assert failed["result_state"] == "absent"
    assert failed["source_state"] == "transcript_failed"
    assert failed["generation_state"] == "idle"
    assert failed["next_action"] == "open_transcript"

    asyncio.run(update_source(transcript_status="available", segment_count=0))
    empty = client.get(url, headers=auth_headers()).json()["catalog_entry"]
    assert empty["result_state"] == "absent"
    assert empty["source_state"] == "empty"
    assert empty["generation_state"] == "idle"
    assert empty["next_action"] == "open_transcript"


async def _generate_and_store(client, meeting_id, service) -> None:
    outcome_set = await service.ensure_outcomes_for_meeting(
        client.app_state["sessionmaker"], meeting_id=meeting_id
    )
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
        assert meeting is not None
        stored = await db.get(MeetingOutcomeSet, outcome_set.id)
        assert stored is not None
        stored.template_key = "graf-auto-v1"
        stored.template_version = 1
        stored.revision_state = "accepted"
        stored.accepted_at = stored.generated_at or datetime.now(UTC)
        db.add(
            MeetingSummarySlot(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
                is_meeting_default=True,
                current_outcome_set_id=stored.id,
                current_binding_class="verified_complete",
                default_resolution_source="explicit_meeting",
                default_resolution_version="test-fixture-v1",
                default_resolved_at=datetime.now(UTC),
            )
        )
        await db.commit()


def test_cabinet_detail_shows_stored_outcomes_instead_of_deferred_placeholders(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    truth = payload["notes_action_truth"]
    assert truth["source_basis"] == "stored_output"
    assert truth["summary"]["state"] == "available"
    assert truth["summary"]["items"]
    assert truth["summary"]["items"][0]["source_refs"]
    assert truth["action_items"]["state"] in {"not_found", "not_inferable"}
    assert payload["meeting"]["notes_available"] is True
    assert payload["transcript"]["available"] is True
    assert payload["playback"]["available"] is True


def test_pointerless_legacy_outcome_cannot_attach_to_new_revision_result(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "legacy-pointerless-revision-boundary")
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))

    async def seed_new_result() -> tuple[object, object]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            previous = await db.scalar(
                select(ProcessingResult)
                .where(ProcessingResult.meeting_id == meeting_id)
                .order_by(ProcessingResult.result_version.desc())
            )
            assert meeting is not None and previous is not None
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            assert slot is not None
            slot.current_outcome_set_id = None
            slot.current_binding_class = None
            revision = MediaRevision(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                local_media_revision_id="legacy-pointerless-revision-boundary--new",
                revision_number=2,
                source_kind="reprocess",
                status="accepted",
                manifest_sha256="b" * 64,
                track_sha256_by_role={},
                duration_seconds=60,
                immutable=True,
            )
            db.add(revision)
            await db.flush()
            new_result = ProcessingResult(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=revision.id,
                mediascribe_job_id=previous.mediascribe_job_id,
                processing_workflow_id=previous.processing_workflow_id,
                result_version=previous.result_version + 1,
                status="imported",
                transcript_status="available",
                source_result_hash="legacy-pointerless-new-result",
            )
            db.add(new_result)
            await db.commit()
            return revision, new_result

    _, new_result = asyncio.run(seed_new_result())

    async def read_bound_outcome() -> object | None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            return await queries._current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting_id,
                processing_result_id=new_result.id,
            )

    assert asyncio.run(read_bound_outcome()) is None


def test_pointerless_generating_outcome_with_items_is_not_egressable(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "pointerless-generating-no-egress")
    asyncio.run(
        _seed_outcome_set(
            client,
            meeting_id=meeting_id,
            status="generating",
            category_state="processing",
            items=[
                {
                    "category": "summary",
                    "text": "private provisional content",
                    "source_refs_json": [{"segment_id": "private"}],
                }
            ],
        )
    )

    async def read_pointerless_outcome() -> object | None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            return await current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
            )

    assert asyncio.run(read_pointerless_outcome()) is None


def test_legacy_current_outcome_without_hash_remains_visible_after_lineage_rollout(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "legacy-outcome-hash-bind")
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))

    async def clear_legacy_hashes() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            current_id = await db.scalar(
                select(MeetingSummarySlot.current_outcome_set_id).where(
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            assert current_id is not None
            outcome = await db.scalar(
                select(MeetingOutcomeSet).where(MeetingOutcomeSet.id == current_id)
            )
            assert outcome is not None
            result.source_result_hash = None
            outcome.source_result_hash = None
            await db.commit()

    asyncio.run(clear_legacy_hashes())
    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["notes_action_truth"]["source_basis"] == "stored_output"

    async def read_bound_hashes() -> tuple[str | None, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            outcome = await current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=None,
            )
            assert outcome is not None
            result = await db.get(ProcessingResult, outcome.processing_result_id)
            assert result is not None
            return result.source_result_hash, outcome.source_result_hash

    result_hash, outcome_hash = asyncio.run(read_bound_hashes())
    assert result_hash is None
    assert outcome_hash is None


def test_cabinet_embedded_route_renders_stored_outcome_categories(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))

    response = client.get(f"/desktop/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    html = response.text
    assert "Итоги встречи" in html
    assert 'data-outcome-category="summary"' in html
    assert 'data-outcome-state="available"' in html
    assert 'data-outcome-source-basis="stored_output"' in html


def test_cabinet_preserves_transcript_playback_when_outcomes_are_processing(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    asyncio.run(
        _seed_outcome_set(
            client, meeting_id=meeting_id, status="generating", category_state="processing"
        )
    )

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["meeting"]["status"] == "ready"
    assert payload["transcript"]["available"] is True
    assert payload["playback"]["available"] is True
    assert payload["notes_action_truth"]["source_basis"] == "policy_deferral"
    assert payload["notes_action_truth"]["summary"]["state"] == "deferred"
    assert payload["notes_action_truth"]["summary"]["items"] == []


def test_cabinet_blocks_outcome_content_without_hiding_review_when_generation_failed(
    client,
) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    asyncio.run(
        _seed_outcome_set(
            client,
            meeting_id=meeting_id,
            status="blocked",
            category_state="blocked",
            failure_reason="outcomes_dependency_unavailable",
        )
    )

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"]["available"] is True
    assert payload["playback"]["available"] is True
    assert payload["notes_action_truth"]["source_basis"] == "policy_deferral"
    assert payload["notes_action_truth"]["summary"]["state"] == "deferred"
    assert payload["notes_action_truth"]["decisions"]["state"] == "deferred"
    assert payload["notes_action_truth"]["summary"]["items"] == []


def test_cabinet_renders_partial_outcome_truth_with_available_items(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    asyncio.run(
        _seed_outcome_set(
            client,
            meeting_id=meeting_id,
            status="partial",
            states={
                "summary": "available",
                "key_points": "available",
                "decisions": "not_found",
                "action_items": "blocked",
                "followups": "not_found",
                "risks": "not_found",
                "questions": "not_found",
                "evidence": "available",
            },
            items=[
                {
                    "category": "summary",
                    "sequence": 0,
                    "text": "Синтетический итог встречи готов.",
                    "source_refs_json": [
                        {
                            "sequence": 0,
                            "start_seconds": 0.0,
                            "end_seconds": 12.5,
                            "evidence_kind": "segment",
                        }
                    ],
                }
            ],
        )
    )

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    truth = response.json()["notes_action_truth"]
    assert truth["source_basis"] == "stored_output"
    assert truth["summary"]["state"] == "available"
    assert truth["summary"]["items"][0]["source_refs"][0]["sequence"] == 0
    assert truth["action_items"]["state"] == "blocked"


def test_cabinet_web_renders_processing_and_blocked_outcomes_in_russian_without_content(
    client,
) -> None:
    processing_id = create_outcome_ready_meeting(client, "cabinet-outcome-processing-web")
    blocked_id = create_outcome_ready_meeting(client, "cabinet-outcome-blocked-web")
    asyncio.run(
        _seed_outcome_set(
            client, meeting_id=processing_id, status="generating", category_state="processing"
        )
    )
    asyncio.run(
        _seed_outcome_set(
            client,
            meeting_id=blocked_id,
            status="blocked",
            category_state="blocked",
            failure_reason="outcomes_generation_failed",
        )
    )

    processing = client.get(f"/meetings/{processing_id}", headers=auth_headers())
    blocked = client.get(f"/meetings/{blocked_id}", headers=auth_headers())

    assert processing.status_code == 200
    assert blocked.status_code == 200
    processing_notes = _notes_panel(processing.text)
    blocked_notes = _notes_panel(blocked.text)
    assert 'data-outcome-source-basis="policy_deferral"' in processing_notes
    assert 'data-outcome-state="deferred"' in processing_notes
    assert 'class="notes-aggregate-state"' in processing_notes
    assert "Ключевые пункты" not in processing_notes
    assert "data-outcome-category" not in processing_notes
    assert "Источник: отложено политикой" in processing_notes
    assert 'data-outcome-source-basis="policy_deferral"' in blocked_notes
    assert 'class="notes-aggregate-state"' in blocked_notes
    assert "Источник: отложено политикой" in blocked_notes
    assert "Синтетический итог встречи готов." not in blocked_notes


def test_no_accepted_outcome_opens_preparing_result_without_transcript_mock(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "cabinet-no-accepted-preparing")
    asyncio.run(
        _seed_outcome_set(
            client,
            meeting_id=meeting_id,
            status="generating",
            category_state="processing",
            generator_kind="litellm",
            revision_state=None,
        )
    )

    response = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    assert 'id="detail-tab-outcomes" aria-selected="true"' in response.text
    outcomes = _outcomes_panel(response.text)
    assert "Итоги отложены" in outcomes
    assert "Формат: <strong data-summary-format-label>Авто</strong>" in outcomes
    assert outcomes.count('class="notes-aggregate-state"') == 1
    assert "data-outcome-category" not in outcomes
    assert SAFE_TRANSCRIPT_TEXT not in outcomes


def test_no_accepted_outcome_opens_blocked_error_with_one_safe_action(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "cabinet-no-accepted-blocked")
    asyncio.run(
        _seed_outcome_set(
            client,
            meeting_id=meeting_id,
            status="blocked",
            category_state="blocked",
            failure_reason="outcomes_dependency_unavailable",
            generator_kind="litellm",
            revision_state=None,
        )
    )

    response = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    assert 'id="detail-tab-outcomes" aria-selected="true"' in response.text
    outcomes = _outcomes_panel(response.text)
    assert outcomes.count('class="notes-aggregate-state"') == 1
    assert 'data-outcome-state="deferred"' in outcomes
    assert outcomes.count("data-summary-refresh-button") == 1
    assert "data-outcome-category" not in outcomes
    assert SAFE_TRANSCRIPT_TEXT not in outcomes


def test_fully_empty_accepted_ai_outcome_collapses_to_one_meeting_level_explanation(
    client,
) -> None:
    meeting_id = create_outcome_ready_meeting(client, "cabinet-ai-accepted-empty")
    asyncio.run(
        _seed_outcome_set(
            client,
            meeting_id=meeting_id,
            status="available",
            category_state="not_found",
            generator_kind="litellm",
        )
    )

    response = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    assert 'id="detail-tab-outcomes" aria-selected="true"' in response.text
    outcomes = _outcomes_panel(response.text)
    assert outcomes.count('class="notes-aggregate-state"') == 1
    assert 'data-outcome-state="empty"' in outcomes
    assert re.search(r'class="notes-aggregate-state"[^>]*>.*?<p>[^<]+</p>', outcomes, re.DOTALL)
    assert "data-outcome-category" not in outcomes


def test_accepted_ai_outcome_renders_stored_result_without_deterministic_mock(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "cabinet-ai-accepted-ready")
    ai_summary = "Команда согласовала выпуск после завершения обязательной проверки."
    asyncio.run(
        _seed_outcome_set(
            client,
            meeting_id=meeting_id,
            status="available",
            states={
                "summary": "available",
                "key_points": "not_found",
                "decisions": "not_found",
                "action_items": "not_found",
                "followups": "not_found",
                "risks": "not_found",
                "questions": "not_found",
                "evidence": "available",
            },
            items=[
                {
                    "category": "summary",
                    "text": ai_summary,
                    "source_refs_json": [
                        {
                            "sequence": 0,
                            "start_seconds": 0.0,
                            "end_seconds": 12.5,
                            "evidence_kind": "segment",
                        }
                    ],
                }
            ],
            generator_kind="litellm",
        )
    )

    api_response = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers()
    )
    page = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert api_response.status_code == 200
    assert page.status_code == 200
    truth = api_response.json()["notes_action_truth"]
    assert truth["provenance"]["generator_kind"] == "litellm"
    assert truth["summary"]["items"][0]["text"] == ai_summary
    assert SAFE_TRANSCRIPT_TEXT not in str(truth)
    outcomes = _outcomes_panel(page.text)
    assert ai_summary in outcomes
    assert SAFE_TRANSCRIPT_TEXT not in outcomes


def test_cabinet_web_and_embedded_routes_render_matching_outcome_truth(client) -> None:
    ready_id = create_outcome_ready_meeting(client, "cabinet-outcome-parity-ready")
    processing_id = create_outcome_ready_meeting(client, "cabinet-outcome-parity-processing")
    service = _service_module()
    asyncio.run(_generate_and_store(client, ready_id, service))
    asyncio.run(
        _seed_outcome_set(
            client, meeting_id=processing_id, status="generating", category_state="processing"
        )
    )

    for meeting_id, expected_basis in (
        (ready_id, "stored_output"),
        (processing_id, "policy_deferral"),
    ):
        web = client.get(f"/meetings/{meeting_id}", headers=auth_headers())
        embedded = client.get(f"/desktop/meetings/{meeting_id}", headers=auth_headers())

        assert web.status_code == 200
        assert embedded.status_code == 200
        assert _outcome_source_basis(web.text) == expected_basis
        assert _outcome_source_basis(embedded.text) == expected_basis
        assert _outcome_states(web.text) == _outcome_states(embedded.text)
        if expected_basis == "stored_output":
            assert set(_outcome_states(web.text)) == {
                "summary",
                "key_points",
                "evidence",
            }
        else:
            assert _outcome_states(web.text) == {}
            assert 'class="notes-aggregate-state"' in web.text
            assert 'class="notes-aggregate-state"' in embedded.text
        assert 'class="playback-bar detail-playback"' in web.text
        assert 'class="playback-bar detail-playback"' in embedded.text


def test_denied_viewer_cannot_infer_outcome_content_or_existence(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "cabinet-outcome-denied")
    service = _service_module()
    asyncio.run(_generate_and_store(client, meeting_id, service))
    outcome_text = asyncio.run(_first_outcome_text(client, meeting_id))
    headers = {
        "X-Organization-Id": str(FOREIGN_ORG_ID),
        "X-Workspace-Id": str(FOREIGN_WORKSPACE_ID),
        "X-User-Id": str(FOREIGN_USER_ID),
        "X-Device-Id": str(FOREIGN_DEVICE_ID),
    }

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=headers)
    page = client.get(f"/meetings/{meeting_id}", headers=headers)

    assert response.status_code in {403, 404}
    assert page.status_code in {403, 404}
    assert outcome_text not in response.text
    assert outcome_text not in page.text
    assert "data-outcome-category" not in page.text


def _outcome_source_basis(html: str) -> str:
    match = re.search(r'data-outcome-source-basis="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def _outcome_states(html: str) -> dict[str, str]:
    return dict(re.findall(r'data-outcome-category="([^"]+)" data-outcome-state="([^"]+)"', html))


def _outcomes_panel(html: str) -> str:
    start = html.index('id="detail-panel-outcomes"')
    end = html.index('id="detail-panel-recording"', start)
    return html[start:end]


def _notes_panel(html: str) -> str:
    outcomes = _outcomes_panel(html)
    return outcomes[outcomes.index('<section class="notes"') :]


async def _first_outcome_text(client, meeting_id) -> str:
    async with client.app_state["sessionmaker"]() as db:
        text = await db.scalar(
            select(MeetingOutcomeItem.text)
            .where(MeetingOutcomeItem.meeting_id == meeting_id)
            .where(MeetingOutcomeItem.text.is_not(None))
            .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
        )
        assert text is not None
        return text


async def _seed_outcome_set(
    client,
    *,
    meeting_id,
    status: str,
    category_state: str | None = None,
    states: dict[str, str] | None = None,
    items: list[dict] | None = None,
    failure_reason: str | None = None,
    generator_kind: str = "deterministic_extractive",
    revision_state: str | None = "candidate",
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        result = await db.scalar(
            select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
        )
        assert result is not None
        states = states or {
            "summary": category_state or "processing",
            "key_points": category_state or "processing",
            "decisions": category_state or "processing",
            "action_items": category_state or "processing",
            "followups": category_state or "processing",
            "risks": category_state or "processing",
            "questions": category_state or "processing",
            "evidence": category_state or "processing",
        }
        outcome_set = MeetingOutcomeSet(
            workspace_id=result.workspace_id,
            meeting_id=result.meeting_id,
            media_revision_id=result.media_revision_id,
            processing_result_id=result.id,
            status=status,
            summary_state=states["summary"],
            key_points_state=states["key_points"],
            decisions_state=states["decisions"],
            action_items_state=states["action_items"],
            followups_state=states["followups"],
            risks_state=states["risks"],
            questions_state=states["questions"],
            evidence_state=states["evidence"],
            generator_kind=generator_kind,
            generator_version=OUTCOME_GENERATOR_VERSION,
            template_key="graf-auto-v1",
            template_version=1,
            source_result_hash=result.source_result_hash,
            revision_state=(
                "accepted" if status in {"available", "partial"} else revision_state
            ),
            generated_at=datetime.now(UTC) if status in {"available", "partial"} else None,
            failure_reason=failure_reason,
        )
        db.add(outcome_set)
        await db.flush()
        if status in {"available", "partial"}:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            outcome_set.revision_state = "accepted"
            outcome_set.accepted_at = outcome_set.generated_at
            meeting.current_outcome_set_id = outcome_set.id
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.meeting_id == meeting_id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            if slot is None:
                slot = MeetingSummarySlot(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting_id,
                    template_key="graf-auto-v1",
                    is_meeting_default=True,
                    default_resolution_source="explicit_meeting",
                    default_resolution_version="slot-fixture-v1",
                    default_resolved_at=datetime.now(UTC),
                )
                db.add(slot)
                await db.flush()
            slot.current_outcome_set_id = outcome_set.id
            slot.current_binding_class = "verified_complete"
        for item in items or []:
            db.add(
                MeetingOutcomeItem(
                    workspace_id=result.workspace_id,
                    meeting_id=result.meeting_id,
                    outcome_set_id=outcome_set.id,
                    category=item["category"],
                    sequence=item.get("sequence", 0),
                    state=item.get("state", "available"),
                    text=item.get("text"),
                    truth_label=item.get("truth_label", "supported"),
                    source_refs_json=item.get("source_refs_json", []),
                )
            )
        if status in {"available", "partial"}:
            meeting = await db.scalar(
                select(Meeting).where(Meeting.id == meeting_id).with_for_update()
            )
            assert meeting is not None
            meeting.current_outcome_set_id = outcome_set.id
        await db.commit()
