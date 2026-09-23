from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.integration.test_playback_normalization_finalize import _accept_first_party_recording
from twobrain_rec_server.billing.storage import CANONICAL_PLAYBACK_PROFILE
from twobrain_rec_server.db.models import MediaRevision, Meeting, PurgeJournal, TrackArtifact
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.deletion.service import reconcile_source_retention_purges
from twobrain_rec_server.normalization.statuses import VALIDATION_VERSION


def _retained_recording(client, *, historical: bool, suffix: str) -> UUID:
    if not historical:
        meeting, result = _accept_first_party_recording(
            client, local_recording_id=suffix, include_playback=True,
        )
        assert result["status_code"] == 200
        return UUID(str(meeting["meeting_id"]))

    async def seed_saved_artifacts() -> UUID:
        # Saved pre-v5 rows exercise retention/deletion compatibility only.
        # They never pass through the retired upload or submission producer.
        meeting_id, revision_id = uuid4(), uuid4()
        payloads = {
            "manifest": b"{}",
            "microphone": b"historical-source-a",
            "system": b"historical-source-b",
            "playback": b"historical-review",
        }
        digests = {role: sha256(body).hexdigest() for role, body in payloads.items()}
        async with client.app_state["sessionmaker"]() as db:
            db.add(Meeting(
                id=meeting_id, workspace_id=WORKSPACE_ID,
                created_by_user_id=USER_ID, device_id=DEVICE_ID,
                local_recording_id=suffix, duration_seconds=60,
                status="ingested_pending_processing",
            ))
            await db.flush()
            db.add(MediaRevision(
                id=revision_id, workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                local_media_revision_id=f"{suffix}--historical", revision_number=1,
                source_kind="initial_recording", status="accepted", immutable=True,
                duration_seconds=60, manifest_sha256=digests["manifest"],
                track_sha256_by_role={role: digest for role, digest in digests.items() if role != "playback"},
                accepted_at=datetime.now(UTC),
            ))
            await db.flush()
            for role, body in payloads.items():
                key = f"tests/historical-retention/{meeting_id}/{role}"
                client.app_state["storage"].put_bytes(key, body)
                db.add(TrackArtifact(
                    workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                    media_revision_id=revision_id, track_role=role,
                    codec="m4a-aac-lc" if role == "playback" else "pcm_s16le",
                    sample_rate_hz=48_000, channel_count=1, duration_seconds=60,
                    byte_length=len(body), sha256=digests[role], storage_object_key=key,
                    status="candidate" if role == "playback" else "stored",
                ))
            await db.commit()
        return meeting_id

    return asyncio.run(seed_saved_artifacts())


@pytest.mark.parametrize("historical", [False, True], ids=["canonical", "historical"])
def test_source_retention_purge_requires_both_gates_and_records_exact_bytes(client, historical) -> None:
    meeting_id = _retained_recording(client, historical=historical, suffix="source-retention-purge")
    source_roles = ("microphone", "system") if historical else ("media",)
    now = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)

    async def prepare_and_purge() -> tuple[int, TrackArtifact, PurgeJournal]:
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="deletion_purge_reconciliation",
                    actor_id="source-retention-test",
                    reason_category="source_retention",
                    feature_area="deletion",
                ),
            )
            sources = list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == meeting_id,
                        TrackArtifact.track_role.in_(source_roles),
                    )
                )
            )
            assert {source.track_role for source in sources} == set(source_roles)
            playback = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.meeting_id == meeting_id,
                    TrackArtifact.track_role == "playback",
                )
            )
            assert playback is not None
            playback.status = "stored"
            playback.normalization_profile_version = CANONICAL_PLAYBACK_PROFILE
            playback.validated_at = now - timedelta(days=8)
            playback.derivation_kind = "uploaded_candidate"
            playback.source_fingerprint_sha256 = "a" * 64
            playback.validation_version = VALIDATION_VERSION
            for source in sources:
                source.source_transcript_imported_at = now - timedelta(days=8)
                source.source_lifecycle_state = "recoverable"
                source.byte_length = max(source.byte_length, 1)
            await db.commit()
            assert (
                await reconcile_source_retention_purges(
                    db,
                    storage=client.app_state["storage"],
                    retention_period=timedelta(days=7),
                    policy_version="source-audio-v1",
                    backup_expiry_days=30,
                    now=now,
                    limit=10,
                )
                == 0
            )
            sources = list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == meeting_id,
                        TrackArtifact.track_role.in_(source_roles),
                    )
                )
            )
            assert all(source.status == "stored" for source in sources)
            for source in sources:
                source.source_playback_verified_at = now - timedelta(days=8)
            await db.commit()
            purged = await reconcile_source_retention_purges(
                db,
                storage=client.app_state["storage"],
                retention_period=timedelta(days=7),
                policy_version="source-audio-v1",
                backup_expiry_days=30,
                now=now,
                limit=10,
            )
            rows = list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == meeting_id,
                        TrackArtifact.track_role.in_(source_roles),
                    )
                )
            )
            journals = list(
                await db.scalars(
                    select(PurgeJournal).where(
                        PurgeJournal.meeting_id == meeting_id,
                        PurgeJournal.artifact_class == "source_retention",
                    )
                )
            )
            assert len(rows) == len(source_roles)
            assert len(journals) == len(source_roles)
            for row in rows:
                assert row.status == "purged"
                assert row.storage_object_key not in client.app_state["storage"].objects
                receipt = next(item for item in journals if item.object_key == row.storage_object_key)
                assert receipt.state == "purged"
                assert receipt.metadata_json["actual_primary_bytes"] == row.byte_length
            assert playback.storage_object_key in client.app_state["storage"].objects
            source = rows[0]
            journal = next(row for row in journals if row.object_key == source.storage_object_key)
            return purged, source, journal

    purged, source, journal = asyncio.run(prepare_and_purge())
    assert purged == len(source_roles)
    assert source.status == "purged"
    assert source.source_lifecycle_state == "purged"
    assert source.source_purged_at is not None
    assert journal.state == "purged"
    assert journal.metadata_json["actual_primary_bytes"] == source.byte_length
    assert journal.metadata_json["customer_quota_bytes"] == 0
    assert journal.metadata_json["cogs_status"] == "exact_bytes_recorded_cost_model_external"


@pytest.mark.parametrize("historical", [False, True], ids=["canonical", "historical"])
def test_deletion_override_purges_source_without_retention_gates(client, historical) -> None:
    meeting_id = _retained_recording(
        client, historical=historical, suffix="source-retention-delete-override",
    )
    source_roles = ("microphone", "system") if historical else ("media",)
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": "Delete this meeting everywhere GRAF controls."},
    )
    assert response.status_code == 202

    async def load_sources() -> list[TrackArtifact]:
        async with client.app_state["sessionmaker"]() as db:
            return list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == UUID(str(meeting_id)),
                        TrackArtifact.track_role.in_(source_roles),
                    )
                )
            )

    sources = asyncio.run(load_sources())
    assert {source.track_role for source in sources} == set(source_roles)
    assert all(source.status == "purged" for source in sources)
    assert all(source.source_lifecycle_state == "purged" for source in sources)
    assert all(source.storage_object_key not in client.app_state["storage"].objects for source in sources)
