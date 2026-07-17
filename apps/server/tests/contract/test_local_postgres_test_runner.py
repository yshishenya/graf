from pathlib import Path

from tests.fixtures.postgres_test_database import (
    TEST_DATABASE_PREFIX,
    disposable_postgres_database_url,
)

ROOT = Path(__file__).resolve().parents[4]
RUNNER = ROOT / "apps/server/scripts/run_local_postgres_tests.sh"


def test_runner_uses_only_dev_compose_and_disposable_database_names() -> None:
    script = RUNNER.read_text(encoding="utf-8")

    assert "infra/docker-compose.dev.yml" in script
    assert "infra/docker-compose.yml" not in script
    assert TEST_DATABASE_PREFIX in script
    assert "RLS_TEST_DATABASE_URL" in script
    assert "drop database if exists" in script
    assert "with (force)" in script


def test_disposable_database_url_rejects_unsafe_targets(monkeypatch) -> None:
    monkeypatch.setenv(
        "TWOBRAIN_DATABASE_URL",
        "postgresql+asyncpg://twobrain_rec:twobrain_rec@db.example.test:5432/twobrain_rec_test_x",
    )

    try:
        disposable_postgres_database_url()
    except BaseException as error:
        assert "disposable local PostgreSQL" in str(error)
    else:
        raise AssertionError("unsafe remote target must be rejected")


def test_disposable_database_url_accepts_runner_target(monkeypatch) -> None:
    expected = "postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:54329/twobrain_rec_test_x"
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", expected)

    assert disposable_postgres_database_url() == expected
