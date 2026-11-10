"""F292: real public-reader boundaries, legacy compatibility and audience transitions."""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from html import unescape
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import PERSONAL_WORKSPACE_ID, WORKSPACE_ID
from tests.fixtures.artifacts import track_descriptor
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_retained_playback_m4a,
    add_workspace_user,
    set_artifact_policy,
)
from tests.fixtures.processing import apply_job_worker_scope
from tests.integration.test_playback_normalization_media_matrix import _pipeline, _run_ffmpeg
from tests.integration.test_summary_sharing import prepare
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaRevision,
    MediaScribeJob,
    Meeting,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingShareGrant,
    MeetingShareInvitation,
    MeetingSummarySlot,
    PlaybackNormalizationJob,
    ProcessingResult,
    ProcessingWorkflow,
    TrackArtifact,
    TranscriptSegment,
)
from twobrain_rec_server.normalization.service import run_normalization_job


def publish(client, meeting, template, scope="full_meeting"):
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/link",
        headers=auth_headers(),
        json={"template_key": template, "content_scope": scope},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return data, data["share_url"].split("https://graf.example.test")[-1]


def test_full_reader_keeps_required_json_date_when_recording_time_is_unknown(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    created = datetime(2026, 7, 10, 13, 25, tzinfo=UTC)

    async def remove_recording_time():
        async with client.app.state.db_sessionmaker() as db:
            row = await db.get(Meeting, meeting)
            row.started_at = None
            row.created_at = created
            await db.commit()

    asyncio.run(remove_recording_time())
    _, path = publish(client, meeting, template)
    html = client.get(path, headers={"Accept": "text/html"})
    assert html.status_code == 200
    assert "data-user-datetime" not in html.text
    response = client.get(path, headers={"Accept": "application/json"})
    assert response.status_code == 200, response.text
    assert datetime.fromisoformat(response.json()["occurred_at"]) == created


def test_full_reader_and_explicit_scope_preserve_legacy(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    add_retained_playback_m4a(client, UUID(str(meeting)), b"synthetic-audio")
    link, path = publish(client, meeting, template, "summary_only")
    again, _ = publish(client, meeting, template)
    assert again == link  # Copy cannot silently widen a previously published document.
    assert "transcript" not in client.get(path).json()
    changed = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/link/scope",
        headers=auth_headers(),
        json={
            "grant_id": link["grant_id"],
            "expected_version": link["version"],
            "template_key": template,
            "content_scope": "full_meeting",
        },
    )
    assert changed.status_code == 200, changed.text
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert SAFE_TRANSCRIPT_TEXT in str(response.json()["transcript"])
    assert set(response.json()) == {
        "meeting_label",
        "occurred_at",
        "duration_seconds",
        "summary_sections",
        "protocol",
        "transcript",
        "speakers",
        "media_version",
        "playback_available",
        "summary_source_stale",
    }
    full = response.json()
    keys = {speaker["speaker_key"] for speaker in full["speakers"]}
    assert keys and all(key.startswith("speaker-") for key in keys)
    assert all(turn["speaker_key"] in keys for turn in full["transcript"])
    assert all(set(speaker) == {"speaker_key", "label", "confirmed", "talk_time_percent", "segments"}
               for speaker in full["speakers"])
    html = client.get(path, headers={"Accept": "text/html"})
    assert html.text.count("data-playback-shell") == 1
    assert html.text.count("data-timeline-track") == len(keys)
    assert "data-comments-url" not in html.text
    assert "data-processing-result-id" not in html.text
    assert "data-public-sharing" in html.text and "data-public-transcript" in html.text
    assert "data-public-welcome" in html.text and "Начать пользоваться GRAF" in html.text
    assert html.headers["referrer-policy"] == "no-referrer"
    assert html.headers["cache-control"] == "private, no-store"
    stale = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/link/scope",
        headers=auth_headers(),
        json={
            "grant_id": link["grant_id"],
            "expected_version": link["version"],
            "content_scope": "summary_only",
            "template_key": template,
        },
    )
    assert stale.status_code == 409


