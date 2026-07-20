from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.fakes.auth_contexts import (
    DEVICE_ID,
    ORG_ID,
    REVOKED_DEVICE_ID,
    USER_ID,
    WORKSPACE_ID,
)
from tests.fakes.fake_minio import FakeMinioStorage
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import add_retained_playback_m4a
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.base import Base
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingTargetRegistryEntry,
    MeetingTargetRegistryVersion,
    Organization,
    PlaybackNormalizationJob,
    RegisteredDevice,
    TrackArtifact,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.ingest.store import InMemoryIngestStore
from twobrain_rec_server.main import create_app
from twobrain_rec_server.meeting_detection.registry import registry_entries, registry_etag
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
)

REGISTRY_DATA = (
    Path(__file__).resolve().parents[2]
    / "src/twobrain_rec_server/db/migrations/data/0019_meeting_target_registry.json"
)
SYNTHETIC_DURATION_SECONDS = 40
TEST_DATABASE_PREFIX = "twobrain_rec_test_"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


async def _seed_database(app: FastAPI) -> None:
    async with app.state.db_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    registry_document = json.loads(REGISTRY_DATA.read_text(encoding="utf-8"))
    async with app.state.db_sessionmaker() as session:
        registry_version = MeetingTargetRegistryVersion(
            workspace_id=None,
            registry_version=registry_document["registryVersion"],
            schema_version=registry_document["schemaVersion"],
            status="published",
            source="migration",
            document_json=registry_document,
            etag=registry_etag(registry_document),
        )
        session.add_all(
            [
                Organization(id=ORG_ID, slug="e2e-org", name="Feature 099 E2E"),
                Workspace(
                    id=WORKSPACE_ID,
                    organization_id=ORG_ID,
                    slug="e2e-workspace",
                    name="Feature 099 E2E",
                ),
                UserIdentity(
                    id=USER_ID,
                    organization_id=ORG_ID,
                    external_subject=str(USER_ID),
                    display_name="Feature 099 Owner",
                ),
                WorkspaceMembership(
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    role="owner",
                    status="active",
                ),
                RegisteredDevice(
                    id=DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="feature-099-device",
                    status="active",
                ),
                RegisteredDevice(
                    id=REVOKED_DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="feature-099-revoked-device",
                    status="revoked",
                ),
                registry_version,
            ]
        )
        await session.flush()
        session.add_all(
            MeetingTargetRegistryEntry(registry_version_id=registry_version.id, **entry)
            for entry in registry_entries(registry_document)
        )
        await session.commit()


def _synthetic_m4a(runtime_directory: Path) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required for the local UI harness")
    output = runtime_directory / "synthetic-review.m4a"
    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-xerror",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate=48000:duration={SYNTHETIC_DURATION_SECONDS}",
            "-filter:a",
            "volume=0.0001",
            "-vn",
            "-sn",
            "-dn",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-threads",
            "1",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-c:a",
            "aac",
            "-profile:a",
            "aac_low",
            "-b:a",
            "64k",
            "-disposition:a:0",
            "default",
            "-movflags",
            "+faststart",
            "-f",
            "ipod",
            str(output),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "synthetic media generation failed "
            f"with {len(completed.stderr)} bytes of redacted diagnostics"
        )
    return output.read_bytes()


async def _set_harness_truth(
    app: FastAPI,
    *,
    available_id: UUID,
    preparing_id: UUID,
    unavailable_id: UUID,
    independent_id: UUID,
) -> None:
    titles = {
        available_id: "099: playback доступен",
        preparing_id: "099: playback готовится автоматически",
        unavailable_id: "099: источник недоступен",
        independent_id: "099: playback и текст независимы",
    }
    async with app.state.db_sessionmaker() as db:
        for meeting_id, title in titles.items():
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            meeting.title = title
            meeting.duration_seconds = SYNTHETIC_DURATION_SECONDS
        ready_artifacts = list(
            await db.scalars(
                select(TrackArtifact).where(
                    TrackArtifact.meeting_id.in_((available_id, independent_id)),
                    TrackArtifact.track_role == "playback",
                )
            )
        )
        assert len(ready_artifacts) == 2
        for artifact in ready_artifacts:
            artifact.duration_seconds = SYNTHETIC_DURATION_SECONDS
        unavailable_job = await db.scalar(
            select(PlaybackNormalizationJob).where(
                PlaybackNormalizationJob.meeting_id == unavailable_id
            )
        )
        assert unavailable_job is not None
        unavailable_job.state = "terminal"
        unavailable_job.reason_code = "corrupt_source"
        unavailable_job.terminal_at = datetime.now(UTC)
        await db.commit()


async def _publish_playback(
    app: FastAPI,
    *,
    meeting_id: UUID,
    body: bytes,
) -> None:
    object_key = f"tests/feature-099/{meeting_id}/meeting-review.m4a"
    app.state.storage.put_bytes(object_key, body)
    async with app.state.db_sessionmaker() as db:
        job = await db.scalar(
            select(PlaybackNormalizationJob).where(
                PlaybackNormalizationJob.meeting_id == meeting_id,
                PlaybackNormalizationJob.profile_version == CANONICAL_PROFILE_VERSION,
            )
        )
        assert job is not None
        artifact = await db.scalar(
            select(TrackArtifact).where(
                TrackArtifact.meeting_id == meeting_id,
                TrackArtifact.media_revision_id == job.media_revision_id,
                TrackArtifact.track_role == "playback",
            )
        )
        if artifact is None:
            artifact = TrackArtifact(
                workspace_id=job.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=job.media_revision_id,
                track_role="playback",
                codec="m4a-aac-lc",
                sample_rate_hz=48_000,
                channel_count=1,
                duration_seconds=SYNTHETIC_DURATION_SECONDS,
                byte_length=len(body),
                sha256=sha256(body).hexdigest(),
                storage_object_key=object_key,
                status="stored",
            )
            db.add(artifact)
        artifact.codec = "m4a-aac-lc"
        artifact.sample_rate_hz = 48_000
        artifact.channel_count = 1
        artifact.duration_seconds = SYNTHETIC_DURATION_SECONDS
        artifact.byte_length = len(body)
        artifact.sha256 = sha256(body).hexdigest()
        artifact.storage_object_key = object_key
        artifact.status = "stored"
        artifact.normalization_profile_version = CANONICAL_PROFILE_VERSION
        artifact.validation_version = VALIDATION_VERSION
        artifact.validated_at = datetime.now(UTC)
        artifact.derivation_kind = "single_source_transcode"
        artifact.source_fingerprint_sha256 = job.source_fingerprint_sha256
        await db.flush()
        job.state = "ready"
        job.reason_code = None
        job.canonical_track_artifact_id = artifact.id
        job.ready_at = datetime.now(UTC)
        await db.commit()


