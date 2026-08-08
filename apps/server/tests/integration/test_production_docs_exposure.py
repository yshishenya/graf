from pathlib import Path

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app

REPO_ROOT = Path(__file__).parents[4]


def test_production_disables_interactive_docs_and_openapi_json() -> None:
    app = create_app(
        Settings(
            env="production",
            database_url="postgresql+asyncpg://twobrain_rec:secret@rec-postgres:5432/twobrain_rec",
            minio_endpoint="rec-minio:9000",
            minio_access_key="twobrain_rec_api",
            minio_secret_key="prod-api-secret",
            minio_bucket="test-bucket",
            web_csrf_secret="prod-web-csrf-secret-32-bytes-minimum",
            auth_ru_local_storage_attested=True,
            playback_normalization_enabled=True,
            temporal_address="rec-temporal:7233",
        )
    )

    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_deployment_docs_and_templates_do_not_contain_live_secret_markers() -> None:
    paths = [
        REPO_ROOT / "docs/deployments/2brain-rec/README.md",
        REPO_ROOT / "infra/env/rec.production.env.example",
    ]

    forbidden = ["Bearer ", "X-Amz-Signature", "twobrain_rec_dev_secret", "minioadmin"]
    for path in paths:
        text = path.read_text()
        for marker in forbidden:
            assert marker not in text
