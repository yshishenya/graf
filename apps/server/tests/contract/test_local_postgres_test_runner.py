import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

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
    assert 'workers="${GRAF_TEST_WORKERS:-4}"' in script
    assert "GRAF_TEST_WORKERS must be an integer from 1 through 8." in script
    assert "--dist=loadfile" in script
    assert "-m \"not strict_rls and not serial_performance\"" in script
    assert "-m \"serial_performance and not strict_rls\"" in script
    assert "if run_phase performance" in script
    assert 'performance_gate="${GRAF_PERFORMANCE_GATE:-report}"' in script
    assert 'export GRAF_PERFORMANCE_GATE="$performance_gate"' in script
    assert "refusing --fast with GRAF_PERFORMANCE_GATE=required; use --full" in script
    assert 'postgres_test_performance_gate=%s result=fail' in script
    assert "report_only_fail" not in script
    performance_test = (
        ROOT / "apps/server/tests/integration/test_calendar_auto_context_match.py"
    ).read_text(encoding="utf-8")
    assert 'os.environ.get("GRAF_PERFORMANCE_GATE", "required") == "report"' in performance_test
    assert "pytest.xfail" in performance_test
    assert "-m strict_rls" in script
    assert "--durations=20" in script
    assert "collection_digest" in script
    assert "--graf-collection-file" in script
    assert "test phase union is missing or repeats cases" in script
    assert "run_phase focused" in script
    assert "postgres_test_phase=%s status=fail" in script
    assert 'if [[ "$requested_mode" == "full" && "$mode" == "focused" ]]; then' in script
    assert "refusing --full with a focused pytest selection" in script


def test_runner_exposes_a_fast_unit_lane_without_replacing_full_coverage() -> None:
    script = RUNNER.read_text(encoding="utf-8")

    assert 'requested_mode="${argument#--}"' in script
    assert 'refusing --fast with a focused pytest selection' in script
    assert "not postgres and not browser" in script
    assert "postgres or browser" in script
    assert 'selection=(-q tests/unit)' in script
    assert 'postgres_test_result=pass mode=fast' in script


def test_local_ci_requires_an_explicit_lane_and_exposes_component_selection() -> None:
    script = LOCAL_CI.read_text(encoding="utf-8")

    assert 'requested_mode="unselected"' in script
    assert 'usage: $0 --fast|--full|--plan|--focused|--help' in script
    assert 'classify_path()' in script
    assert 'run_server_tests full' in script
    assert 'run_server_tests fast' in script
    assert "ci-receipt" not in script


def test_remote_deploy_runs_one_authoritative_full_gate() -> None:
    script = REMOTE_CD.read_text(encoding="utf-8")

    assert "echo authoritative_full_required" in script
    assert "local_ci=full_passed" in script
    assert "infra/scripts/ci-local.sh --full" in script
    assert "ci-receipt" not in script


