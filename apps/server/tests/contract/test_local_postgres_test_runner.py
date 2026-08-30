from pathlib import Path

from tests.fixtures.postgres_test_database import (
    TEST_DATABASE_PREFIX,
    TEST_DATABASE_PREFIX_ENV,
    TEST_POSTGRES_ADMIN_URL_ENV,
    TEST_POSTGRES_MEDIA_PASSWORD_ENV,
    clean_database_name,
    disposable_postgres_database_url,
    worker_database_name,
)

ROOT = Path(__file__).resolve().parents[4]
RUNNER = ROOT / "apps/server/scripts/run_local_postgres_tests.sh"
LOCAL_CI = ROOT / "infra/scripts/ci-local.sh"
REMOTE_CD = ROOT / "infra/scripts/cd-remote.sh"


def test_runner_uses_an_isolated_postgres_container_and_disposable_database_names() -> None:
    script = RUNNER.read_text(encoding="utf-8")

    assert "postgres:17-alpine" in script
    assert "docker run --detach --rm" in script
    assert "127.0.0.1::5432" in script
    assert "docker rm --force" in script
    assert "for start_attempt in 1 2" in script
    assert "postgres_test_container_start_retry=1" in script
    assert "postgres_initialized=true" in script
    assert TEST_DATABASE_PREFIX in script
    assert "RLS_TEST_DATABASE_URL" in script
    assert TEST_DATABASE_PREFIX_ENV in script
    assert TEST_POSTGRES_ADMIN_URL_ENV in script
    assert TEST_POSTGRES_MEDIA_PASSWORD_ENV in script
    assert "RLS_TEST_MEDIA_DATABASE_URL" in script
    assert "openssl rand -hex 24" in script


def test_disposable_database_url_rejects_unsafe_targets(monkeypatch) -> None:
    monkeypatch.delenv(TEST_DATABASE_PREFIX_ENV, raising=False)
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
    monkeypatch.delenv(TEST_DATABASE_PREFIX_ENV, raising=False)
    expected = "postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:54329/twobrain_rec_test_x"
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", expected)

    assert disposable_postgres_database_url() == expected


def test_worker_and_clean_database_names_are_bounded_and_run_scoped(monkeypatch) -> None:
    run_prefix = f"{TEST_DATABASE_PREFIX}runner_contract"
    monkeypatch.setenv(TEST_DATABASE_PREFIX_ENV, run_prefix)
    monkeypatch.setenv(
        "TWOBRAIN_DATABASE_URL",
        f"postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:54329/{run_prefix}",
    )

    worker_name = worker_database_name("gw0")
    clean_name = clean_database_name("gw0")

    assert worker_name == f"{run_prefix}_gw0"
    assert clean_name.startswith(f"{run_prefix}_clean_gw0_")
    assert len(clean_name) <= 63


def test_full_runner_keeps_strict_rls_tests_and_uses_a_bounded_parallel_lane() -> None:
    script = RUNNER.read_text(encoding="utf-8")

    assert script.count("--extra dev --extra evaluation") >= 4
    assert "GRAF_TEST_WORKERS" in script
    assert 'workers="${GRAF_TEST_WORKERS:-8}"' in script
    assert "GRAF_TEST_WORKERS must be an integer from 1 through 8." in script
    assert "--dist=loadfile" in script
    assert "-m \"not strict_rls and not serial_performance\"" in script
    assert "-m \"serial_performance and not strict_rls\"" in script
    assert "if run_phase performance" in script
    assert 'performance_gate="${GRAF_PERFORMANCE_GATE:-report}"' in script
    assert 'postgres_test_performance_gate=report result=report_only_fail' in script
    assert 'postgres_test_performance_gate=required result=fail' in script
    assert "-m strict_rls" in script
    assert "--durations=20" in script
    assert "collection_digest" in script
    assert "awk '/^tests\\// { print }'" in script
    assert "awk '/^tests\\// { print $1 }'" not in script
    assert "if run_phase focused" in script
    assert "postgres_test_phase=%s status=fail" in script
    assert 'if [[ "$requested_mode" == "full" && "$mode" == "focused" ]]; then' in script
    assert "refusing --full with a focused pytest selection" in script


def test_runner_exposes_a_fast_unit_lane_without_replacing_full_coverage() -> None:
    script = RUNNER.read_text(encoding="utf-8")

    assert 'requested_mode="fast"' in script
    assert 'refusing --fast with a focused pytest selection' in script
    assert 'postgres_test_mode=fast worker_count=1 suite=tests/unit' in script
    assert 'pytest "${timing_args[@]}" -q tests/unit' in script
    assert 'postgres_test_result=pass mode=fast' in script


def test_local_ci_requires_an_explicit_lane_and_exposes_component_selection() -> None:
    script = LOCAL_CI.read_text(encoding="utf-8")

    assert 'requested_mode="unselected"' in script
    assert 'usage: $0 --fast|--full|--help' in script
    assert 'classify_path()' in script
    assert 'run_server_tests full' in script
    assert 'run_server_tests fast' in script
    assert 'ci_receipt_result=skipped reason=dirty_worktree' in script


def test_remote_deploy_reuses_only_valid_full_receipt_or_runs_full_fallback() -> None:
    script = REMOTE_CD.read_text(encoding="utf-8")

    assert "valid_full_receipt_or_full_fallback" in script
    assert "python3 infra/scripts/ci-receipt.py validate" in script
    assert "local_ci=receipt_reused" in script
    assert "local_ci=full_fallback" in script
    assert "infra/scripts/ci-local.sh --full" in script
