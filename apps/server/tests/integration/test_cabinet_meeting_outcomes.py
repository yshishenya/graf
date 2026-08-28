from __future__ import annotations

import asyncio
import importlib
import re
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID
from tests.fixtures.cabinet import (
    FOREIGN_DEVICE_ID,
    FOREIGN_ORG_ID,
    FOREIGN_USER_ID,
    FOREIGN_WORKSPACE_ID,
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
    ProcessingResult,
    ProcessingWorkflow,
)
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.outcomes.ai_service import resolve_summary_candidate
from twobrain_rec_server.outcomes.store import OUTCOME_GENERATOR_VERSION


def _service_module():
    try:
        return importlib.import_module("twobrain_rec_server.outcomes.service")
    except ModuleNotFoundError as exc:
        raise AssertionError("outcome service module is missing") from exc


async def _generate_and_accept(client, meeting_id, service) -> None:
    await service.ensure_outcomes_for_meeting(
        client.app_state["sessionmaker"], meeting_id=meeting_id
    )
    async with client.app_state["sessionmaker"]() as db:
        attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                MeetingOutcomeGenerationAttempt.candidate_id.is_not(None),
            )
            .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
        )
        meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
        assert attempt is not None and meeting is not None and attempt.candidate_id is not None
        await resolve_summary_candidate(
            db,
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            candidate_id=attempt.candidate_id,
            requested_by_user_id=USER_ID,
            accept=True,
            expected_current_outcome_set_id=None,
        )
        await db.commit()


def test_cabinet_detail_shows_stored_outcomes_instead_of_deferred_placeholders(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()
    asyncio.run(_generate_and_accept(client, meeting_id, service))

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
    asyncio.run(_generate_and_accept(client, meeting_id, service))

    async def seed_new_result() -> tuple[object, object]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            previous = await db.scalar(
                select(ProcessingResult)
                .where(ProcessingResult.meeting_id == meeting_id)
                .order_by(ProcessingResult.result_version.desc())
            )
            assert meeting is not None and previous is not None
            meeting.current_outcome_set_id = None
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
            return await queries._latest_outcome_set(
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


def test_accepted_outcome_is_hidden_when_a_replacement_attempt_owns_the_revision(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-replacement-attempt-fence")
    service = _service_module()
    asyncio.run(_generate_and_accept(client, meeting_id, service))

    async def replace_attempt() -> object | None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            current = await db.get(ProcessingWorkflow, result.processing_workflow_id)
            assert current is not None
            db.add(
                ProcessingWorkflow(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=result.media_revision_id,
                    workflow_id=f"processing/{result.media_revision_id}/replacement",
                    purpose="transcription",
                    status=ProcessingStatus.STARTING.value,
                    attempt_ordinal=current.attempt_ordinal + 1,
                )
            )
            await db.commit()
            return await current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=None,
            )

    assert asyncio.run(replace_attempt()) is None


def test_unpinned_current_outcome_is_hidden_after_lineage_rollout(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "legacy-outcome-hash-bind")
    service = _service_module()
    asyncio.run(_generate_and_accept(client, meeting_id, service))

    async def restore_migrated_legacy_hashes() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert (
                meeting is not None
                and result is not None
                and meeting.current_outcome_set_id is not None
            )
            outcome = await db.scalar(
                select(MeetingOutcomeSet).where(
                    MeetingOutcomeSet.id == meeting.current_outcome_set_id
                )
            )
            assert outcome is not None
            legacy_hash = sha256(f"legacy-processing-result:{result.id}".encode()).hexdigest()
            result.source_result_hash = legacy_hash
            outcome.source_result_hash = legacy_hash
            await db.commit()

    asyncio.run(restore_migrated_legacy_hashes())
    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["notes_action_truth"]["source_basis"] != "stored_output"

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
            assert outcome is None
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            return result.source_result_hash, None

    result_hash, outcome_hash = asyncio.run(read_bound_hashes())
    assert result_hash is not None
    assert outcome_hash is None


def test_unaccepted_current_outcome_is_not_a_runtime_fallback(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "unaccepted-outcome-runtime-fallback")
    service = _service_module()
    asyncio.run(_generate_and_accept(client, meeting_id, service))

    async def clear_revision_state_and_read() -> object | None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None and meeting.current_outcome_set_id is not None
            outcome = await db.get(MeetingOutcomeSet, meeting.current_outcome_set_id)
            assert outcome is not None
            outcome.revision_state = None
            await db.commit()
            return await current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=None,
            )

    assert asyncio.run(clear_revision_state_and_read()) is None


def test_cabinet_embedded_route_renders_stored_outcome_categories(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()
    asyncio.run(_generate_and_accept(client, meeting_id, service))

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
    assert 'data-outcome-source-basis="policy_deferral"' in processing.text
    assert 'data-outcome-state="deferred"' in processing.text
    assert 'class="notes-aggregate-state"' in processing.text
    assert "Ключевые пункты" not in processing.text
    assert "data-outcome-category" not in processing.text
    assert "Источник: отложено политикой" in processing.text
    assert 'data-outcome-source-basis="policy_deferral"' in blocked.text
    assert 'class="notes-aggregate-state"' in blocked.text
    assert "Источник: отложено политикой" in blocked.text
    assert "Синтетический итог встречи готов." not in blocked.text


def test_cabinet_web_and_embedded_routes_render_matching_outcome_truth(client) -> None:
    ready_id = create_outcome_ready_meeting(client, "cabinet-outcome-parity-ready")
    processing_id = create_outcome_ready_meeting(client, "cabinet-outcome-parity-processing")
    service = _service_module()
    asyncio.run(_generate_and_accept(client, ready_id, service))
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
                "decisions",
                "action_items",
                "followups",
                "risks",
                "questions",
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
    asyncio.run(_generate_and_accept(client, meeting_id, service))
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
            generator_version=OUTCOME_GENERATOR_VERSION,
            source_result_hash=result.source_result_hash,
            revision_state="accepted" if status in {"available", "partial"} else "candidate",
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
