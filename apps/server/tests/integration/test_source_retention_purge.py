from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.integration.test_playback_normalization_finalize import _accept_first_party_recording
from twobrain_rec_server.billing.storage import CANONICAL_PLAYBACK_PROFILE
from twobrain_rec_server.db.models import PurgeJournal, TrackArtifact
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.deletion.service import reconcile_source_retention_purges
from twobrain_rec_server.normalization.statuses import VALIDATION_VERSION


def test_source_retention_purge_requires_both_gates_and_records_exact_bytes(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="source-retention-purge",
        include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
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
                        TrackArtifact.track_role.in_(("microphone", "system")),
                    )
                )
            )
            assert len(sources) == 2
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
                        TrackArtifact.track_role.in_(("microphone", "system")),
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
                        TrackArtifact.track_role.in_(("microphone", "system")),
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
            assert len(rows) == 2
            assert len(journals) == 2
            source = rows[0]
            journal = next(row for row in journals if row.object_key == source.storage_object_key)
            return purged, source, journal

    purged, source, journal = asyncio.run(prepare_and_purge())
    assert purged == 2
    assert source.status == "purged"
    assert source.source_lifecycle_state == "purged"
    assert source.source_purged_at is not None
    assert journal.state == "purged"
    assert journal.metadata_json["actual_primary_bytes"] == source.byte_length
    assert journal.metadata_json["customer_quota_bytes"] == 0
    assert journal.metadata_json["cogs_status"] == "exact_bytes_recorded_cost_model_external"


def test_deletion_override_purges_source_without_retention_gates(client) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="source-retention-delete-override",
        include_playback=False,
    )
    assert result["status_code"] == 200
    meeting_id = meeting["meeting_id"]
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
                        TrackArtifact.track_role.in_(("microphone", "system")),
                    )
                )
            )

    sources = asyncio.run(load_sources())
    assert sources
    assert all(source.status == "purged" for source in sources)
    assert all(source.source_lifecycle_state == "purged" for source in sources)
