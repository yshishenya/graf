from __future__ import annotations

import json

import pytest

from tests.fixtures.outcome_prompts import desired_prompts
from twobrain_rec_server.outcomes.prompt_bundle import (
    ROOT_BUNDLE_PROMPT_NAME,
    ResolvedPromptBundle,
    build_root_bundle_document,
    build_root_export,
    fetch_root_bundle_by_label,
    load_root_export_bytes,
    root_bundle_document,
    snapshot_bundle_metadata,
    validate_root_bundle_document,
)
from twobrain_rec_server.outcomes.prompts import (
    canonical_json,
    validate_prompt_snapshot,
)
from twobrain_rec_server.outcomes.templates import BUILT_IN_TEMPLATES


def _child(name: str, version: int):
    prompt_type, prompt, config = desired_prompts()[name]
    return validate_prompt_snapshot(
        name=name,
        version=version,
        prompt=prompt,
        prompt_type=prompt_type,
        config=config,
    )


def _bundle() -> ResolvedPromptBundle:
    children = {
        template.prompt_name: _child(template.prompt_name, index + 1)
        for index, template in enumerate(BUILT_IN_TEMPLATES)
    }
    children["graf/meeting-outcome/custom"] = _child(
        "graf/meeting-outcome/custom", len(children) + 1
    )
    children["graf/meeting-outcome/verify"] = _child("graf/meeting-outcome/verify", 12)
    children["graf/meeting-outcome/extract"] = _child("graf/meeting-outcome/extract", 13)
    document = build_root_bundle_document(children)
    root = validate_root_bundle_document(document, root_prompt_version=42)
    return ResolvedPromptBundle(root=root, children=children, source="langfuse_production")


def test_root_requires_extraction_but_verifier_never_sees_its_notes():
    bundle = _bundle()
    without_extractor = {name: child for name, child in bundle.children.items() if not name.endswith("/extract")}
    with pytest.raises(ValueError, match="children_invalid"):
        build_root_bundle_document(without_extractor)
    synthesis = canonical_json(bundle.children["graf/meeting-outcome/auto"].prompt)
    verifier = canonical_json(bundle.children["graf/meeting-outcome/verify"].prompt)
    assert "{{extraction_json}}" in synthesis
    assert "{{draft_json}}" in verifier and "{{extraction_json}}" not in verifier


def test_root_binds_activation_and_rejects_reordered_stages():
    from copy import deepcopy
    from hashlib import sha256

    document = build_root_bundle_document(_bundle().children)
    assert [row["role"] for row in document["activation"]["stages"]] == [
        "extraction", "synthesis", "verification",
    ]
    changed = deepcopy(document)
    changed["activation"]["stages"].reverse()
    changed["activation_hash"] = sha256(canonical_json(changed["activation"]).encode()).hexdigest()
    body = {key: value for key, value in changed.items() if key != "bundle_hash"}
    changed["bundle_hash"] = sha256(canonical_json(body).encode()).hexdigest()
    with pytest.raises(ValueError, match="activation"):
        validate_root_bundle_document(changed, root_prompt_version=42)


def test_dev_resolves_only_the_root_label_and_uses_evaluation_source():
    from types import SimpleNamespace

    bundle = _bundle()
    requested = []

    class Client:
        def get_prompt(self, name, **kwargs):
            requested.append((name, kwargs))
            if name == ROOT_BUNDLE_PROMPT_NAME:
                return SimpleNamespace(version=42, prompt=canonical_json(build_root_bundle_document(bundle.children)))
            child = bundle.children[name]
            return SimpleNamespace(version=child.version, prompt=child.prompt, config=child.config)

    result = fetch_root_bundle_by_label(Client(), label="dev")
    assert result.source == "langfuse_evaluation"
    assert requested[0][1]["label"] == "dev"
    assert all("version" in args and "label" not in args for _, args in requested[1:])


def test_evaluation_snapshot_requires_exact_run_and_export(tmp_path):
    from copy import deepcopy
    from uuid import uuid4

    from twobrain_rec_server.outcomes.prompt_bundle import (
        build_evaluation_snapshot,
        validate_evaluation_snapshot,
    )

    run_id = uuid4()
    snapshot = build_evaluation_snapshot(_bundle(), project_id="synthetic-project", run_id=run_id)
    restored, authority = validate_evaluation_snapshot(snapshot)
    assert restored.root.root_prompt_version == 42 and authority["run_id"] == str(run_id)
    assert authority["publication_sink"] == "evaluation_only"
    for field in ("run_id", "root_export_hash", "activation_hash"):
        changed = deepcopy(snapshot)
        changed["authority"][field] = str(uuid4()) if field == "run_id" else "a" * 64
        with pytest.raises(ValueError):
            validate_evaluation_snapshot(changed)


