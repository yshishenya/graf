import asyncio

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import twobrain_rec_server.main as main_module
from twobrain_rec_server.config import Settings


def test_main_module_does_not_construct_app_at_import_time() -> None:
    assert "app" not in main_module.__dict__


def test_app_lifespan_disposes_engine_and_closes_storage(monkeypatch, postgres_worker_database_url: str) -> None:
    class FakeEngine:
        disposed = False

        async def dispose(self) -> None:
            self.disposed = True

    class FakeStorage:
        closed = False

        def close(self) -> None:
            self.closed = True

    engine = FakeEngine()
    storage = FakeStorage()
    monkeypatch.setattr(main_module, "create_engine", lambda _settings: engine)
    monkeypatch.setattr(main_module, "create_sessionmaker", lambda _created_engine: object())
    monkeypatch.setattr(main_module, "get_storage", lambda _settings: storage)

    app = main_module.create_app(
        Settings(
            database_url=postgres_worker_database_url,
            minio_endpoint="localhost:9000",
            minio_access_key="test",
            minio_secret_key="test",
            minio_bucket="test-bucket",
        )
    )

    with TestClient(app):
        pass

    assert engine.disposed is True
    assert storage.closed is True


def test_development_lifespan_runs_and_stops_calendar_reconciler(
    monkeypatch, postgres_worker_database_url: str, tmp_path
) -> None:
    class FakeEngine:
        async def dispose(self) -> None:
            pass

    started = asyncio.Event()
    stopped = asyncio.Event()

    async def fake_reconciler(_settings) -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    key_file = tmp_path / "calendar-key"
    key_file.write_bytes(Fernet.generate_key())
    monkeypatch.setattr(main_module, "create_engine", lambda _settings: FakeEngine())
    monkeypatch.setattr(main_module, "create_sessionmaker", lambda _engine: object())
    monkeypatch.setattr(main_module, "get_storage", lambda _settings: object())
    monkeypatch.setattr(main_module, "run_calendar_sync_reconciler", fake_reconciler)
    app = main_module.create_app(
        Settings(
            env="development",
            database_url=postgres_worker_database_url,
            minio_endpoint="localhost:9000",
            minio_access_key="test",
            minio_secret_key="test",
            minio_bucket="test-bucket",
            credential_encryption_key_file=key_file,
        )
    )

    with TestClient(app):
        assert started.is_set()

    assert stopped.is_set()