@pytest.mark.parametrize(("args", "expected"), [
    (["--help"], 0),
    (["--fast", "--full"], 2),
    (["--focused", "--a5-invalid-option"], 4),
    (["--focused", "--collect-only", "-q", "tests/unit/test_account_closure.py"], 0),
    (["--focused", "--partitioned", "--collect-only", "-q", "tests/unit/test_account_closure.py"], 0),
])
def test_argument_and_collection_paths_do_not_start_docker(tmp_path, args, expected):
    calls = tmp_path / "docker-calls"
    docker = tmp_path / "docker"
    docker.write_text('#!/bin/sh\nprintf called >> "$DOCKER_CALLS"\nexit 79\n')
    docker.chmod(0o755)
    result = subprocess.run(
        ["bash", str(RUNNER), *args], cwd=ROOT,
        env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"], "DOCKER_CALLS": str(calls)},
        capture_output=True, text=True, check=False,
    )
    assert not calls.exists(), result.stdout + result.stderr
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.fixture
def partition_run(tmp_path):
    """Exercise real pytest collection/xdist with only uv and Docker replaced."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    events = tmp_path / "events.jsonl"
    docker_calls = tmp_path / "docker.jsonl"
    uv = bin_dir / "uv"
    uv.write_text(f'''#!{sys.executable}
import json, os, sys
os.environ["PYTHONPATH"] = {str(ROOT / "apps/server/tests/fixtures")!r}
os.chdir({str(tmp_path)!r})
args = sys.argv[sys.argv.index("pytest") + 1:]
args = ["test_resources" if arg == "tests.fixtures.test_resources" else arg for arg in args]
if os.environ.get("TAMPER_PHASE") and "--graf-phase-file" in args:
    path = args[args.index("--graf-phase-file") + 1]
    value = json.load(open(path))
    value["nodeids"].append("test_missing.py::test_missing")
    with open(path, "w") as output: json.dump(value, output)
os.execv(sys.executable, [sys.executable, "-m", "pytest", "-p", "test_resources", *args])
''')
    docker = bin_dir / "docker"
    docker.write_text(f'''#!{sys.executable}
import json, os, sys
with open(os.environ["DOCKER_CALLS"], "a") as output:
    output.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1] == "logs": print("PostgreSQL init process complete; ready for start up.")
if sys.argv[1] == "port": print("127.0.0.1:54329")
''')
    uv.chmod(0o755)
    docker.chmod(0o755)
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers =\n    strict_rls\n    serial_performance\n    selected\n")
    (tmp_path / "conftest.py").write_text('''import json, os
import pytest
from postgres_test_database import worker_database_name
@pytest.fixture(autouse=True)
def record(request):
    worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
    with open(os.environ["EVENTS"], "a") as output:
        output.write(json.dumps({"name": request.node.name,
            "worker": worker, "prefix": os.environ.get("GRAF_TEST_DATABASE_PREFIX"),
            "database": worker_database_name(worker)}) + "\\n")
    assert os.environ.get("FAIL_CASE") != request.node.name
''')
    for name, markers in {"plain": ["selected"], "other": [],
                          "performance": ["selected", "serial_performance"],
                          "strict": ["selected", "strict_rls"],
                          "both": ["selected", "strict_rls", "serial_performance"]}.items():
        (tmp_path / f"test_{name}.py").write_text(
            "import pytest\n" + "".join(f"@pytest.mark.{marker}\n" for marker in markers)
            + f"def test_{name}(): pass\n"
        )

    def run(*args, fail_case="", addopts="", config_addopts="", tamper_phase="", full=False):
        if config_addopts:
            with (tmp_path / "pytest.ini").open("a") as output:
                output.write("addopts = " + config_addopts + "\n")
        result = subprocess.run(
            ["bash", str(RUNNER), "--full" if full else "--focused", *args,
             *([] if full else [str(tmp_path)])], cwd=ROOT,
            env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                 "EVENTS": str(events), "DOCKER_CALLS": str(docker_calls), "FAIL_CASE": fail_case,
                 "TAMPER_PHASE": tamper_phase,
                 "GRAF_TEST_WORKERS": "2", "PYTEST_ADDOPTS": addopts, "GRAF_TEST_REPORT_DIR": ""},
            capture_output=True, text=True, check=False, timeout=60,
        )
        rows = [json.loads(line) for line in events.read_text().splitlines()] if events.exists() else []
        calls = [json.loads(line) for line in docker_calls.read_text().splitlines()] if docker_calls.exists() else []
        return result, rows, calls
    return run


@pytest.mark.parametrize("failure,expected", [
    ("", {"test_both", "test_strict", "test_performance", "test_plain", "test_other"}),
    ("test_strict", {"test_both", "test_strict"}),
    ("test_performance", {"test_both", "test_strict", "test_performance"}),
])
def test_full_checks_short_serial_phases_first_and_cleans_up(partition_run, failure, expected):
    result, rows, calls = partition_run("-q", full=True, fail_case=failure)
    assert (result.returncode != 0) == bool(failure), result.stdout + result.stderr
    assert {row["name"] for row in rows} == expected
    assert {row["name"] for row in rows[:2]} == {"test_both", "test_strict"}
    assert all(row["worker"] == "master" for row in rows[:3])
    if not failure:
        assert rows[2]["name"] == "test_performance"
        assert all(row["worker"].startswith("gw") for row in rows[3:])
        assert "mode=full collection_digest=" in result.stdout
    else:
        assert "postgres_test_result=pass" not in result.stdout
    assert len(rows) == len(expected)
    assert calls[-1][0] == "rm"


@pytest.mark.parametrize("marker_args", [("-m", "other", "-m", "selected"), ("-mselected",)])
def test_partition_preserves_selection_and_serial_marker_precedence(partition_run, marker_args):
    result, rows, calls = partition_run("--partitioned", *marker_args, "-k", "not other", "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(row["name"] for row in rows) == ["test_both", "test_performance", "test_plain", "test_strict"]
    assert rows[0]["name"] == "test_plain" and rows[0]["worker"].startswith("gw")
    assert all(row["worker"] == "master" for row in rows[1:])
    assert rows[1]["name"] == "test_performance"
    assert len({row["prefix"] for row in rows}) == 1
    assert all(row["database"] == row["prefix"] + "_" + row["worker"] for row in rows)
    assert calls[-1][0] == "rm"
    assert "mode=focused" in result.stdout and "partitioned=true" in result.stdout


def test_ordinary_focused_remains_serial(partition_run):
    result, rows, _ = partition_run("-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(rows) == 5 and all(row["worker"] == "master" for row in rows)


def test_partition_keeps_env_and_config_selection(partition_run):
    result, rows, _ = partition_run("--partitioned", "-q", addopts="-m selected", config_addopts="-k 'not other'")
    assert result.returncode == 0, result.stdout + result.stderr
    assert {row["name"] for row in rows} == {"test_plain", "test_performance", "test_strict", "test_both"}
    assert all(row["worker"] == "master" for row in rows if row["name"] != "test_plain")


@pytest.mark.parametrize("options", ["-f", "--looponfail", "-d", "-n3", "--dist=load",
                                     "--tx=popen", "--max-worker-restart=2"])
@pytest.mark.parametrize("source", ["cli", "env", "config"])
def test_partition_rejects_effective_xdist_options_before_collection(partition_run, tmp_path, options, source):
    # Collection must not import a test module, let alone start a loop/worker/DB.
    sentinel = tmp_path / "collected"
    (tmp_path / "test_sentinel.py").write_text(
        f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\ndef test_ok(): pass\n"
    )
    args = (options,) if source == "cli" else ()
    kwargs = {"addopts" if source == "env" else "config_addopts": options} if source != "cli" else {}
    result, rows, calls = partition_run("--partitioned", "--collect-only", *args, **kwargs)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "partitioned owns" in result.stdout + result.stderr
    assert not sentinel.exists() and not rows and not calls


def test_partition_uses_distinct_worker_databases(partition_run):
    result, rows, _ = partition_run("--partitioned", "-k", "plain or other", "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(rows) == 2 and len({row["database"] for row in rows}) == 2


def test_partition_keeps_explicit_deselection_and_ignore(partition_run, tmp_path):
    result, rows, _ = partition_run("--partitioned", "--ignore", str(tmp_path / "test_other.py"),
                                   "--deselect=test_both.py::test_both", "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert {row["name"] for row in rows} == {"test_plain", "test_performance", "test_strict"}


def test_partition_large_inventory_avoids_macos_argv_limit(partition_run, tmp_path):
    (tmp_path / "test_many.py").write_text(
        "import pytest\n@pytest.mark.serial_performance\n"
        "@pytest.mark.parametrize('value', range(1500), ids=lambda value: 'x' * 200 + str(value))\n"
        "def test_many(value): pass\n"
    )
    result, rows, _ = partition_run("--partitioned", "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(rows) == len({row["name"] for row in rows}) == 1505


def test_partition_does_not_confuse_nodeid_prefixes(partition_run, tmp_path):
    (tmp_path / "test_prefix.py").write_text(
        "import pytest\ndef test_prefix(): pass\n"
        "@pytest.mark.strict_rls\ndef test_prefix_longer(): pass\n"
    )
    result, rows, _ = partition_run("--partitioned", "-k", "prefix", "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert {row["name"] for row in rows} == {"test_prefix", "test_prefix_longer"}
    assert next(row for row in rows if row["name"] == "test_prefix_longer")["worker"] == "master"


def test_partition_rejects_changed_inventory_before_running_cases(partition_run):
    result, rows, calls = partition_run("--partitioned", "-k", "performance", "-q", tamper_phase="1")
    assert result.returncode != 0
    assert "differs from the original collection" in result.stderr + result.stdout
    assert not rows and calls[-1][0] == "rm"


@pytest.mark.parametrize("selection,expected", [
    (("-k", "plain"), 0), (("-k", "absent"), 5),
    (("--collect-only",), 0), (("--invalid-partition-option",), 4),
    (("--full",), 2), (("-n2",), 2), (("--dist=load",), 2),
])
def test_partition_empty_groups_and_pre_execution_failures(partition_run, selection, expected):
    result, rows, calls = partition_run("--partitioned", *selection, "-q")
    assert result.returncode == expected, result.stdout + result.stderr
    if selection == ("-k", "plain"):
        assert [row["name"] for row in rows] == ["test_plain"]
    else:
        assert not calls and not rows


@pytest.mark.parametrize("case,expected_names", [
    ("plain", {"test_plain"}),
    ("performance", {"test_plain", "test_performance"}),
    ("strict", {"test_plain", "test_performance", "test_strict"}),
])
def test_partition_failure_stops_following_phases_and_cleans_up(partition_run, case, expected_names):
    result, rows, calls = partition_run("--partitioned", "-k", "not both and not other", "-q", fail_case=f"test_{case}")
    assert result.returncode == 1, result.stdout + result.stderr
    assert {row["name"] for row in rows} == expected_names
    assert calls[-1][0] == "rm"
