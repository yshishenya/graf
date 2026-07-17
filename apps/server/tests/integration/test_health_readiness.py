from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.fakes.fake_minio import FakeMinioStorage
from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app


def test_ready_reports_not_ready_when_database_probe_fails(client) -> None:
    client.app.state.db_sessionmaker = None

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}

    blocked_internal = client.get("/api/v1/health/ready/internal")
    assert blocked_internal.status_code == 403
    assert blocked_internal.json() == {"status": "forbidden"}

    internal = client.get("/api/v1/health/ready/internal", headers={"X-Internal-Health-Check": "true"})
    assert internal.status_code == 503
    assert internal.json()["checks"]["postgres"] == "unreachable"


def test_ready_reports_not_ready_when_minio_probe_fails(client) -> None:
    class FailingStorage:
        def ensure_bucket(self) -> None:
            raise RuntimeError("minio unavailable")

    client.app.state.storage = FailingStorage()

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}

    internal = client.get("/api/v1/health/ready/internal", headers={"X-Internal-Health-Check": "true"})
    assert internal.status_code == 503
    assert internal.json()["checks"]["minio"] == "unreachable"


def test_ready_reports_ready_without_dependency_detail(client) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

    internal = client.get("/api/v1/health/ready/internal", headers={"X-Internal-Health-Check": "true"})
    assert internal.status_code == 200
    assert internal.json()["status"] == "ready"
    assert internal.json()["checks"]["postgres"] == "ok"
    assert internal.json()["checks"]["minio"] == "ok"


def test_ready_reports_not_ready_when_database_schema_is_empty(postgres_clean_database_url: str) -> None:
    database_url = postgres_clean_database_url
    settings = Settings(
        database_url=database_url,
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
    )
    engine = create_async_engine(database_url)
    app = create_app(settings)
    app.state.db_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    app.state.storage = FakeMinioStorage()

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/health/ready")
        internal = test_client.get("/api/v1/health/ready/internal", headers={"X-Internal-Health-Check": "true"})
    import asyncio

    asyncio.run(engine.dispose())

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert internal.status_code == 503
    assert internal.json()["checks"]["postgres"] == "unreachable"