def test_public_playback_ranges_revoke_and_media_fence(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    body = b"x" * (4 * 1024 * 1024 + 17)
    add_retained_playback_m4a(client, UUID(str(meeting)), body)
    link, path = publish(client, meeting, template)
    version = client.get(path).json()["media_version"]
    audio = path.replace("?", "/playback?") + "&media_version=" + version
    response = client.get(audio)
    assert response.status_code == 200, response.text[:100]
    assert response.content == body
    partial = client.get(audio, headers={"Range": "bytes=3-19"})
    assert partial.status_code == 206 and partial.content == body[3:20]
    assert partial.headers["content-range"] == f"bytes 3-19/{len(body)}"
    assert client.get(audio, headers={"Range": f"bytes={len(body)}-"}).status_code == 416
    assert client.get(audio.replace(version, "0" * 24)).status_code == 409
    revoked = client.request(
        "DELETE",
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/link",
        headers=auth_headers(),
        json={"grant_id": link["grant_id"], "expected_version": link["version"]},
    )
    assert revoked.status_code == 200
    assert client.get(audio, headers={"Range": "bytes=0-3"}).status_code == 404
    assert client.get(path).status_code == 404


def test_public_playback_uses_the_versioned_revision_before_outcomes(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    async def align_fixture_duration():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(Meeting, meeting)
            row.duration_seconds = 60
            await db.commit()

    asyncio.run(align_fixture_duration())
    original_bytes = add_retained_playback_m4a(client, meeting, b"synthetic-original")
    _, path = publish(client, meeting, template)
    original = client.get(path).json()
    version_a = original["media_version"]
    assert original["playback_available"] and original["transcript"]
    assert original["summary_sections"] or original["protocol"]
    playback = path.replace("?", "/playback?") + "&media_version="
    assert client.get(playback + version_a).content == original_bytes

    def assert_blocked(version, code):
        for headers in ({}, {"Range": "bytes=0-7"}):
            response = client.get(playback + version, headers=headers)
            assert response.status_code == 409 and response.json()["code"] == code
            assert "content-range" not in response.headers
            assert response.headers["content-type"] != "audio/mp4"

    def assert_playback(version, expected):
        response = client.get(playback + version)
        assert response.status_code == 200 and response.content == expected
        response = client.get(playback + version, headers={"Range": "bytes=32-95"})
        assert response.status_code == 206 and response.content == expected[32:96]
        assert response.headers["content-range"] == f"bytes 32-95/{len(expected)}"

    session = client.post(
        f"/api/v1/meetings/{meeting}/media-revisions/upload-sessions",
        headers=auth_headers(),
        json={
            "local_media_revision_id": "f292-t004-synthetic-b",
            "source_kind": "reprocess",
            "duration_seconds": 60,
            "expected_tracks": ["manifest", "media"],
        },
    )
    assert session.status_code == 202, (session.status_code, session.json().get("code"))
    session_id = session.json()["upload_session"]["session_id"]
    replacement_audio = tmp_path / "replacement.wav"
    _run_ffmpeg(["-f", "lavfi", "-i", "sine=frequency=660:sample_rate=16000:duration=60",
                 "-c:a", "pcm_s16le", str(replacement_audio)])
    tracks = []
    for role, data in {
        "manifest": b"{}",
        "media": replacement_audio.read_bytes(),
    }.items():
        upload = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": sha256(data).hexdigest()},
            content=data,
        )
        assert upload.status_code == 200, (role, upload.status_code)
        tracks.append(track_descriptor(role, data=data, duration_seconds=60))
    accepted = client.post(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks, "archive_audio": True},
    )
    assert accepted.status_code == 200, (accepted.status_code, accepted.json().get("code"))
    revision_b = accepted.json()["meeting"]["media_revision"]
    assert revision_b["revision_number"] == 2 and revision_b["status"] == "accepted"

    pending = client.get(path).json()
    version_b = pending["media_version"]
    assert version_b != version_a
    assert_blocked(version_a, "shared_media_changed")
    assert_blocked(version_b, "playback_unavailable")
    assert not pending["playback_available"] and not pending["transcript"] and not pending["speakers"]
    assert "data-playback-shell" not in client.get(path, headers={"Accept": "text/html"}).text

    async def normalize_replacement():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob)
                .join(MediaRevision, MediaRevision.id == PlaybackNormalizationJob.media_revision_id)
                .where(MediaRevision.meeting_id == UUID(str(meeting)), MediaRevision.revision_number == 2)
            )
            assert job is not None and job.planned_action == "normalize_source"
            await apply_job_worker_scope(db, job)
            return await run_normalization_job(
                db=db, storage=client.app_state["storage"], job_id=job.id,
                work_directory=tmp_path, pipeline=_pipeline(),
            )

    execution = asyncio.run(normalize_replacement())
    assert execution.derivation_kind == "single_source_transcode"

    async def published_artifact():
        async with client.app_state["sessionmaker"]() as db:
            canonical = await db.get(TrackArtifact, execution.canonical_track_artifact_id)
            revision = await db.get(MediaRevision, canonical.media_revision_id)
            assert revision.revision_number == 2 and revision.status == "accepted"
            assert canonical.status == "stored" and canonical.validated_at is not None
            assert canonical.derivation_kind == "single_source_transcode"
            assert canonical.duration_seconds == 60
            body = client.app_state["storage"].get_bytes(canonical.storage_object_key)
            assert body[4:8] == b"ftyp" and body != original_bytes
            assert sha256(body).hexdigest() == canonical.sha256
            return body
    replacement_bytes = asyncio.run(published_artifact())
    ready = client.get(path).json()
    assert ready["media_version"] == version_b and ready["playback_available"]
    assert not ready["transcript"] and not ready["speakers"]
    assert_playback(version_b, replacement_bytes)

    async def seed_result_and_outcomes():
        # This fixture defines the state after publication; it does not test publication writers.
        async with client.app_state["sessionmaker"]() as db:
            canonical = await db.get(TrackArtifact, execution.canonical_track_artifact_id)
            common = {"workspace_id": canonical.workspace_id, "meeting_id": meeting,
                      "media_revision_id": canonical.media_revision_id}
            input_media = await db.scalar(select(TrackArtifact).filter_by(**common, track_role="media"))
            workflow = ProcessingWorkflow(**common, workflow_id="synthetic-published-replacement",
                                          status="processed", attempt_ordinal=1)
            db.add(workflow)
            await db.flush()
            job = MediaScribeJob(**common, processing_workflow_id=workflow.id,
                                 external_job_id="fixture-replacement-job", status="ready",
                                 request_mode="single_track", source_track_artifact_id=input_media.id)
            db.add(job)
            await db.flush()
            result = ProcessingResult(**common, mediascribe_job_id=job.id, processing_workflow_id=workflow.id,
                                      status="imported", transcript_status="available", diarization_status="available",
                                      segment_count=1, diarization_segment_count=1, language="ru",
                                      source_result_hash="synthetic-replacement-result", imported_at=datetime.now(UTC))
            db.add(result)
            await db.flush()
            segment = {"workspace_id": canonical.workspace_id, "meeting_id": meeting, "processing_result_id": result.id,
                       "sequence": 0, "start_seconds": Decimal("0"), "end_seconds": Decimal("1"),
                       "text": "Проверка новой версии.", "source_role": "mixed"}
            transcript = TranscriptSegment(**segment)
            db.add_all([transcript, DiarizationSegment(**segment, speaker_label="Speaker 1")])
            slot = await db.scalar(select(MeetingSummarySlot).filter_by(
                workspace_id=canonical.workspace_id, meeting_id=meeting, is_meeting_default=True,
            ))
            assert slot is not None
            outcome = MeetingOutcomeSet(**common, processing_result_id=result.id, status="available",
                summary_state="available", generator_version="synthetic-replacement",
                template_key=slot.template_key, template_version=1, revision_state="accepted",
                source_result_hash=result.source_result_hash, accepted_at=datetime.now(UTC))
            db.add(outcome)
            await db.flush()
            db.add(MeetingOutcomeItem(
                workspace_id=canonical.workspace_id, meeting_id=meeting, outcome_set_id=outcome.id,
                category="summary", sequence=0, state="available", text="Новый итог.",
                source_refs_json=[{"transcript_segment_id": str(transcript.id)}],
            ))
            await db.commit()
            return slot.id, outcome.id
    slot_id, outcome_id = asyncio.run(seed_result_and_outcomes())
    with_old_outcomes = client.get(path).json()
    version_result_b = with_old_outcomes["media_version"]
    assert version_result_b not in (version_a, version_b)
    assert with_old_outcomes["transcript"][0]["text"] == "Проверка новой версии."
    assert with_old_outcomes["summary_sections"] or with_old_outcomes["protocol"]
    assert with_old_outcomes["summary_source_stale"] is True
    old_outcomes_html = client.get(path, headers={"Accept": "text/html"}).text
    assert "По предыдущей версии расшифровки" in old_outcomes_html
    old_outcomes_panel = old_outcomes_html.split('id="outcomes"', 1)[1].split("</section>", 1)[0]
    assert "Сохранённый итог." in old_outcomes_panel and "data-public-seek" not in old_outcomes_panel
    assert "data-public-seek" in old_outcomes_html
    assert_blocked(version_b, "shared_media_changed")
    assert_playback(version_result_b, replacement_bytes)

    async def publish_outcomes():
        async with client.app_state["sessionmaker"]() as db:
            slot = await db.get(MeetingSummarySlot, slot_id)
            slot.current_outcome_set_id = outcome_id
            await db.commit()

    asyncio.run(publish_outcomes())
    aligned = client.get(path).json()
    assert aligned["media_version"] == version_result_b and aligned["summary_source_stale"] is False
    assert aligned["summary_sections"] == [
        {"category": "summary", "text": "Новый итог.", "sources": [{"start_ms": 0, "time": "0:00"}]},
    ]
    assert "По предыдущей версии расшифровки" not in client.get(
        path, headers={"Accept": "text/html"},
    ).text
    assert_playback(version_result_b, replacement_bytes)


