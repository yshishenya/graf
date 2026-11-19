import hashlib
import json
import os
import shlex
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

    phase = script.split("run_phase() {", 1)[1].split("start_postgres() {", 1)[0]
    assert 'uv "${uv_run[@]}" --extra dev --extra evaluation pytest "${report_args[@]}" "$@"' in phase
    assert 'uv "${uv_collection[@]}" --extra dev --extra evaluation pytest -c "$repo_root/apps/server/pyproject.toml" --collect-only' in script
    assert 'uv_run+=(--no-sync)' in script
    assert 'uv_collection+=(--no-sync)' in script
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
    assert "postgres_test_result=pass" not in result.stdout
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
args = [{str(tmp_path)!r} if arg == "tests/unit" else arg for arg in args]
# The real project config is covered by test_test_resources.py; keep this fixture isolated.
args = [{str(tmp_path / "pytest.ini")!r} if arg == {str(ROOT / "apps/server/pyproject.toml")!r} else arg for arg in args]
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
            "database": worker_database_name(worker) if os.environ.get("GRAF_TEST_DATABASE_PREFIX") else None}) + "\\n")
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

    def run(*args, fail_case="", addopts="", config_addopts="", tamper_phase="", full=False, fast=False, runner=RUNNER):
        if config_addopts:
            with (tmp_path / "pytest.ini").open("a") as output:
                output.write("addopts = " + config_addopts + "\n")
        result = subprocess.run(
            ["bash", str(runner), "--fast" if fast else "--full" if full else "--focused", *args,
             *([] if full or fast else [str(tmp_path)])], cwd=ROOT,
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


def test_partition_keeps_path_separator(partition_run):
    result, rows, calls = partition_run("--partitioned", "-q", "--")
    assert result.returncode == 0, result.stdout + result.stderr
    assert {row["name"] for row in rows} == {
        "test_plain", "test_other", "test_performance", "test_strict", "test_both",
    }
    assert len(rows) == 5
    assert all(row["worker"].startswith("gw") for row in rows[:2])
    assert all(row["worker"] == "master" for row in rows[2:])
    assert calls[-1][0] == "rm"


def test_partition_keeps_env_and_config_selection(partition_run):
    result, rows, _ = partition_run("--partitioned", "-q", addopts="-m selected", config_addopts="-k 'not test_performance'")
    assert result.returncode == 0, result.stdout + result.stderr
    assert {row["name"] for row in rows} == {"test_plain", "test_strict", "test_both"}
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


@pytest.mark.parametrize(("args", "message"), [
    (("--shard", "1/4", "-q"), "--shard requires --focused --partitioned"),
    (("--focused", "--shard", "1/4"), "--shard requires --focused --partitioned"),
    (("--focused", "--partitioned", "--shard", "4/4"), "index must be 0-based"),
    (("--focused", "--partitioned", "--shard", "1/1"), "total >= 2"),
    (("--focused", "--partitioned", "--shard", "2/0"), "total >= 2"),
    (("--focused", "--partitioned", "--shard", "1"), "expected index/total"),
    (("--focused", "--partitioned", "--shard", "a/b"), "expected index/total"),
    (("--focused", "--partitioned", "--shard", "-1/4"), "expected index/total"),
    (("--focused", "--partitioned", "--shard", "2/"), "expected index/total"),
    (("--focused", "--partitioned", "--shard", "2/4/1"), "expected index/total"),
    (("--shard",), "requires an index/total"),
    (("--focused", "--partitioned", "--phases", "strict,unknown"), "unknown test phase"),
    (("--focused", "--partitioned", "--phases", "strict,strict"), "repeated test phase"),
    (("--focused", "--partitioned", "--phases", "strict,"), "comma-separated phase list"),
    (("--focused", "--partitioned", "--phases", ""), "comma-separated phase list"),
    (("--focused", "--partitioned", "--phases", "STRICT"), "comma-separated phase list"),
    (("--focused", "--phases", "strict"), "--phases requires --focused --partitioned"),
    (("--phases",), "requires a comma-separated"),
])
def test_partition_flag_validation_rejects_bad_requests(tmp_path, args, message):
    calls = tmp_path / "docker-calls"
    docker = tmp_path / "docker"
    docker.write_text('#!/bin/sh\nprintf called >> "$DOCKER_CALLS"\nexit 79\n')
    docker.chmod(0o755)
    result = subprocess.run(
        ["bash", str(RUNNER), *args], cwd=ROOT,
        env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"], "DOCKER_CALLS": str(calls)},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert message in result.stdout + result.stderr, result.stdout + result.stderr
    assert not calls.exists(), result.stdout + result.stderr


@pytest.mark.parametrize("shard,expected", [
    ("0/2", {"test_other"}),
    ("1/2", {"test_plain"}),
])
def test_partition_shard_executes_exactly_one_slice(partition_run, shard, expected):
    result, rows, calls = partition_run("--partitioned", "--phases", "parallel", "--shard", shard, "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    # The declared part covers only its own slice, and never the serial phases.
    assert {row["name"] for row in rows} == expected
    assert all(row["worker"].startswith("gw") for row in rows)
    assert f"postgres_test_shard={shard} shard_count=1 parallel_count=2" in result.stdout
    assert "postgres_test_result=pass mode=focused partitioned=true shard=" in result.stdout
    assert calls[-1][0] == "rm"


def test_partition_shard_without_cases_fails_before_postgres(partition_run):
    result, rows, calls = partition_run("--partitioned", "--phases", "parallel", "--shard", "2/4", "-q")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "selected no cases" in result.stdout + result.stderr
    assert not rows and not calls


def test_partition_shard_forces_the_parallel_phase_set(partition_run):
    result, rows, _ = partition_run("--partitioned", "--shard", "0/2", "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert {row["name"] for row in rows} == {"test_other"}
    assert "postgres_test_shard_forced_phases=parallel" in result.stdout


def test_partition_shard_rejects_changed_inventory_before_running_cases(partition_run):
    # Under xdist a collection mismatch aborts the phase without running a case;
    # the precise slice check itself is covered by the plugin contract below.
    result, rows, calls = partition_run(
        "--partitioned", "--phases", "parallel", "--shard", "0/2", "-k", "plain", "-q", tamper_phase="1"
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert not rows
    assert "postgres_test_phase=focused-parallel status=fail" in result.stderr
    assert "no tests ran" in result.stdout
    assert calls[-1][0] == "rm"


def test_phase_shard_declaration_must_equal_the_collection_slice(tmp_path):
    """Часть обязана быть ровно срезом nodeids[index::total] собранного набора."""
    for name in ("plain", "other"):
        (tmp_path / f"test_{name}.py").write_text(f"def test_{name}(): pass\n")
    (tmp_path / "test_strictly.py").write_text(
        "import pytest\n@pytest.mark.strict_rls\ndef test_strictly(): pass\n"
    )
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers =\n    strict_rls\n    serial_performance\n")
    phase = tmp_path / "parallel.json"
    # The sorted parallel phase is [test_other.py::test_other, test_plain.py::test_plain].
    phase.write_text(json.dumps({"phase": "parallel", "nodeids": ["test_other.py::test_other"]}))
    env = {**os.environ, "PYTHONPATH": str(ROOT / "apps/server/tests/fixtures")}

    def collect(shard: str):
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "test_resources", "-c", str(tmp_path / "pytest.ini"),
             "--collect-only", "-q", f"--graf-phase-file={phase}", f"--graf-phase-shard={shard}", str(tmp_path)],
            cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
        )

    accepted = collect("0/2")
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert "test_other" in accepted.stdout and "test_plain" not in accepted.stdout
    rejected = collect("1/2")
    assert rejected.returncode != 0
    assert "differs from the original collection" in rejected.stdout + rejected.stderr
    undeclared = collect("")
    assert undeclared.returncode != 0
    assert "differs from the original collection" in undeclared.stdout + undeclared.stderr


@pytest.mark.parametrize("phases,expected", [
    ("parallel", {"test_plain", "test_other"}),
    ("strict", {"test_both", "test_strict"}),
    ("performance", {"test_performance"}),
    ("strict,performance", {"test_both", "test_strict", "test_performance"}),
])
def test_partition_phases_select_exact_groups(partition_run, phases, expected):
    result, rows, calls = partition_run("--partitioned", "--phases", phases, "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert {row["name"] for row in rows} == expected
    assert len(rows) == len(expected)
    assert calls[-1][0] == "rm"


@pytest.mark.parametrize("mode,original_status", [
    ((), 0), (("--partitioned",), 0), (("--full",), 0), (("--fast",), 0),
    (("--partitioned", "--shard", "0/2"), 0),
    (("--partitioned",), 17), (("--partitioned",), 130), (("--partitioned",), 143),
])
def test_cleanup_failure_preserves_failure_or_rejects_success(partition_run, tmp_path, mode, original_status):
    docker = tmp_path / "bin/docker"
    docker.write_text(docker.read_text().replace(
        'if sys.argv[1] == "logs":',
        'if sys.argv[1] == "rm": sys.exit(91)\nif sys.argv[1] == "logs":',
    ))
    if original_status:
        uv = tmp_path / "bin/uv"
        uv.write_text(uv.read_text().replace(
            "os.execv(sys.executable,",
            'if "--collect-only" not in args:\n'
            + (f'    os.kill(os.getppid(), {original_status - 128})\n    sys.exit(0)\n'
               if original_status >= 128 else f'    sys.exit({original_status})\n')
            + "os.execv(sys.executable,",
        ))
    result, _, calls = partition_run(
        *(arg for arg in mode if arg not in {"--full", "--fast"}), "-q",
        full="--full" in mode, fast="--fast" in mode,
    )
    assert result.returncode == (original_status or 1), result.stdout + result.stderr
    assert "postgres_test_result=pass" not in result.stdout
    assert "postgres_test_cleanup=isolated_container_remove_failed" in result.stderr
    assert "postgres_test_cleanup=isolated_container_removed" not in result.stdout
    started = next(call[call.index("--name") + 1] for call in calls if call[0] == "run")
    assert [call for call in calls if call[0] == "rm"] == [["rm", "--force", "--volumes", started]]


def test_startup_cleanup_failure_keeps_container_owned(partition_run, tmp_path):
    docker = tmp_path / "bin/docker"
    docker.write_text(docker.read_text().replace(
        'if sys.argv[1] == "logs":',
        'if sys.argv[1] == "rm": sys.exit(91)\n'
        'if sys.argv[1] == "exec" and "psql" in sys.argv: sys.exit(92)\n'
        'if sys.argv[1] == "logs":',
    ))
    result, rows, calls = partition_run("--partitioned", "-q")
    assert result.returncode != 0, result.stdout + result.stderr
    assert not rows
    assert len([call for call in calls if call[0] == "run"]) == 1
    started = next(call[call.index("--name") + 1] for call in calls if call[0] == "run")
    assert [call for call in calls if call[0] == "rm"] == [
        ["rm", "--force", "--volumes", started], ["rm", "--force", "--volumes", started],
    ]
    assert "postgres_test_result=pass" not in result.stdout
    assert "postgres_test_cleanup=isolated_container_remove_failed" in result.stderr
    assert "postgres_test_cleanup=isolated_container_removed" not in result.stdout


@pytest.mark.parametrize("mode", [(), ("--partitioned",), ("--full",), ("--fast",),
                                  ("--partitioned", "--shard", "0/2")])
def test_pass_marker_follows_successful_cleanup(partition_run, mode):
    result, _, _ = partition_run(
        *(arg for arg in mode if arg not in {"--full", "--fast"}), "-q",
        full="--full" in mode, fast="--fast" in mode,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("postgres_test_result=pass") == 1
    assert result.stdout.index("postgres_test_cleanup=isolated_container_removed") < result.stdout.index("postgres_test_result=pass")


def test_fast_pure_pass_follows_cleanup_without_starting_docker(partition_run, tmp_path):
    for name in ("strict", "both"):
        (tmp_path / f"test_{name}.py").unlink()
    result, rows, calls = partition_run("-q", fast=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(rows) == 3 and not calls
    assert result.stdout.count("postgres_test_result=pass mode=fast") == 1
    assert result.stdout.index("postgres_test_cleanup=container_not_started") < result.stdout.index("postgres_test_result=pass")


@pytest.fixture
def minio_run(partition_run, tmp_path, monkeypatch):
    """Use the existing real collection harness with synthetic MinIO consumers."""
    # Change only artifact inputs in a disposable copy: real wc/shasum still
    # reject truncated/corrupt downloads, without fetching a 100 MB executable.
    payloads = {arch: ("synthetic-minio-" + arch + "\n").encode() for arch in ("amd64", "arm64")}
    script = RUNNER.read_text()
    assignment = next(line for line in script.splitlines() if line.startswith("repo_root="))
    script = script.replace(assignment, "repo_root=" + shlex.quote(str(ROOT)), 1)
    for arch, digest, size in [
        ("amd64", "fe8b37f38487b6caf758a71d6669a8c42a9a3ec88e7381cc24a39f067b0fa4c9", 110756024),
        ("arm64", "1fdf97b30dbe10e13db00f1c405bf16935d7e1d530b537b4ebd2ed941457280c", 104988856),
    ]:
        assert script.count(digest) == script.count(str(size)) == 1
        script = script.replace(digest, hashlib.sha256(payloads[arch]).hexdigest()).replace(str(size), str(len(payloads[arch])))
    runner = tmp_path / "minio-runner.sh"
    runner.write_text(script)
    temporary = tmp_path / "runner-temp"
    temporary.mkdir()
    monkeypatch.setenv("TMPDIR", str(temporary))
    integration = tmp_path / "tests/integration"
    integration.mkdir(parents=True)
    check = '''import json, os, re, pytest
def check_store():
    with open(os.environ["MINIO_CREDENTIALS"]) as source: credentials = json.load(source)
    valid = (os.environ.get("GRAF_TEST_STRICT_MINIO_ENDPOINT") == "127.0.0.1:54900"
        and bool(re.fullmatch("[a-f0-9]{32}", os.environ.get("GRAF_TEST_STRICT_MINIO_ACCESS", "")))
        and bool(re.fullmatch("[a-f0-9]{48}", os.environ.get("GRAF_TEST_STRICT_MINIO_SECRET", "")))
        and os.environ.get("GRAF_TEST_STRICT_MINIO_ACCESS") == credentials[0]
        and os.environ.get("GRAF_TEST_STRICT_MINIO_SECRET") == credentials[1])
    assert valid, "runner must provide its own ready store"
'''
    (integration / "test_calendar_auto_context_match.py").write_text(check + '''
@pytest.mark.parametrize("tamper", [False, True], ids=["valid", "missing-attempt-metadata"])
def test_strict_track_assembly_real_minio_and_calendar_owner(tamper): check_store()
''')
    (integration / "test_smoke_cleanup_deadlock.py").write_text(check + '''
@pytest.mark.strict_rls
@pytest.mark.parametrize("live_minio", [False, True], ids=["residue", "real-minio"])
def test_interrupted_smoke_retains_unconfirmed_object_intent_and_preserves_neighbor(live_minio):
    if live_minio: check_store()
''')
    # Collection must be isolated too, before any service could be started.
    uv = tmp_path / "bin/uv"
    uv.write_text(uv.read_text().replace(
        'if os.environ.get("TAMPER_PHASE")',
        'if "--collect-only" in args:\n'
        '    assert not any(os.environ.get("GRAF_TEST_STRICT_MINIO_" + key) for key in ("ENDPOINT", "ACCESS", "SECRET"))\n'
        'if os.environ.get("TAMPER_PHASE")',
    ))
    docker = tmp_path / "bin/docker"
    docker.write_text(f'''#!{sys.executable}
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
path = os.environ["DOCKER_CALLS"]
with open(path, "a") as output: output.write(json.dumps(args) + "\\n")
calls = [json.loads(line) for line in open(path)]
runs = [call for call in calls if call[0] == "run" and "--label" in call]
fault = os.environ.get("MINIO_FAULT", "")
if args[0] in ("pull", "build"): sys.exit(97)
if args[:2] == ["image", "inspect"]: print(os.environ.get("MINIO_ARCH", "amd64"))
if args[0] == "run" and "--label" in args:
    mount = args[args.index("--mount") + 1]
    binary = Path(next(field[7:] for field in mount.split(",") if field.startswith("source=")))
    assert binary.is_file() and binary.stat().st_mode & 0o777 == 0o555
    with open(os.environ["MINIO_CREDENTIALS"], "w") as output:
        json.dump([os.environ["MINIO_ROOT_USER"], os.environ["MINIO_ROOT_PASSWORD"]], output)
    if fault == "start": sys.exit(9)
if args[0] == "inspect":
    if args[args.index("--format") + 1] == "{{{{.Image}}}}":
        assert any(call[0] == "exec" and "psql" in call for call in calls)
        print("not-an-image-id" if fault == "base-image" else "sha256:" + "a" * 64)
    else:
        if fault in ("inspect", "absent", "inventory"): sys.exit(1)
        label = runs[-1][runs[-1].index("--label") + 1].split("=", 1)[1]
        print("b" * 64 + " " + ("foreign-owner" if fault == "owner" else label))
if args[0] == "ps":
    if fault == "inventory": sys.exit(1)
    if fault != "absent": print("b" * 64)
if args[0] == "rm" and args[-1] == "b" * 64:
    mount = runs[-1][runs[-1].index("--mount") + 1]
    binary = Path(next(field[7:] for field in mount.split(",") if field.startswith("source=")))
    assert binary.is_file(), "must unmount before deleting the binary"
    if fault == "remove": sys.exit(9)
if args[0] == "logs": print("PostgreSQL init process complete; ready for start up.")
if args[0] == "port":
    print(os.environ.get("MINIO_PORT", "127.0.0.1:54900") if args[-1] == "9000/tcp" else "127.0.0.1:54329")
''')
    curl = tmp_path / "bin/curl"
    curl.write_text(f'''#!{sys.executable}
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["CURL_CALLS"], "a") as output: output.write(json.dumps(args) + "\\n")
fault = os.environ.get("MINIO_FAULT", "")
if "--output" in args:
    arch = "arm64" if "linux-arm64." in args[-1] else "amd64"
    payload = {payloads!r}[arch]
    if fault == "size": payload = payload[:-1]
    if fault == "checksum": payload = b"X" + payload[1:]
    Path(args[args.index("--output") + 1]).write_bytes(payload)
    sys.exit(22 if fault == "download" else 0)
sys.exit(7 if fault == "readiness" else 0)
''')
    curl.chmod(0o755)
    sleep = tmp_path / "bin/sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    monkeypatch.setenv("CURL_CALLS", str(tmp_path / "curl.jsonl"))
    monkeypatch.setenv("MINIO_CREDENTIALS", str(tmp_path / "minio-credentials.json"))
    for key in ("ENDPOINT", "ACCESS", "SECRET"):
        monkeypatch.setenv("GRAF_TEST_STRICT_MINIO_" + key, "inherited-operator-value")
    return lambda *args, **kwargs: partition_run(*args, runner=runner, **kwargs)


@pytest.mark.parametrize("args,expected", [
    (("-k", "strict_track_assembly"), 2),
    (("--partitioned", "--phases", "strict", "-k", "interrupted_smoke"), 2),
    (("--partitioned", "--phases", "parallel", "--shard", "0/2", "-k", "strict_track_assembly"), 1),
])
def test_selected_minio_consumers_receive_an_owned_ready_store(minio_run, tmp_path, args, expected):
    result, rows, calls = minio_run(*args, "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(rows) == expected
    run = [call for call in calls if call[0] == "run" and "--label" in call]
    assert len(run) == 1
    assert run[0][run[0].index("--publish") + 1] == "127.0.0.1::9000"
    assert run[0][run[0].index("--tmpfs") + 1] == "/data:rw,size=256m"
    assert run[0][-3:] == ["sha256:" + "a" * 64, "server", "/data"]
    assert "--pull=never" in run[0]
    assert run[0][run[0].index("--entrypoint") + 1] == "/graf-test-minio"
    mount = run[0][run[0].index("--mount") + 1]
    fields = mount.split(",")
    assert len(fields) == 4 and fields[0] == "type=bind" and fields[2:] == ["target=/graf-test-minio", "readonly"]
    assert not Path(fields[1].removeprefix("source=")).exists()
    assert calls.index(run[0]) > next(i for i, call in enumerate(calls) if call[0] == "exec" and "psql" in call)
    assert not any(call[0] in ("pull", "build") for call in calls)
    assert [run[0][i + 1] for i, arg in enumerate(run[0]) if arg == "--env"] == ["MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"]
    assert [call for call in calls if call[0] == "rm"][0] == ["rm", "--force", "--volumes", "b" * 64]
    curl_calls = [json.loads(line) for line in (tmp_path / "curl.jsonl").read_text().splitlines()]
    download, curl = curl_calls
    assert download[download.index("--proto") + 1] == download[download.index("--proto-redir") + 1] == "=https"
    assert download[download.index("--max-time") + 1] == "120"
    assert download[-1].startswith("https://github.com/minio/minio/releases/download/RELEASE.2025-05-24T17-08-30Z/minio.linux-")
    assert curl[curl.index("--noproxy") + 1] == "*"
    assert curl[curl.index("--max-time") + 1] == "1"
    assert curl[-1] == "http://127.0.0.1:54900/minio/health/ready"
    assert "inherited-operator-value" not in result.stdout + result.stderr
    credentials = json.loads((tmp_path / "minio-credentials.json").read_text())
    leaked = any(value in result.stdout + result.stderr for value in credentials)
    assert not leaked
    assert result.stdout.index("minio_test_cleanup=isolated_container_removed") < result.stdout.index("postgres_test_result=pass")


@pytest.mark.parametrize("args", [
    ("--collect-only", "-k", "strict_track_assembly"),
    ("-k", "test_plain"),
    ("--partitioned", "--phases", "performance"),
    ("--partitioned", "--phases", "strict", "-k", "residue"),
    # Sorted parallel inventory: other, plain, calendar[missing], calendar[valid].
    ("--partitioned", "--phases", "parallel", "--shard", "0/4"),
])
def test_unselected_minio_consumers_never_start_minio(minio_run, tmp_path, args):
    result, _, calls = minio_run(*args, "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not any(call[0] in ("image", "pull", "inspect", "ps") or "--label" in call for call in calls)
    assert not (tmp_path / "curl.jsonl").exists()


@pytest.mark.parametrize("fault", ["start", "readiness", "owner", "inspect", "inventory", "remove"])
def test_minio_failures_never_pass_or_remove_unknown_containers(minio_run, tmp_path, monkeypatch, fault):
    monkeypatch.setenv("MINIO_FAULT", fault)
    result, rows, calls = minio_run("-k", "strict_track_assembly", "-q")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "postgres_test_result=pass" not in result.stdout
    removed = [call for call in calls if call[0] == "rm" and call[-1] == "b" * 64]
    assert bool(removed) == (fault in ("start", "readiness", "remove"))
    assert bool(list((tmp_path / "runner-temp").glob("graf-postgres-test.*/minio"))) == (fault in ("owner", "inspect", "inventory", "remove"))
    assert any(call[0] == "rm" and call[-1].startswith("graf-postgres-test-") for call in calls)
    if fault in ("start", "readiness"):
        assert not rows
    if fault == "readiness":
        assert len((tmp_path / "curl.jsonl").read_text().splitlines()) == 61


@pytest.mark.parametrize("endpoint", ["0.0.0.0:54900", "127.0.0.1:0", "127.0.0.1:65536", "127.0.0.1:54900\n[::]:54900"])
def test_minio_refuses_unsafe_published_endpoints(minio_run, tmp_path, monkeypatch, endpoint):
    monkeypatch.setenv("MINIO_PORT", endpoint)
    result, rows, calls = minio_run("-k", "strict_track_assembly", "-q")
    assert result.returncode != 0 and not rows, result.stdout + result.stderr
    assert len((tmp_path / "curl.jsonl").read_text().splitlines()) == 1  # download only
    assert ["rm", "--force", "--volumes", "b" * 64] in calls


@pytest.mark.parametrize("status", [17, 130, 143])
def test_minio_is_cleaned_after_pytest_failure_or_signal(minio_run, tmp_path, status):
    uv = tmp_path / "bin/uv"
    uv.write_text(uv.read_text().replace(
        "os.execv(sys.executable,",
        'if "--collect-only" not in args:\n'
        + (f'    os.kill(os.getppid(), {status - 128})\n    sys.exit(0)\n'
           if status >= 128 else f'    sys.exit({status})\n')
        + "os.execv(sys.executable,",
    ))
    result, rows, calls = minio_run("-k", "strict_track_assembly", "-q")
    assert result.returncode == status and not rows, result.stdout + result.stderr
    assert "postgres_test_result=pass" not in result.stdout
    assert ["rm", "--force", "--volumes", "b" * 64] in calls


@pytest.mark.parametrize("arch", ["amd64", "arm64"])
def test_minio_download_matches_the_resolved_postgres_architecture(minio_run, tmp_path, monkeypatch, arch):
    monkeypatch.setenv("MINIO_ARCH", arch)
    result, _, calls = minio_run("-k", "strict_track_assembly", "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    downloads = [json.loads(line) for line in (tmp_path / "curl.jsonl").read_text().splitlines() if "--output" in json.loads(line)]
    assert len(downloads) == 1 and downloads[0][-1].endswith("minio.linux-" + arch + ".RELEASE.2025-05-24T17-08-30Z")
    assert not any(call[0] in ("pull", "build") for call in calls)


@pytest.mark.parametrize("fault", ["download", "size", "checksum", "base-image", "architecture"])
def test_minio_invalid_artifact_or_base_never_starts_a_container(minio_run, tmp_path, monkeypatch, fault):
    monkeypatch.setenv("MINIO_FAULT", fault)
    if fault == "architecture":
        monkeypatch.setenv("MINIO_ARCH", "unsupported")
    result, rows, calls = minio_run("-k", "strict_track_assembly", "-q")
    assert result.returncode != 0 and not rows, result.stdout + result.stderr
    assert "postgres_test_result=pass" not in result.stdout
    assert not any(call[0] == "run" and "--label" in call for call in calls)
    # uv keeps its own lock file in TMPDIR; only runner artifacts must be gone.
    leftovers = [
        item
        for item in (tmp_path / "runner-temp").iterdir()
        if not (item.name.startswith("uv-") and item.suffix == ".lock")
    ]
    assert not leftovers
    assert any(call[0] == "rm" and call[-1].startswith("graf-postgres-test-") for call in calls)


def test_full_runner_shares_one_minio_across_serial_and_parallel_consumers(minio_run):
    result, rows, calls = minio_run("-q", full=True)
    assert result.returncode == 0 and len(rows) == 9, result.stdout + result.stderr
    assert len([call for call in calls if call[0] == "run" and "--label" in call]) == 1
    assert ["rm", "--force", "--volumes", "b" * 64] in calls


def test_minio_cleanup_accepts_only_confirmed_absence(minio_run, monkeypatch):
    monkeypatch.setenv("MINIO_FAULT", "absent")
    result, _, calls = minio_run("-k", "strict_track_assembly", "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "minio_test_cleanup=container_absent" in result.stdout
    assert any(call[0] == "ps" for call in calls)
    assert ["rm", "--force", "--volumes", "b" * 64] not in calls


FAKE_DOCKER = r'''#!{python}
import json, os, sys
from pathlib import Path

state_path = Path(os.environ["DOCKER_STATE"])
calls_path = Path(os.environ["DOCKER_CALLS"])
state = json.loads(state_path.read_text()) if state_path.exists() else {{"runs": 0, "containers": {{}}}}
def save():
    state_path.write_text(json.dumps(state))
def log(args):
    with calls_path.open("a") as output:
        output.write(json.dumps(args) + "\n")
def find(reference):
    for container in state["containers"].values():
        if reference in (container["id"], container["name"], "/" + container["name"]):
            return container
    return None

args = sys.argv[1:]
log(args)
command = args[0] if args else ""
if command == "info":
    sys.exit(0)
if command == "image":
    if os.environ.get("IMAGE_OK", "1") != "1":
        sys.exit(1)
    print(os.environ["FAKE_IMAGE_ID"])
    sys.exit(0)
if command == "inspect":
    container = find(args[-1])
    if container is None:
        sys.exit(1)
    print("|".join([container["id"], "/" + container["name"], container["token"], container["image"]]))
    sys.exit(0)
if command == "ps":
    pattern = None
    for index, value in enumerate(args):
        if value == "--filter" and index + 1 < len(args) and args[index + 1].startswith("name=^/"):
            pattern = args[index + 1][6:]
            if pattern.endswith("$"):
                pattern = pattern[:-1]
    for container in state["containers"].values():
        if pattern is not None and "/" + container["name"] != pattern:
            continue
        print(container["id"])
    sys.exit(0)
if command == "run":
    if os.environ.get("RUN_FAIL_BEFORE_CREATE") == "1":
        sys.exit(125)
    state["runs"] += 1
    name = None
    token = None
    cidfile = None
    image = args[-1]
    index = 1
    while index < len(args):
        value = args[index]
        if value == "--name":
            index += 1; name = args[index]
        elif value == "--label":
            index += 1
            label = args[index]
            if label.startswith("pro.2brain.graf.f099.run="):
                token = label.split("=", 1)[1]
        elif value == "--cidfile":
            index += 1; cidfile = args[index]
        elif value in ("--env", "--tmpfs", "--publish"):
            index += 1
        index += 1
    container_id = "container-" + str(state["runs"])
    state["containers"][container_id] = {{
        "id": container_id,
        "name": name,
        "token": token,
        "image": image,
        "ready": state["runs"] >= int(os.environ.get("READY_AFTER", "1")),
    }}
    if os.environ.get("CIDFILE", "1") == "1" and cidfile:
        Path(cidfile).write_text(container_id)
    save()
    if os.environ.get("RUN_FAIL_AFTER_CREATE") == "1":
        sys.exit(125)
    print(container_id)
    sys.exit(0)
if command == "logs":
    container = find(args[-1])
    if container is None:
        sys.exit(1)
    print("PostgreSQL init process complete; ready for start up." if container["ready"] else "starting")
    sys.exit(0)
if command == "exec":
    container = find(args[1])
    if container is None:
        sys.exit(1)
    if "psql" in args and os.environ.get("SQL_FAIL") == "1":
        sys.exit(1)
    if (
        "psql" in args
        and os.environ.get("SQL_FAIL_FIRST") == "1"
        and container["id"] == "container-1"
    ):
        sys.exit(1)
    sys.exit(0)
if command == "port":
    print("127.0.0.1:54329")
    sys.exit(0)
if command == "rm":
    if os.environ.get("RM_FAIL") == "1":
        sys.exit(1)
    container = find(args[-1])
    if container is not None:
        state["containers"].pop(container["id"], None)
        save()
    sys.exit(0)
sys.exit(2)
'''


@pytest.fixture
def resource_run(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "docker-calls.jsonl"
    state = tmp_path / "docker-state.json"
    image_id = "sha256:" + "a" * 64
    docker = bin_dir / "docker"
    docker.write_text(FAKE_DOCKER.format(python=sys.executable))
    docker.chmod(0o755)
    uv = bin_dir / "uv"
    uv.write_text(f'''#!{sys.executable}
import json, sys
from pathlib import Path
args = sys.argv[sys.argv.index("pytest") + 1:]
if "--collect-only" in args:
    path = Path(args[args.index("--graf-collection-file") + 1])
    nodes = ["acceptance/playback_normalization_real_transport.py::test_real"]
    path.write_text(json.dumps({{"baseline": nodes, "parallel": nodes, "performance": [], "strict": [], "pure": nodes, "resource": []}}))
sys.exit(0)
''')
    uv.chmod(0o755)
    context = tmp_path / "postgres-context"
    context.mkdir(mode=0o700)
    manifest = context / "postgres-resource.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "run_token": "b" * 32,
        "container_name": "graf-postgres-test-f099-" + "b" * 32,
        "image_id": image_id,
    }))
    manifest.chmod(0o600)

    def run(*args, env=None, mode="--focused"):
        return subprocess.run(
            ["bash", str(RUNNER), mode, *args], cwd=ROOT,
            env={
                **os.environ,
                "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                "DOCKER_CALLS": str(calls),
                "DOCKER_STATE": str(state),
                "FAKE_IMAGE_ID": image_id,
                "GRAF_TEST_POSTGRES_RESOURCE_DIR": str(context),
                **(env or {}),
            },
            capture_output=True, text=True, check=False, timeout=60,
        )

    run.context = context
    run.image_id = image_id
    run.calls = lambda: [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
    run.state = state
    return run


def test_resource_context_requires_an_admitted_manifest_before_docker(resource_run):
    manifest = resource_run.context / "postgres-resource.json"
    manifest.write_text(json.dumps({"schema_version": 1, "run_token": "b" * 32}))
    manifest.chmod(0o600)
    result = resource_run("-q", "tests/unit/test_acceptance.py")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "invalid GRAF_TEST_POSTGRES_RESOURCE_DIR" in result.stderr
    assert resource_run.calls() == []


def test_resource_context_rejects_symlinked_manifest(resource_run, tmp_path):
    manifest = resource_run.context / "postgres-resource.json"
    target = tmp_path / "manifest.json"
    target.write_text(manifest.read_text())
    target.chmod(0o600)
    manifest.unlink()
    manifest.symlink_to(target)
    result = resource_run("-q", "tests/unit/test_acceptance.py")
    assert result.returncode == 2, result.stdout + result.stderr
    assert resource_run.calls() == []


def test_collect_only_validates_context_without_docker(resource_run):
    result = resource_run("--collect-only", "-q", "tests/unit/test_acceptance.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert resource_run.calls() == []
    assert not (resource_run.context / "postgres-state.json").exists()


def test_resource_context_runs_the_admitted_image_and_cleans_by_id(resource_run):
    result = resource_run("-q", "tests/unit/test_acceptance.py")
    assert result.returncode == 0, result.stdout + result.stderr
    calls = resource_run.calls()
    run_call = next(call for call in calls if call[0] == "run")
    assert "--pull=never" in run_call
    assert run_call[-1] == resource_run.image_id
    assert "--label" in run_call and f"pro.2brain.graf.f099.run={'b' * 32}" in run_call
    assert any(call[:2] == ["image", "inspect"] for call in calls)
    assert any(call[0] == "inspect" for call in calls)
    removals = [call for call in calls if call[0] == "rm"]
    assert removals == [["rm", "--force", "--volumes", "container-1"]]
    assert "postgres_test_resource_cleanup=removed" in result.stdout
    assert "postgres_test_result=pass mode=focused" in result.stdout
    state = json.loads((resource_run.context / "postgres-state.json").read_text())
    assert state["phase"] == "removed"


def test_resource_context_stops_before_sql_when_the_image_changed(resource_run):
    result = resource_run("-q", "tests/unit/test_acceptance.py", env={"IMAGE_OK": "0"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Admitted PostgreSQL image ID is unavailable" in result.stderr
    assert not any(call[0] == "run" for call in resource_run.calls())
    assert not any(call[0] == "exec" for call in resource_run.calls())


def test_resource_context_does_not_remove_a_foreign_container(resource_run):
    resource_run.state.write_text(json.dumps({
        "runs": 0,
        "containers": {
            "foreign": {
                "id": "foreign", "name": "graf-postgres-test-f099-" + "b" * 32,
                "token": "c" * 32, "image": resource_run.image_id, "ready": True,
            }
        },
    }))
    result = resource_run("-q", "tests/unit/test_acceptance.py", env={"RUN_FAIL_BEFORE_CREATE": "1"})
    assert result.returncode != 0, result.stdout + result.stderr
    assert "foreign_or_mismatched_container" in result.stderr
    assert not any(call[0] == "rm" for call in resource_run.calls())
    preserved = json.loads(resource_run.state.read_text())
    assert "foreign" in preserved["containers"]


def test_resource_context_retries_only_after_confirmed_removal(resource_run):
    result = resource_run(
        "-q", "tests/unit/test_acceptance.py",
        env={"SQL_FAIL_FIRST": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert [call[0] for call in resource_run.calls()].count("run") == 2
    assert "postgres_test_container_start_retry=1" in result.stderr


def test_resource_context_stops_after_a_failed_cleanup_without_retrying(resource_run):
    result = resource_run(
        "-q", "tests/unit/test_acceptance.py",
        env={"SQL_FAIL_FIRST": "1", "RM_FAIL": "1"},
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert [call[0] for call in resource_run.calls()].count("run") == 1
    assert "postgres_test_resource_cleanup=remove_failed" in result.stderr
    assert "postgres_test_result=pass" not in result.stdout


def test_resource_context_adopts_a_container_when_the_create_response_is_lost(resource_run):
    result = resource_run(
        "-q", "tests/unit/test_acceptance.py", env={"RUN_FAIL_AFTER_CREATE": "1"}
    )
    assert result.returncode == 0, result.stdout + result.stderr
    calls = resource_run.calls()
    assert [call[0] for call in calls].count("run") == 1
    assert any(call[0] == "inspect" for call in calls)
    assert [call for call in calls if call[0] == "rm"] == [["rm", "--force", "--volumes", "container-1"]]
    assert "postgres_test_result=pass mode=focused" in result.stdout


def test_resource_context_cleans_by_identity_when_the_cidfile_is_missing(resource_run):
    result = resource_run(
        "-q", "tests/unit/test_acceptance.py", env={"CIDFILE": "0"}
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (resource_run.context / "postgres.cid").exists()
    assert [call for call in resource_run.calls() if call[0] == "rm"] == [
        ["rm", "--force", "--volumes", "container-1"]
    ]
