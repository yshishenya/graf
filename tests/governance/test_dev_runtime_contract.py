from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40


def test_fixture_binds_every_component_to_one_exact_sha():
    payload = json.loads(
        (ROOT / "tests/governance/fixtures/feature_229/runtime/manifest-valid.json").read_text()
    )
    assert len(payload["source_sha"]) == 40
    assert {component["source_sha"] for component in payload["components"].values()} == {SHA}


def test_contract_names_one_server_rendered_origin_and_dev_app():
    payload = json.loads(
        (ROOT / "tests/governance/fixtures/feature_229/runtime/manifest-valid.json").read_text()
    )
    assert payload["dev_boundary"]["backend_origin"] == payload["dev_boundary"]["frontend_origin"]
    assert payload["app_identity"] == {"bundle_id": "pro.2brain.graf.dev", "channel": "dev"}


def test_contract_fixture_has_no_private_content_or_secret_fields():
    text = (ROOT / "tests/governance/fixtures/feature_229/runtime/manifest-valid.json").read_text()
    lowered = text.lower()
    assert "password" not in lowered
    assert "api_key" not in lowered
    assert "transcript" not in lowered
    assert "raw_audio" not in lowered
