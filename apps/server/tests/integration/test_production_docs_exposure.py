from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app


def test_production_disables_interactive_docs_and_openapi_json(tmp_path) -> None:
    app = create_app(
        Settings(
            env="production",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'prod-docs.db'}",
            minio_endpoint="rec-minio:9000",
            minio_access_key="twobrain_rec_api",
            minio_secret_key="prod-api-secret",
            minio_bucket="test-bucket",
        )
    )

    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
