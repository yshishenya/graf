from fastapi.testclient import TestClient

import twobrain_rec_server.main as main_module
from twobrain_rec_server.config import Settings


def test_main_module_does_not_construct_app_at_import_time() -> None:
    assert "app" not in main_module.__dict__


def test_app_lifespan_disposes_engine_and_closes_storage(monkeypatch, tmp_path) -> None:
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
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'lifecycle.db'}",
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
