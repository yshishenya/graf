from __future__ import annotations

import json

import pytest

from tests.fixtures.outcome_prompts import outcome_config
from twobrain_rec_server.outcomes.prompt_bundle import (
    ROOT_BUNDLE_PROMPT_NAME,
    ROOT_BUNDLE_SCHEMA_VERSION,
    ResolvedPromptBundle,
    build_root_bundle_document,
    build_root_export,
    fetch_root_bundle_by_label,
    load_root_export_bytes,
    promote_root_bundle_label,
    snapshot_bundle_metadata,
    validate_root_bundle_document,
)
from twobrain_rec_server.outcomes.prompts import (
    canonical_json,
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
    refs = {
        name: (snapshot.version, snapshot.canonical_hash)
        for name, snapshot in children.items()
    }
    body = {
        "children": [
            {"hash": digest, "name": name, "version": version}
            for name, (version, digest) in sorted(refs.items())
        ],
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
        for snapshot in restored.children.values()
    )
    assert snapshot_bundle_metadata(restored.child("graf/meeting-outcome/auto"))["root_prompt_version"] == 42


def test_build_root_bundle_document_pins_exact_child_hashes() -> None:
    bundle = _bundle()
    document = build_root_bundle_document(bundle.children)
    assert set(document) == {"bundle_hash", "children", "schema_version"}

    assert document["bundle_hash"] == bundle.root.bundle_hash
    assert {
        child["name"]: child["version"] for child in document["children"]
    } == {
        name: version for name, (version, _digest) in bundle.root.children.items()
    }


def test_root_bundle_promotion_bootstraps_when_production_label_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _bundle()

    class NotFoundError(Exception):
        pass

    class Prompt:
        def __init__(self, version: int, prompt: object, config: dict[str, object]):
            self.version = version
            self.prompt = prompt
            self.config = config

    class Client:
        def __init__(self) -> None:
            self.promoted = False

        def get_prompt(self, name: str, **kwargs: object) -> Prompt:
            if kwargs.get("label") == "production":
                if not self.promoted:
                    raise NotFoundError()
                return Prompt(42, json.dumps({
                    "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
                    "bundle_hash": bundle.root.bundle_hash,
                    "children": [
                        {"name": n, "version": v, "hash": h}
                        for n, (v, h) in sorted(bundle.root.children.items())
                    ],
                }), {})
            if name == ROOT_BUNDLE_PROMPT_NAME:
                document = {
                    "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
                    "bundle_hash": bundle.root.bundle_hash,
                    "children": [
                        {"name": n, "version": v, "hash": h}
                        for n, (v, h) in sorted(bundle.root.children.items())
                    ],
                }
                return Prompt(42, json.dumps(document), {})
            child = bundle.children[name]
            return Prompt(child.version, child.prompt, child.config)

        def update_prompt(self, **kwargs: object) -> None:
            self.updated = kwargs
            self.promoted = True

        def clear_prompt_cache(self) -> None:
            return None

    import sys
    import types

    module = types.ModuleType("langfuse.api.commons.errors.not_found_error")
    module.NotFoundError = NotFoundError
    monkeypatch.setitem(sys.modules, module.__name__, module)

    promoted = promote_root_bundle_label(
        Client(),
        expected_source_version=None,
        target_version=42,
        protected_label_capability_verified=True,
    )
    assert promoted.root.root_prompt_version == 42


def test_langfuse_root_fetch_reads_children_by_numeric_version() -> None:
    bundle = _bundle()
    root_document = {
        "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
        "bundle_hash": bundle.root.bundle_hash,
        "children": [
            {"name": name, "version": version, "hash": digest}
            for name, (version, digest) in sorted(bundle.root.children.items())
        ],
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
