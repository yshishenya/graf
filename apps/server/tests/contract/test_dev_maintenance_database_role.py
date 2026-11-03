from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml
from sqlalchemy.engine import make_url

SERVER_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SERVER_ROOT.parents[1]


def dev_compose() -> dict:
    class Loader(yaml.SafeLoader):
        pass

    Loader.add_constructor("!override", lambda loader, node: loader.construct_sequence(node))
    return yaml.load((REPO_ROOT / "infra/docker-compose.dev.yml").read_text(), Loader=Loader)


def dev_role_helper(monkeypatch):
    monkeypatch.syspath_prepend(str(SERVER_ROOT / "scripts"))
    return importlib.import_module("bootstrap_dev_database_roles")


def test_dev_maintenance_waits_for_protected_role_after_migrations() -> None:
    services = dev_compose()["services"]
    maintenance = services["rec-maintenance"]
    assert make_url(maintenance["environment"]["TWOBRAIN_DATABASE_URL"]).username == "twobrain_rec_maintenance"
    assert maintenance["depends_on"]["rec-db-runtime-bootstrap"]["condition"] == "service_completed_successfully"
    bootstrap = services["rec-db-runtime-bootstrap"]
    assert bootstrap["depends_on"]["rec-migrate"]["condition"] == "service_completed_successfully"
    assert bootstrap["depends_on"]["rec-postgres"]["condition"] == "service_healthy"
    assert bootstrap["image"] == services["rec-migrate"]["image"]
    assert bootstrap["restart"] == "no"
    assert bootstrap["command"] == ["python", "/app/scripts/bootstrap_dev_database_roles.py"]
    assert bootstrap["environment"]["TWOBRAIN_ENV"] == "development"


@pytest.mark.parametrize("environment", ["production", "test", ""])
def test_dev_bootstrap_refuses_other_environments(monkeypatch, environment):
    import asyncio

    helper = dev_role_helper(monkeypatch)
    monkeypatch.setenv("TWOBRAIN_ENV", environment)
    calls = []

    async def forbidden():
        calls.append(True)

    monkeypatch.setattr(helper, "_bootstrap", forbidden)
    with pytest.raises(RuntimeError, match="development"):
        asyncio.run(helper.bootstrap_development_roles())
    assert calls == []


@pytest.mark.parametrize("failure", [False, True])
def test_dev_bootstrap_reuses_guarded_helper_and_removes_temporary_passwords(monkeypatch, failure):
    import asyncio
    import os
    import stat

    helper = dev_role_helper(monkeypatch)
    monkeypatch.setenv("TWOBRAIN_ENV", "development")
    for name in ("OWNER", "APP", "MAINTENANCE", "MEDIA"):
        monkeypatch.setenv(f"TWOBRAIN_DB_{name}_PASSWORD", "synthetic-local-password")
        monkeypatch.delenv(f"TWOBRAIN_DB_{name}_PASSWORD_FILE", raising=False)
    observed_paths = []

    async def shared_bootstrap():
        for name in ("OWNER", "APP", "MAINTENANCE", "MEDIA"):
            path = Path(os.environ[f"TWOBRAIN_DB_{name}_PASSWORD_FILE"])
            assert path.read_text() == "synthetic-local-password"
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            observed_paths.append(path)
        if failure:
            raise RuntimeError("synthetic bootstrap failure")

    monkeypatch.setattr(helper, "_bootstrap", shared_bootstrap)
    if failure:
        with pytest.raises(RuntimeError, match="synthetic bootstrap failure"):
            asyncio.run(helper.bootstrap_development_roles())
    else:
        asyncio.run(helper.bootstrap_development_roles())
    assert len(observed_paths) == 4
    assert all(not path.exists() for path in observed_paths)
    assert all(f"TWOBRAIN_DB_{name}_PASSWORD_FILE" not in os.environ
               for name in ("OWNER", "APP", "MAINTENANCE", "MEDIA"))
