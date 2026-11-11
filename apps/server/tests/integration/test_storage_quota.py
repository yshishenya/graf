import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.integration.test_billing_notification_flow import (
    billing_maintenance_probe_url as billing_maintenance_probe_url,
)
from tests.integration.test_billing_notification_flow import rls_engine as rls_engine
from twobrain_rec_server.billing.catalog import (
    ADDON_CAPACITY_BYTES,
    PERSONAL_STORAGE_BYTES,
    classify_storage_threshold,
    storage_capacity_bytes,
)
from twobrain_rec_server.billing.storage import (
    CANONICAL_PLAYBACK_FILENAME,
    CANONICAL_PLAYBACK_PROFILE,
    StorageAdmissionError,
    StorageProjection,
    StorageReservation,
    admit_storage,
    commit_object_bytes,
    commit_storage_reservation,
    is_chargeable_playback_artifact,
    release_storage,
    reserve_storage,
)
from twobrain_rec_server.db.models import (
    StorageReservation as StorageReservationRow,
)


class _ScalarQueueSession:
    def __init__(self, *rows: object) -> None:
        self.rows = list(rows)
        self.flushed = False

    async def scalar(self, _query: object) -> object:
        return self.rows.pop(0)

    async def flush(self) -> None:
        self.flushed = True


def test_storage_projection_uses_exact_decimal_capacities_and_thresholds() -> None:
    projection = StorageProjection(used_bytes=4_000_000_000, reserved_bytes=0, capacity_bytes=PERSONAL_STORAGE_BYTES)
    assert projection.threshold == "80%"
    assert StorageProjection(used_bytes=4_750_000_000, reserved_bytes=0, capacity_bytes=PERSONAL_STORAGE_BYTES).threshold == "95%"
    assert classify_storage_threshold(used_bytes=PERSONAL_STORAGE_BYTES, capacity_bytes=PERSONAL_STORAGE_BYTES) == "full"
    assert storage_capacity_bytes("personal", ADDON_CAPACITY_BYTES[0]) == ADDON_CAPACITY_BYTES[0]


def test_storage_reservation_rejects_admission_and_object_stat_overrun() -> None:
    with pytest.raises(StorageAdmissionError):
        admit_storage(StorageProjection(100, 50, 120), 1)
    reservation = StorageReservation("r1", 100)
    with pytest.raises(StorageAdmissionError):
        commit_object_bytes(reservation=reservation, actual_bytes=101)


def test_storage_projection_is_bounded_by_capacity() -> None:
    projection = StorageProjection(used_bytes=200, reserved_bytes=10, capacity_bytes=250)
    assert projection.available_bytes == 40


def test_storage_reservation_release_is_idempotent_and_capacity_validation_is_fail_closed() -> None:
    reservation = StorageReservation("r1", declared_bytes=100)
    release_storage(reservation)
    release_storage(reservation)
    assert reservation.state == "released"
    with pytest.raises(ValueError):
        StorageProjection(used_bytes=0, reserved_bytes=0, capacity_bytes=0)


def test_storage_admission_allows_exact_boundary_after_reserved_bytes() -> None:
    projection = StorageProjection(used_bytes=179, reserved_bytes=20, capacity_bytes=200)
    admit_storage(projection, 1)
    with pytest.raises(StorageAdmissionError):
        admit_storage(projection, 2)


def test_storage_commit_records_verified_smaller_object_without_rounding() -> None:
    reservation = StorageReservation("verified-smaller", declared_bytes=100)

    assert commit_object_bytes(reservation=reservation, actual_bytes=73) == 73
    assert reservation.committed_bytes == 73
    assert reservation.state == "committed"


def test_only_active_canonical_playback_object_counts_toward_customer_quota() -> None:
    common = {
        "track_role": "playback",
        "normalization_profile_version": CANONICAL_PLAYBACK_PROFILE,
        "storage_object_key": f"workspace/meeting/{CANONICAL_PLAYBACK_FILENAME}",
    }
    assert is_chargeable_playback_artifact(status="stored", **common)
    assert not is_chargeable_playback_artifact(status="deleted", **common)
    assert not is_chargeable_playback_artifact(
        status="stored",
        **{**common, "storage_object_key": common["storage_object_key"] + ".tmp"},
    )
    assert not is_chargeable_playback_artifact(
        status="stored", **{**common, "track_role": "media"}
    )


