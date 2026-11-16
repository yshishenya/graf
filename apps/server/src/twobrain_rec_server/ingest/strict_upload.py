"""Journal and accept strict calendar upload attempts."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from math import ceil, isfinite
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from threading import Event
from time import monotonic
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    MediaRevision,
    Meeting,
    PurgeJournal,
    TemporaryUploadObject,
    TrackArtifact,
    UploadPart,
    UploadSession,
    Workspace,
)
from twobrain_rec_server.db.tenant_context import require_database_context
from twobrain_rec_server.domain.statuses import MediaRevisionStatus, TrackRole, UploadSessionStatus
from twobrain_rec_server.ingest.status import get_calendar_upload_session_proof
from twobrain_rec_server.ingest.store import (
    _STRICT_PUBLICATION,
    UploadPartRecord,
    UploadSessionRecord,
)
from twobrain_rec_server.processing.fences import lock_meeting_fence, meeting_is_deleted_or_deleting
from twobrain_rec_server.storage.object_keys import (
    build_final_artifact_prefix,
    build_track_object_key,
)
from twobrain_rec_server.storage.recovery import (
    await_storage_worker,
    meeting_storage_read_fence_path,
    storage_recovery_snapshot,
)
from twobrain_rec_server.storage.strict_upload_cleanup import strict_upload_key_matches_epoch
from twobrain_rec_server.storage.strict_upload_keys import (
    STRICT_UPLOAD_ATTEMPT,
    is_strict_upload_key,
)
from twobrain_rec_server.storage.strict_upload_writer import (
    StrictMultipartWrite,
    StrictUploadWriteError,
    StrictUploadWriteTarget,
)

# The deployment authority must keep an active, uniquely allocated epoch and
# its exact MinIO permissions unchanged until every admitted operation drains.
StrictUploadWriteAdmission = Callable[
    [str, str, int], AbstractContextManager[StrictUploadWriteTarget | None]
]


@dataclass(frozen=True, slots=True)
class StrictUploadObject:
    workspace_id: UUID
    meeting_id: UUID
    revision_id: UUID
    session_id: UUID
    role: TrackRole
    part_number: int | None = None

    def key(self, organization_id: UUID, epoch: int, number: int) -> str:
        scope = dict(organization_id=organization_id, workspace_id=self.workspace_id, meeting_id=self.meeting_id)
        if self.part_number is None:
            base = build_final_artifact_prefix(**scope)
            return f"{base}/media-revisions/{self.revision_id}/attempts/{epoch}/{number}/tracks/{self.role.value}"
        base = build_track_object_key(
            **scope, upload_session_id=self.session_id, track_role=self.role, part_number=self.part_number,
        )
        return f"{base}/calendar-attempts/{epoch}/{number}"


@dataclass(frozen=True, slots=True)
class StagedStrictUpload:
    id: UUID
    object: StrictUploadObject
    key: str
    scope: str
    recovery: str
    epoch: int
    deletion_epoch: int
    upload_id: str
    calendar_attempt_id: UUID
    attempt_number: int
    byte_length: int
    sha256: str


def _remaining(deadline: float) -> float:
    remaining = deadline - monotonic()
    if not isfinite(remaining) or remaining <= 0:
        raise StrictUploadWriteError("protected_upload_stopped")
    return remaining


@asynccontextmanager
async def _phase(db: AsyncSession, deadline: float):
    async with asyncio.timeout(_remaining(deadline)):
        async with db.begin():
            # Bound server-side ownership even if the client loses its
            # connection while the S3 worker is still waiting for a response.
            milliseconds = ceil(_remaining(deadline) * 1000) + 1000
            await db.execute(
                text("select set_config('transaction_timeout', :duration, true)"),
                {"duration": f"{milliseconds}ms"},
            )
            yield


async def _lock_attempt(
    db: AsyncSession, *, attempt_id: UUID, object: StrictUploadObject, key: str, scope: str,
    epoch: int, deletion_epoch: int, write_state: str, upload_id: str | None,
) -> PurgeJournal:
    row = await db.scalar(select(PurgeJournal).where(
        PurgeJournal.id == attempt_id,
        PurgeJournal.workspace_id == object.workspace_id,
        PurgeJournal.meeting_id == object.meeting_id,
        PurgeJournal.media_revision_id == object.revision_id,
        PurgeJournal.artifact_class == STRICT_UPLOAD_ATTEMPT,
        PurgeJournal.object_key == key,
        PurgeJournal.storage_scope == scope,
        PurgeJournal.storage_epoch == epoch,
        PurgeJournal.deletion_epoch == deletion_epoch,
        PurgeJournal.state == "pending",
        PurgeJournal.attempt_count == 0,
        PurgeJournal.write_state == write_state,
        PurgeJournal.multipart_upload_id == upload_id,
    ).with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise StrictUploadWriteError("protected_upload_journal_not_admitted")
    return row


async def stage_strict_upload(
    db: AsyncSession, *, settings: Settings, object: StrictUploadObject, epoch: int,
    admission: StrictUploadWriteAdmission, admit_product: Callable[[Meeting], Awaitable[None]],
    source: BinaryIO, byte_length: int, expected_sha256: str, deadline: float,
) -> StagedStrictUpload:
    """Return only a settled attempt; the caller still owns late product acceptance.

    Use a dedicated request-scoped session between transactions. The product
    callback must revalidate current calendar access under Meeting, without
    network I/O, product mutation, or a commit.
    """
    scope = settings.strict_storage_scope
    require_database_context(db, allowed_context_kinds=frozenset({"request"}), workspace_id=object.workspace_id)
    if (
        db.in_transaction() or db.new or db.dirty or db.deleted
        or not scope or not 0 < epoch <= 2**63 - 1
        or (object.part_number is not None and not 0 <= object.part_number <= 2**31 - 1)
    ):
        raise StrictUploadWriteError("protected_upload_context_invalid")

    with storage_recovery_snapshot(settings) as recovery:
        if recovery in {None, "legacy"}:
            raise StrictUploadWriteError("protected_upload_recovery_unknown")
        with admission(scope, recovery, epoch) as target:
            if target is None:
                raise StrictUploadWriteError("protected_upload_generation_not_admitted")
            attempt_id = uuid4()
            async with _phase(db, deadline):
                meeting = await lock_meeting_fence(db, workspace_id=object.workspace_id, meeting_id=object.meeting_id)
                if meeting is None or meeting_is_deleted_or_deleting(meeting):
                    raise StrictUploadWriteError("protected_upload_meeting_not_admitted")
                organization_id = await db.scalar(select(Workspace.organization_id).where(Workspace.id == object.workspace_id))
                revision = await db.scalar(select(MediaRevision.id).where(
                    MediaRevision.id == object.revision_id,
                    MediaRevision.workspace_id == object.workspace_id,
                    MediaRevision.meeting_id == object.meeting_id,
                ))
                calendar_attempt_id = await db.scalar(select(UploadSession.calendar_match_attempt_id).where(
                    UploadSession.id == object.session_id,
                    UploadSession.workspace_id == object.workspace_id,
                    UploadSession.meeting_id == object.meeting_id,
                    UploadSession.media_revision_id == object.revision_id,
                    UploadSession.calendar_match_attempt_id.is_not(None),
                ))
                if organization_id is None or revision is None or calendar_attempt_id is None:
                    raise StrictUploadWriteError("protected_upload_owner_not_admitted")
                deletion_epoch = meeting.deletion_epoch
                transaction = db.get_transaction()
                await admit_product(meeting)
                if db.get_transaction() is not transaction or db.new or db.dirty or db.deleted:
                    raise StrictUploadWriteError("protected_upload_product_admission_invalid")
                number = await db.scalar(text("select nextval('public.strict_upload_attempt_no')"))
                key = object.key(organization_id, epoch, number)
                db.add(PurgeJournal(
                    id=attempt_id, workspace_id=object.workspace_id, meeting_id=object.meeting_id,
                    media_revision_id=object.revision_id, deletion_epoch=deletion_epoch,
                    artifact_class=STRICT_UPLOAD_ATTEMPT, object_key=key, storage_scope=scope,
                    storage_epoch=epoch, state="pending", write_state="intent",
                    metadata_json={
                        "upload_session_id": str(object.session_id), "calendar_attempt_id": str(calendar_attempt_id),
                        "byte_length": byte_length, "sha256": expected_sha256,
                    },
                    next_retry_at=datetime.now(UTC) + timedelta(seconds=_remaining(deadline)),
                ))

            cancelled = Event()
            writer = StrictMultipartWrite(
                target, key=key, epoch=epoch, attempt_id=attempt_id, deadline=deadline, cancelled=cancelled,
            )

            async def lock(write_state: str, upload_id: str | None = None) -> PurgeJournal:
                return await _lock_attempt(
                    db, attempt_id=attempt_id, object=object, key=key, scope=scope,
                    epoch=epoch, deletion_epoch=deletion_epoch, write_state=write_state, upload_id=upload_id,
                )

            async def io[T](run: Callable[[], T]) -> T:
                _remaining(deadline)
                operation = asyncio.get_running_loop().run_in_executor(None, run)
                return await await_storage_worker(operation, cancelled)

            async with _phase(db, deadline):
                (await lock("intent")).write_state = "create_possible"
            async with _phase(db, deadline):
                row = await lock("create_possible")
                upload_id = await io(writer.create)
                row.multipart_upload_id = upload_id
                row.write_state = "upload_id_known"
            async with _phase(db, deadline):
                row = await lock("upload_id_known", upload_id)
                await io(lambda: writer.transfer(
                    upload_id, source, byte_length=byte_length, expected_sha256=expected_sha256,
                ))
                _remaining(deadline)
                row.write_state = "settled"
            return StagedStrictUpload(
                attempt_id, object, key, scope, recovery, epoch, deletion_epoch, upload_id,
                calendar_attempt_id, number, byte_length, expected_sha256,
            )


async def _lock_calendar_owner(
    db: AsyncSession, obj: StrictUploadObject, *, calendar_attempt_id: UUID, deletion_epoch: int,
) -> tuple[MediaRevision, UploadSession]:
    meeting = await lock_meeting_fence(db, workspace_id=obj.workspace_id, meeting_id=obj.meeting_id)
    if (
        meeting is None or meeting_is_deleted_or_deleting(meeting)
        or meeting.deletion_epoch != deletion_epoch
    ):
        raise StrictUploadWriteError("protected_upload_meeting_not_admitted")
    revision = await db.scalar(select(MediaRevision).where(
        MediaRevision.id == obj.revision_id,
        MediaRevision.workspace_id == obj.workspace_id,
        MediaRevision.meeting_id == obj.meeting_id,
    ).with_for_update().execution_options(populate_existing=True))
    owner = await db.scalar(select(UploadSession).where(
        UploadSession.id == obj.session_id,
        UploadSession.workspace_id == obj.workspace_id,
        UploadSession.meeting_id == obj.meeting_id,
        UploadSession.media_revision_id == obj.revision_id,
        UploadSession.calendar_match_attempt_id == calendar_attempt_id,
    ).with_for_update().execution_options(populate_existing=True))
    if revision is None or owner is None:
        raise StrictUploadWriteError("protected_upload_owner_not_admitted")
    return revision, owner


@asynccontextmanager
async def accept_strict_uploads(
    db: AsyncSession, *, settings: Settings, staged: tuple[StagedStrictUpload, ...],
    tenant_scope: TenantScope, admission: StrictUploadWriteAdmission, deadline: float,
):
    """Publish the owners and accept their exact attempts with one commit.

    The caller writes product state in the yielded transaction without committing
    or performing storage I/O. A lost commit reply leaves reconciliation to the journal.
    """
    if not staged or db.in_transaction() or db.new or db.dirty or db.deleted:
        raise StrictUploadWriteError("protected_upload_context_invalid")
    first = staged[0]
    obj = first.object
    require_database_context(db, allowed_context_kinds=frozenset({"request"}), workspace_id=obj.workspace_id)
    keys = frozenset(item.key for item in staged)
    if (
        len(keys) != len(staged)
        or len({item.id for item in staged}) != len(staged)
        or len({(item.object.role, item.object.part_number) for item in staged}) != len(staged)
        or any(
            (
                item.object.workspace_id, item.object.meeting_id, item.object.revision_id, item.object.session_id,
                item.scope, item.recovery, item.epoch, item.deletion_epoch, item.calendar_attempt_id,
                item.object.part_number is None,
            ) != (
                obj.workspace_id, obj.meeting_id, obj.revision_id, obj.session_id,
                first.scope, first.recovery, first.epoch, first.deletion_epoch, first.calendar_attempt_id,
                obj.part_number is None,
            )
            for item in staged
        )
    ):
        raise StrictUploadWriteError("protected_upload_batch_invalid")

    with storage_recovery_snapshot(settings) as recovery:
        if recovery in {None, "legacy"} or recovery != first.recovery or settings.strict_storage_scope != first.scope:
            raise StrictUploadWriteError("protected_upload_recovery_unknown")
        with admission(first.scope, recovery, first.epoch) as target:
            if target is None:
                raise StrictUploadWriteError("protected_upload_generation_not_admitted")
            async with _phase(db, deadline):
                revision, owner = await _lock_calendar_owner(
                    db, obj, calendar_attempt_id=first.calendar_attempt_id, deletion_epoch=first.deletion_epoch,
                )
                organization_id = await db.scalar(select(Workspace.organization_id).where(
                    Workspace.id == obj.workspace_id,
                ))
                if organization_id is None or any(
                    item.key != item.object.key(organization_id, item.epoch, item.attempt_number) for item in staged
                ):
                    raise StrictUploadWriteError("protected_upload_batch_invalid")
                await get_calendar_upload_session_proof(
                    obj.meeting_id, obj.session_id, obj.revision_id, tenant_scope, db,
                    expected_attempt_id=first.calendar_attempt_id,
                )
                locked = []
                for item in sorted(staged, key=lambda item: item.id):
                    row = await _lock_attempt(
                        db, attempt_id=item.id, object=item.object, key=item.key, scope=item.scope,
                        epoch=item.epoch, deletion_epoch=item.deletion_epoch,
                        write_state="settled", upload_id=item.upload_id,
                    )
                    if row.metadata_json != {
                        "upload_session_id": str(obj.session_id), "calendar_attempt_id": str(item.calendar_attempt_id),
                        "byte_length": item.byte_length, "sha256": item.sha256,
                    }:
                        raise StrictUploadWriteError("protected_upload_journal_not_admitted")
                    locked.append((item, row))

                def prevent_early_commit(_session) -> None:
                    # A root commit can run this hook with a savepoint still open.
                    raise StrictUploadWriteError("protected_upload_commit_not_owned")

                transaction = db.get_transaction()
                db.info[_STRICT_PUBLICATION] = transaction, {item.key: item for item, _ in locked}
                event.listen(db.sync_session, "before_commit", prevent_early_commit)
                try:
                    yield
                finally:
                    event.remove(db.sync_session, "before_commit", prevent_early_commit)
                    db.info.pop(_STRICT_PUBLICATION, None)
                if db.get_transaction() is not transaction:
                    raise StrictUploadWriteError("protected_upload_commit_not_owned")

                await db.flush()
                if (
                    obj.part_number is None and (
                        owner.status != UploadSessionStatus.FINALIZED.value
                        or owner.finalized_at is None or revision.status != MediaRevisionStatus.ACCEPTED.value
                    )
                    or obj.part_number is not None and owner.status != UploadSessionStatus.UPLOADING.value
                ):
                    raise StrictUploadWriteError("protected_upload_owner_not_published")
                for item, row in locked:
                    await _require_published_owner(db, owner, item)
                    row.state = "retained"
                    row.write_state = "accepted"
                    row.next_retry_at = None


async def _require_published_owner(db: AsyncSession, owner: UploadSession, item: StagedStrictUpload) -> None:
    obj = item.object
    if obj.part_number is not None:
        artifact = await db.scalar(select(UploadPart.id).where(
            UploadPart.upload_session_id == obj.session_id,
            UploadPart.track_role == obj.role.value,
            UploadPart.part_number == obj.part_number,
            UploadPart.storage_object_key == item.key,
            UploadPart.byte_length == item.byte_length,
            UploadPart.sha256 == item.sha256,
            UploadPart.status == "accepted",
        ))
        custody = ("accepted_part", "pending")
    else:
        artifact = await db.scalar(select(TrackArtifact.id).where(
            TrackArtifact.workspace_id == obj.workspace_id,
            TrackArtifact.meeting_id == obj.meeting_id,
            TrackArtifact.media_revision_id == obj.revision_id,
            TrackArtifact.track_role == obj.role.value,
            TrackArtifact.storage_object_key == item.key,
            TrackArtifact.byte_length == item.byte_length,
            TrackArtifact.sha256 == item.sha256,
            TrackArtifact.status == ("candidate" if obj.role is TrackRole.PLAYBACK else "stored"),
        ))
        custody = ("transient_source", "processing") if not owner.archive_audio and obj.role is TrackRole.MEDIA else None
    if artifact is None:
        raise StrictUploadWriteError("protected_upload_owner_not_published")
    if custody is not None and await db.scalar(select(TemporaryUploadObject.id).where(
        TemporaryUploadObject.upload_session_id == obj.session_id,
        TemporaryUploadObject.workspace_id == obj.workspace_id,
        TemporaryUploadObject.media_revision_id == obj.revision_id,
        TemporaryUploadObject.storage_object_key == item.key,
        TemporaryUploadObject.byte_length == item.byte_length,
        TemporaryUploadObject.object_role == custody[0],
        TemporaryUploadObject.cleanup_status == custody[1],
    )) is None:
        raise StrictUploadWriteError("protected_upload_custody_not_published")


async def download_strict_part(
    db: AsyncSession, *, settings: Settings, tenant_scope: TenantScope, session: UploadSessionRecord,
    part: UploadPartRecord, storage: object, destination: Path, recovery: str,
    deletion_epoch: int, deadline: float,
) -> int:
    """Read only this accepted part; never fall back to the ordinary object reader."""
    require_database_context(db, allowed_context_kinds=frozenset({"request"}), workspace_id=session.workspace_id)
    download = getattr(storage, "download_strict_source_to_path_async", None)
    fence = meeting_storage_read_fence_path(settings, session.workspace_id, session.meeting_id)
    if (
        db.in_transaction() or not callable(download) or fence is None
        or session.media_revision_id is None or session.calendar_match_attempt_id is None
        or not 0 < part.byte_length <= settings.max_upload_part_bytes
    ):
        raise StrictUploadWriteError("protected_upload_part_not_admitted")
    base = build_track_object_key(
        organization_id=session.organization_id, workspace_id=session.workspace_id, meeting_id=session.meeting_id,
        upload_session_id=session.id, track_role=part.track_role, part_number=part.part_number,
    )
    if not part.object_key.startswith(f"{base}/calendar-attempts/"):
        raise StrictUploadWriteError("protected_upload_part_not_admitted")

    query = select(
        PurgeJournal.id, PurgeJournal.storage_epoch, PurgeJournal.metadata_json, PurgeJournal.multipart_upload_id,
    ).where(
        PurgeJournal.workspace_id == session.workspace_id,
        PurgeJournal.meeting_id == session.meeting_id,
        PurgeJournal.media_revision_id == session.media_revision_id,
        PurgeJournal.artifact_class == STRICT_UPLOAD_ATTEMPT,
        PurgeJournal.object_key == part.object_key,
        PurgeJournal.storage_scope == settings.strict_storage_scope,
        PurgeJournal.deletion_epoch == deletion_epoch,
        PurgeJournal.state == "retained",
        PurgeJournal.write_state == "accepted",
        PurgeJournal.multipart_upload_id.is_not(None),
    )
    owner = select(UploadPart.id).where(
        UploadPart.upload_session_id == session.id,
        UploadPart.track_role == part.track_role.value,
        UploadPart.part_number == part.part_number,
        UploadPart.byte_offset == part.byte_offset,
        UploadPart.byte_length == part.byte_length,
        UploadPart.sha256 == part.sha256,
        UploadPart.storage_object_key == part.object_key,
        UploadPart.status == "accepted",
    )
    with storage_recovery_snapshot(settings) as current:
        if current in {None, "legacy"} or current != recovery:
            raise StrictUploadWriteError("protected_upload_recovery_unknown")
        async with _phase(db, deadline):
            attempt = (await db.execute(query)).one_or_none()
        if (
            attempt is None or attempt.storage_epoch is None or not attempt.multipart_upload_id
            or not strict_upload_key_matches_epoch(part.object_key, attempt.storage_epoch)
            or attempt.metadata_json != {
                "upload_session_id": str(session.id), "calendar_attempt_id": str(session.calendar_match_attempt_id),
                "byte_length": part.byte_length, "sha256": part.sha256,
            }
        ):
            raise StrictUploadWriteError("protected_upload_part_not_admitted")

        async def admit() -> bool:
            # MinIO takes the shared meeting storage lock before calling this.
            # Commit the lifecycle check before it opens the network response.
            async with _phase(db, deadline):
                await _lock_calendar_owner(
                    db, StrictUploadObject(
                        session.workspace_id, session.meeting_id, session.media_revision_id,
                        session.id, part.track_role, part.part_number,
                    ), calendar_attempt_id=session.calendar_match_attempt_id, deletion_epoch=deletion_epoch,
                )
                await get_calendar_upload_session_proof(
                    session.meeting_id, session.id, session.media_revision_id, tenant_scope, db,
                    expected_attempt_id=session.calendar_match_attempt_id,
                )
                return (
                    (await db.execute(query.with_for_update(of=PurgeJournal))).one_or_none() == attempt
                    and await db.scalar(owner) is not None
                )

        return await download(
            part.object_key, destination, epoch=attempt.storage_epoch, attempt_id=attempt.id,
            deadline=deadline, fence_path=fence, admit=admit,
            expected_length=part.byte_length, expected_sha256=part.sha256, max_bytes=part.byte_length,
        )


@asynccontextmanager
async def assemble_strict_track(
    db: AsyncSession, *, settings: Settings, tenant_scope: TenantScope, session: UploadSessionRecord,
    track: TrackDescriptor, storage: object, recovery: str, deletion_epoch: int, deadline: float,
):
    """Yield a verified, rewound stream for the dedicated multipart writer."""
    parts = sorted(
        (part for (role, _number), part in session.parts.items() if role == track.track_role),
        key=lambda part: part.byte_offset,
    )
    if (
        len(parts) < 2 or not 0 < track.byte_length <= settings.max_track_bytes
        or session.expected_track_sizes.get(track.track_role) != track.byte_length
        or len({part.part_number for part in parts}) != len(parts)
        or len({part.object_key for part in parts}) != len(parts)
    ):
        raise StrictUploadWriteError("protected_upload_track_parts_invalid")
    cursor = 0
    for part in parts:
        if (
            part.track_role != track.track_role or part.byte_offset != cursor
            or not 0 < part.byte_length <= settings.max_upload_part_bytes
            or not is_strict_upload_key(part.object_key)
        ):
            raise StrictUploadWriteError("protected_upload_track_parts_invalid")
        cursor += part.byte_length
    if cursor != track.byte_length:
        raise StrictUploadWriteError("protected_upload_track_parts_invalid")

    _remaining(deadline)
    with TemporaryDirectory(prefix="graf-strict-track-") as scratch, TemporaryFile(dir=scratch, mode="w+b") as body:
        part_path = Path(scratch) / "part"
        digest = sha256()
        loop = asyncio.get_running_loop()
        cancelled = Event()

        def append_part(part: UploadPartRecord) -> None:
            part_digest = sha256()
            remaining = part.byte_length
            with part_path.open("rb") as downloaded:
                while remaining:
                    if cancelled.is_set():
                        return
                    _remaining(deadline)
                    chunk = downloaded.read(min(remaining, 4 * 1024 * 1024))
                    if not chunk:
                        raise StrictUploadWriteError("protected_upload_track_part_mismatch")
                    remaining -= len(chunk)
                    part_digest.update(chunk)
                    digest.update(chunk)
                    body.write(chunk)
                if downloaded.read(1) or part_digest.hexdigest() != part.sha256:
                    raise StrictUploadWriteError("protected_upload_track_part_mismatch")
            part_path.unlink()

        for part in parts:
            _remaining(deadline)
            transferred = await download_strict_part(
                db, settings=settings, tenant_scope=tenant_scope, session=session, part=part, storage=storage,
                destination=part_path, recovery=recovery, deletion_epoch=deletion_epoch, deadline=deadline,
            )
            if transferred != part.byte_length:
                raise StrictUploadWriteError("protected_upload_track_part_mismatch")
            await await_storage_worker(loop.run_in_executor(None, append_part, part), cancelled)

        if digest.hexdigest() != track.sha256:
            raise StrictUploadWriteError("protected_upload_track_digest_mismatch")
        await await_storage_worker(loop.run_in_executor(None, body.seek, 0), cancelled)
        # Keep the generation that authenticated all inputs through use of this stream.
        with storage_recovery_snapshot(settings) as current:
            if current in {None, "legacy"} or current != recovery:
                raise StrictUploadWriteError("protected_upload_recovery_unknown")
            _remaining(deadline)
            yield body
