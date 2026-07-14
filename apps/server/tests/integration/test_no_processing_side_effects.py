from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.artifacts import deterministic_wav_bytes
from twobrain_rec_server.db.models import (
    MediaScribeJob,
    PlaybackNormalizationJob,
    ProcessingResult,
    ProcessingWorkflow,
)


def test_readiness_excludes_temporal_and_mediascribe_dependencies(client) -> None:
    response = client.get(
        "/api/v1/health/ready/internal",
        headers=auth_headers() | {"X-Internal-Health-Check": "true"},
    )
    assert response.status_code == 200
    checks = response.json()["checks"]
    assert checks["temporal"] == "not_required"
    assert checks["mediascribe"] in {"not_required", "not_configured"}
    assert checks["langfuse"] in {"not_required", "not_configured"}


def test_manual_normalization_dispatch_has_no_processing_side_effects(client) -> None:
    temporal = FakeTemporalClient()
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.settings.processing_enabled = False
    client.app.state.temporal_client = temporal

    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "duration_seconds": "30",
            "local_recording_id": "manual-normalization-no-processing",
        },
        files={"file": ("audio.wav", deterministic_wav_bytes(256), "audio/wav")},
    )

    assert response.status_code == 202

    async def counts() -> tuple[int, int, int, int]:
        async with client.app_state["sessionmaker"]() as db:
            values = []
            for model in (
                PlaybackNormalizationJob,
                ProcessingWorkflow,
                MediaScribeJob,
                ProcessingResult,
            ):
                values.append(await db.scalar(select(func.count()).select_from(model)))
            return tuple(values)

    normalization_jobs, workflows, provider_jobs, results = client.portal.call(counts)
    assert normalization_jobs == 1
    assert workflows == 0
    assert provider_jobs == 0
    assert results == 0
    assert len(temporal.starts) == 1
    assert next(iter(temporal.starts)).startswith("playback-normalization/")
