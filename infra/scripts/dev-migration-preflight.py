#!/usr/bin/env python3
"""Fail-closed migration gate for the isolated GRAF Dev database.

The module is intentionally dependency-free so it can be used both by the
host adapter and in governance fixtures.  It only observes Alembic state and
never mutates ``alembic_version``.  An empty, newly-created database is the
only state that may proceed to the normal migration command.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable


REVISION_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class MigrationPreflightError(RuntimeError):
    """An expected, safe-to-report preflight failure."""


def _revisions(values: Iterable[str]) -> list[str]:
    result: set[str] = set()
    for value in values:
        value = value.strip().strip(",")
        if value and REVISION_RE.fullmatch(value):
            result.add(value)
    return sorted(result)


def classify_migration_state(expected_heads: Iterable[str], observed_heads: Iterable[str]) -> dict[str, Any]:
    """Return a metadata-only, deterministic migration verdict.

    ``empty`` is represented by no observed revision.  Multiple current heads,
    unknown revisions and graph divergence all block startup.  A single exact
    current head is the only already-migrated state accepted.
    """

    expected = _revisions(expected_heads)
    observed = _revisions(observed_heads)
    if not expected:
        return {
            "status": "blocked",
            "reason": "migration_graph_unresolved",
            "expected_heads": [],
            "observed_heads": observed,
            "next_action": "resolve the checked-out Alembic graph before starting Dev",
        }
    if not observed:
        return {
            "status": "empty",
            "reason": "new_namespace",
            "expected_heads": expected,
            "observed_heads": [],
            "next_action": "run the normal Alembic upgrade command in this isolated namespace",
        }
    if len(observed) != 1:
        return {
            "status": "blocked",
            "reason": "multiple_or_divergent_heads",
            "expected_heads": expected,
            "observed_heads": observed,
            "next_action": "create a fresh Dev namespace; do not stamp or edit alembic_version",
        }
    current = observed[0]
    if current not in expected:
        return {
            "status": "blocked",
            "reason": "unknown_or_divergent_revision",
            "expected_heads": expected,
            "observed_heads": observed,
            "next_action": "preserve this state and create a fresh Dev namespace; do not repair revision manually",
        }
    if len(expected) != 1:
        return {
            "status": "blocked",
            "reason": "multiple_graph_heads",
            "expected_heads": expected,
            "observed_heads": observed,
            "next_action": "resolve multiple Alembic graph heads before starting Dev",
        }
    return {
        "status": "matching",
        "reason": "exact_head",
        "expected_heads": expected,
        "observed_heads": observed,
        "next_action": "continue with the migration gate and application readiness",
    }


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        # Keep command output out of receipts: it may contain URLs or driver
        # diagnostics.  The operator gets a stable metadata-only reason.
        raise MigrationPreflightError(f"migration observation command failed: {command[0]}")
    return completed.stdout


def _parse_heads(output: str) -> list[str]:
    return _revisions(
        match.group(1)
        for match in re.finditer(r"^\s*([A-Za-z0-9_.-]+)\s+\(head\)\s*$", output, re.MULTILINE)
    )


def _parse_current(output: str) -> list[str]:
    # Alembic current emits ``<revision> (head)`` or ``<revision>``.  Ignore
    # informational lines and treat an absent version table as an empty state.
    values = []
    for line in output.splitlines():
        line = line.strip()
        if not line or "Context impl" in line or "Will assume" in line:
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)(?:\s+\(head\))?\s*$", line)
        if match:
            values.append(match.group(1))
    return _revisions(values)


def _alembic_command(operation: str) -> list[str]:
    return (["uv", "run"] if shutil.which("uv") else []) + ["alembic", operation]


def observe_checkout(server_root: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Observe Alembic graph/current state without issuing a mutating command."""

    run_env = dict(os.environ if env is None else env)
    configured_expected = run_env.get("GRAF_DEV_EXPECTED_MIGRATION_HEAD", "").strip()
    configured_observed = run_env.get("GRAF_DEV_OBSERVED_MIGRATION_REVISION", "").strip()
    # An expected graph head may safely come from the immutable manifest, but
    # it must not stand in for observing the database. Fixture mode is only
    # valid when the observed revision is explicitly supplied; live startup
    # must still run ``alembic current``.
    if configured_observed:
        expected = _revisions(configured_expected.split(","))
        observed = _revisions(configured_observed.split(","))
    else:
        expected = (
            _revisions(configured_expected.split(","))
            if configured_expected
            else _parse_heads(_run(_alembic_command("heads"), server_root, run_env))
        )
        try:
            observed = _parse_current(_run(_alembic_command("current"), server_root, run_env))
        except MigrationPreflightError as exc:
            # A fresh DB has no alembic_version table.  Any other failure is a
            # blocker and must not be mistaken for an empty namespace.
            marker = str(exc).lower()
            if "version table" in marker or "does not exist" in marker:
                observed = []
            else:
                raise
    return classify_migration_state(expected, observed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-root", type=Path, default=Path(__file__).resolve().parents[2] / "apps" / "server")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = observe_checkout(args.server_root)
    except MigrationPreflightError as exc:
        result = {
            "status": "blocked",
            "reason": "observation_failed",
            "expected_heads": [],
            "observed_heads": [],
            "next_action": "preserve the Dev state and inspect the bounded migration diagnostic",
        }
        if not args.json:
            print(str(exc), file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] in {"empty", "matching"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
