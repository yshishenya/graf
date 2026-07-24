from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.cabinet import create_outcome_ready_meeting, seed_cabinet_meetings
from twobrain_rec_server.api.cabinet import _summary_candidate_projection
from twobrain_rec_server.db.models import (
    DispatchIntent,
    MediaScribeJob,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    ProcessingResult,
    SummaryTemplate,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.outcomes.ai_service import (
    create_summary_candidate,
    resolve_summary_candidate,
)
from twobrain_rec_server.outcomes.dispatch import ensure_dispatch_intent
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_processing_result

SERVER_ROOT = Path(__file__).resolve().parents[2]
CABINET_JS = SERVER_ROOT / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
MEETING_TEMPLATE = (
    SERVER_ROOT
    / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html"
)
SETTINGS_TEMPLATE = (
    SERVER_ROOT
    / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html"
)


def test_summary_selector_keeps_auto_four_recommendations_and_all_formats(client) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id

    response = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    html = response.text
    listbox = html.split('id="summary-format-listbox"', 1)[1].split("</div>", 1)[0]
    assert 'data-summary-format-button aria-haspopup="listbox"' in html
    assert 'data-summary-format-listbox data-recommended-limit="4" role="listbox"' in html
    assert listbox.count("data-summary-format-option") == 4
    assert ">Авто</button>" in listbox
    assert "Все форматы…" in listbox
    assert 'role="option"' in listbox
    assert 'aria-selected="true"' in listbox


def test_personal_template_management_lives_in_settings_not_quick_selector(client) -> None:
    settings = client.get("/settings", headers=auth_headers())

    assert settings.status_code == 200
    html = settings.text
    quick_source = MEETING_TEMPLATE.read_text(encoding="utf-8")
    settings_source = SETTINGS_TEMPLATE.read_text(encoding="utf-8")
    assert 'id="summary-formats"' in html
    assert "data-summary-template-create" in html
    assert "data-summary-template-copy" in html
    assert "data-summary-template-form" in html
    assert "data-summary-template-create" not in quick_source
    for action in ("duplicate", "archive", "DELETE", "PATCH"):
        assert action in CABINET_JS.read_text(encoding="utf-8")
    assert "Создать формат" in settings_source
    assert html.count("data-summary-default-template") == 1
    assert "Формат по умолчанию" in html


def test_candidate_ui_preserves_current_notes_until_explicit_accept() -> None:
    script = CABINET_JS.read_text(encoding="utf-8")

    assert "Текущие итоги остаются на месте" in script
    assert "Текущие итоги сохранены" in script
    assert 'text: "Использовать"' in script
    assert 'text: "Оставить текущие"' in script
    assert "expected_current_outcome_set_id: currentOutcomeSetId" in script
    assert "Обновить итоги" in script
    assert "request_intent_id" in script
    assert "manual_refresh" in script
    assert '/${candidate.candidate_id}/${accept ? "accept" : "reject"}' in script
    assert "window.location.reload()" in script
    assert "JSON.stringify({" in script
    assert "template: activeTemplate" in script
    assert 'text: "Обновить страницу"' in script
    assert "Создать новый вариант" in script
    assert "currentSummaryFormatTemplateId" in script
    assert "currentSummaryFormatVersion" in script
    assert "candidateErrorAction" in script
    assert '"summary_revision_conflict"' in script
    assert 'result_invalid: "Модель вернула неподтверждённый результат.' in script
    assert 'summary_generation_in_progress: "Другой вариант уже готовится.' in script
    assert 'summary_request_unavailable: "Не удалось связаться с сервисом итогов.' in script
    assert "const latestFailure = candidates.find" in script
    assert "candidate.template_version" in script
    assert 'candidate.next_action === "new_candidate"' in script
    assert 'action: () => requestCurrentRefresh()' in script
    assert "loadPreview(candidate, generation).then" in script
    assert "Предпросмотр пока недоступен" in script
    assert "source_revision_label" in script


def test_candidate_list_ignores_legacy_deterministic_attempts(client) -> None:
    """Legacy outcome provenance is not a candidate and must not break the list API."""
    meeting_id = create_outcome_ready_meeting(client, "legacy-candidate-list")

    async def seed_legacy_attempt() -> None:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            db.add(
                MeetingOutcomeGenerationAttempt(
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting_id,
                    media_revision_id=result.media_revision_id,
                    processing_result_id=result.id,
                    status="stored",
                    provider_kind="deterministic_extractive",
                    generator_version="legacy-test",
                    candidate_id=None,
                )
            )
            await db.commit()

    client.portal.call(seed_legacy_attempt)
    listed = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
    )

    assert listed.status_code == 200
    assert listed.json() == {"candidates": []}