def test_transcription_and_legacy_source_filenames_never_count_as_playback_quota() -> None:
    for filename in ("meeting-transcription.wav", "mic.wav", "incoming.wav"):
        assert not is_chargeable_playback_artifact(
            track_role="playback",
            status="stored",
            normalization_profile_version=CANONICAL_PLAYBACK_PROFILE,
            storage_object_key=f"workspace/meeting/{filename}",
        )


def test_storage_reservation_rejects_expiry_at_or_before_admission() -> None:
    now = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)

    async def reserve() -> None:
        with pytest.raises(ValueError, match="expiry must be in the future"):
            await reserve_storage(
                _ScalarQueueSession(),
                workspace_id=uuid4(),
                reservation_key="expired",
                declared_bytes=1,
                capacity_bytes=10,
                now=now,
                expires_at=now,
            )

    asyncio.run(reserve())


@pytest.mark.parametrize("stale_state", ["active", "released"])
def test_storage_reservation_re_admits_expired_or_released_row(
    client,
    stale_state: str,
) -> None:
    now = datetime.now(UTC)
    reservation_key = f"storage-re-admission-{stale_state}"

    async def re_admit() -> tuple[object, object, int, str, datetime | None]:
        async with client.app_state["sessionmaker"]() as db:
            stale = StorageReservationRow(
                workspace_id=WORKSPACE_ID,
                idempotency_key=reservation_key,
                declared_bytes=100,
                state=stale_state,
                expires_at=(
                    now - timedelta(seconds=1)
                    if stale_state == "active"
                    else now + timedelta(minutes=1)
                ),
            )
            db.add(stale)
            await db.commit()
            stale_id = stale.id
            await reserve_storage(
                db,
                workspace_id=WORKSPACE_ID,
                reservation_key=reservation_key,
                declared_bytes=120,
                capacity_bytes=1_000,
                now=now,
                expires_at=now + timedelta(minutes=30),
            )
            await db.commit()
            persisted = await db.scalar(
                select(StorageReservationRow).where(StorageReservationRow.id == stale_id)
            )
            assert persisted is not None
            return (
                stale_id,
                persisted.id,
                persisted.declared_bytes,
                persisted.state,
                persisted.expires_at,
            )

    stale_id, reservation_id, declared_bytes, state, expires_at = asyncio.run(re_admit())
    assert reservation_id == stale_id
    assert declared_bytes == 120
    assert state == "active"
    assert expires_at is not None and expires_at > now


def test_storage_commit_requires_verified_canonical_artifact_and_fresh_reservation() -> None:
    now = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)
    workspace_id = uuid4()
    reservation_id = uuid4()
    artifact_id = uuid4()
    reservation = SimpleNamespace(
        id=reservation_id,
        workspace_id=workspace_id,
        state="active",
        expires_at=now + timedelta(minutes=1),
        committed_bytes=0,
        declared_bytes=100,
        artifact_id=None,
    )
    unverified_artifact = SimpleNamespace(
        id=artifact_id,
        workspace_id=workspace_id,
        track_role="media",
        status="stored",
        normalization_profile_version=None,
        storage_object_key="workspace/meeting/meeting-transcription.wav",
        byte_length=80,
    )

    async def commit() -> None:
        with pytest.raises(StorageAdmissionError, match="verified canonical playback"):
            await commit_storage_reservation(
                _ScalarQueueSession(reservation, unverified_artifact),
                reservation_id=reservation_id,
                artifact_id=artifact_id,
                actual_bytes=80,
                now=now,
            )

    asyncio.run(commit())
    assert reservation.committed_bytes == 0


def test_storage_commit_rejects_expired_reservation_before_artifact_lookup() -> None:
    now = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)
    reservation = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        state="active",
        expires_at=now - timedelta(seconds=1),
        committed_bytes=0,
        declared_bytes=100,
        artifact_id=None,
    )

    async def commit() -> None:
        with pytest.raises(StorageAdmissionError, match="expired"):
            await commit_storage_reservation(
                _ScalarQueueSession(reservation),
                reservation_id=reservation.id,
                artifact_id=uuid4(),
                actual_bytes=80,
                now=now,
            )

    asyncio.run(commit())