async def _job_state(app: FastAPI, meeting_id: UUID) -> str:
    async with app.state.db_sessionmaker() as db:
        job = await db.scalar(
            select(PlaybackNormalizationJob).where(
                PlaybackNormalizationJob.meeting_id == meeting_id
            )
        )
        assert job is not None
        return job.state


def create_harness(
    *,
    runtime_directory: Path,
    origin: str,
    database_url: str,
) -> tuple[FastAPI, dict[str, object]]:
    settings = Settings(
        env="development",
        log_level="WARNING",
        database_url=database_url,
        minio_endpoint="localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        public_base_url=origin,
        web_login_workspace_id=WORKSPACE_ID,
        legacy_header_auth_enabled=True,
    )
    app = create_app(settings)
    app.state.storage = FakeMinioStorage()
    app.state.ingest_store = InMemoryIngestStore()
    asyncio.run(_seed_database(app))
    asyncio.run(app.state.db_engine.dispose())
    app.state.db_engine = create_engine(settings)
    app.state.db_sessionmaker = create_sessionmaker(app.state.db_engine)
    body = _synthetic_m4a(runtime_directory)

    with TestClient(app) as client:
        client.app_state["engine"] = app.state.db_engine
        client.app_state["sessionmaker"] = app.state.db_sessionmaker
        client.app_state["storage"] = app.state.storage
        seeds = seed_cabinet_meetings(client)
        add_retained_playback_m4a(client, seeds.ready_id, body)
        add_retained_playback_m4a(client, seeds.partial_id, body)
    asyncio.run(
        _set_harness_truth(
            app,
            available_id=seeds.ready_id,
            preparing_id=seeds.processing_id,
            unavailable_id=seeds.failed_id,
            independent_id=seeds.partial_id,
        )
    )
    asyncio.run(app.state.db_engine.dispose())
    app.state.db_engine = create_engine(settings)
    app.state.db_sessionmaker = create_sessionmaker(app.state.db_engine)

    harness_state: dict[str, object] = {
        "origin": origin,
        "available_id": seeds.ready_id,
        "preparing_id": seeds.processing_id,
        "unavailable_id": seeds.failed_id,
        "independent_id": seeds.partial_id,
        "transition_started": False,
        "transition_body": body,
    }

    @app.get("/__feature099/state", include_in_schema=False)
    async def feature_099_state() -> dict[str, object]:
        return {
            "available": await _job_state(app, seeds.ready_id),
            "preparing": await _job_state(app, seeds.processing_id),
            "unavailable": await _job_state(app, seeds.failed_id),
            "independent": await _job_state(app, seeds.partial_id),
            "transition_started": harness_state["transition_started"],
        }

    @app.post("/__feature099/start-transition", include_in_schema=False)
    async def feature_099_start_transition() -> dict[str, object]:
        if not harness_state["transition_started"]:
            harness_state["transition_started"] = True

            async def publish_after_delay() -> None:
                await asyncio.sleep(2.5)
                await _publish_playback(
                    app,
                    meeting_id=seeds.processing_id,
                    body=body,
                )

            asyncio.create_task(publish_after_delay())
        return {"scheduled": True, "delay_seconds": 2.5}

    return app, harness_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the isolated feature 099 UI harness")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--database-url", required=True)
    arguments = parser.parse_args()
    parsed_database_url = urlparse(arguments.database_url)
    if (
        parsed_database_url.scheme != "postgresql+asyncpg"
        or parsed_database_url.hostname not in LOOPBACK_HOSTS
        or not parsed_database_url.path.lstrip("/").startswith(TEST_DATABASE_PREFIX)
    ):
        parser.error(
            "--database-url must target a disposable local PostgreSQL database created by "
            "apps/server/scripts/run_local_postgres_tests.sh"
        )
    runtime_directory = Path(tempfile.mkdtemp(prefix="graf-feature-099-ui-"))
    origin = f"http://{arguments.host}:{arguments.port}"
    app, state = create_harness(
        runtime_directory=runtime_directory,
        origin=origin,
        database_url=arguments.database_url,
    )
    public_state = {
        "origin": origin,
        "available_id": str(state["available_id"]),
        "preparing_id": str(state["preparing_id"]),
        "unavailable_id": str(state["unavailable_id"]),
        "independent_id": str(state["independent_id"]),
    }
    if arguments.state_file is not None:
        arguments.state_file.write_text(
            json.dumps(public_state, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(public_state, sort_keys=True), flush=True)
    try:
        uvicorn.run(app, host=arguments.host, port=arguments.port, log_level="warning")
    finally:
        shutil.rmtree(runtime_directory, ignore_errors=True)
        if arguments.state_file is not None:
            arguments.state_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
