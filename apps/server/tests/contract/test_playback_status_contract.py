from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import add_retained_playback_m4a, set_meeting_deletion_state
from twobrain_rec_server.cabinet.access import AccessDecision
from twobrain_rec_server.cabinet.egress import review_playback_state
from twobrain_rec_server.db.models import (
    MediaRevision,
    Meeting,
    PlaybackNormalizationJob,
    TrackArtifact,
)
from twobrain_rec_server.domain.statuses import DeletionState, TrackRole


def test_list_and_detail_expose_the_same_durable_automatic_preparing_state(client) -> None:
    seeds = seed_cabinet_meetings(client)

    detail = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())
    listing = client.get("/api/v1/cabinet/meetings", headers=auth_headers())

    assert detail.status_code == 200
    assert listing.status_code == 200
    list_item = next(
        item for item in listing.json()["items"] if item["meeting_id"] == str(seeds.ready_id)
    )
    expected = {
        "state": "preparing",
        "reason_code": "normalization_queued",
        "label": "Аудио готовится автоматически",
        "automatic_recovery": True,
        "can_play": False,
        "action": "disabled",
    }
    assert {key: detail.json()["playback"][key] for key in expected} == expected
    assert list_item["playback"] == expected


def test_ready_canonical_playback_is_independent_from_transcript_processing(client) -> None:
    seeds = seed_cabinet_meetings(client)
    for meeting_id in (seeds.processing_id, seeds.failed_id):
        add_retained_playback_m4a(client, meeting_id)

        response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())

        assert response.status_code == 200
        payload = response.json()
        assert payload["playback"]["state"] == "available"
        assert payload["playback"]["reason_code"] == "canonical_ready"
        assert payload["playback"]["can_play"] is True
        assert payload["playback"]["available"] is True
        assert payload["processing"]["state"] in {"processing", "failed"}


def test_unvalidated_candidate_and_source_artifacts_are_never_playback_egress(client) -> None:
    seeds = seed_cabinet_meetings(client)
    candidate_body = b"private-unvalidated-playback-candidate"

    async def add_candidate() -> None:
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.scalar(
                select(MediaRevision).where(
                    MediaRevision.workspace_id == WORKSPACE_ID,
                    MediaRevision.meeting_id == seeds.ready_id,
                )
            )
            assert revision is not None
            object_key = f"tests/cabinet/{seeds.ready_id}/unvalidated-candidate.m4a"
            client.app_state["storage"].put_bytes(object_key, candidate_body)
            db.add(
                TrackArtifact(
                    workspace_id=WORKSPACE_ID,
                    meeting_id=seeds.ready_id,
                    media_revision_id=revision.id,
                    track_role=TrackRole.PLAYBACK.value,
                    codec="m4a-aac-lc",
                    sample_rate_hz=48_000,
                    channel_count=1,
                    duration_seconds=1,
                    byte_length=len(candidate_body),
                    sha256=sha256(candidate_body).hexdigest(),
                    storage_object_key=object_key,
                    status="candidate",
                )
            )
            await db.commit()

    asyncio.run(add_candidate())

    response = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/playback", headers=auth_headers()
    )

    assert response.status_code == 409
    assert response.json()["code"] == "playback_unavailable"
    assert candidate_body not in response.content


def test_terminal_source_truth_is_safe_and_has_no_repair_action(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def mark_terminal() -> None:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.workspace_id == WORKSPACE_ID,
                    PlaybackNormalizationJob.meeting_id == seeds.ready_id,
                )
            )
            assert job is not None
            job.state = "terminal"
            job.reason_code = "unsupported_codec"
            job.terminal_at = datetime.now(UTC)
            await db.commit()

    asyncio.run(mark_terminal())

    detail = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())
    html = client.get(f"/desktop/meetings/{seeds.ready_id}", headers=auth_headers())

    assert detail.status_code == 200
    playback = detail.json()["playback"]
    assert playback["state"] == "unavailable"
    assert playback["reason_code"] == "unsupported_media"
    assert playback["automatic_recovery"] is False
    assert playback["can_play"] is False
    assert playback["action"] == "disabled"
    assert "<audio" not in html.text
    forbidden = ("retry", "reprocess-playback", "backfill", "повторить", "загрузить заново")
    assert not any(word in html.text.casefold() for word in forbidden)