@pytest.mark.parametrize(("first", "second"), [("workspace", "link"), ("link", "workspace")])
def test_audience_transitions_preserve_addressed_access(client, tmp_path, first, second):
    meeting, template = prepare(client, tmp_path)
    meeting_id = UUID(str(meeting))
    add_workspace_user(client)
    client.app.state.settings.share_workspace_audience_enabled = True
    expires_at = datetime.now(UTC) + timedelta(days=2)
    base = f"/api/v1/cabinet/meetings/{meeting_id}"
    addressed = client.post(
        base + "/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "full_meeting",
            "can_comment": True,
            "can_download": True,
            "can_export": False,
            "expires_at": expires_at.isoformat(),
        },
    )
    assert addressed.status_code == 201, addressed.text
    grant_id = UUID(addressed.json()["grant"]["grant_id"])

    async def seed_invitation():
        async with client.app_state["sessionmaker"]() as db:
            owner = await db.get(Meeting, meeting_id)
            invitation = MeetingShareInvitation(
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                invited_by_user_id=owner.created_by_user_id,
                normalized_address_hash="synthetic-f292-recipient",
                encrypted_delivery_address="synthetic-ciphertext",
                token_hash="synthetic-f292-invitation",
                status="pending",
                expires_at=expires_at,
            )
            db.add(invitation)
            await db.flush()
            invitation_id = invitation.id
            await db.commit()
            return invitation_id

    invitation_id = client.portal.call(seed_invitation)

    async def check(audience):
        async with client.app_state["sessionmaker"]() as db:
            grants = (await db.scalars(
                select(MeetingShareGrant).where(
                    MeetingShareGrant.meeting_id == meeting_id,
                    MeetingShareGrant.status == "active",
                )
            )).all()
            assert sorted(g.audience_type for g in grants) == (
                ["user"] if audience == "invite_only" else sorted([audience, "user"])
            )
            grant = next(g for g in grants if g.audience_type == "user")
            assert (grant.id, grant.audience_id) == (grant_id, SHARED_USER_ID)
            assert (grant.content_scope, grant.expires_at) == ("full_meeting", expires_at)
            assert (grant.can_comment, grant.can_edit, grant.can_download, grant.can_export) == (
                True, False, True, False,
            )
            invitation = await db.get(MeetingShareInvitation, invitation_id)
            assert invitation is not None and invitation.meeting_id == meeting_id
            assert (invitation.status, invitation.expires_at) == ("pending", expires_at)

    url = base + "/sharing/general-access"
    initial = client.get(url, headers=auth_headers())
    assert initial.status_code == 200
    state = initial.json()
    assert state["audience"] == "invite_only"
    client.portal.call(check, "invite_only")
    for audience in (first, second, "invite_only"):
        response = client.post(
            url,
            headers=auth_headers(),
            json={
                "audience": audience,
                "content_scope": "full_meeting",
                "template_key": template,
                "expected_fingerprint": state["fingerprint"],
            },
        )
        assert response.status_code == 200, response.text
        changed = response.json()
        assert changed["fingerprint"] != state["fingerprint"]
        state = changed
        if audience == first:
            stale = state["fingerprint"]
        assert state["audience"] == audience
        client.portal.call(check, audience)

    conflict = client.post(
        url,
        headers=auth_headers(),
        json={"audience": first, "expected_fingerprint": stale, "template_key": template},
    )
    assert conflict.status_code == 409
    client.portal.call(check, "invite_only")


