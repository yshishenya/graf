"""Synthetic content restore with the committed deletion fence retained; no real backup I/O."""

import asyncio
from copy import deepcopy

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import add_retained_playback_m4a
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaRevision,
    Meeting,
    ProcessingResult,
    TrackArtifact,
    TranscriptSegment,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def test_restored_old_transcript_and_audio_cannot_bypass_retained_deletion_fence(client):
    seeds = seed_cabinet_meetings(client)
    meeting_id = seeds.ready_id
    audio = add_retained_playback_m4a(client, meeting_id, b"synthetic-restore-audio")
    detail = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())
    assert detail.status_code == 200
    assert SAFE_TRANSCRIPT_TEXT in detail.text
    assert detail.json()["playback"]["available"] is True

    async def snapshot_content():
        async with client.app_state["sessionmaker"]() as db:
            snapshot = []
            for model in (MediaRevision, TrackArtifact, ProcessingResult, TranscriptSegment, DiarizationSegment):
                rows = (await db.scalars(select(model).where(model.meeting_id == meeting_id))).all()
                assert rows, model.__name__
                snapshot.append((model, [deepcopy({column.key: getattr(row, column.key)
                                                for column in model.__table__.columns}) for row in rows]))
            return snapshot

    snapshot = asyncio.run(snapshot_content())
    artifact_rows = next(rows for model, rows in snapshot if model is TrackArtifact)
    storage = client.app_state["storage"]
    old_objects = {row["storage_object_key"]: storage.objects[row["storage_object_key"]]
                   for row in artifact_rows}
    deleted = client.post(f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
                          headers=auth_headers(), json={"confirmation_boundary": BOUNDED_DELETE_COPY})
    assert deleted.status_code == 202
    assert all(key not in storage.objects for key in old_objects)

    async def restore_content_under_existing_fence():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            fence = (meeting.deleted_at, meeting.deletion_state, meeting.deletion_epoch)
            assert fence[0] is not None and fence[1] != "none" and fence[2] > 0
            # Restore old content metadata without restoring the pre-delete Meeting row.
            for model, rows in snapshot:
                for row in rows:
                    await db.merge(model(**row))
                await db.flush()
            await db.commit()
            await db.refresh(meeting)
            assert (meeting.deleted_at, meeting.deletion_state, meeting.deletion_epoch) == fence
            segments = (await db.scalars(select(TranscriptSegment).where(
                TranscriptSegment.meeting_id == meeting_id))).all()
            assert SAFE_TRANSCRIPT_TEXT in [segment.text for segment in segments]

    asyncio.run(restore_content_under_existing_fence())
    storage.objects.update(old_objects)
    assert audio in storage.objects.values(), "The restored audio really exists in synthetic storage"
    for path in (
        f"/api/v1/cabinet/meetings/{meeting_id}",
        f"/meetings/{meeting_id}",
        f"/desktop/meetings/{meeting_id}",
        f"/api/v1/cabinet/meetings/{meeting_id}/downloads/transcript",
        f"/api/v1/cabinet/meetings/{meeting_id}/downloads/audio",
        f"/api/v1/cabinet/meetings/{meeting_id}/playback",
    ):
        response = client.get(path, headers=auth_headers())
        assert response.status_code in {404, 409}, (path, response.status_code)
        assert SAFE_TRANSCRIPT_TEXT not in response.text
        assert audio not in response.content
    listing = client.get("/api/v1/cabinet/meetings", headers=auth_headers())
    assert listing.status_code == 200
    ids = {item["meeting_id"] for item in listing.json()["items"]}
    assert str(meeting_id) not in ids
    assert str(seeds.processing_id) in ids, "The fence must not hide unaffected meetings"
    report = client.get(f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report", headers=auth_headers())
    assert report.status_code == 200
    assert SAFE_TRANSCRIPT_TEXT not in report.text