def test_terminal_reason_copy_is_bounded_and_safe_for_every_public_category(client) -> None:
    seeds = seed_cabinet_meetings(client)
    expected = {
        "empty_source": ("empty_source", "В исходном файле нет данных"),
        "no_audio": ("no_audio", "В файле нет пригодной аудиодорожки"),
        "ambiguous_audio_tracks": (
            "ambiguous_audio_tracks",
            "В файле несколько равноправных аудиодорожек",
        ),
        "unsupported_container": (
            "unsupported_media",
            "Формат или кодек файла не поддерживается",
        ),
        "unsupported_codec": (
            "unsupported_media",
            "Формат или кодек файла не поддерживается",
        ),
        "encrypted_media": (
            "encrypted_media",
            "Защищённый файл нельзя подготовить для воспроизведения",
        ),
        "corrupt_source": (
            "corrupt_source",
            "Файл повреждён и не может быть воспроизведён",
        ),
        "stream_limit_exceeded": (
            "limit_exceeded",
            "Файл превышает допустимые параметры",
        ),
        "duration_limit_exceeded": (
            "limit_exceeded",
            "Файл превышает допустимые параметры",
        ),
        "source_size_limit_exceeded": (
            "limit_exceeded",
            "Файл превышает допустимые параметры",
        ),
        "source_missing": (
            "source_missing",
            "Исходный файл больше не хранится в GRAF",
        ),
        "source_mismatch": (
            "source_mismatch",
            "Целостность исходного файла не подтверждена",
        ),
    }

    async def project(reason: str) -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.workspace_id == WORKSPACE_ID,
                    PlaybackNormalizationJob.meeting_id == seeds.ready_id,
                )
            )
            assert job is not None
            job.state = "terminal"
            job.reason_code = reason
            job.terminal_at = datetime.now(UTC)
            await db.commit()
        response = client.get(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        return response.json()["playback"]

    for durable_reason, (public_reason, label) in expected.items():
        playback = asyncio.run(project(durable_reason))
        expected_projection = {
            "state": "unavailable",
            "reason_code": public_reason,
            "label": label,
            "automatic_recovery": False,
            "can_play": False,
            "action": "disabled",
        }
        assert {key: playback[key] for key in expected_projection} == expected_projection
        serialized = str(playback).casefold()
        forbidden = (
            "retry",
            "reprocess",
            "backfill",
            "повторить",
            "загрузить заново",
            "администратор",
            "object_key",
            "stderr",
            "stdout",
        )
        assert not any(marker in serialized for marker in forbidden)


def test_deletion_truth_precedes_access_and_terminal_job_truth(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_meeting_deletion_state(client, seeds.ready_id, DeletionState.REQUESTED.value)

    async def project():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.workspace_id == WORKSPACE_ID,
                    PlaybackNormalizationJob.meeting_id == seeds.ready_id,
                )
            )
            assert meeting is not None and job is not None
            job.state = "terminal"
            job.reason_code = "corrupt_source"
            job.terminal_at = datetime.now(UTC)
            await db.commit()
            return await review_playback_state(
                db,
                meeting=meeting,
                access=AccessDecision(
                    state="denied",
                    label="Not available",
                    reason=None,
                    can_view=False,
                    can_share=False,
                    can_manage_team_visibility=False,
                    can_download=False,
                    can_export=False,
                ),
            )

    playback = asyncio.run(project())

    assert playback.state == "deleting"
    assert playback.reason_code == "meeting_deleting"
    assert playback.label == "Аудио удаляется"


def test_accepted_revision_without_job_projects_reconciliation_pending(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def remove_job() -> None:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.workspace_id == WORKSPACE_ID,
                    PlaybackNormalizationJob.meeting_id == seeds.ready_id,
                )
            )
            assert job is not None
            await db.delete(job)
            await db.commit()

    asyncio.run(remove_job())

    response = client.get(f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers())

    assert response.status_code == 200
    expected = {
        "state": "preparing",
        "reason_code": "reconciliation_pending",
        "automatic_recovery": True,
        "can_play": False,
        "action": "disabled",
    }
    playback = response.json()["playback"]
    assert {key: playback[key] for key in expected} == expected


def test_playback_recovery_has_no_public_mutation_endpoint_or_repair_control(client) -> None:
    seeds = seed_cabinet_meetings(client)

    html = client.get(f"/meetings/{seeds.ready_id}", headers=auth_headers())
    schema = client.app.openapi()

    assert html.status_code == 200
    assert 'data-playback-poll-active="true"' in html.text
    assert f'data-playback-poll-url="/meetings/{seeds.ready_id}"' in html.text
    playback_paths = [path for path in schema["paths"] if "playback" in path]
    assert playback_paths
    assert all(set(schema["paths"][path]) <= {"get"} for path in playback_paths)
    forbidden = ("retry", "reprocess-playback", "backfill", "повторить", "конвертировать")
    assert not any(word in html.text.casefold() for word in forbidden)