def test_candidate_list_hides_candidates_from_an_older_processing_result(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "stale-candidate-list")

    async def seed_candidate_and_new_result() -> UUID:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            candidate = await create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            candidate.status = "candidate"
            job = await db.get(MediaScribeJob, result.mediascribe_job_id)
            assert job is not None
            db.add(
                ProcessingResult(
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting_id,
                    media_revision_id=result.media_revision_id,
                    mediascribe_job_id=job.id,
                    result_version=result.result_version + 1,
                    status="imported",
                    transcript_status="available",
                    diarization_status=result.diarization_status,
                    summary_status=result.summary_status,
                    language=result.language,
                    segment_count=result.segment_count,
                    diarization_segment_count=result.diarization_segment_count,
                    source_result_hash="newer-list-result",
                    imported_at=datetime.now(UTC) + timedelta(seconds=1),
                )
            )
            await db.commit()
            return candidate.candidate_id

    candidate_id = client.portal.call(seed_candidate_and_new_result)
    listed = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
    )

    assert listed.status_code == 200
    assert str(candidate_id) not in {
        candidate["candidate_id"] for candidate in listed.json()["candidates"]
    }


def test_candidate_list_hides_superseded_accepted_attempts(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "superseded-accepted-candidates")

    async def seed_two_accepted_candidates() -> tuple[UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            first = await create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            first_set = MeetingOutcomeSet(
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                candidate_id=first.candidate_id,
                status="available",
                source_kind="litellm",
                generator_kind="litellm",
                generator_version="test-list-first",
                template_key=first.template_key,
                template_version=first.template_version,
                revision_state="accepted",
            )
            db.add(first_set)
            await db.flush()
            first.status = "accepted"
            first.outcome_set_id = first_set.id
            meeting.current_outcome_set_id = first_set.id

            second = await create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=first_set.id,
                request_intent="manual_format",
            )
            second_set = MeetingOutcomeSet(
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                candidate_id=second.candidate_id,
                status="available",
                source_kind="litellm",
                generator_kind="litellm",
                generator_version="test-list-second",
                template_key=second.template_key,
                template_version=second.template_version,
                revision_state="accepted",
            )
            db.add(second_set)
            await db.flush()
            second.status = "accepted"
            second.outcome_set_id = second_set.id
            first_set.revision_state = "superseded"
            meeting.current_outcome_set_id = second_set.id
            await db.commit()
            return first.candidate_id, second.candidate_id

    first_id, second_id = client.portal.call(seed_two_accepted_candidates)
    listed = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
    )

    assert listed.status_code == 200
    candidate_ids = {candidate["candidate_id"] for candidate in listed.json()["candidates"]}
    assert str(first_id) not in candidate_ids
    assert str(second_id) in candidate_ids


def test_temporal_dispatch_failure_keeps_candidate_retryable_and_current_summary(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "temporal-dispatch-retry")

    async def generate_baseline():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            outcome_set = await ensure_outcomes_for_processing_result(db, result=result)
            await db.commit()
            return outcome_set.id

    client.portal.call(generate_baseline)

    class FailingTemporalClient:
        async def start_workflow(self, *_args, **_kwargs):
            raise RuntimeError("simulated Temporal outage")

    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = FailingTemporalClient()
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
            "expected_current_outcome_set_id": None,
        },
    )

    assert response.status_code == 503
    assert response.json()["code"] == "summary_generation_unavailable"

    async def load_candidate() -> MeetingOutcomeGenerationAttempt | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(MeetingOutcomeGenerationAttempt)
                .where(
                    MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                    MeetingOutcomeGenerationAttempt.template_key == "graf-meeting-minutes-v1",
                )
                .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
            )

    candidate = client.portal.call(load_candidate)
    assert candidate is not None
    assert candidate.status == "queued"
    assert candidate.failure_code == "summary_generation_unavailable"
    assert candidate.failure_source == "temporal_dispatch"
    assert candidate.workflow_run_id is None

    listed = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
    )
    assert listed.status_code == 200
    projection = listed.json()["candidates"][0]
    assert projection["state"] == "generating"
    assert projection["reason_code"] == "temporary_unavailable"
    assert projection["retryable"] is True
    assert projection["next_action"] == "retry"


