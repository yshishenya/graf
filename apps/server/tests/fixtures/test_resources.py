"""Resource selection and metadata-only timings; never serialize test payloads."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

POSTGRES_FIXTURES = frozenset({
    "postgres_worker_database_url", "postgres_clean_database_url", "postgres_advisory_lock",
})
_report_path: Path | None = None


def pytest_addoption(parser):
    parser.addoption("--graf-report-file", help="Write safe phase timing metadata")
    parser.addoption("--graf-collection-file", help="Write the selected resource/Full phase inventory")


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


def pytest_collection_finish(session):
    output = session.config.getoption("--graf-collection-file")
    if not output or hasattr(session.config, "workerinput"):
        return
    groups = {name: [] for name in ("baseline", "pure", "resource", "parallel", "performance", "strict")}
    for item in session.items:
        groups["baseline"].append(item.nodeid)
        resource = item.get_closest_marker("postgres") or item.get_closest_marker("browser")
        groups["resource" if resource else "pure"].append(item.nodeid)
        phase = "strict" if item.get_closest_marker("strict_rls") else (
            "performance" if item.get_closest_marker("serial_performance") else "parallel"
        )
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