def test_general_access_rejects_wrong_workspace_and_missing_cookie_csrf(client, tmp_path):
    from tests.integration.test_web_owner_session_context import (
        OWNER_REVIEW_TEST_TOKEN,
        _seed_owner_review_session,
    )
    from twobrain_rec_server.auth.csrf import issue_csrf_token
    from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME

    meeting, _ = prepare(client, tmp_path)
    client.app.state.settings.share_workspace_audience_enabled = True
    url = f"/api/v1/cabinet/meetings/{meeting}/sharing/general-access"
    session = client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    owner_view = client.get(url)
    assert owner_view.status_code == 200
    before = owner_view.json()
    assert before["audience"] == "invite_only"
    payload = {"audience": "workspace", "expected_fingerprint": before["fingerprint"]}
    assert client.post(url, json=payload).status_code == 403
    assert client.get(url).json() == before
    csrf = issue_csrf_token(session_id=session.id, secret=client.app.state.web_csrf_secret)
    updated = client.post(url, headers={"X-CSRF-Token": csrf}, json=payload)
    assert updated.status_code == 200 and updated.json()["audience"] == "workspace"
    client.cookies.clear()

    other_workspace = {**auth_headers(), "X-Workspace-Id": str(PERSONAL_WORKSPACE_ID)}
    payload = {"audience": "invite_only", "expected_fingerprint": updated.json()["fingerprint"]}
    assert client.get(url, headers=other_workspace).status_code in {403, 404}
    assert client.post(url, headers=other_workspace, json=payload).status_code in {403, 404}
    assert client.get(url, headers=auth_headers()).json() == updated.json()


