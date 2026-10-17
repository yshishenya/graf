"""Полный HTTP-бюджет детали F270/SC-003; PostgreSQL, без подмен чтения."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, literal, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_workspace_user,
    auth_headers_for,
    grant_meeting_to_user,
)
from twobrain_rec_server.cabinet import access, egress, queries
from twobrain_rec_server.cabinet.read_prefetch import (
    CabinetReadPrefetch,
    active_read_prefetch,
    install_read_prefetch,
)
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    ExternalIdentity,
    MediaRevision,
    Meeting,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingShareGrant,
    MeetingSpeakerName,
    MeetingSummarySlot,
    ProcessingResult,
    ProcessingWorkflow,
    SummaryTemplate,
    TranscriptSegment,
)


def _publish_summary(client, meeting_id, *, custom=False):
    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            key = "detail-budget-personal" if custom else "graf-auto-v1"
            template = None
            if custom:
                template = SummaryTemplate(
                    workspace_id=WORKSPACE_ID, owner_user_id=USER_ID, template_key=key,
                    kind="personal", name="Шаблон проверки детали", purpose="Synthetic test",
                    sections_json=[], output_language="ru", detail_level="standard",
                    version=1, status="active",
                )
                db.add(template)
                await db.flush()
            outcome = MeetingOutcomeSet(
                workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                media_revision_id=result.media_revision_id, processing_result_id=result.id,
                status="available", summary_state="available", source_kind="db_fixture",
                generator_kind="db_fixture", generator_version="detail-budget-test",
                source_result_hash=result.source_result_hash, source_fingerprint=f"result:{result.id}",
                content_hash="detail-budget-summary", template_key=key,
                template_id=template.id if template is not None else None,
                revision_state="accepted",
            )
            db.add(outcome)
            await db.flush()
            db.add_all([
                MeetingOutcomeItem(
                    workspace_id=WORKSPACE_ID, meeting_id=meeting_id, outcome_set_id=outcome.id,
                    category="summary", sequence=0, state="available", text="Синтетический итог проверки",
                    truth_label="supported",
                ),
                MeetingSummarySlot(
                    workspace_id=WORKSPACE_ID, meeting_id=meeting_id, template_key=key,
                    current_outcome_set_id=outcome.id, current_binding_class="verified_complete",
                    is_meeting_default=True, default_resolution_source="explicit_meeting",
                    default_resolution_version="detail-budget-test", default_resolved_at=datetime.now(UTC),
                ),
            ])
            await db.commit()
            return result.id
    return client.portal.call(seed)


def _detail_queries(client, path: str) -> tuple[int, object]:
    count = 0

    def executed(_conn, _cursor, _statement, _parameters, _context, _many):
        nonlocal count
        count += 1

    engine = client.app_state["engine"].sync_engine
    event.listen(engine, "before_cursor_execute", executed)
    try:
        response = client.get(path, headers=auth_headers())
    finally:
        event.remove(engine, "before_cursor_execute", executed)
    assert response.status_code == 200, path
    return count, response


@pytest.mark.parametrize("prefix", ["/meetings", "/desktop/meetings"])
def test_full_ready_detail_query_budget(client, prefix):
    seeds = seed_cabinet_meetings(client)
    path = f"{prefix}/{seeds.ready_id}"
    count, response = _detail_queries(client, path)
    assert SAFE_TRANSCRIPT_TEXT in response.text
    print(f"F270_DETAIL_BUDGET {prefix}: {count} SQL")
    assert count <= 25, f"{prefix}: полная деталь требует {count} SQL, предел SC-003 — 25"


@pytest.mark.parametrize("prefix", ["/meetings", "/desktop/meetings"])
@pytest.mark.parametrize("custom", [False, True])
def test_full_published_detail_query_budget(client, prefix, custom):
    seeds = seed_cabinet_meetings(client)
    _publish_summary(client, seeds.ready_id, custom=custom)
    count, response = _detail_queries(client, f"{prefix}/{seeds.ready_id}")
    assert "Синтетический итог проверки" in response.text
    if custom:
        assert "Шаблон проверки детали" in response.text
    print(f"F270_DETAIL_PUBLISHED {prefix} custom={custom}: {count} SQL")
    assert count <= 25, f"{prefix}: опубликованные итоги требуют {count} SQL, предел — 25"


@pytest.mark.parametrize("state", ["ready", "processing", "failed", "partial", "foreign", "no-revision", "no-result", "published", "custom", "missing-template"])
def test_detail_matches_original_reads(client, monkeypatch, state):
    seeds = seed_cabinet_meetings(client)
    meeting_id = getattr(seeds, state + "_id", seeds.ready_id)
    suffix = ""
    if state in {"published", "custom", "missing-template"}:
        _publish_summary(client, meeting_id, custom=state == "custom")
        if state == "missing-template":
            suffix = "?summary_format=not-created"
    if state in {"no-revision", "no-result"}:
        async def remove_visibility():
            async with client.app_state["sessionmaker"]() as db:
                model = MediaRevision if state == "no-revision" else ProcessingResult
                row = await db.scalar(select(model).where(model.meeting_id == meeting_id))
                row.status = "pending" if state == "no-revision" else "failed"
                await db.commit()
        client.portal.call(remove_visibility)
    path = f"/api/v1/cabinet/meetings/{meeting_id}{suffix}"
    headers = {**auth_headers(), "X-Request-ID": str(uuid4())}
    actual = client.get(path, headers=headers)

    async def original_reads(*_args, **_kwargs):
        return None

    monkeypatch.setattr(queries, "_prefetch_meeting_review_reads", original_reads)
    expected = client.get(path, headers=headers)
    assert actual.status_code == expected.status_code
    assert actual.json() == expected.json()


@pytest.mark.parametrize("prefix", ["/meetings", "/desktop/meetings"])
def test_detail_budget_catches_extra_sql(client, monkeypatch, prefix):
    original = queries._prefetch_meeting_review_reads
    async def repeated_reads(db, **kwargs):
        value = await original(db, **kwargs)
        await db.scalar(select(literal(1)))
        await db.scalar(select(literal(1)))
        return value
    monkeypatch.setattr(queries, "_prefetch_meeting_review_reads", repeated_reads)
    with pytest.raises(AssertionError, match="полная деталь требует 26 SQL"):
        test_full_ready_detail_query_budget(client, prefix)


@pytest.mark.parametrize("prefix", ["/meetings", "/desktop/meetings"])
def test_detail_query_count_does_not_grow_with_history(client, prefix):
    meeting_id = seed_cabinet_meetings(client).ready_id
    async def grow(start, stop):
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.scalar(select(MediaRevision).where(MediaRevision.meeting_id == meeting_id))
            revision.revision_number = 100
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            result.segment_count = result.diarization_segment_count = stop + 1
            for index in range(start, stop):
                old = MediaRevision(
                    workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                    local_media_revision_id=f"budget-history-{index}", revision_number=index + 2,
                    status="accepted", immutable=True,
                )
                db.add(old)
                await db.flush()
                workflow = ProcessingWorkflow(
                    workspace_id=WORKSPACE_ID, meeting_id=meeting_id, media_revision_id=old.id,
                    workflow_id=f"budget-history-{uuid4()}", status="processed", attempt_ordinal=1,
                )
                db.add(workflow)
                await db.flush()
                db.add_all([
                    ProcessingResult(
                        workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                        media_revision_id=old.id, processing_workflow_id=workflow.id,
                        mediascribe_job_id=result.mediascribe_job_id, result_version=index + 10,
                        status="imported", transcript_status="available", diarization_status="available",
                        segment_count=1, diarization_segment_count=1,
                    ),
                    TranscriptSegment(
                        workspace_id=WORKSPACE_ID, meeting_id=meeting_id, processing_result_id=result.id,
                        sequence=index + 2, start_seconds=index + 30, end_seconds=index + 31,
                        text=f"Budget segment {index}", source_role="mixed",
                    ),
                    DiarizationSegment(
                        workspace_id=WORKSPACE_ID, meeting_id=meeting_id, processing_result_id=result.id,
                        sequence=index + 2, start_seconds=index + 30, end_seconds=index + 31,
                        text=f"Budget segment {index}", source_role="mixed", speaker_label=f"Budget {index}",
                    ),
                    MeetingSpeakerName(
                        workspace_id=WORKSPACE_ID, meeting_id=meeting_id, speaker_key=f"Budget {index}",
                        display_name=f"Budget name {index}", updated_by_user_id=USER_ID,
                    ),
                ])
            await db.commit()
    client.portal.call(grow, 0, 5)
    small, _ = _detail_queries(client, f"{prefix}/{meeting_id}")
    client.portal.call(grow, 5, 50)
    large, response = _detail_queries(client, f"{prefix}/{meeting_id}")
    assert "Budget segment 49" in response.text
    assert large == small <= 25, f"{prefix}: 5→50 связей: {small}→{large} SQL"
    print(f"F270_DETAIL_HISTORY {prefix}: 5={small} 50={large}")


def test_detail_scope_restores_parent_after_nested_read_and_exception(client, monkeypatch):
    meeting_id = seed_cabinet_meetings(client).ready_id
    original = queries._prefetch_meeting_review_reads
    nested = False
    async def with_nested_read(db, **kwargs):
        nonlocal nested
        current = await original(db, **kwargs)
        if not nested:
            nested = True
            await queries.get_cabinet_meeting_review(db, workspace_id=WORKSPACE_ID,
                                                    meeting_id=meeting_id, viewer_user_id=USER_ID)
            assert active_read_prefetch(db) is current
        return current
    async def scenario():
        async with client.app_state["sessionmaker"]() as db:
            parent = CabinetReadPrefetch(workspace_id=uuid4(), viewer_user_id=uuid4())
            install_read_prefetch(db, parent)
            monkeypatch.setattr(queries, "_prefetch_meeting_review_reads", with_nested_read)
            result = await queries.get_cabinet_meeting_review(db, workspace_id=WORKSPACE_ID,
                                                             meeting_id=meeting_id, viewer_user_id=USER_ID)
            assert result is not None and nested
            assert active_read_prefetch(db) is parent
            async def failing(db, **kwargs):
                await original(db, **kwargs)
                raise RuntimeError("synthetic detail failure")
            monkeypatch.setattr(queries, "_prefetch_meeting_review_reads", failing)
            with pytest.raises(RuntimeError, match="synthetic detail failure"):
                await queries.get_cabinet_meeting_review(db, workspace_id=WORKSPACE_ID,
                                                         meeting_id=meeting_id, viewer_user_id=USER_ID)
            assert active_read_prefetch(db) is parent
    client.portal.call(scenario)


def test_detail_recipient_identity_is_read_again_after_revocation(client):
    meeting_id = seed_cabinet_meetings(client).ready_id
    add_workspace_user(client)
    grant_meeting_to_user(client, meeting_id)
    async def scenario():
        async with client.app_state["sessionmaker"]() as db:
            identity = ExternalIdentity(user_id=SHARED_USER_ID, provider="yandex",
                                        provider_subject="detail-budget-recipient", email="detail@example.test",
                                        is_verified=True, is_active=True)
            db.add(identity)
            grant = await db.scalar(select(MeetingShareGrant).where(MeetingShareGrant.meeting_id == meeting_id))
            grant.metadata_json = {"source": "accepted_external_invitation",
                                   "recipient_address_hash": next(iter(access.invitation_address_hashes(identity.email)))}
            await db.flush()
            prefetch = CabinetReadPrefetch(workspace_id=WORKSPACE_ID, viewer_user_id=SHARED_USER_ID,
                                          cache_access=False)
            install_read_prefetch(db, prefetch)
            assert await access._share_grant_recipient_is_valid(db, grant=grant, viewer_user_id=SHARED_USER_ID)
            identity.is_verified = False
            await db.flush()
            assert not await access._share_grant_recipient_is_valid(db, grant=grant, viewer_user_id=SHARED_USER_ID)
            assert prefetch.viewer_verified_emails == {}
    client.portal.call(scenario)


def test_latest_and_effective_keep_different_result_order(client):
    meeting_id = seed_cabinet_meetings(client).ready_id
    async def scenario():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            first = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            first.imported_at = datetime(2026, 10, 16, 12, tzinfo=UTC)
            second = ProcessingResult(
                workspace_id=WORKSPACE_ID, meeting_id=meeting_id, media_revision_id=first.media_revision_id,
                processing_workflow_id=first.processing_workflow_id, mediascribe_job_id=first.mediascribe_job_id,
                result_version=first.result_version + 1, status="imported", transcript_status="available",
                diarization_status="available", segment_count=1, diarization_segment_count=1,
                imported_at=first.imported_at - timedelta(hours=1),
            )
            db.add(second)
            await db.flush()
            assert (await queries._latest_result(db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                                                 media_revision_id=first.media_revision_id)).id == first.id
            assert (await egress._effective_complete_result(db, meeting=meeting)).id == second.id
            with queries._meeting_review_read_scope(db):
                await queries._prefetch_meeting_review_reads(db, meeting=meeting, viewer_user_id=USER_ID,
                                                             selected_summary_template_key=None, source_result_id=None)
                assert (await queries._latest_result(db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                                                     media_revision_id=first.media_revision_id)).id == first.id
                assert (await egress._effective_complete_result(db, meeting=meeting)).id == second.id
    client.portal.call(scenario)


@pytest.mark.parametrize("state", ["member", "full", "summary-only", "revoked", "expired", "workspace-plus-user", "deleted"])
def test_shared_detail_matches_original_reads(client, monkeypatch, state):
    meeting_id = seed_cabinet_meetings(client).ready_id
    add_workspace_user(client)
    if state != "member":
        grant_meeting_to_user(client, meeting_id)

    async def configure():
        async with client.app_state["sessionmaker"]() as db:
            grant = await db.scalar(select(MeetingShareGrant).where(MeetingShareGrant.meeting_id == meeting_id))
            if state == "summary-only":
                grant.content_scope = "summary_only"
                grant.can_download = grant.can_export = False
            elif state == "revoked":
                grant.status = "revoked"
            elif state == "expired":
                grant.expires_at = datetime.now(UTC) - timedelta(days=1)
            elif state == "workspace-plus-user":
                db.add(MeetingShareGrant(
                    workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                    grant_type="workspace", audience_type="workspace", audience_id=WORKSPACE_ID,
                    content_scope="summary_only", status="active", created_by_user_id=USER_ID,
                ))
            elif state == "deleted":
                meeting = await db.get(Meeting, meeting_id)
                meeting.deletion_state = "deleting"
            await db.commit()
    client.portal.call(configure)
    path = f"/api/v1/cabinet/meetings/{meeting_id}"
    headers = {**auth_headers_for(), "X-Request-ID": str(uuid4())}
    actual = client.get(path, headers=headers)
    async def original_reads(*_args, **_kwargs):
        return None
    monkeypatch.setattr(queries, "_prefetch_meeting_review_reads", original_reads)
    expected = client.get(path, headers=headers)
    assert actual.status_code == expected.status_code
    assert actual.json() == expected.json()


@pytest.mark.parametrize("state", ["available", "failed", "candidate", "legacy"])
def test_detail_prefetch_preserves_outcome_resolver_flags(client, state):
    meeting_id = seed_cabinet_meetings(client).ready_id
    result_id = _publish_summary(client, meeting_id)

    async def scenario():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            outcome = await db.scalar(select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == meeting_id))
            slot = await db.scalar(select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id))
            if state == "failed":
                outcome.status = "failed"
            elif state == "candidate":
                outcome.revision_state = "candidate"
            elif state == "legacy":
                slot.current_binding_class = "migrated_legacy_read_only"
                slot.legacy_migration_proof_hash = "a" * 64
            await db.flush()

            async def resolutions():
                values = []
                for key in (None, "graf-auto-v1", "missing"):
                    for include in (False, True):
                        for legacy in (False, True):
                            for source in (None, result_id, uuid4()):
                                resolved = await egress.current_outcome_set(
                                    db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                                    processing_result_id=source, template_key=key,
                                    include_non_publishable=include, allow_legacy_read_only=legacy,
                                )
                                values.append(resolved.id if resolved is not None else None)
                return values

            expected = await resolutions()
            with queries._meeting_review_read_scope(db):
                await queries._prefetch_meeting_review_reads(
                    db, meeting=meeting, viewer_user_id=USER_ID,
                    selected_summary_template_key="graf-auto-v1", source_result_id=None,
                )
                assert await resolutions() == expected
            assert (any(expected)) == (state != "candidate")
    client.portal.call(scenario)


@pytest.mark.parametrize("change", ["revoked", "deleted"])
def test_detail_second_read_observes_access_change_in_same_session(client, change):
    meeting_id = seed_cabinet_meetings(client).ready_id
    add_workspace_user(client)
    grant_meeting_to_user(client, meeting_id)

    async def scenario():
        async with client.app_state["sessionmaker"]() as db:
            before = await queries.get_cabinet_meeting_review(
                db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id, viewer_user_id=SHARED_USER_ID,
            )
            assert before is not None
            assert active_read_prefetch(db) is None
            if change == "revoked":
                row = await db.scalar(select(MeetingShareGrant).where(MeetingShareGrant.meeting_id == meeting_id))
                row.status = "revoked"
            else:
                row = await db.get(Meeting, meeting_id)
                row.deletion_state = "deleting"
            await db.flush()
            after = await queries.get_cabinet_meeting_review(
                db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id, viewer_user_id=SHARED_USER_ID,
            )
            assert after is None
            assert active_read_prefetch(db) is None
    client.portal.call(scenario)


def test_detail_source_and_selected_template_match_original_helper(client, monkeypatch):
    meeting_id = seed_cabinet_meetings(client).ready_id
    source_id = _publish_summary(client, meeting_id, custom=True)

    async def original_reads(*_args, **_kwargs):
        return None

    async def scenario():
        async with client.app_state["sessionmaker"]() as db:
            args = dict(workspace_id=WORKSPACE_ID, meeting_id=meeting_id, viewer_user_id=USER_ID,
                        selected_summary_template_key="detail-budget-personal", source_result_id=source_id)
            actual = await queries.get_cabinet_meeting_review(db, **args)
            monkeypatch.setattr(queries, "_prefetch_meeting_review_reads", original_reads)
            expected = await queries.get_cabinet_meeting_review(db, **args)
            assert actual is not None and expected is not None
            assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
    client.portal.call(scenario)