def test_worker_failure_wins_when_temporal_dispatch_ack_races(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "temporal-dispatch-worker-race")

    async def seed_queued_candidate():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            attempt = await create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            await db.commit()
            return attempt.candidate_id

    candidate_id = client.portal.call(seed_queued_candidate)

    class RacingTemporalClient:
        async def start_workflow(self, _workflow, payload, **_kwargs):
            async with client.app_state["sessionmaker"]() as db:
                attempt = await db.scalar(
                    select(MeetingOutcomeGenerationAttempt).where(
                        MeetingOutcomeGenerationAttempt.candidate_id == UUID(payload["candidate_id"])
                    )
                )
                assert attempt is not None
                attempt.status = "generating"
                attempt.failure_code = "litellm_endpoint_unavailable"
                attempt.failure_source = "worker"
                await db.commit()
            raise RuntimeError("Temporal acknowledgement raced with worker state")

    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = RacingTemporalClient()
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
            "expected_current_outcome_set_id": None,
        },
    )

    assert response.status_code == 202
    assert response.json()["state"] == "generating"

    async def load_state() -> tuple[str | None, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id
                )
            )
            assert attempt is not None
            return attempt.failure_code, attempt.failure_source

    assert client.portal.call(load_state) == ("litellm_endpoint_unavailable", "worker")

    class SuccessfulTemporalClient:
        async def start_workflow(self, _workflow, payload, **_kwargs):
            async with client.app_state["sessionmaker"]() as db:
                attempt = await db.scalar(
                    select(MeetingOutcomeGenerationAttempt).where(
                        MeetingOutcomeGenerationAttempt.candidate_id == UUID(payload["candidate_id"])
                    )
                )
                assert attempt is not None
                attempt.status = "generating"
                attempt.failure_code = "langfuse_prompt_unavailable"
                attempt.failure_source = "worker"
                await db.commit()
            return {"run_id": "worker-run"}

    client.app.state.outcome_temporal_client = SuccessfulTemporalClient()
    successful_ack = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
            "expected_current_outcome_set_id": None,
        },
    )
    assert successful_ack.status_code == 202
    assert client.portal.call(load_state) == ("langfuse_prompt_unavailable", "worker")


def test_ready_candidate_is_reused_without_a_second_temporal_dispatch(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "ready-candidate-no-replay")

    async def seed_ready_candidate():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            attempt = await create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            attempt.status = "candidate"
            await db.commit()
            return attempt.candidate_id

    candidate_id = client.portal.call(seed_ready_candidate)

    class ExplodingTemporalClient:
        async def start_workflow(self, *_args, **_kwargs):
            raise AssertionError("a ready candidate must not be dispatched again")

    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = ExplodingTemporalClient()
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
            "expected_current_outcome_set_id": None,
        },
    )

    assert response.status_code == 202
    assert response.json()["candidate_id"] == str(candidate_id)
    assert response.json()["state"] == "ready"


