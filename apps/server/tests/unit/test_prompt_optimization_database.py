from types import SimpleNamespace

import pytest

from twobrain_rec_server.db import session as session_module


def _settings(url: str) -> SimpleNamespace:
    return SimpleNamespace(prompt_optimization_database_url=url)


def test_prompt_optimization_database_rejects_non_maintenance_role(monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="maintenance database role"):
        session_module.create_prompt_optimization_database(
            _settings("postgresql+asyncpg://twobrain_rec_app:pw@db:5432/rec")
        )


def test_prompt_optimization_database_attaches_exact_rls_context(monkeypatch) -> None:
    engine = object()

    class FakeSession:
        def __init__(self) -> None:
            self.sync_session = self
            self.info: dict[str, object] = {}

    monkeypatch.setattr(session_module, "create_engine", lambda *_args, **_kwargs: engine)
    monkeypatch.setattr(session_module, "create_sessionmaker", lambda _engine: FakeSession)

    _engine, sessionmaker = session_module.create_prompt_optimization_database(
        _settings("postgresql+asyncpg://twobrain_rec_maintenance:pw@db:5432/rec"),
        actor_id="owner:t057",
        reason_category="t057_live_run",
    )

    session = sessionmaker()
    assert session.info["tenant_context"] == {
        "app.context_kind": "maintenance",
        "app.maintenance_operation": "prompt_optimization",
        "app.maintenance_actor": "owner:t057",
        "app.maintenance_reason": "t057_live_run",
        "app.maintenance_feature_area": "prompt_optimization",
    }