def test_login_continuation_never_copies_share_secret_into_login_url(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    client.app.state.settings.env = "development"
    client.app.state.settings.local_http_auth_cookie_enabled = True
    _, path = publish(client, meeting, template)
    response = client.get(
        path.replace("?", "/continue?") + "&action=sign-in", follow_redirects=False
    )
    assert response.status_code == 303
    token = path.split("/public-shares/")[1].split("?")[0]
    assert token not in response.headers["location"]
    assert response.headers["location"].startswith("/login?next=")
    assert client.get(response.headers["location"]).status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    resumed = client.get("/shared-meeting/continue", follow_redirects=False)
    assert resumed.status_code == 303 and resumed.headers["location"] == path


def test_rotation_expiry_narrowing_and_legacy_writer_cannot_bypass_version(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    add_retained_playback_m4a(client, UUID(str(meeting)), b"audio")
    link, path = publish(client, meeting, template)
    version = client.get(path).json()["media_version"]
    audio = path.replace("?", "/playback?") + "&media_version=" + version
    base = f"/api/v1/cabinet/meetings/{meeting}"
    assert (
        client.post(base + f"/shares/{link['grant_id']}/rotate", headers=auth_headers()).status_code
        == 409
    )
    assert (
        client.delete(base + f"/shares/{link['grant_id']}", headers=auth_headers()).status_code
        == 409
    )
    rotated = client.post(
        base + "/summary-sharing/link/rotate",
        headers=auth_headers(),
        json={"grant_id": link["grant_id"], "expected_version": link["version"]},
    ).json()
    assert client.get(path).status_code == 404 and client.get(audio).status_code == 404
    current = rotated["share_url"].split("https://graf.example.test")[-1]
    narrowed = client.post(
        base + "/summary-sharing/link/scope",
        headers=auth_headers(),
        json={
            "grant_id": rotated["grant_id"],
            "expected_version": rotated["version"],
            "content_scope": "summary_only",
            "template_key": template,
        },
    )
    assert narrowed.status_code == 200, narrowed.text
    assert "transcript" not in client.get(current).json()
    assert (
        client.get(current.replace("?", "/playback?") + "&media_version=" + version).status_code
        == 404
    )

    async def expire():
        async with client.app_state["sessionmaker"]() as db:
            grant = await db.get(MeetingShareGrant, UUID(link["grant_id"]))
            grant.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    asyncio.run(expire())
    assert client.get(current).status_code == 404


def test_public_current_result_fence_and_anonymous_audit(client, tmp_path):
    from uuid import uuid4

    from twobrain_rec_server.db.models import Meeting, MeetingEgressAuditEvent

    meeting, template = prepare(client, tmp_path)
    add_retained_playback_m4a(client, UUID(str(meeting)), b"audio")
    link, path = publish(client, meeting, template)
    version = client.get(path).json()["media_version"]
    audio = path.replace("?", "/playback?") + "&media_version=" + version
    assert client.get(audio).status_code == 200

    async def replace():
        async with client.app_state["sessionmaker"]() as db:
            events = (
                await db.scalars(
                    select(MeetingEgressAuditEvent).where(
                        MeetingEgressAuditEvent.meeting_id == UUID(str(meeting)),
                        MeetingEgressAuditEvent.event_type == "playback_requested",
                    )
                )
            ).all()
            assert events and events[-1].actor_user_id is None and events[-1].device_id is None
            assert events[-1].metadata_json["share_grant_id"] == link["grant_id"]
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == UUID(str(meeting)))
            )
            result.status = "failed"
            await db.commit()

    asyncio.run(replace())
    assert client.get(path).json()["transcript"] == []
    assert client.get(audio).status_code == 409
    foreign = path.replace(str(WORKSPACE_ID), str(uuid4()))
    assert client.get(foreign).status_code == 404

    async def delete():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(Meeting, UUID(str(meeting)))
            row.deletion_state = "requested"
            await db.commit()

    asyncio.run(delete())
    assert client.get(path).status_code == 404


def test_continuation_tamper_expiry_and_invalid_context_are_safe(client, tmp_path):
    from cryptography.fernet import Fernet

    from twobrain_rec_server.cabinet.public_sharing import CONTINUATION_COOKIE

    meeting, template = prepare(client, tmp_path)
    _, path = publish(client, meeting, template)
    route = path.replace("?", "/continue?")
    assert (
        client.get(route + "&tab=outcomes&position_ms=10", follow_redirects=False).status_code
        == 422
    )
    position = "&tab=recording&position_ms=14000&media_version=" + "a" * 24
    settings = client.app.state.settings
    settings.env = "production"
    settings.local_http_auth_cookie_enabled = True
    assert client.base_url.scheme == "http"
    production = client.get(route + position, follow_redirects=False)
    assert production.status_code == 303
    assert production.headers["location"] == "/login?next=%2Fshared-meeting%2Fcontinue"
    flags = {part.strip().lower() for part in production.headers["set-cookie"].split(";")[1:]}
    assert {"secure", "httponly", "samesite=lax", "max-age=600"} <= flags
    client.cookies.clear()
    settings.env = "development"
    response = client.get(route + position, follow_redirects=False)
    assert response.status_code == 303
    assert "secure" not in {part.strip().lower() for part in response.headers["set-cookie"].split(";")[1:]}
    resumed = client.get("/shared-meeting/continue", follow_redirects=False)
    assert (
        resumed.headers["location"]
        == path + "&media_version=" + "a" * 24 + "#recording?position_ms=14000"
    )
    key = client.app.state.settings.credential_encryption_key_file.read_bytes()
    for candidate in [
        Fernet(key)
        .encrypt_at_time(path.encode(), int(datetime.now(UTC).timestamp()) - 601)
        .decode(),
        Fernet(key).encrypt(b"https://evil.example.test/").decode(),
        "tampered",
    ]:
        client.cookies.set(CONTINUATION_COOKIE, candidate)
        assert (
            client.get("/shared-meeting/continue", follow_redirects=False).headers["location"]
            == "/meetings"
        )