def test_root_export_round_trip_preserves_exact_children_and_binding() -> None:
    bundle = _bundle()
    _, payload, _ = build_root_export(bundle)

    restored = load_root_export_bytes(payload)

    assert restored.root.root_prompt_version == 42
    assert restored.root.bundle_hash == bundle.root.bundle_hash
    assert set(restored.children) == set(bundle.children)
    assert all(
        snapshot.root_bundle_hash == bundle.root.bundle_hash
        for snapshot in restored.children.values()
    )
    assert snapshot_bundle_metadata(restored.child("graf/meeting-outcome/auto"))["root_prompt_version"] == 42


def test_compiled_schema_preserves_field_order_after_snapshot_round_trip() -> None:
    bundle = _bundle()
    _, payload, _ = build_root_export(bundle)
    restored = load_root_export_bytes(payload)

    def property_order(value):
        if isinstance(value, list):
            return [property_order(child) for child in value]
        if isinstance(value, dict):
            return {
                key: list(child) if key == "properties" else property_order(child)
                for key, child in value.items()
            } | {
                "nested_properties": {
                    key: property_order(child)
                    for key, child in value.get("properties", {}).items()
                }
            }
        return value

    for name, original in bundle.children.items():
        snapshot = restored.child(name)
        unchanged_config = canonical_json(snapshot.config)
        request = snapshot.litellm_request([])
        assert request == original.litellm_request([])
        assert snapshot.model_parameters == original.model_parameters
        assert "reasoning_effort" not in request
        expected = original.config["response_format"]["json_schema"]["schema"]
        actual = request["response_format"]["json_schema"]["schema"]
        assert property_order(actual) == property_order(expected), name
        assert canonical_json(snapshot.config) == unchanged_config


def test_build_root_bundle_document_pins_exact_child_hashes() -> None:
    bundle = _bundle()
    document = build_root_bundle_document(bundle.children)
    assert set(document) == {"bundle_hash", "children", "schema_version", "runtime_contract_hash", "activation", "activation_hash"}

    assert document["bundle_hash"] == bundle.root.bundle_hash
    assert {
        child["name"]: child["version"] for child in document["children"]
    } == {
        name: version for name, (version, _digest) in bundle.root.children.items()
    }


def test_root_requires_verifier_and_current_runtime_contract():
    bundle = _bundle()
    children = {name: child for name, child in bundle.children.items() if name != "graf/meeting-outcome/verify"}
    with pytest.raises(ValueError, match="children_invalid"):
        build_root_bundle_document(children)
    document = build_root_bundle_document(bundle.children)
    assert "runtime_contract_hash" in document
    document["runtime_contract_hash"] = "0" * 64
    with pytest.raises(ValueError, match="runtime_contract"):
        validate_root_bundle_document(document, root_prompt_version=42)


def test_langfuse_root_fetch_reads_children_by_numeric_version() -> None:
    bundle = _bundle()
    root_document = root_bundle_document(bundle.root)

    class Prompt:
        def __init__(self, version: int, prompt: object, config: dict[str, object]):
            self.version = version
            self.prompt = prompt
            self.config = config

    class Client:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        def get_prompt(self, name: str, **kwargs: object) -> Prompt:
            self.calls.append((name, kwargs))
            if name == "graf/meeting-outcome/root-bundle":
                return Prompt(42, json.dumps(root_document), {})
            child = bundle.children[name]
            return Prompt(child.version, child.prompt, child.config)

    client = Client()
    restored = fetch_root_bundle_by_label(client)

    assert restored.source == "langfuse_production"
    assert [(name, kwargs["version"]) for name, kwargs in client.calls[1:]] == [
        (name, bundle.root.children[name][0]) for name in sorted(bundle.children)
    ]


def test_root_bundle_rejects_changed_child_hash() -> None:
    bundle = _bundle()
    _, payload, _ = build_root_export(bundle)
    changed = json.loads(payload)
    changed["children"]["graf/meeting-outcome/auto"]["canonical_hash"] = "b" * 64

    with pytest.raises(ValueError, match="child_hash_mismatch|child_mismatch"):
        load_root_export_bytes(canonical_json(changed).encode())


def test_root_export_rejects_unknown_bundle_fields() -> None:
    _, payload, _ = build_root_export(_bundle())
    changed = json.loads(payload)
    changed["bundle"]["unexpected"] = {}
    with pytest.raises(ValueError, match="export_invalid"):
        load_root_export_bytes(canonical_json(changed).encode())


def test_root_round_trip_preserves_different_child_models() -> None:
    from dataclasses import replace

    children = dict(_bundle().children)
    name = "graf/meeting-outcome/custom"
    child = children[name]
    children[name] = validate_prompt_snapshot(
        name=name, version=22, prompt_type=child.prompt_type, prompt=child.prompt,
        config={**child.config, "model": "gemini/gemini-3.8-flash", "top_p": 0.6},
    )
    document = build_root_bundle_document(children)
    bundle = replace(_bundle(), children=children, root=validate_root_bundle_document(
        document, root_prompt_version=43,
    ))
    _, payload, _ = build_root_export(bundle)
    restored = load_root_export_bytes(payload)
    assert restored.child(name).litellm_request([]) == children[name].litellm_request([])
    assert restored.child(name).model != restored.child("graf/meeting-outcome/auto").model
