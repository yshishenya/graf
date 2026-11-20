import asyncio
import json
from contextlib import asynccontextmanager, contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from time import monotonic
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID, tenant_scope
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.db.models import (
    Meeting,
    PurgeJournal,
    TemporaryUploadObject,
    TrackArtifact,
    UploadPart,
    UploadSession,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.domain.statuses import TrackRole, UploadSessionStatus
from twobrain_rec_server.ingest import store, strict_upload
from twobrain_rec_server.ingest.media_revisions import mark_media_revision_accepted
from twobrain_rec_server.storage.recovery import read_with_storage_fence, storage_read_fence
from twobrain_rec_server.storage.strict_upload_writer import StrictUploadWriteError


@pytest.mark.parametrize(("scenario", "phases", "durable"), [
    ("success", ["create", "transfer"], "settled"),
    ("missing_generation", [], None),
    ("product_denied", [], None),
    ("cancel_transfer", ["create", "transfer"], "upload_id_known"),
    ("lost_intent_commit", [], "intent"),
    ("cleaner_claimed", [], "create_possible"),
    ("lost_create_reply", ["create"], "create_possible"),
    ("lost_id_commit", ["create"], "upload_id_known"),
    ("lost_complete_reply", ["create", "transfer"], "upload_id_known"),
    ("lost_settled_commit", ["create", "transfer"], "settled"),
    ("rolled_back_settled_commit", ["create", "transfer"], "upload_id_known"),
])
async def test_strict_multipart_never_skips_durable_journal_phases(
    client, tmp_path, monkeypatch, scenario, phases, durable,
):
    meeting = client.post(
        "/api/v1/meetings", headers=auth_headers(),
        json={"local_recording_id": "strict-journal-test", "duration_seconds": 2},
    ).json()
    meeting_id = UUID(meeting["meeting_id"])
    opened = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions", headers=auth_headers(),
        json={"expected_track_sizes": {"media": 1}},
    )
    assert opened.status_code == 200
    session_id = UUID(opened.json()["session_id"])
    sessions = client.app_state["sessionmaker"]
    async with sessions.begin() as seed:
        saved = await seed.get(UploadSession, session_id)
        # This suite tests the journal boundary; calendar/device policy is
        # exercised separately by the actual ingest routes.
        saved.calendar_match_attempt_id = uuid4()
        request = strict_upload.StrictUploadObject(
            WORKSPACE_ID, meeting_id, saved.media_revision_id, session_id, TrackRole.MEDIA,
            part_number=0 if scenario == "success" else None,
        )

    recovery_file = tmp_path / "recovery"
    recovery_file.with_suffix(".lock").touch()
    recovery_id = uuid4()
    recovery_file.write_text(json.dumps({
        "schema": 1, "scope": "isolated-storage", "state": "reconciled", "recovery_id": str(recovery_id),
    }))
    settings = client.app.state.settings
    settings.strict_storage_scope = "isolated-storage"
    settings.strict_storage_recovery_file = recovery_file
    settings.strict_storage_recovery_id = recovery_id

    loop = asyncio.get_running_loop()
    request_task = asyncio.current_task()
    calls = []
    drained_while_locked = []

    async def read_row():
        async with sessions() as observer:
            return await observer.scalar(select(PurgeJournal).where(PurgeJournal.meeting_id == meeting_id))

    async def verify_boundary(attempt_id, key, state, upload_id):
        async with sessions.begin() as observer:
            row = await observer.get(PurgeJournal, attempt_id)
            assert (row.write_state, row.multipart_upload_id, row.object_key) == (state, upload_id, key)
            # Network waits hold the attempt, never the whole meeting.
            assert await observer.scalar(select(Meeting.id).where(Meeting.id == meeting_id).with_for_update(nowait=True))
            with pytest.raises(DBAPIError) as error:
                async with observer.begin_nested():
                    await observer.scalar(select(PurgeJournal.id).where(
                        PurgeJournal.id == attempt_id,
                    ).with_for_update(nowait=True))
            assert error.value.orig.sqlstate == "55P03"

    class ObservedWriter:
        def __init__(self, target, *, key, attempt_id, cancelled, **kwargs):
            self.key, self.attempt_id = key, attempt_id
            self.cancelled = cancelled

        def inspect(self, state, upload_id):
            asyncio.run_coroutine_threadsafe(
                verify_boundary(self.attempt_id, self.key, state, upload_id), loop,
            ).result(timeout=4)

        def create(self):
            calls.append("create")
            self.inspect("create_possible", None)
            if scenario == "lost_create_reply":
                raise OSError("synthetic lost reply")
            return "synthetic-multipart-id"

        def transfer(self, upload_id, source, *, byte_length, expected_sha256):
            calls.append("transfer")
            self.inspect("upload_id_known", upload_id)
            assert source.read() == b"x" and byte_length == 1 and expected_sha256 == sha256(b"x").hexdigest()
            if scenario == "lost_complete_reply":
                raise OSError("synthetic lost reply")
            if scenario == "cancel_transfer":
                assert request_task is not None
                loop.call_soon_threadsafe(request_task.cancel)
                loop.call_soon_threadsafe(request_task.cancel)
                assert self.cancelled.wait(4)
                self.inspect("upload_id_known", upload_id)
                drained_while_locked.append(True)

    @contextmanager
    def authority(scope, recovery, epoch):
        assert (scope, recovery, epoch) == ("isolated-storage", str(recovery_id), 3)
        yield None if scenario == "missing_generation" else object()

    async def product_access(locked_meeting):
        assert locked_meeting.id == meeting_id
        if scenario == "product_denied":
            raise StrictUploadWriteError("synthetic product admission denied")

    real_phase = strict_upload._phase
    phase_number = 0

    @asynccontextmanager
    async def inject_fault(db, deadline):
        nonlocal phase_number
        phase_number += 1
        number = phase_number
        async with real_phase(db, deadline):
            yield
            if scenario == "rolled_back_settled_commit" and number == 4:
                raise OSError("synthetic failed commit")
        if (scenario, number) in {
            ("lost_intent_commit", 1), ("lost_id_commit", 3), ("lost_settled_commit", 4),
        }:
            raise OSError("synthetic lost commit response")
        if scenario == "cleaner_claimed" and number == 2:
            row = await read_row()
            async with sessions.begin() as cleaner:
                claimed = await cleaner.get(PurgeJournal, row.id)
                claimed.state = "deleting"
                claimed.attempt_count = 1

    monkeypatch.setattr(strict_upload, "StrictMultipartWrite", ObservedWriter)
    monkeypatch.setattr(strict_upload, "_phase", inject_fault)
    async with sessions() as db:
        await apply_tenant_scope(db, tenant_scope())
        await db.commit()
        operation = strict_upload.stage_strict_upload(
            db, settings=settings, object=request, epoch=3, admission=authority, admit_product=product_access,
            source=BytesIO(b"x"), byte_length=1, expected_sha256=sha256(b"x").hexdigest(), deadline=monotonic() + 10,
        )
        if scenario == "success":
            staged = await operation
            assert staged.upload_id == "synthetic-multipart-id"
            assert f"/sessions/{session_id}/tracks/media/parts/00000000/calendar-attempts/3/" in staged.key
        else:
            expected = asyncio.CancelledError if scenario == "cancel_transfer" else (StrictUploadWriteError, OSError)
            with pytest.raises(expected):
                await operation
        assert not db.in_transaction()
    assert calls == phases
    assert drained_while_locked == ([True] if scenario == "cancel_transfer" else [])
    row = await read_row()
    if durable is None:
        assert row is None
    else:
        assert row.write_state == durable
        assert row.state == ("deleting" if scenario == "cleaner_claimed" else "pending")
        assert row.multipart_upload_id == (
            "synthetic-multipart-id" if durable in {"settled", "upload_id_known"} else None
        )