def test_public_stream_is_bounded_and_closes_on_size_mismatch():
    import pytest

    from twobrain_rec_server.cabinet.egress import ReviewAudioBuildError, _bounded_public_stream

    class Body:
        def __init__(self, chunks):
            self.chunks = chunks
            self.closed = False

        def __iter__(self):
            return iter(self.chunks)

        def close(self):
            self.closed = True

    body = Body([b"x" * 65536] * 80)
    chunks = list(_bounded_public_stream(body, expected_length=65536 * 80))
    assert (
        max(map(len, chunks)) <= 4 * 1024 * 1024
        and sum(map(len, chunks)) > 4 * 1024 * 1024
        and body.closed
    )
    for chunks, expected in [
        ([b"a"], 2),
        ([b"abc"], 2),
        ([b"x" * (4 * 1024 * 1024 + 1)], 4 * 1024 * 1024 + 1),
    ]:
        body = Body(chunks)
        with pytest.raises(ReviewAudioBuildError):
            list(_bounded_public_stream(body, expected_length=expected))
        assert body.closed


def test_full_link_without_summary_and_summary_html_never_embeds_recording(client, tmp_path):
    from tests.fixtures.cabinet import create_ready_meeting

    meeting, template = prepare(client, tmp_path)
    fresh = create_ready_meeting(client, "f292-without-summary")
    _, path = publish(client, fresh, template)
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert response.json()["summary_sections"] == []
    assert SAFE_TRANSCRIPT_TEXT in str(response.json()["transcript"])
    _, summary = publish(client, meeting, template, "summary_only")
    html = client.get(summary, headers={"Accept": "text/html"})
    assert html.status_code == 200, html.text
    assert "data-public-welcome" in html.text
    assert "data-public-transcript" not in html.text and "<audio" not in html.text
    assert SAFE_TRANSCRIPT_TEXT not in html.text


