from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SERVER_ROOT.parents[1]


def test_pipeline_markers_are_registered() -> None:
    pyproject = (SERVER_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for marker in ("requires_postgres", "governance", "strict_rls", "spike"):
        assert f'"{marker}:' in pyproject


def test_postgres_runner_has_safe_boundary_and_phase_accounting() -> None:
    runner = (SERVER_ROOT / "scripts" / "run_local_postgres_tests.sh").read_text(
        encoding="utf-8"
    )

    for marker in (
        "postgres:17-alpine",
        "127.0.0.1",
        "twobrain_rec_test_",
        "trap cleanup EXIT",
        "collection",
        "strict_rls",
        "phase",
    ):
        assert marker in runner


def test_full_runner_orders_ordinary_governance_and_strict_phases_without_optional_spikes() -> None:
    runner = (SERVER_ROOT / "scripts" / "run_local_postgres_tests.sh").read_text(encoding="utf-8")

    ordinary = '"not governance and not strict_rls and not spike"'
    governance = '"governance and not strict_rls and not spike"'
    strict = '"strict_rls and not spike"'
    assert ordinary in runner
    assert governance in runner
    assert strict in runner
    assert runner.index("run_phase ordinary") < runner.index("run_phase governance") < runner.index(
        "run_phase strict"
    )


def test_ci_local_exposes_fast_full_and_governance_lanes() -> None:
    ci = (REPO_ROOT / "infra" / "scripts" / "ci-local.sh").read_text(encoding="utf-8")

    for lane in ("--fast", "--full", "--governance"):
        assert lane in ci