def test_retryable_failed_candidate_reuses_identity_and_replaces_run_id(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "retryable-failed-candidate")

    async def seed_failed_candidate():
        async with client.app_state["sessionmaker"]() as db:
            attempt = await create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
                request_intent="manual_format",
            )
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            intent = await ensure_dispatch_intent(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                candidate_id=attempt.candidate_id,
                idempotency_key=attempt.idempotency_key or f"candidate:{attempt.candidate_id}",
                source_fingerprint=attempt.source_fingerprint,
            )
            attempt.status = "failed"
            attempt.failure_code = "summary_generation_retries_exhausted"
            attempt.workflow_run_id = "old-failed-run"
            attempt.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            intent.state = "terminal_failed"
            intent.reconciliation_state = "terminal"
            await db.commit()
            return attempt.candidate_id

    candidate_id = client.portal.call(seed_failed_candidate)
    temporal = FakeTemporalClient()
    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = temporal
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
            "expected_current_outcome_set_id": None,
        },
    )

    assert response.status_code == 202
    assert response.json()["candidate_id"] == str(candidate_id)
    assert response.json()["state"] == "generating"
    assert len(temporal.starts) == 1

    async def load_candidate() -> MeetingOutcomeGenerationAttempt | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id
                )
            )

    candidate = client.portal.call(load_candidate)
    assert candidate is not None
    assert candidate.status == "queued"
    assert candidate.failure_code is None
    assert candidate.workflow_run_id == "run-1"
    assert candidate.expires_at is not None
    assert candidate.expires_at > datetime.now(UTC) + timedelta(hours=23)

    async def load_dispatch() -> tuple[int, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            intents = (
                await db.scalars(
                    select(DispatchIntent).where(DispatchIntent.candidate_id == candidate_id)
                )
            ).all()
            assert len(intents) == 1
            intent = intents[0]
            return len(intents), intent.state, intent.idempotency_key

    count, dispatch_state, dispatch_key = client.portal.call(load_dispatch)
    assert count == 1
    assert dispatch_state == "started"
    assert dispatch_key == candidate.idempotency_key


def test_active_candidate_blocks_a_different_format(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "one-active-candidate")

    async def seed_active_candidate():
        async with client.app_state["sessionmaker"]() as db:
            attempt = await create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            await db.commit()
            return attempt.candidate_id

    client.portal.call(seed_active_candidate)
    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = FakeTemporalClient()
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
        json={
            "template_key": "graf-outline-v1",
            "template_id": None,
            "template_version": 1,
            "expected_current_outcome_set_id": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "summary_generation_in_progress"


def test_already_started_dispatch_does_not_clear_existing_run_id(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "already-started-run-preserved")

    async def seed_queued_candidate():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            attempt = await create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            attempt.workflow_run_id = "existing-temporal-run"
            await db.commit()
            return attempt.candidate_id

    candidate_id = client.portal.call(seed_queued_candidate)

    class _AlreadyStartedError(RuntimeError):
        pass

    class AlreadyStartedTemporalClient:
        async def start_workflow(self, *_args, **_kwargs):
            raise _AlreadyStartedError("already started")

    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = AlreadyStartedTemporalClient()
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
            "expected_current_outcome_set_id": None,
        },
    )

    assert response.status_code == 202
    assert response.json()["candidate_id"] == str(candidate_id)

    async def load_run_id() -> str | None:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id
                )
            )
            return attempt.workflow_run_id if attempt is not None else None

    assert client.portal.call(load_run_id) == "existing-temporal-run"


def test_format_selection_uses_the_rendered_accepted_revision_and_starts_temporal(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def generate_baseline():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            outcome_set = await ensure_outcomes_for_processing_result(db, result=result)
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            baseline_attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.outcome_set_id == outcome_set.id,
                    MeetingOutcomeGenerationAttempt.candidate_id.is_not(None),
                )
            )
            assert baseline_attempt is not None and baseline_attempt.candidate_id is not None
            await resolve_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                candidate_id=baseline_attempt.candidate_id,
                requested_by_user_id=USER_ID,
                accept=True,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
            )
            await db.commit()
            return outcome_set.id

    accepted_id = client.portal.call(generate_baseline)
    page = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert page.status_code == 200
    assert f'data-current-outcome-set-id="{accepted_id}"' in page.text

    temporal = FakeTemporalClient()
    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = temporal
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
            "expected_current_outcome_set_id": str(accepted_id),
        },
    )

    assert response.status_code == 202
    assert response.json()["state"] == "generating"
    assert response.json()["current_outcome_set_id"] == str(accepted_id)
    assert len(temporal.starts) == 1
    started = next(iter(temporal.starts.values()))
    assert started["payload"]["template_key"] == "graf-meeting-minutes-v1"


