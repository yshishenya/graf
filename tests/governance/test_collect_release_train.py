from __future__ import annotations

import importlib.util
import json
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "collect_release_train.py"
_SPEC = importlib.util.spec_from_file_location("collect_release_train", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
collector = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(collector)


ROOT = Path(__file__).resolve().parents[2]


def test_candidate_checks_run_concurrently_and_keep_exact_gate() -> None:
    calls: list[list[str]] = []

    def command(argv: list[str]) -> tuple[int, str, str]:
        calls.append(argv)
        if argv[:3] == ["gh", "repo", "view"]:
            return 0, "yshishenya/graf\n", ""
        if argv[:3] == ["gh", "pr", "list"]:
            return 0, json.dumps(
                [
                    {"number": 1, "mergeCommit": {"oid": "a" * 40}, "headRefOid": "b" * 40},
                    {"number": 2, "mergeCommit": {"oid": "c" * 40}, "headRefOid": "d" * 40},
                ]
            ), ""
        if argv[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (0, "", "") if argv[-1] == "f" * 40 else (1, "", "not ancestor")
        if argv[:2] == ["gh", "api"]:
            return 0, "42\n", ""
        raise AssertionError(argv)

    result = collector.collect(base_sha="e" * 40, source_sha="f" * 40, command=command, workers=2)

    assert result["prs"] == ["1", "2"]
    assert result["receipts"] == ["pr-1-governance-42", "pr-2-governance-42"]
    assert any(argv[:2] == ["gh", "api"] for argv in calls)


def test_missing_proof_is_reported_without_dropping_the_other_pr() -> None:
    def command(argv: list[str]) -> tuple[int, str, str]:
        if argv[:3] == ["gh", "repo", "view"]:
            return 0, "yshishenya/graf\n", ""
        if argv[:3] == ["gh", "pr", "list"]:
            return 0, json.dumps(
                [
                    {"number": 1, "mergeCommit": {"oid": "a" * 40}, "headRefOid": "b" * 40},
                    {"number": 2, "mergeCommit": {"oid": "c" * 40}, "headRefOid": "d" * 40},
                ]
            ), ""
        if argv[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (0, "", "") if argv[-1] == "f" * 40 else (1, "", "not ancestor")
        if argv[:2] == ["gh", "api"]:
            return (0, "42\n", "") if any("b" * 40 in item for item in argv) else (1, "", "TLS timeout")
        raise AssertionError(argv)

    result = collector.collect(base_sha="e" * 40, source_sha="f" * 40, command=command, workers=2)

    assert result["prs"] == ["1"]
    assert result["receipts"] == ["pr-1-governance-42"]
    assert result["skips"][0]["number"] == "2"
    assert "governance-fast" in result["skips"][0]["reason"]
