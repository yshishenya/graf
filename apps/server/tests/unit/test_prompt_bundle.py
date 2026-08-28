from __future__ import annotations

import json

import pytest

from twobrain_rec_server.outcomes.prompt_bundle import (
    ROOT_BUNDLE_SCHEMA_VERSION,
    ResolvedPromptBundle,
    build_root_export,
    fetch_root_bundle_by_label,
    load_root_export_bytes,
    route_binding_hash,
    snapshot_bundle_metadata,
    validate_root_bundle_document,
)
from twobrain_rec_server.outcomes.prompts import (
    canonical_json,
    outcome_config,
    validate_prompt_snapshot,
)
from twobrain_rec_server.outcomes.templates import BUILT_IN_TEMPLATES


def _child(name: str, version: int):
    return validate_prompt_snapshot(
        name=name,
        version=version,
        prompt=[
            {
                "role": "system",
                "content": (
                    "Language={{output_language}} detail={{detail_level}} "
                    "sections={{template_sections_json}}"
                ),
            },
            {"role": "user", "content": "Transcript={{transcript_json}}"},
        ],
        prompt_type="chat",
        config=outcome_config(schema_name="graf_meeting_outcome_test"),
    )


def _bundle() -> ResolvedPromptBundle:
    children = {
        template.prompt_name: _child(template.prompt_name, index + 1)
        for index, template in enumerate(BUILT_IN_TEMPLATES)
    }
    children["graf/meeting-outcome/custom"] = _child(
        "graf/meeting-outcome/custom", len(children) + 1
    )
    descriptor = {
        "alias": "gpt-5.6-luna",
        "binding_version": "graf-litellm-route-v1",
        "allowed_provider_models": [{"provider": "openai", "model": "gpt-5.6-luna"}],
        "request_compiler_hash": "a" * 64,
        "request_compiler_version": "graf-chat-compiler-v1",
    }
    binding = {**descriptor, "binding_hash": route_binding_hash(descriptor)}
    refs = {
        name: (snapshot.version, snapshot.canonical_hash)
        for name, snapshot in children.items()
    }
    body = {
        "children": [
            {"hash": digest, "name": name, "version": version}
            for name, (version, digest) in sorted(refs.items())
        ],
        "route_binding": binding,
        "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
    }
    document = {
        **body,
        "bundle_hash": __import__("hashlib").sha256(canonical_json(body).encode()).hexdigest(),
    }
    root = validate_root_bundle_document(document, root_prompt_version=42)
    return ResolvedPromptBundle(root=root, children=children, source="langfuse_production")


def test_root_export_round_trip_preserves_exact_children_and_binding() -> None:
    bundle = _bundle()
    _, payload, _ = build_root_export(bundle)

    restored = load_root_export_bytes(payload)

    assert restored.root.root_prompt_version == 42
    assert restored.root.bundle_hash == bundle.root.bundle_hash
    assert set(restored.children) == set(bundle.children)
    assert all(
        snapshot.root_bundle_hash == bundle.root.bundle_hash
        and snapshot.route_binding_hash == bundle.root.route_binding_hash
        for snapshot in restored.children.values()
    )
    assert snapshot_bundle_metadata(restored.child("graf/meeting-outcome/auto"))["root_prompt_version"] == 42


def test_langfuse_root_fetch_reads_children_by_numeric_version() -> None:
    bundle = _bundle()
    root_document = {
        "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
        "bundle_hash": bundle.root.bundle_hash,
        "children": [
            {"name": name, "version": version, "hash": digest}
            for name, (version, digest) in sorted(bundle.root.children.items())
        ],
        "route_binding": bundle.root.route_binding,
    }

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
