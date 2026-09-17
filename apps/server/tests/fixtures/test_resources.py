"""Resource selection and metadata-only timings; never serialize test payloads."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import pytest

POSTGRES_FIXTURES = frozenset({
    "postgres_worker_database_url", "postgres_clean_database_url", "postgres_advisory_lock",
})
_report_path: Path | None = None


def pytest_addoption(parser):
    parser.addoption("--graf-report-file", help="Write safe phase timing metadata")
    parser.addoption("--graf-collection-file", help="Write the selected resource/Full phase inventory")
    parser.addoption("--graf-phase-file", help="Execute one exact phase from the selected inventory")
    parser.addoption("--graf-phase-shard", help="Execute one index/total slice of the selected phase")
    parser.addoption("--graf-partition-preflight", action="store_true", help="Reject conflicting effective xdist options before collection")


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config):
    # Loaded with -p: pytest has parsed CLI, PYTEST_ADDOPTS and config addopts,
    # but has not entered xdist's loop/worker hooks or imported test modules.
    options = early_config.known_args_namespace
    if not getattr(options, "graf_partition_preflight", False):
        return
    defaults = {
        "numprocesses": None, "dist": "no", "distload": False, "looponfail": False,
        "tx": [], "px": [], "maxprocesses": None, "maxworkerrestart": None,
        "maxschedchunk": None, "loadscopereorder": True, "rsyncdir": [], "rsyncignore": [],
        "testrunuid": None, "usepdb": False, "trace": False, "graf_phase_file": None,
        "graf_phase_shard": None,
    }
    if any(getattr(options, name, default) != default for name, default in defaults.items()):
        raise pytest.UsageError("partitioned owns xdist settings; use GRAF_TEST_WORKERS")


def pytest_configure(config):
    global _report_path
    for marker in ("postgres: requires isolated PostgreSQL", "browser: requires Playwright/Chromium"):
        config.addinivalue_line("markers", marker)
    modules = Path(__file__).parents[1] / "browser/node_modules"
    if not os.environ.get("GRAF_NODE_MODULES") and (modules / "playwright/package.json").is_file():
        os.environ["GRAF_NODE_MODULES"] = str(modules)
    _report_path = None
    if config.getoption("--graf-report-file") and not hasattr(config, "workerinput"):
        _report_path = Path(config.getoption("--graf-report-file"))
        # Each attempt/phase owns a new file; an old report is never a cache hit.
        with _report_path.open("x", encoding="utf-8"):
            pass


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    for item in items:
        if POSTGRES_FIXTURES.intersection(item.fixturenames) or item.get_closest_marker("strict_rls"):
            item.add_marker(pytest.mark.postgres)


def phase_for(item):
    if item.get_closest_marker("strict_rls"):
        return "strict"
    return "performance" if item.get_closest_marker("serial_performance") else "parallel"


def selected_shard(value):
    """Parse an optional index/total slice declaration for one exact phase."""
    if value in (None, ""):
        return None
    match = re.fullmatch(r"(\d+)/(\d+)", str(value))
    if match is None:
        raise pytest.UsageError("invalid selected test shard")
    index, total = int(match.group(1)), int(match.group(2))
    if total < 2 or index >= total:
        raise pytest.UsageError("invalid selected test shard")
    return index, total


@pytest.hookimpl(specname="pytest_collection_modifyitems", trylast=True)
def pytest_partition_collection(items, config):
    phase_file = config.getoption("--graf-phase-file")
    if not phase_file:
        return
    try:
        value = json.loads(Path(phase_file).read_text())
        phase, expected = value["phase"], value["nodeids"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise pytest.UsageError("cannot read selected test phase") from error
    if (not isinstance(phase, str) or phase not in {"parallel", "performance", "strict"}
            or not isinstance(expected, list) or not expected
            or any(not isinstance(node, str) or not node for node in expected)
            or len(set(expected)) != len(expected)):
        raise pytest.UsageError("invalid or empty selected test phase")
    phase_items = [item for item in items if phase_for(item) == phase]
    observed = sorted(item.nodeid for item in phase_items)
    shard = selected_shard(config.getoption("--graf-phase-shard"))
    if shard is None:
        # The whole phase must run: any missing or repeated case is a defect.
        if observed != sorted(expected):
            raise pytest.UsageError("selected test phase differs from the original collection")
        selected = phase_items
    else:
        # A part must execute exactly nodeids[index::total] of this collection.
        # Losing or duplicating a case still fails here, and the aggregating job
        # proves that the parts cover the full parallel set.
        index, total = shard
        if observed[index::total] != sorted(expected):
            raise pytest.UsageError("selected test shard differs from the original collection")
        wanted = set(expected)
        selected = [item for item in phase_items if item.nodeid in wanted]
    kept = {id(item) for item in selected}
    config.hook.pytest_deselected(items=[item for item in items if id(item) not in kept])
    items[:] = selected


def pytest_collection_finish(session):
    output = session.config.getoption("--graf-collection-file")
    if not output or hasattr(session.config, "workerinput"):
        return
    groups = {name: [] for name in ("baseline", "pure", "resource", "parallel", "performance", "strict")}
    for item in session.items:
        groups["baseline"].append(item.nodeid)
        resource = item.get_closest_marker("postgres") or item.get_closest_marker("browser")
        groups["resource" if resource else "pure"].append(item.nodeid)
        phase = phase_for(item)
        groups[phase].append(item.nodeid)
    Path(output).write_text(json.dumps(groups, sort_keys=True) + "\n", encoding="utf-8")


def pytest_runtest_setup(item):
    if item.get_closest_marker("browser"):
        modules = Path(os.environ.get("GRAF_NODE_MODULES", ""))
        if not (modules / "playwright/package.json").is_file():
            pytest.fail("Browser proof requires npm ci in tests/browser and playwright install chromium", pytrace=False)


def pytest_runtest_logreport(report):
    if _report_path is None:
        return
    path = report.nodeid.split("::", 1)[0]
    if Path(path).is_absolute() or ".." in Path(path).parts:
        path = "external-test"
    row = {
        "file": path,
        "case_id": hashlib.sha256(report.nodeid.encode()).hexdigest(),
        "when": report.when,
        "outcome": report.outcome,
        "duration": round(report.duration, 6),
    }
    with _report_path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(row, sort_keys=True) + "\n")