def test_owner_preview_is_private_and_cross_workspace_is_hidden(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    created = client.post(
        "/api/v1/cabinet/summary-templates",
        headers=auth_headers(),
        json={
            "name": "Мой формат для проверки",
            "purpose": "Проверка предпросмотра",
            "sections": ["summary"],
            "output_language": "ru",
            "detail_level": "standard",
        },
    )
    assert created.status_code == 201
    template = created.json()

    async def seed_candidate():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            attempt = await create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key=template["template_key"],
                template_id=template["template_id"],
                template_version=template["version"],
                expected_current_outcome_set_id=None,
            )
            outcome_set = MeetingOutcomeSet(
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                media_revision_id=attempt.media_revision_id,
                processing_result_id=result.id,
                status="available",
                source_kind="litellm",
                generator_kind="litellm",
                generator_version="test-preview",
                template_id=template["template_id"],
                template_key=template["template_key"],
                template_version=template["version"],
                revision_state="candidate",
            )
            db.add(outcome_set)
            await db.flush()
            db.add_all(
                [
                    MeetingOutcomeItem(
                        workspace_id=WORKSPACE_ID,
                        meeting_id=meeting_id,
                        outcome_set_id=outcome_set.id,
                        category="summary",
                        sequence=sequence,
                        state="available",
                        text="Пункт предпросмотра",
                        owner_text="",
                        due_date_text="",
                        truth_label="supported",
                        source_refs_json=[f"legacy-ref-{index}" for index in range(40)],
                    )
                    for sequence in range(205)
                ]
                + [
                    MeetingOutcomeItem(
                        workspace_id=WORKSPACE_ID,
                        meeting_id=meeting_id,
                        outcome_set_id=outcome_set.id,
                        category="legacy_unknown",
                        sequence=0,
                        state="available",
                        text="Legacy category",
                        owner_text="",
                        due_date_text="",
                        truth_label="supported",
                        source_refs_json=["legacy-unknown"],
                    )
                ]
            )
            attempt.outcome_set_id = outcome_set.id
            attempt.status = "candidate"
            await db.commit()
            return attempt.candidate_id

    candidate_id = client.portal.call(seed_candidate)
    preview = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/preview",
        headers=auth_headers(),
    )
    assert preview.status_code == 200
    assert preview.headers["cache-control"] == "private, no-store"
    assert preview.headers["pragma"] == "no-cache"
    assert preview.json()["template_key"] == template["template_key"]
    assert preview.json()["items"][0]["category"] == "summary"
    assert len(preview.json()["items"]) == 200
    assert all(item["category"] == "summary" for item in preview.json()["items"])
    assert all(len(item["source_refs"]) == 32 for item in preview.json()["items"])
    listed = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
    )
    assert listed.status_code == 200
    listed_candidate = next(
        item for item in listed.json()["candidates"] if item["candidate_id"] == str(candidate_id)
    )
    assert listed_candidate["template_name"] == template["name"]

    async def expire_candidate() -> None:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id
                )
            )
            assert attempt is not None
            attempt.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    client.portal.call(expire_candidate)
    expired_candidate = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}",
        headers=auth_headers(),
    )
    assert expired_candidate.status_code == 200
    assert expired_candidate.json()["state"] == "expired"
    assert expired_candidate.json()["preview"] == []
    expired_preview = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/preview",
        headers=auth_headers(),
    )
    assert expired_preview.status_code == 409
    assert expired_preview.json()["code"] == "summary_candidate_expired"

    async def reopen_expiry_window() -> None:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id
                )
            )
            assert attempt is not None
            attempt.expires_at = datetime.now(UTC) + timedelta(hours=1)
            await db.commit()

    client.portal.call(reopen_expiry_window)

    async def seed_newer_result() -> None:
        async with client.app_state["sessionmaker"]() as db:
            current = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert current is not None
            db.add(
                ProcessingResult(
                    workspace_id=current.workspace_id,
                    meeting_id=current.meeting_id,
                    media_revision_id=current.media_revision_id,
                    mediascribe_job_id=current.mediascribe_job_id,
                    processing_workflow_id=current.processing_workflow_id,
                    result_version=current.result_version + 1,
                    status=current.status,
                    transcript_status=current.transcript_status,
                    diarization_status=current.diarization_status,
                    summary_status=current.summary_status,
                    language=current.language,
                    segment_count=current.segment_count,
                    diarization_segment_count=current.diarization_segment_count,
                    source_result_hash="newer-result-for-stale-candidate",
                    imported_at=current.imported_at - timedelta(minutes=1),
                )
            )
            await db.commit()

    client.portal.call(seed_newer_result)
    stale_preview = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/preview",
        headers=auth_headers(),
    )
    assert stale_preview.status_code == 409
    assert stale_preview.json()["code"] == "summary_source_revision_stale"
    stale_candidate = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}",
        headers=auth_headers(),
    )
    assert stale_candidate.status_code == 409
    assert stale_candidate.json()["code"] == "summary_source_revision_stale"

    foreign_headers = {
        **auth_headers(),
        "X-Organization-Id": "10000000-0000-0000-0000-000000000016",
        "X-Workspace-Id": "20000000-0000-0000-0000-000000000016",
        "X-User-Id": "30000000-0000-0000-0000-000000000016",
        "X-Device-Id": "40000000-0000-0000-0000-000000000016",
    }
    hidden = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/preview",
        headers=foreign_headers,
    )
    assert hidden.status_code in {403, 404}