def test_storage_commit_accepts_only_exact_verified_playback_bytes() -> None:
    now = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)
    workspace_id = uuid4()
    reservation_id = uuid4()
    artifact_id = uuid4()
    reservation = SimpleNamespace(
        id=reservation_id,
        workspace_id=workspace_id,
        state="active",
        expires_at=now + timedelta(minutes=1),
        committed_bytes=0,
        declared_bytes=100,
        artifact_id=None,
    )
    artifact = SimpleNamespace(
        id=artifact_id,
        workspace_id=workspace_id,
        track_role="playback",
        status="stored",
        normalization_profile_version=CANONICAL_PLAYBACK_PROFILE,
        storage_object_key="workspace/meeting/meeting-review.m4a",
        byte_length=73,
    )

    async def commit() -> None:
        db = _ScalarQueueSession(reservation, artifact)
        assert await commit_storage_reservation(
            db,
            reservation_id=reservation_id,
            artifact_id=artifact_id,
            actual_bytes=73,
            now=now,
        ) == 73
        assert db.flushed is True

    asyncio.run(commit())
    assert reservation.committed_bytes == 73
    assert reservation.artifact_id == artifact_id
    assert reservation.state == "committed"


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("case,expected", [
    ("larger", 33), ("smaller", 9), ("late_old", 33),
    ("queued", 24), ("failed", 24), ("candidate", 24),
    ("temporary", 24), ("no_archive", 0), ("foreign_revision", 24),
    ("foreign_meeting", 24), ("other_meeting", 57),
])
async def test_storage_primary_is_latest_published_revision(rls_engine, case, expected):
    from tests.integration.test_rls_postgres_policies import _seed_probe_rows
    from twobrain_rec_server.billing.storage import project_active_playback_storage
    from twobrain_rec_server.db.models import MediaRevision, Meeting, TrackArtifact, UploadSession
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

    ids = await _seed_probe_rows(rls_engine)
    sessions = create_sessionmaker(rls_engine)
    workspace, meeting = ids["workspace_a"], ids["meeting_a"]
    context = MaintenanceTenantContext(operation_name="migration_verification", actor_id="test-storage-primary",
                                       reason_category="synthetic-selection", feature_area="billing")
    now = datetime.now(UTC)

    def artifact(revision, size, **changes):
        values = dict(workspace_id=workspace, meeting_id=meeting, media_revision_id=revision.id,
                      track_role="playback", codec="aac", sample_rate_hz=48000, channel_count=1,
                      duration_seconds=60, byte_length=size, sha256="a" * 64,
                      storage_object_key=f"synthetic/{revision.id}/meeting-review.m4a", status="stored",
                      normalization_profile_version=CANONICAL_PLAYBACK_PROFILE, validated_at=now,
                      derivation_kind="uploaded_candidate", source_fingerprint_sha256="b" * 64,
                      validation_version="playback_validator_v1")
        values.update(changes)
        return TrackArtifact(**values)

    async with sessions.begin() as db:
        await apply_tenant_context(db, context)
        old = MediaRevision(id=uuid4(), workspace_id=workspace, meeting_id=meeting,
                            local_media_revision_id="old", revision_number=1, status="accepted")
        next_meeting = meeting
        if case == "other_meeting":
            other = Meeting(id=uuid4(), workspace_id=workspace, created_by_user_id=ids["user_a"],
                            device_id=ids["device_a"], local_recording_id="independent", duration_seconds=60)
            db.add(other)
            await db.flush()
            next_meeting = other.id
        new = MediaRevision(id=uuid4(), workspace_id=workspace, meeting_id=next_meeting,
                            local_media_revision_id="new", revision_number=2,
                            status="failed" if case == "failed" else "accepted")
        if case == "foreign_revision":
            new.workspace_id, new.meeting_id = ids["workspace_b"], ids["meeting_b"]
        db.add_all([old, new])
        await db.flush()
        old_artifact = artifact(old, 24)
        db.add(old_artifact)
        await db.flush()
        if case not in {"queued", "failed"}:
            changes = {}
            if case == "candidate":
                changes = dict(status="candidate", normalization_profile_version=None,
                               validated_at=None, source_fingerprint_sha256=None, validation_version=None)
            elif case == "temporary":
                changes = dict(storage_object_key="synthetic/meeting-review.m4a.tmp")
            elif case == "foreign_meeting":
                changes = dict(meeting_id=ids["meeting_b"])
            elif case == "other_meeting":
                changes = dict(meeting_id=next_meeting)
            # A later verification and larger old artifact cannot determine
            # the billable primary. Actual recovery is covered separately.
            if case == "late_old":
                old_artifact.validated_at = now + timedelta(hours=1)
                old_artifact.byte_length = 99
            db.add(artifact(new, 9 if case == "smaller" else 33, **changes))
        if case == "no_archive":
            db.add(UploadSession(workspace_id=workspace, meeting_id=meeting, media_revision_id=new.id,
                                 device_id=ids["device_a"], created_by_user_id=ids["user_a"],
                                 status="finalized", archive_audio=False,
                                 max_package_bytes_snapshot=1000, max_track_bytes_snapshot=1000,
                                 expires_at=now + timedelta(hours=1)))

    async with sessions() as db:
        await apply_tenant_context(db, context)
        projection = await project_active_playback_storage(db, workspace_id=workspace,
                                                           capacity_bytes=1000, reserved_bytes=7)
        assert (projection.used_bytes, projection.reserved_bytes) == (expected, 7)
        # A quota read must not rewrite retained canonical/lifecycle metadata.
        assert (await db.get(TrackArtifact, old_artifact.id)).status == "stored"


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_storage_primary_commit_rollback_and_delete_preserve_lifecycle(rls_engine):
    from tests.integration.test_rls_postgres_policies import _seed_probe_rows
    from twobrain_rec_server.billing.storage import (
        logically_release_playback_quota,
        project_active_playback_storage,
    )
    from twobrain_rec_server.db.models import MediaRevision, TrackArtifact
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

    ids = await _seed_probe_rows(rls_engine)
    sessions = create_sessionmaker(rls_engine)
    workspace, meeting = ids["workspace_a"], ids["meeting_a"]
    write_context = MaintenanceTenantContext(operation_name="migration_verification", actor_id="test-storage-primary",
                                             reason_category="synthetic-atomicity", feature_area="billing")
    read_context = MaintenanceTenantContext(operation_name="billing_reconciliation", actor_id="test-storage-primary",
                                            reason_category="synthetic-atomicity", feature_area="billing")

    async def publish(db, number, size):
        revision = MediaRevision(id=uuid4(), workspace_id=workspace, meeting_id=meeting,
                                 local_media_revision_id=f"revision-{number}", revision_number=number,
                                 status="accepted")
        db.add(revision)
        await db.flush()
        artifact = TrackArtifact(workspace_id=workspace, meeting_id=meeting, media_revision_id=revision.id,
                                 track_role="playback", codec="aac", sample_rate_hz=48000, channel_count=1,
                                 duration_seconds=60, byte_length=size, sha256="a" * 64,
                                 storage_object_key=f"synthetic/{revision.id}/meeting-review.m4a", status="stored",
                                 normalization_profile_version=CANONICAL_PLAYBACK_PROFILE, validated_at=datetime.now(UTC),
                                 derivation_kind="uploaded_candidate", source_fingerprint_sha256="b" * 64,
                                 validation_version="playback_validator_v1")
        db.add(artifact)
        await db.flush()
        return artifact.id

    async def used():
        async with sessions() as db:
            await apply_tenant_context(db, read_context)
            return (await project_active_playback_storage(db, workspace_id=workspace, capacity_bytes=1000)).used_bytes

    async with sessions.begin() as db:
        await apply_tenant_context(db, write_context)
        old = await publish(db, 1, 24)
    async with sessions.begin() as db:
        await apply_tenant_context(db, write_context)
        new = await publish(db, 2, 33)
        assert await used() == 24  # Independent reader cannot see uncommitted replacement.
    assert await used() == 33
    async with sessions() as db:
        await apply_tenant_context(db, write_context)
        await publish(db, 3, 9)
        assert await used() == 33
        await db.rollback()
    assert await used() == 33
    async with sessions.begin() as db:
        await apply_tenant_context(db, write_context)
        retained = [(await db.get(TrackArtifact, key)) for key in (old, new)]
        assert [row.status for row in retained] == ["stored", "stored"]
        keys = [row.storage_object_key for row in retained]
        await logically_release_playback_quota(db, workspace_id=workspace, meeting_id=meeting)
        assert [row.status for row in retained] == ["deleted", "deleted"]
        assert [row.storage_object_key for row in retained] == keys
    assert await used() == 0  # Physical purge of either retained object cannot revive the other.