def test_personal_roles_and_scope_do_not_require_download_permission(client, tmp_path):
    from tests.fixtures.cabinet_access import auth_headers_for

    meeting, template = prepare(client, tmp_path)
    add_workspace_user(client)
    base = f"/api/v1/cabinet/meetings/{meeting}"
    response = client.post(
        base + "/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "summary_only",
        },
    )
    grant = response.json()["grant"]["grant_id"]
    version = response.json()["grant"]["version"]
    for role, scope in [
        ("editor", "full_meeting"),
        ("commenter", "full_meeting"),
        ("viewer", "full_meeting"),
        ("summary", "summary_only"),
    ]:
        changed = client.patch(
            base + f"/shares/{grant}/permissions",
            headers=auth_headers(),
            json={
                "expected_version": version,
                "content_scope": scope,
                "can_comment": role in ("editor", "commenter"),
                "can_edit": role == "editor",
            },
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["content_scope"] == scope
        stale = client.patch(base + f"/shares/{grant}/permissions", headers=auth_headers(),
            json={"expected_version":version,"can_comment":False,"can_edit":False})
        assert stale.status_code == 409
        stale_revoke = client.delete(base + f"/shares/{grant}?expected_version={version}", headers=auth_headers())
        assert stale_revoke.status_code == 409
        version = changed.json()["version"]
    denied = client.patch(
        base + f"/shares/{grant}/permissions",
        headers=auth_headers_for(user_id=SHARED_USER_ID),
        json={"content_scope": "full_meeting", "can_comment": True, "can_edit": True},
    )
    assert denied.status_code in (403, 404)


def test_legacy_visibility_and_disabled_audiences_are_truthful(client, tmp_path):
    from twobrain_rec_server.db.models import Meeting

    meeting, template = prepare(client, tmp_path)
    base = f"/api/v1/cabinet/meetings/{meeting}"

    async def visible():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(Meeting, UUID(str(meeting)))
            row.visibility = "team"
            await db.commit()

    asyncio.run(visible())
    state = client.get(base + "/sharing/general-access", headers=auth_headers()).json()
    assert state["audience"] == "workspace" and state["content_scope"] == "full_meeting"
    assert state["capabilities"]["workspace"] is False
    assert (
        client.post(
            base + "/summary-sharing/link", headers=auth_headers(), json={"template_key": template}
        ).status_code
        == 409
    )
    changed = client.post(
        base + "/sharing/general-access",
        headers=auth_headers(),
        json={
            "audience": "invite_only",
            "expected_fingerprint": state["fingerprint"],
        },
    )
    assert changed.status_code == 200 and changed.json()["audience"] == "invite_only"
    assert changed.json()["fingerprint"] != state["fingerprint"]
    blocked = client.post(
        base + "/sharing/general-access",
        headers=auth_headers(),
        json={
            "audience": "workspace",
            "expected_fingerprint": changed.json()["fingerprint"],
        },
    )
    assert blocked.status_code == 403
    assert (
        client.get(base + "/sharing/general-access", headers=auth_headers()).json()["audience"]
        == "invite_only"
    )


@pytest.mark.parametrize(("download", "export"), [(False, False), (True, False), (False, True), (True, True)])
def test_external_full_invitation_keeps_file_permissions_independent(
    client, tmp_path, monkeypatch, download, export
):
    from tests.fakes.fake_temporal import FakeTemporalClient
    from tests.integration.test_recording_share_public_link import _independent_invitation_login
    from tests.integration.test_web_owner_session_context import (
        OWNER_REVIEW_TEST_TOKEN,
        _seed_owner_review_session,
    )
    from twobrain_rec_server.auth.csrf import issue_csrf_token
    from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
    from twobrain_rec_server.cabinet.access import open_invitation_delivery
    from twobrain_rec_server.db.models import MeetingShareInvitation

    meeting_id, _ = prepare(client, tmp_path)
    meeting_id = UUID(str(meeting_id))
    audio = b"synthetic-f292-audio"
    add_retained_playback_m4a(client, meeting_id, audio)
    set_artifact_policy(client, meeting_id, audio_download="allowed", transcript_download="allowed")
    monkeypatch.setattr(client.app.state, "temporal_client", FakeTemporalClient(), raising=False)
    session = client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    owner_csrf = issue_csrf_token(session_id=session.id, secret=client.app.state.web_csrf_secret)
    url = f"/api/v1/cabinet/meetings/{meeting_id}/share-invitations"
    address = "reader-f292@example.test"
    payload = {
        "address": address,
        "content_scope": "full_meeting",
        "can_download": download,
        "can_export": export,
    }
    headers = {"X-CSRF-Token": owner_csrf}
    if not download and not export:
        assert client.post(url, json=payload).status_code == 403
        for permission in ("can_download", "can_export"):
            summary = {**payload, "content_scope": "summary_only", permission: True}
            assert client.post(url, headers=headers, json=summary).status_code == 422

    created = client.post(url, headers=headers, json=payload)
    assert created.status_code == 202
    invitation_id = created.json()["invitation_id"]
    expires_at = datetime.fromisoformat(created.json()["expires_at"])
    if not download and not export:
        repeated = client.post(
            url, headers=headers, json={**payload, "can_download": True, "can_export": True}
        )
        assert repeated.status_code == 202 and repeated.json()["invitation_id"] == invitation_id

    async def read_invitation():
        key = client.app.state.settings.credential_encryption_key_file.read_bytes().strip()
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(MeetingShareInvitation, UUID(invitation_id))
            assert row is not None and row.content_scope == "full_meeting"
            assert (row.can_download, row.can_export) == (download, export)
            _, token = open_invitation_delivery(row.encrypted_delivery_address, key=key)
            return token

    client.cookies.clear()
    accepted = _independent_invitation_login(
        client, recipient_email=address, raw_token=client.portal.call(read_invitation)
    )
    assert accepted.status_code == 303
    assert accepted.headers["location"] == f"/shared-meetings/{meeting_id}?workspace_id={WORKSPACE_ID}"
    page = client.get(accepted.headers["location"], headers={"Accept": "text/html"})
    assert page.status_code == 200 and SAFE_TRANSCRIPT_TEXT in page.text

    async def check_grant():
        async with client.app_state["sessionmaker"]() as db:
            grant = await db.scalar(
                select(MeetingShareGrant).where(MeetingShareGrant.meeting_id == meeting_id)
            )
            assert grant is not None and grant.status == "active" and grant.content_scope == "full_meeting"
            assert (grant.can_download, grant.can_export) == (download, export)
            assert grant.expires_at == expires_at

    client.portal.call(check_grant)
    base = f"/api/v1/cabinet/shared-meetings/{meeting_id}"
    params = {"workspace_id": str(WORKSPACE_ID)}
    playback = client.get(base + "/playback", params=params)
    assert playback.status_code == 200 and playback.content == audio

    file_response = client.get(base + "/downloads/audio", params=params)
    assert file_response.status_code == (200 if download else 409)
    if download:
        assert file_response.content == audio
        assert file_response.headers["content-disposition"].startswith("attachment;")
    else:
        assert file_response.json()["code"] == "artifact_unavailable"

    transcript = client.get(base + "/downloads/transcript", params=params)
    assert transcript.status_code == (200 if download else 409)
    if download:
        assert SAFE_TRANSCRIPT_TEXT in transcript.text
    else:
        assert transcript.json()["code"] == "artifact_unavailable"

    capabilities = client.get(base + "/content-exports", params=params)
    assert capabilities.status_code == 200
    assert capabilities.json()["transcript"]["state"] == ("available" if export else "denied")
    csrf = re.search(r'<meta name="csrf-token" content="([^"]+)"', page.text)
    assert csrf is not None
    exported = client.post(
        base + "/content-exports",
        params=params,
        headers={"X-CSRF-Token": csrf.group(1)},
        json={
            "content_scope": "transcript",
            "format": "txt",
            "processing_result_id": capabilities.json()["processing_result_id"],
        },
    )
    assert exported.status_code == (200 if export else 409)
    if export:
        assert SAFE_TRANSCRIPT_TEXT in exported.text
        assert exported.headers["content-disposition"].startswith("attachment;")
    else:
        assert exported.json()["code"] == "export_unavailable"


def test_public_signup_returns_to_original_recording_with_personal_session(client, tmp_path, monkeypatch):
    from tests.fakes.auth_contexts import AUTH_BOOTSTRAP_WORKSPACE_ID, USER_ID
    from tests.integration.test_web_owner_session_context import (
        _set_workspace_self_enrollment_policy,
    )
    from twobrain_rec_server.auth import email_delivery
    from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
    from twobrain_rec_server.auth.sessions import hash_token
    from twobrain_rec_server.cabinet.public_sharing import CONTINUATION_COOKIE
    from twobrain_rec_server.db.models import (
        AuthSession,
        ExternalIdentity,
        Workspace,
        WorkspaceMembership,
    )

    async def reject_external_delivery(**kwargs):
        pytest.fail("The synthetic signup must not call a mail provider")

    monkeypatch.setattr(email_delivery, "send_email_login_code", reject_external_delivery)
    client.portal.call(_set_workspace_self_enrollment_policy, client, False)
    monkeypatch.setattr(client, "base_url", client.base_url.copy_with(scheme="https"))
    meeting, template = prepare(client, tmp_path)
    audio = b"synthetic-public-signup-audio"
    add_retained_playback_m4a(client, UUID(str(meeting)), audio)
    _, path = publish(client, meeting, template)
    guest = client.get(path, headers={"Accept": "text/html"})
    assert guest.status_code == 200 and 'data-authenticated="false"' in guest.text
    version = re.search(r'data-media-version="([a-f0-9]{24})"', guest.text)
    signup_link = re.search(r'data-public-auth="sign-up" href="([^"]+)"', guest.text)
    assert version is not None and signup_link is not None
    media_version = version.group(1)
    continue_path = "/shared-meeting/continue"
    started = client.get(
        unescape(signup_link.group(1)) + f"&tab=recording&position_ms=500&media_version={media_version}",
        follow_redirects=False,
    )
    assert started.status_code == 303
    signup_url = urlsplit(started.headers["location"])
    assert signup_url.path == "/sign-up" and parse_qs(signup_url.query) == {"next": [continue_path]}
    cookie = started.headers["set-cookie"].lower()
    assert all(value in cookie for value in ("httponly", "samesite=lax", "secure", "max-age=600"))
    assert client.cookies.get(CONTINUATION_COOKIE)
    signup = client.get(started.headers["location"])
    assert signup.status_code == 200
    email_link = re.search(r'class="email-mode-trigger" href="([^"]+)"', signup.text)
    assert email_link is not None
    email_step = client.get(unescape(email_link.group(1)))
    assert email_step.status_code == 200 and 'action="/sign-up/email/start"' in email_step.text
    assert f'name="next" value="{continue_path}"' in email_step.text

    address = "new-f292-reader@example.test"

    async def read_identity():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(select(ExternalIdentity).where(ExternalIdentity.email == address))

    start = client.post("/sign-up/email/start", data={"email": address, "next": continue_path})
    assert start.status_code == 200
    state = re.search(r'name="state" value="([^"]+)"', start.text)
    code = re.search(r"Код для локальной проверки: <strong>([0-9]{6})</strong>", start.text)
    assert state is not None and code is not None
    assert client.portal.call(read_identity) is None and not client.cookies.get(AUTH_SESSION_COOKIE_NAME)
    verified = client.post(
        "/sign-up/email/verify",
        data={"email": address, "state": state.group(1), "code": code.group(1), "next": "/meetings"},
        follow_redirects=False,
    )
    assert verified.status_code == 303 and verified.headers["location"] == continue_path
    session_token = client.cookies.get(AUTH_SESSION_COOKIE_NAME)
    assert session_token

    resumed = client.get(verified.headers["location"], follow_redirects=False)
    assert resumed.status_code == 303
    assert resumed.headers["location"] == path + f"&media_version={media_version}#recording?position_ms=500"
    assert not client.cookies.get(CONTINUATION_COOKIE)
    reader = client.get(resumed.headers["location"], headers={"Accept": "text/html"})
    assert reader.status_code == 200 and 'data-authenticated="true"' in reader.text
    assert f'data-media-version="{media_version}"' in reader.text
    assert SAFE_TRANSCRIPT_TEXT in reader.text and "data-playback-shell" in reader.text
    assert 'href="/meetings">Мои встречи</a>' in reader.text
    playback = client.get(path.replace("?", "/playback?") + f"&media_version={media_version}")
    assert playback.status_code == 200 and playback.content == audio
    own_meetings = client.get("/meetings", follow_redirects=False)
    assert own_meetings.status_code == 200 and "Мои встречи" in own_meetings.text

    identity = client.portal.call(read_identity)
    assert identity is not None and identity.is_verified and identity.user_id != USER_ID

    async def check_workspace():
        async with client.app_state["sessionmaker"]() as db:
            session = await db.scalar(
                select(AuthSession).where(AuthSession.session_token_hash == hash_token(session_token))
            )
            assert session is not None and session.status == "active" and session.user_id == identity.user_id
            workspace = await db.get(Workspace, session.workspace_id)
            assert workspace is not None and workspace.kind == "personal"
            assert workspace.owner_user_id == identity.user_id
            membership = await db.get(WorkspaceMembership, (workspace.id, identity.user_id))
            assert membership is not None and (membership.role, membership.status) == ("owner", "active")
            assert AUTH_BOOTSTRAP_WORKSPACE_ID != WORKSPACE_ID
            for foreign_workspace in (WORKSPACE_ID, AUTH_BOOTSTRAP_WORKSPACE_ID):
                assert await db.get(WorkspaceMembership, (foreign_workspace, identity.user_id)) is None

    client.portal.call(check_workspace)
