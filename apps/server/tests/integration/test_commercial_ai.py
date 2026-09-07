"""AI admissions obey assigned rights under the actual application DB role."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.integration.test_commercial_egress import _deny
from tests.integration.test_commercial_egress import commercial as commercial
from twobrain_rec_server.billing.admin_grants import revoke_adjustment
from twobrain_rec_server.db.models import (
    DispatchIntent,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingSummarySlot,
)
from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context
from twobrain_rec_server.outcomes.ai_service import ensure_automatic_summary_candidate

pytestmark = pytest.mark.strict_rls


async def _worker_context(db):
    await apply_tenant_context(db, TenantDatabaseContext(organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID, context_kind="worker"))


async def _state(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        return (
            meeting.current_outcome_set_id,
            [(r.id, r.current_outcome_set_id) for r in await db.scalars(
                select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id).order_by(MeetingSummarySlot.id))],
            [(r.id, r.status) for r in await db.scalars(
                select(MeetingOutcomeGenerationAttempt).where(MeetingOutcomeGenerationAttempt.meeting_id == meeting_id).order_by(MeetingOutcomeGenerationAttempt.id))],
            [(r.id, r.state) for r in await db.scalars(
                select(DispatchIntent).where(DispatchIntent.meeting_id == meeting_id).order_by(DispatchIntent.id))],
        )


@pytest.mark.parametrize("feature", ["ai_summary", "ai_outcomes"])
@pytest.mark.parametrize("subject", [None, USER_ID])
def test_ai_denies_all_new_entrypoints_without_mutating_saved_results(commercial, feature, subject):
    client, meeting = commercial
    client.app.state.settings.outcome_generation_enabled = True
    adjustment = client.portal.call(lambda: _deny(client, feature, subject=subject))
    before = client.portal.call(lambda: _state(client, meeting))
    base = f"/api/v1/cabinet/meetings/{meeting}"
    payload = {"template_key": "graf-meeting-minutes-v1", "template_version": 1}
    for path, body in [
        ("/summary-candidates", payload),
        ("/summaries/graf-meeting-minutes-v1/ensure", {"idempotency_key": str(uuid4())}),
        ("/summaries/graf-meeting-minutes-v1/refresh", {"idempotency_key": str(uuid4()), "template_version": 1}),
    ]:
        response = client.post(base + path, headers=auth_headers(), json=body)
        assert response.status_code == 403, response.text
        assert response.json()["code"] == "commercial_ai_generation_denied"

    async def automatic():
        async with client.app.state.db_sessionmaker() as db:
            await _worker_context(db)
            result = await ensure_automatic_summary_candidate(db, workspace_id=WORKSPACE_ID, meeting_id=meeting)
            await db.commit()  # A denied admission must not leave side effects even if caller commits.
            return result
    assert client.portal.call(automatic) is None
    assert client.portal.call(lambda: _state(client, meeting)) == before
    assert client.get(base + "/downloads/transcript", headers=auth_headers()).status_code == 200

    async def revoke():
        async with client.app_state["sessionmaker"]() as db:
            await revoke_adjustment(db, workspace_id=WORKSPACE_ID, adjustment_id=adjustment,
                source_kind="migration", source_ref=f"synthetic:{uuid4()}", reason="Synthetic AI restore")
            await db.commit()
    client.portal.call(revoke)
    response = client.post(base + "/summary-candidates", headers=auth_headers(), json=payload)
    assert response.status_code == 202, response.text
    assert client.portal.call(lambda: _state(client, meeting)) != before


def test_ai_restriction_preserves_admitted_candidate_and_worker_snapshot(commercial):
    from twobrain_rec_server.outcomes.ai_service import snapshot_candidate_transcript

    client, meeting = commercial
    client.app.state.settings.outcome_generation_enabled = True
    base = f"/api/v1/cabinet/meetings/{meeting}"
    response = client.post(base + "/summary-candidates", headers=auth_headers(), json={
        "template_key": "graf-meeting-minutes-v1", "template_version": 1,
    })
    assert response.status_code == 202, response.text
    before = client.portal.call(lambda: _state(client, meeting))
    client.portal.call(lambda: _deny(client, "ai_summary", subject=USER_ID))
    replay = client.post(base + "/summary-candidates", headers=auth_headers(), json={
        "template_key": "graf-meeting-minutes-v1", "template_version": 1,
    })
    assert replay.status_code == 202, replay.text
    assert replay.json()["candidate_id"] == response.json()["candidate_id"]

    async def snapshot():
        async with client.app_state["sessionmaker"]() as db:
            candidate = await db.scalar(select(MeetingOutcomeGenerationAttempt.candidate_id).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting,
                MeetingOutcomeGenerationAttempt.candidate_id.is_not(None)))
        assert candidate is not None
        metadata, chunks = await snapshot_candidate_transcript(client.app.state.db_sessionmaker,
            workspace_id=WORKSPACE_ID, candidate_id=candidate, settings=client.app.state.settings)
        assert metadata["snapshot_hash"] and chunks
    client.portal.call(snapshot)
    assert client.portal.call(lambda: _state(client, meeting)) == before
    assert client.get(base + "/summary-candidates", headers=auth_headers()).status_code == 200
    denied = client.post(base + "/summary-candidates", headers=auth_headers(), json={
        "template_key": "graf-meeting-minutes-v1", "template_version": 1,
        "request_intent": "manual_refresh", "request_intent_id": str(uuid4()),
    })
    assert denied.status_code == 403
    assert denied.json()["code"] == "commercial_ai_generation_denied"


def test_ai_catalog_failure_is_safe_and_does_not_create_automatic_work(commercial, monkeypatch):
    from twobrain_rec_server.billing.catalog import CatalogNotApproved
    from twobrain_rec_server.outcomes import ai_service

    client, meeting = commercial
    client.app.state.settings.outcome_generation_enabled = True
    async def unavailable(*args, **kwargs):
        raise CatalogNotApproved("synthetic-private-error-must-not-escape")
    monkeypatch.setattr(ai_service, "resolve_entitlements", unavailable)
    before = client.portal.call(lambda: _state(client, meeting))
    response = client.post(f"/api/v1/cabinet/meetings/{meeting}/summary-candidates",
        headers=auth_headers(), json={"template_key": "graf-meeting-minutes-v1", "template_version": 1})
    assert response.status_code == 503
    assert response.json()["code"] == "billing_access_unavailable"
    assert "synthetic-private-error" not in response.text
    async def automatic():
        async with client.app.state.db_sessionmaker() as db:
            await _worker_context(db)
            assert await ensure_automatic_summary_candidate(db, workspace_id=WORKSPACE_ID, meeting_id=meeting) is None
            await db.commit()
    client.portal.call(automatic)
    assert client.portal.call(lambda: _state(client, meeting)) == before


def test_ai_admission_waits_for_rights_change_before_taking_meeting_lock(commercial):
    import asyncio
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import text

    from twobrain_rec_server.billing.admin_grants import create_adjustment
    from twobrain_rec_server.db.models import Workspace
    from twobrain_rec_server.outcomes.ai_service import (
        OutcomeGenerationTerminalError,
        create_summary_candidate,
    )

    client, meeting = commercial
    before = client.portal.call(lambda: _state(client, meeting))
    async def race():
        async with client.app_state["sessionmaker"]() as writer:
            await writer.execute(text("set local lock_timeout='1s'"))
            await writer.scalar(select(Workspace.id).where(Workspace.id == WORKSPACE_ID).with_for_update())
            async def admission():
                async with client.app.state.db_sessionmaker() as worker:
                    await _worker_context(worker)
                    return await create_summary_candidate(worker, workspace_id=WORKSPACE_ID,
                        meeting_id=meeting, requested_by_user_id=USER_ID, template_key="graf-meeting-minutes-v1",
                        template_id=None, template_version=1, expected_current_outcome_set_id=None)
            task = asyncio.create_task(admission())
            try:
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(asyncio.shield(task), timeout=0.15)
                assert await writer.scalar(select(Meeting.id).where(Meeting.id == meeting).with_for_update()) == meeting
                now = datetime.now(UTC)
                await create_adjustment(writer, workspace_id=WORKSPACE_ID, subject_user_id=USER_ID,
                    kind="deny", feature_key="ai_summary", value=False, unit="boolean",
                    starts_at=now-timedelta(seconds=1), ends_at=now+timedelta(days=1),
                    source_kind="migration", source_ref=f"synthetic:{uuid4()}", reason="Synthetic concurrent restriction")
                await writer.commit()
                with pytest.raises(OutcomeGenerationTerminalError, match="^commercial_ai_generation_denied$"):
                    await asyncio.wait_for(task, timeout=3)
            finally:
                await writer.rollback()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    client.portal.call(race)
    assert client.portal.call(lambda: _state(client, meeting)) == before


def test_browser_ai_denial_keeps_detail_but_auth_failures_still_clear_it():
    import re
    import subprocess
    from pathlib import Path

    script = (Path(__file__).resolve().parents[2] / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js").read_text()
    names = ["accessLossProblemCodes", "detailActionProblemCodes", "summaryActionProblemCodes",
             "authorizationRecoveryKind", "responseProblemCode", "recoverMeetingDetailFromResponse"]
    sections = []
    for name in names:
        match = re.search(r"  const " + name + r" = [\s\S]*?\n  (?:};|\]\);)", script)
        assert match is not None, name
        sections.append(match.group())
    harness = """
const assert = require('node:assert/strict');
const location = {pathname:'/meetings/synthetic'};
const document = {querySelector:()=>({}),body:{dataset:{}}};
const window = {location:{href:'http://localhost/meetings/synthetic'}};
let recovered = 0;
const renderMeetingDetailRecovery = () => { recovered++; };
""" + "\n".join(sections) + """
(async () => {
  for (const [status,code,expected] of [
    [403,'commercial_ai_generation_denied',false],
    [403,'device_revoked',true], [403,'unknown_denial',true],
    [401,'auth_session_invalid',true], [404,'meeting_not_found',true],
  ]) {
    const before = recovered;
    const result = await recoverMeetingDetailFromResponse(new Response(JSON.stringify({code}),{status}),
      {actionProblemCodes:summaryActionProblemCodes});
    assert.equal(result,expected,code);
    assert.equal(recovered-before,expected ? 1 : 0,code);
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run(["node", "-e", harness], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
