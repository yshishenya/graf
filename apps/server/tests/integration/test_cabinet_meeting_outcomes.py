from __future__ import annotations

import asyncio
import importlib
import re
from datetime import UTC, datetime

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import (
    FOREIGN_DEVICE_ID,
    FOREIGN_ORG_ID,
    FOREIGN_USER_ID,
    FOREIGN_WORKSPACE_ID,
    create_outcome_ready_meeting,
)
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    ProcessingResult,
)
from twobrain_rec_server.outcomes.store import OUTCOME_GENERATOR_VERSION


def _service_module():
    try:
        return importlib.import_module("twobrain_rec_server.outcomes.service")
    except ModuleNotFoundError as exc:
        raise AssertionError("outcome service module is missing") from exc


def test_cabinet_detail_shows_stored_outcomes_instead_of_deferred_placeholders(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()
    asyncio.run(service.ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=meeting_id))

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


def test_cabinet_embedded_route_renders_stored_outcome_categories(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()
    asyncio.run(service.ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=meeting_id))

    response = client.get(f"/desktop/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    html = response.text
    assert "Итоги встречи" in html
    assert "data-outcome-category=\"summary\"" in html
    assert "data-outcome-state=\"available\"" in html
    assert "data-outcome-source-basis=\"stored_output\"" in html


def test_cabinet_preserves_transcript_playback_when_outcomes_are_processing(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    asyncio.run(_seed_outcome_set(client, meeting_id=meeting_id, status="generating", category_state="processing"))

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["meeting"]["status"] == "ready"
    assert payload["transcript"]["available"] is True
    assert payload["playback"]["available"] is True
    assert payload["notes_action_truth"]["source_basis"] == "processing_status"
    assert payload["notes_action_truth"]["summary"]["state"] == "processing"
    assert payload["notes_action_truth"]["summary"]["items"] == []


def test_cabinet_blocks_outcome_content_without_hiding_review_when_generation_failed(client) -> None:
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
    assert payload["notes_action_truth"]["source_basis"] == "blocked"
    assert payload["notes_action_truth"]["summary"]["state"] == "blocked"
    assert payload["notes_action_truth"]["decisions"]["state"] == "blocked"
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
                    "source_refs_json": [{"sequence": 0, "start_seconds": 0.0, "end_seconds": 12.5, "evidence_kind": "segment"}],
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


def test_cabinet_web_renders_processing_and_blocked_outcomes_in_russian_without_content(client) -> None:
    processing_id = create_outcome_ready_meeting(client, "cabinet-outcome-processing-web")
    blocked_id = create_outcome_ready_meeting(client, "cabinet-outcome-blocked-web")
    asyncio.run(_seed_outcome_set(client, meeting_id=processing_id, status="generating", category_state="processing"))
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
    assert 'data-outcome-source-basis="processing_status"' in processing.text
    assert 'data-outcome-state="processing"' in processing.text
    assert "Ключевое" in processing.text
    assert "Источник итогов: статус обработки" in processing.text
    assert 'data-outcome-source-basis="blocked"' in blocked.text
    assert "Источник итогов: заблокировано" in blocked.text
    assert "Синтетический итог встречи готов." not in blocked.text


def test_cabinet_web_and_embedded_routes_render_matching_outcome_truth(client) -> None:
    ready_id = create_outcome_ready_meeting(client, "cabinet-outcome-parity-ready")
    processing_id = create_outcome_ready_meeting(client, "cabinet-outcome-parity-processing")
    service = _service_module()
    asyncio.run(service.ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=ready_id))
    asyncio.run(_seed_outcome_set(client, meeting_id=processing_id, status="generating", category_state="processing"))

    for meeting_id, expected_basis in ((ready_id, "stored_output"), (processing_id, "processing_status")):
        web = client.get(f"/meetings/{meeting_id}", headers=auth_headers())
        embedded = client.get(f"/desktop/meetings/{meeting_id}", headers=auth_headers())

        assert web.status_code == 200
        assert embedded.status_code == 200
        assert _outcome_source_basis(web.text) == expected_basis
        assert _outcome_source_basis(embedded.text) == expected_basis
        assert _outcome_states(web.text) == _outcome_states(embedded.text)
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
        assert 'class="playback-bar detail-playback"' in web.text
        assert 'class="playback-bar detail-playback"' in embedded.text


def test_denied_viewer_cannot_infer_outcome_content_or_existence(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "cabinet-outcome-denied")
    service = _service_module()
    asyncio.run(service.ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=meeting_id))
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
        result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
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
        await db.commit()
