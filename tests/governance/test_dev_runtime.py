from __future__ import annotations

import json
from pathlib import Path
import runpy

import pytest


ROOT = Path(__file__).resolve().parents[2]
validate = runpy.run_path(str(ROOT / "scripts/validate-dev-runtime.py"))["validate"]


@pytest.mark.parametrize("pointer", [None, '{"feature_id":"255","owned_paths":[]}', '{"feature_id":"999"}', '{'])
def test_runtime_validation_is_independent_of_active_feature(tmp_path, pointer):
    (tmp_path / "infra").mkdir()
    compose = tmp_path / "infra/docker-compose.dev.yml"
    compose.write_text((ROOT / "infra/docker-compose.dev.yml").read_text())
    if pointer is not None:
        (tmp_path / ".specify").mkdir()
        (tmp_path / ".specify/feature.json").write_text(pointer)
    assert validate(tmp_path) == []
    # Active worktree identity is checked separately by validate-agent-context.
    compose.unlink()
    assert validate(tmp_path) == [
        "Dev Compose project is not explicitly graf-dev",
        "Dev processing is not explicitly enabled",
    ]


def test_runtime_validation_preserves_config_and_evidence_guards(tmp_path):
    (tmp_path / "infra").mkdir()
    (tmp_path / "infra/docker-compose.dev.yml").write_text('env_file: inherited.env\n')
    for relative in (".dev/ci-evidence", "tests/governance/fixtures/feature_229"):
        evidence = tmp_path / relative
        evidence.mkdir(parents=True)
        (evidence / "unsafe.json").write_text('{"password":"synthetic-test-value"}')
    assert validate(tmp_path) == [
        "Dev Compose project is not explicitly graf-dev",
        "Dev processing is not explicitly enabled",
        "Dev Compose must not inherit env_file",
        "forbidden evidence content in .dev/ci-evidence/unsafe.json",
        "forbidden evidence content in tests/governance/fixtures/feature_229/unsafe.json",
    ]


def test_manifest_schema_has_full_service_identity_set():
    schema = json.loads((ROOT / "infra/dev/manifest.schema.json").read_text())
    required = set(schema["properties"]["components"]["required"])
    properties = set(schema["properties"]["components"]["properties"])
    assert {"processing_worker", "media_worker", "temporal", "migration", "database", "storage"} <= required
    assert "storage_init" in properties