@pytest.mark.parametrize("scenario", [
    "part", "tracks", "archive_off", "missing_custody", "generation_revoked", "calendar_revoked",
    "cleaner_claimed", "wrong_batch", "second_attempt_invalid", "missing_second_owner", "part_already_owned",
    "commit_reply_lost", "commit_failed", "recovery_changed", "early_commit", "early_root_commit_with_savepoint",
    "wrong_digest", "unowned_store_part", "unowned_store_track", "unowned_transient", "wrong_meeting",
    "read_accepted", "read_owner_changed", "read_cleaner_won", "read_calendar_revoked", "read_multipart_changed",
])
async def test_strict_attempt_acceptance_commits_with_exact_product_owner(client, tmp_path, monkeypatch, scenario):
    meeting_id = UUID(client.post(
        "/api/v1/meetings", headers=auth_headers(),
        json={"local_recording_id": "strict-late-accept", "duration_seconds": 2},
    ).json()["meeting_id"])
    session_id = UUID(client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions", headers=auth_headers(),
        json={"expected_track_sizes": {"media": 1}},
    ).json()["session_id"])
    sessions = client.app_state["sessionmaker"]
    digest = sha256(b"x").hexdigest()
    calendar_attempt_id = uuid4()
    recovery_id = uuid4()
    recovery_file = tmp_path / "recovery"
    recovery_file.with_suffix(".lock").touch()
    recovery_file.write_text(json.dumps({
        "schema": 1, "scope": "isolated-storage", "state": "reconciled", "recovery_id": str(recovery_id),
    }))
    settings = client.app.state.settings
    settings.strict_storage_scope = "isolated-storage"
    settings.strict_storage_recovery_file = recovery_file
    settings.strict_storage_recovery_id = recovery_id
    part = scenario not in {
        "tracks", "archive_off", "wrong_batch", "second_attempt_invalid", "missing_second_owner",
        "unowned_store_track", "unowned_transient", "wrong_meeting",
    }
    other_meeting_id = None
    if scenario == "wrong_meeting":
        other_meeting_id = UUID(client.post(
            "/api/v1/meetings", headers=auth_headers(),
            json={"local_recording_id": "strict-late-accept-other", "duration_seconds": 2},
        ).json()["meeting_id"])

    async with sessions.begin() as seed:
        upload = await seed.get(UploadSession, session_id)
        upload.calendar_match_attempt_id = calendar_attempt_id
        staged = tuple(
            strict_upload.StagedStrictUpload(
                uuid4(), obj, obj.key(tenant_scope().organization_id, 3, number),
                "isolated-storage", str(recovery_id), 3, 0, f"multipart-{number}",
                calendar_attempt_id, number, 1, digest,
            )
            for number, role in enumerate(
                [TrackRole.MEDIA] if part else [TrackRole.MEDIA, TrackRole.PLAYBACK], start=1,
            )
            for obj in [strict_upload.StrictUploadObject(
                WORKSPACE_ID, meeting_id, upload.media_revision_id, session_id, role, 0 if part else None,
            )]
        )
        for i, attempt in enumerate(staged):
            claimed = scenario == "cleaner_claimed" or (scenario == "second_attempt_invalid" and i == 1)
            seed.add(PurgeJournal(
                id=attempt.id, workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                media_revision_id=attempt.object.revision_id, deletion_epoch=0, storage_epoch=3,
                artifact_class="strict_upload_attempt", object_key=attempt.key, storage_scope=attempt.scope,
                state="deleting" if claimed else "pending", attempt_count=int(claimed),
                write_state="settled", multipart_upload_id=attempt.upload_id,
                metadata_json={
                    "upload_session_id": str(session_id), "calendar_attempt_id": str(calendar_attempt_id),
                    "byte_length": 1, "sha256": digest,
                },
            ))
        if scenario == "part_already_owned":
            seed.add(UploadPart(
                upload_session_id=session_id, track_role="media", part_number=0, byte_offset=0,
                byte_length=1, sha256=digest, storage_object_key="existing-authoritative-part", status="accepted",
            ))

    @contextmanager
    def authority(scope, recovery, epoch):
        assert (scope, recovery, epoch) == ("isolated-storage", str(recovery_id), 3)
        yield None if scenario == "generation_revoked" else object()

    # The synthetic calendar link has no real auth session. Keep the actual
    # admission for the revoked case; route tests cover the valid calendar proof.
    if scenario != "calendar_revoked":
        monkeypatch.setattr(strict_upload, "get_calendar_upload_session_proof", AsyncMock())
    real_phase = strict_upload._phase

    @asynccontextmanager
    async def lose_commit_reply(db, deadline):
        async with real_phase(db, deadline):
            yield
            if scenario == "commit_failed":
                raise OSError("synthetic rolled-back commit")
        if scenario == "commit_reply_lost":
            raise OSError("synthetic committed but reply lost")

    monkeypatch.setattr(strict_upload, "_phase", lose_commit_reply)

    if scenario == "recovery_changed":
        settings.strict_storage_recovery_id = uuid4()

    @asynccontextmanager
    async def transaction(db, inputs):
        if scenario.startswith("unowned_"):
            async with db.begin():
                yield
        else:
            async with strict_upload.accept_strict_uploads(
                db, settings=settings, staged=inputs, tenant_scope=tenant_scope(),
                admission=authority, deadline=monotonic() + 10,
            ):
                yield

    async def publish(db):
        inputs = (
            (staged[0], replace(staged[1], object=replace(staged[1].object, session_id=uuid4())))
            if scenario == "wrong_batch" else staged
        )
        if scenario == "wrong_digest":
            inputs = (replace(staged[0], sha256=sha256(b"other").hexdigest()),)
        async with transaction(db, inputs):
            assert scenario not in {
                "cleaner_claimed", "generation_revoked", "calendar_revoked", "wrong_batch", "second_attempt_invalid",
                "recovery_changed", "wrong_digest",
            }
            session = await store.load_upload_session_record(db, session_id)
            assert session is not None
            if part:
                session.status = UploadSessionStatus.UPLOADING
                await store.persist_upload_session(db, session, commit=False)
                record = store.UploadPartRecord(TrackRole.MEDIA, 0, 0, 1, digest, staged[0].key, b"")
                if scenario not in {"missing_custody", "unowned_store_part"}:
                    await store.persist_temporary_upload_object(db, session, record, commit=False)
                await store.persist_upload_part(db, session, record, commit=False)
                if scenario == "early_commit":
                    await db.commit()
                if scenario == "early_root_commit_with_savepoint":
                    root = db.get_transaction()
                    assert root is not None
                    async with db.begin_nested():
                        await root.commit()
            else:
                meeting = await store.load_meeting_record(
                    db, meeting_id=other_meeting_id or meeting_id, retain_in_memory=False,
                )
                assert meeting is not None
                tracks = [
                    TrackDescriptor(
                        track_role=item.object.role, codec="wav", sample_rate_hz=48000, channel_count=1,
                        duration_seconds=2, byte_length=1, sha256=digest,
                    )
                    for item in staged
                ]
                await mark_media_revision_accepted(
                    db, media_revision_id=session.media_revision_id, manifest_sha256=digest, tracks=tracks, commit=False,
                )
                session.status = UploadSessionStatus.FINALIZED
                session.finalized_at = datetime.now(UTC)
                session.archive_audio = scenario not in {"archive_off", "unowned_transient"}
                await store.persist_upload_session(db, session, commit=False)
                if scenario == "unowned_transient":
                    await store.persist_transient_source_objects(
                        db, session=session, source_object_keys={TrackRole.MEDIA: (staged[0].key, 1)},
                        admitted_at=session.finalized_at,
                    )
                await store.persist_finalized_tracks(
                    db, meeting, session, tracks[:1] if scenario == "missing_second_owner" else tracks, digest, {item.object.role: item.key for item in staged},
                    commit=False,
                    reused_strict_keys={staged[0].key} if scenario == "unowned_store_track" else None,
                )
                if scenario == "archive_off":
                    await store.persist_transient_source_objects(
                        db, session=session, source_object_keys={TrackRole.MEDIA: (staged[0].key, 1)},
                        admitted_at=session.finalized_at,
                    )

    successful = scenario in {"part", "tracks", "archive_off"} or scenario.startswith("read_")
    async with sessions() as db:
        await apply_tenant_scope(db, tenant_scope())
        await db.commit()
        if successful:
            await publish(db)
        else:
            expected = {
                "calendar_revoked": ProblemDetail, "part_already_owned": RuntimeError,
                "commit_reply_lost": OSError, "commit_failed": OSError,
                "unowned_store_part": RuntimeError, "unowned_store_track": RuntimeError,
                "unowned_transient": RuntimeError, "wrong_meeting": RuntimeError,
            }.get(scenario, StrictUploadWriteError)
            match = {
                "early_commit": "protected_upload_commit_not_owned",
                "early_root_commit_with_savepoint": "protected_upload_commit_not_owned",
                "wrong_meeting": "finalized_track_owner_mismatch",
                "unowned_store_part": "strict_upload_requires_explicit_ownership",
                "unowned_store_track": "strict_upload_requires_explicit_ownership",
                "unowned_transient": "strict_upload_requires_explicit_ownership",
                "wrong_digest": "protected_upload_journal_not_admitted",
            }.get(scenario)
            with pytest.raises(expected, match=match):
                await publish(db)
        assert not db.in_transaction()

    if scenario.startswith("read_"):
        item = staged[0]
        settings.strict_storage_read_fence_directory = tmp_path
        destination = tmp_path / "download"
        calls = []
        async with sessions() as db:
            await apply_tenant_scope(db, tenant_scope())
            await db.commit()
            async with db.begin():
                session = await store.load_upload_session_record(db, session_id)
            assert session is not None

            class Storage:
                async def download_strict_source_to_path_async(
                    self, key, path, *, epoch, attempt_id, deadline, fence_path, admit,
                    expected_length, expected_sha256, max_bytes,
                ):
                    assert (key, epoch, attempt_id, expected_length, expected_sha256, max_bytes) == (
                        item.key, item.epoch, item.id, 1, digest, 1,
                    )
                    if scenario == "read_owner_changed":
                        async with sessions.begin() as editor:
                            saved = await editor.scalar(select(UploadPart).where(UploadPart.upload_session_id == session_id))
                            saved.byte_offset = 1
                    if scenario in {"read_cleaner_won", "read_multipart_changed"}:
                        async with sessions.begin() as cleaner:
                            row = await cleaner.get(PurgeJournal, item.id)
                            if scenario == "read_cleaner_won":
                                row.state = "deleting"
                            else:
                                row.multipart_upload_id = "changed-multipart-id"
                    if scenario == "read_calendar_revoked":
                        strict_upload.get_calendar_upload_session_proof.side_effect = ProblemDetail(
                            status=404, code="upload_session_not_found", title="Upload session not found",
                        )

                    async def checked_admit():
                        allowed = await admit()
                        assert not db.in_transaction()
                        async with sessions.begin() as observer:
                            assert await observer.scalar(select(Meeting.id).where(
                                Meeting.id == meeting_id,
                            ).with_for_update(nowait=True))
                        return allowed

                    def read(_cancelled):
                        with storage_read_fence(fence_path, exclusive=True) as cleaner:
                            assert cleaner is None
                        calls.append(key)
                        path.write_bytes(b"x")
                        return 1

                    transferred = await read_with_storage_fence(fence_path, admit=checked_admit, read=read)
                    if transferred is None:
                        raise StrictUploadWriteError("synthetic read not admitted")
                    return transferred

            operation = strict_upload.download_strict_part(
                db, settings=settings, tenant_scope=tenant_scope(), session=session,
                part=session.parts[(TrackRole.MEDIA, 0)], storage=Storage(), destination=destination,
                recovery=str(recovery_id), deletion_epoch=0, deadline=monotonic() + 10,
            )
            if scenario == "read_accepted":
                assert await operation == 1
                assert destination.read_bytes() == b"x"
                assert calls == [item.key]
            else:
                with pytest.raises(ProblemDetail if scenario == "read_calendar_revoked" else StrictUploadWriteError):
                    await operation
                assert not destination.exists() and not calls

    committed = successful or scenario == "commit_reply_lost"
    async with sessions() as observer:
        for item in staged:
            row = await observer.get(PurgeJournal, item.id)
            owner = UploadPart if part else TrackArtifact
            assert bool(await observer.scalar(select(owner.id).where(owner.storage_object_key == item.key))) == committed
            assert (row.state, row.write_state) == (
                (("deleting" if scenario == "read_cleaner_won" else "retained"), "accepted") if committed else
                ("deleting" if row.attempt_count else "pending", "settled")
            )
        if scenario == "part_already_owned":
            assert await observer.scalar(select(UploadPart.storage_object_key).where(
                UploadPart.upload_session_id == session_id,
            )) == "existing-authoritative-part"
        custody = (await observer.scalars(select(TemporaryUploadObject).where(
            TemporaryUploadObject.upload_session_id == session_id,
        ))).all()
        assert [(row.object_role, row.cleanup_status) for row in custody] == (
            [("accepted_part", "pending")] if part and committed else
            [("transient_source", "processing")] if scenario == "archive_off" else []
        )