def test_candidate_ui_restores_template_provenance_before_retry() -> None:
    script = CABINET_JS.read_text(encoding="utf-8")

    assert "templateFromCandidate" in script
    assert "provenance.template_key" in script
    assert "provenance.template_version" in script
    assert "provenance.template_id" in script
    assert "resumed.template?.key" in script
    assert "Источник: текущая расшифровка" in script
    assert "summary-candidate-source" in script


def test_candidate_ui_ignores_stale_loads_and_retries_existing_poll() -> None:
    script = CABINET_JS.read_text(encoding="utf-8")

    assert "let candidateRequestGeneration = 0" in script
    assert "const generation = ++candidateRequestGeneration" in script
    assert "const initialCandidateLoadGeneration = candidateRequestGeneration" in script
    assert "if (initialCandidateLoadGeneration !== candidateRequestGeneration) return" in script
    assert "const refreshGeneration = ++candidateRequestGeneration" in script
    assert "candidateRequestInFlightGeneration" in script
    assert "if (generation !== candidateRequestGeneration) return" in script

    poll_source = script[
        script.index("const pollCandidate") : script.index("const requestCandidate")
    ]
    assert 'text: "Проверить снова"' in poll_source
    assert "resumeCandidatePolling(candidate, generation)" in poll_source
    assert "summary_poll_unavailable" in poll_source
    assert "error?.status >= 500" in poll_source
    assert "retryCandidateAction(code)" not in poll_source

    # A new manual generation remains an explicit terminal-state action, not a
    # recovery path for a transient poll failure.
    assert 'requestIntent: "manual_refresh"' in script
    assert 'candidateErrorAction(code, activeTemplate, error)' in script
    assert 'error?.name === "TypeError"' in script
    assert 'candidate.state === "blocked"' in script


def test_summary_selector_keyboard_focus_and_candidate_projection_are_simple(client) -> None:
    script = CABINET_JS.read_text(encoding="utf-8")
    schema = client.get("/openapi.json").json()["components"]["schemas"]

    for key in ("ArrowUp", "ArrowDown", "Home", "End", "Escape"):
        assert key in script
    assert 'button.focus({ preventScroll: true })' in script
    assert "trapModalFocus(dialog, event)" in script
    states = set(schema["SummaryCandidateResponse"]["properties"]["state"]["enum"])
    assert states == {"generating", "ready", "accepted", "closed", "failed", "blocked", "stale", "expired"}
    assert states.isdisjoint({"queued", "blocked_dependency", "candidate", "cancelled"})


def test_terminal_model_validation_failure_has_bounded_non_retry_projection() -> None:
    from types import SimpleNamespace

    reason, retryable, next_action = _summary_candidate_projection(
        SimpleNamespace(status="failed", failure_code="summary_response_invalid")
    )
    assert (reason, retryable, next_action) == ("result_invalid", False, "new_candidate")


def test_candidate_projection_keeps_terminal_dependency_reasons_actionable() -> None:
    from types import SimpleNamespace

    cases = {
        "summary_generation_in_progress": ("generation_in_progress", False, "refresh_status"),
        "summary_prompt_invalid": ("prompt_invalid", False, "choose_format"),
        "summary_transcript_unavailable": ("transcript_unavailable", False, "refresh"),
        "generation_call_content_hash_mismatch": ("content_unavailable", False, "refresh_status"),
    }
    for code, expected in cases.items():
        assert _summary_candidate_projection(
            SimpleNamespace(status="failed", failure_code=code)
        ) == expected
    assert _summary_candidate_projection(
        SimpleNamespace(status="rejected", failure_code=None)
    ) == ("dismissed", False, "new_candidate")


