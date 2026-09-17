"""Tests for the exact source SHA helper used by ``pr-metadata``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/sync-pr-source-sha.py"

BODY_TEMPLATE = """## Как проверено
- `pytest -q`: passed
- Exact source SHA: `{sha}`
"""


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
    )


def test_rewrites_only_the_evidence_line(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    other_sha = "c" * 40
    body.write_text(
        BODY_TEMPLATE.format(sha="a" * 40) + f"\nНе проверяется: {other_sha}\n",
        encoding="utf-8",
    )

    result = run("--body-file", str(body), "--sha", "b" * 40)

    assert result.returncode == 0, result.stderr
    text = body.read_text(encoding="utf-8")
    assert f"- Exact source SHA: `{'b' * 40}`" in text
    # An unrelated hex string must never be touched.
    assert other_sha in text
    assert f"`{'a' * 40}`" not in text


def test_reports_drift_without_writing(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    original = BODY_TEMPLATE.format(sha="a" * 40)
    body.write_text(original, encoding="utf-8")

    result = run("--check", "--body-file", str(body), "--sha", "b" * 40)

    assert result.returncode == 1
    assert "different exact source SHA" in result.stderr
    assert body.read_text(encoding="utf-8") == original


def test_missing_line_is_an_error(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text("## Как проверено\n- ничего\n", encoding="utf-8")

    result = run("--body-file", str(body), "--sha", "b" * 40)

    assert result.returncode == 1
    assert "no 'Exact source SHA' line" in result.stderr


def test_two_lines_are_an_error(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text(
        BODY_TEMPLATE.format(sha="a" * 40) + f"- Exact source SHA: `{'b' * 40}`\n",
        encoding="utf-8",
    )

    result = run("--body-file", str(body), "--sha", "b" * 40)

    assert result.returncode == 1
    assert "exactly one is allowed" in result.stderr


def test_rejects_a_sha_that_is_not_full_length(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text(BODY_TEMPLATE.format(sha="a" * 40), encoding="utf-8")

    result = run("--body-file", str(body), "--sha", "abc")

    assert result.returncode == 2
    assert "not a full 40-character git SHA" in result.stderr
