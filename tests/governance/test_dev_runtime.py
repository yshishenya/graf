from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_feature_pointer_owns_runtime_paths():
    pointer_path = ROOT / ".specify/feature.json"
    # The active feature pointer is intentional per-worktree state and is
    # ignored in clean GitHub Actions checkouts. Validate it when present,
    # but do not make the repository-wide governance lane depend on it.
    if not pointer_path.exists():
        return
    pointer = json.loads(pointer_path.read_text())
    if pointer.get("feature_id") != "229":
        return
    assert pointer["feature_id"] == "229"
    assert "infra/docker-compose.dev.yml" in pointer["owned_paths"]
    assert "scripts/dev-harness.py" in pointer["owned_paths"]

def test_manifest_schema_has_full_service_identity_set():
    schema = json.loads((ROOT / "infra/dev/manifest.schema.json").read_text())
    required = set(schema["properties"]["components"]["required"])
    properties = set(schema["properties"]["components"]["properties"])
    assert {"processing_worker", "media_worker", "temporal", "migration", "database", "storage"} <= required
    assert "storage_init" in properties