def test_workspace_default_format_is_persisted_and_returned_by_list_api(client) -> None:
    headers = auth_headers()
    listed = client.get("/api/v1/cabinet/summary-templates", headers=headers)

    assert listed.status_code == 200
    assert listed.json()["default_template_key"] == "graf-auto-v1"
    assert listed.json()["can_manage_default"] is True

    changed = client.put(
        "/api/v1/cabinet/summary-templates/default",
        headers=headers,
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
        },
    )
    reloaded = client.get("/api/v1/cabinet/summary-templates", headers=headers)

    assert changed.status_code == 200
    assert changed.json()["name"] == "Протокол встречи"
    assert reloaded.status_code == 200
    assert reloaded.json()["default_template_key"] == "graf-meeting-minutes-v1"

    async def load_workspace() -> Workspace:
        async with client.app_state["sessionmaker"]() as db:
            workspace = await db.get(Workspace, WORKSPACE_ID)
            assert workspace is not None
            return workspace

    workspace = client.portal.call(load_workspace)
    assert workspace.default_summary_template_key == "graf-meeting-minutes-v1"
    assert workspace.default_summary_template_id is None
    assert workspace.default_summary_template_version == 1


def test_only_workspace_owner_can_change_default_format(client) -> None:
    async def make_member() -> None:
        async with client.app_state["sessionmaker"]() as db:
            membership = await db.scalar(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == WORKSPACE_ID,
                    WorkspaceMembership.user_id == USER_ID,
                )
            )
            assert membership is not None
            membership.role = "member"
            await db.commit()

    client.portal.call(make_member)
    response = client.put(
        "/api/v1/cabinet/summary-templates/default",
        headers=auth_headers(),
        json={
            "template_key": "graf-outline-v1",
            "template_id": None,
            "template_version": 1,
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "summary_default_forbidden"


def test_workspace_default_rejects_personal_formats(client) -> None:
    headers = auth_headers()
    created = client.post(
        "/api/v1/cabinet/summary-templates",
        headers=headers,
        json={
            "name": "Мои итоги",
            "purpose": "Решения и следующие шаги",
            "sections": ["summary", "decisions", "action_items"],
            "output_language": "ru",
            "detail_level": "standard",
        },
    )
    assert created.status_code == 201
    personal = created.json()

    selected = client.put(
        "/api/v1/cabinet/summary-templates/default",
        headers=headers,
        json={
            "template_key": personal["template_key"],
            "template_id": personal["template_id"],
            "template_version": personal["version"],
        },
    )
    assert selected.status_code == 422
    assert selected.json()["code"] == "summary_default_requires_builtin"

    async def load_workspace() -> Workspace:
        async with client.app_state["sessionmaker"]() as db:
            workspace = await db.get(Workspace, WORKSPACE_ID)
            assert workspace is not None
            return workspace

    workspace = client.portal.call(load_workspace)
    assert workspace.default_summary_template_key == "graf-auto-v1"
    assert workspace.default_summary_template_id is None
    assert workspace.default_summary_template_version == 1


def test_duplicate_personal_template_respects_active_template_limit(client) -> None:
    async def seed_templates() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    SummaryTemplate(
                        workspace_id=WORKSPACE_ID,
                        owner_user_id=USER_ID,
                        template_key=f"limit-{index}",
                        kind="personal",
                        name=f"Формат {index}",
                        purpose="Проверка лимита",
                        sections_json=["summary"],
                        output_language="ru",
                        detail_level="standard",
                        version=1,
                        status="active",
                    )
                    for index in range(100)
                ]
            )
            await db.commit()

    client.portal.call(seed_templates)
    async def load_source_id() -> object:
        async with client.app_state["sessionmaker"]() as db:
            source = await db.scalar(
                select(SummaryTemplate.id).where(
                    SummaryTemplate.workspace_id == WORKSPACE_ID,
                    SummaryTemplate.owner_user_id == USER_ID,
                    SummaryTemplate.status == "active",
                )
            )
            assert source is not None
            return source

    source_id = client.portal.call(load_source_id)
    response = client.post(
        f"/api/v1/cabinet/summary-templates/{source_id}/duplicate",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "summary_template_limit"


def test_default_format_contract_is_migrated_and_explicit(client) -> None:
    schema = client.get("/openapi.json").json()
    migration = (
        SERVER_ROOT
        / "src/twobrain_rec_server/db/migrations/versions/0031_recording_workflow_templates_sharing.py"
    ).read_text(encoding="utf-8")

    operation = schema["paths"]["/api/v1/cabinet/summary-templates/default"]["put"]
    assert operation["operationId"] == "updateDefaultSummaryTemplate"
    assert "can_manage_default" in schema["components"]["schemas"][
        "SummaryTemplateListResponse"
    ]["properties"]
    for field in (
        "default_summary_template_key",
        "default_summary_template_id",
        "default_summary_template_version",
        "fk_workspaces_default_summary_template",
    ):
        assert field in migration
