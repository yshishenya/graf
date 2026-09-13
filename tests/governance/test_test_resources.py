"""Exercise resource selection and safe timing reports through real pytest hooks."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTEST = ["uv", "run", "--frozen", "--project", str(ROOT / "apps/server"),
          "--extra", "dev", "--extra", "evaluation", "python", "-m", "pytest"]


def pytest_run(directory, *args, env=None):
    return subprocess.run(
        [*PYTEST, "-p", "tests.fixtures.test_resources", *args],
        cwd=directory, env={**os.environ, "PYTHONPATH": str(ROOT / "apps/server"), **(env or {})},
        capture_output=True, text=True, check=False,
    )


def test_resource_closure_is_disjoint_and_pure_does_not_request_database(tmp_path):
    (tmp_path / "test_cases.py").write_text('''
import pytest
@pytest.fixture
def postgres_worker_database_url():
    raise AssertionError("database requested")
@pytest.fixture
def indirect(postgres_worker_database_url):
    return postgres_worker_database_url
def test_database(indirect): pass
def test_pure(): pass
@pytest.mark.browser
def test_browser(): pass
@pytest.mark.serial_performance
def test_performance(): pass
@pytest.mark.strict_rls
def test_rls(): pass
''')
    inventory = tmp_path / "inventory.json"
    result = pytest_run(tmp_path, "--collect-only", "-q", "--graf-collection-file", str(inventory))
    assert result.returncode == 0, result.stdout + result.stderr
    value = json.loads(inventory.read_text())
    assert len(value["baseline"]) == 5
    assert set(value["pure"]).isdisjoint(value["resource"])
    assert set(value["pure"] + value["resource"]) == set(value["baseline"])
    phases = value["parallel"] + value["performance"] + value["strict"]
    assert len(set(phases)) == len(phases) == 5
    assert set(phases) == set(value["baseline"])
    assert "test_cases.py::test_database" in value["resource"]
    assert "test_cases.py::test_browser" in value["resource"]
    assert "test_cases.py::test_rls" in value["resource"]
    pure = pytest_run(tmp_path, "-q", "-m", "not postgres and not browser")
    assert pure.returncode == 0, pure.stdout + pure.stderr
    missing = pytest_run(tmp_path, "-q", "test_cases.py::test_database")
    assert missing.returncode != 0 and "database requested" in missing.stdout
    browser = pytest_run(tmp_path, "-q", "test_cases.py::test_browser",
                         env={"GRAF_NODE_MODULES": str(tmp_path / "missing")})
    assert browser.returncode != 0 and "Browser proof requires" in browser.stdout


def test_parallel_timing_report_contains_only_safe_fields_once(tmp_path):
    (tmp_path / "test_cases.py").write_text('''
import pytest
@pytest.mark.parametrize("value", ["synthetic-private-1", "synthetic-private-2"])
def test_payload(value):
    print("synthetic SQL parameters: " + value)
    assert False, value
''')
    report = tmp_path / "parallel.jsonl"
    result = pytest_run(tmp_path, "-q", "-n", "2", *["--graf-report-file", str(report)])
    assert result.returncode == 1, result.stdout + result.stderr
    rows = [json.loads(line) for line in report.read_text().splitlines()]
    assert len(rows) == 6
    assert len({(row["case_id"], row["when"]) for row in rows}) == 6
    assert all(set(row) == {"file", "case_id", "when", "outcome", "duration"} for row in rows)
    assert {row["file"] for row in rows} == {"test_cases.py"}
    assert {row["case_id"] for row in rows} == {
        hashlib.sha256(f"test_cases.py::test_payload[synthetic-private-{n}]".encode()).hexdigest()
        for n in (1, 2)
    }
    assert "synthetic" not in report.read_text()
    assert "SQL" not in report.read_text()


def test_runner_phase_loads_report_options_in_parallel_workers(tmp_path):
    result = subprocess.run(
        ["bash", str(ROOT / "apps/server/scripts/run_local_postgres_tests.sh"),
         "--focused", "-q", "-n", "2",
         "-k", "test_request_context_is_isolated_and_reset_on_errors"],
        cwd=ROOT,
        env={**os.environ, "GRAF_TEST_REPORT_DIR": str(tmp_path / "reports")},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rows = [json.loads(line) for line in (tmp_path / "reports/focused.jsonl").read_text().splitlines()]
    assert len(rows) == 3 and all(row["outcome"] == "passed" for row in rows)
