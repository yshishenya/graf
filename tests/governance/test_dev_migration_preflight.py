from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "dev_migration_preflight", ROOT / "infra" / "scripts" / "dev-migration-preflight.py"
)
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


@pytest.mark.parametrize(
    ("expected", "observed", "status", "reason"),
    [
        (["head_a"], [], "empty", "new_namespace"),
        (["head_a"], ["head_a"], "matching", "exact_head"),
        (["head_a"], ["unknown"], "blocked", "unknown_or_divergent_revision"),
        (["head_a"], ["head_a", "head_b"], "blocked", "multiple_or_divergent_heads"),
        (["head_a", "head_b"], ["head_a"], "blocked", "multiple_graph_heads"),
    ],
)
def test_migration_states_fail_closed_or_allow_only_safe_states(expected, observed, status, reason):
    result = preflight.classify_migration_state(expected, observed)
    assert result["status"] == status
    assert result["reason"] == reason
    assert result["next_action"]


def test_migration_revision_tokens_are_normalized_and_metadata_only():
    result = preflight.classify_migration_state(["head_a", "head_a"], ["head_a"])
    assert result["expected_heads"] == ["head_a"]
    assert "alembic stamp" in result["next_action"] or result["status"] == "matching"


def test_observe_can_use_explicit_fixture_state(tmp_path: Path):
    result = preflight.observe_checkout(
        tmp_path,
        {"GRAF_DEV_EXPECTED_MIGRATION_HEAD": "head_a", "GRAF_DEV_OBSERVED_MIGRATION_REVISION": "old_head"},
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "unknown_or_divergent_revision"


def test_container_preflight_uses_installed_alembic_without_uv(monkeypatch):
    monkeypatch.setattr(preflight.shutil, "which", lambda _: None)
    assert preflight._alembic_command("heads") == ["alembic", "heads"]
