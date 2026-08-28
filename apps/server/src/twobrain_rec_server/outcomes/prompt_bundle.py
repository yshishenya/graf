"""Atomic Langfuse root-bundle resolution for meeting outcomes.

The production label belongs to this bundle only. Child prompts are resolved
by their exact numeric versions from the bundle and never by a child label.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
from io import BytesIO
from typing import Any, Literal

from twobrain_rec_server.outcomes.prompts import (
    PromptSnapshot,
    canonical_json,
    validate_prompt_snapshot,
)
from twobrain_rec_server.outcomes.templates import BUILT_IN_TEMPLATES

ROOT_BUNDLE_PROMPT_NAME = "graf/meeting-outcome/root-bundle"
ROOT_BUNDLE_SCHEMA_VERSION = "graf-outcome-root-bundle-v1"
ROOT_BUNDLE_EXPORT_SCHEMA_VERSION = "graf-outcome-root-bundle-export-v1"
ROOT_BUNDLE_LABEL = "production"
ROOT_BUNDLE_OBJECT_PREFIX = "_system/prompts/verified-production-root"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_BINDING_VERSION = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

OUTCOME_PROMPT_NAMES = frozenset(
    [definition.prompt_name for definition in BUILT_IN_TEMPLATES]
    + ["graf/meeting-outcome/custom"]
)


class PromptBundleError(ValueError):
    """The root or one of its exact children cannot authorize execution."""


@dataclass(frozen=True, slots=True)
class RootBundle:
    root_prompt_version: int
    bundle_hash: str
    children: dict[str, tuple[int, str]]
    route_binding: dict[str, object]

    @property
    def route_binding_hash(self) -> str:
        return str(self.route_binding["binding_hash"])


@dataclass(frozen=True, slots=True)
class ResolvedPromptBundle:
    root: RootBundle
    children: dict[str, PromptSnapshot]
    source: Literal["langfuse_production", "verified_promoted_snapshot"]

    def child(self, name: str) -> PromptSnapshot:
        try:
            return self.children[name]
        except KeyError as exc:
            raise PromptBundleError("root_bundle_child_missing") from exc


def route_binding_hash(descriptor: Mapping[str, object]) -> str:
    return sha256(canonical_json(dict(descriptor)).encode("utf-8")).hexdigest()


def _validate_route_binding(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise PromptBundleError("root_bundle_route_binding_invalid")
    expected = {
        "alias",
        "binding_hash",
        "binding_version",
        "allowed_provider_models",
        "request_compiler_hash",
        "request_compiler_version",
    }
    if set(value) != expected:
        raise PromptBundleError("root_bundle_route_binding_invalid")
    alias = value.get("alias")
    binding_version = value.get("binding_version")
    compiler_version = value.get("request_compiler_version")
    compiler_hash = value.get("request_compiler_hash")
    allowed = value.get("allowed_provider_models")
    if (
        not isinstance(alias, str)
        or not _MODEL.fullmatch(alias)
        or not isinstance(binding_version, str)
        or not _BINDING_VERSION.fullmatch(binding_version)
        or not isinstance(compiler_version, str)
        or not _BINDING_VERSION.fullmatch(compiler_version)
        or not isinstance(compiler_hash, str)
        or not _HEX64.fullmatch(compiler_hash)
        or not isinstance(allowed, list)
        or not allowed
    ):
        raise PromptBundleError("root_bundle_route_binding_invalid")
    pairs: list[dict[str, str]] = []
    for pair in allowed:
        if not isinstance(pair, Mapping) or set(pair) != {"provider", "model"}:
            raise PromptBundleError("root_bundle_route_binding_invalid")
        provider = pair.get("provider")
        model = pair.get("model")
        if (
            not isinstance(provider, str)
            or not _MODEL.fullmatch(provider)
            or not isinstance(model, str)
            or not _MODEL.fullmatch(model)
        ):
            raise PromptBundleError("root_bundle_route_binding_invalid")
        pairs.append({"provider": provider, "model": model})
    descriptor = {
        "alias": alias,
        "binding_version": binding_version,
        "allowed_provider_models": pairs,
        "request_compiler_hash": compiler_hash,
        "request_compiler_version": compiler_version,
    }
    binding_hash = value.get("binding_hash")
    if not isinstance(binding_hash, str) or not _HEX64.fullmatch(binding_hash):
        raise PromptBundleError("root_bundle_route_binding_invalid")
    if route_binding_hash(descriptor) != binding_hash:
        raise PromptBundleError("root_bundle_route_binding_hash_mismatch")
    return {**descriptor, "binding_hash": binding_hash}


def validate_root_bundle_document(
    document: object,
    *,
    root_prompt_version: int,
    expected_children: frozenset[str] = OUTCOME_PROMPT_NAMES,
) -> RootBundle:
    if not isinstance(document, Mapping):
        raise PromptBundleError("root_bundle_invalid")
    expected = {"bundle_hash", "children", "route_binding", "schema_version"}
    if set(document) != expected or document.get("schema_version") != ROOT_BUNDLE_SCHEMA_VERSION:
        raise PromptBundleError("root_bundle_invalid")
    if not isinstance(root_prompt_version, int) or root_prompt_version < 1:
        raise PromptBundleError("root_bundle_version_invalid")
    children = document.get("children")
    if not isinstance(children, list) or len(children) != len(expected_children):
        raise PromptBundleError("root_bundle_children_invalid")
    refs: dict[str, tuple[int, str]] = {}
    for child in children:
        if not isinstance(child, Mapping) or set(child) != {"name", "version", "hash"}:
            raise PromptBundleError("root_bundle_child_invalid")
        name = child.get("name")
        version = child.get("version")
        digest = child.get("hash")
        if (
            not isinstance(name, str)
            or name not in expected_children
            or name in refs
            or not isinstance(version, int)
            or version < 1
            or not isinstance(digest, str)
            or not _HEX64.fullmatch(digest)
        ):
            raise PromptBundleError("root_bundle_child_invalid")
        refs[name] = (version, digest)
    if set(refs) != set(expected_children):
        raise PromptBundleError("root_bundle_children_invalid")
    route_binding = _validate_route_binding(document.get("route_binding"))
    body = {
        "children": [
            {"hash": digest, "name": name, "version": version}
            for name, (version, digest) in sorted(refs.items())
        ],
        "route_binding": route_binding,
        "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
    }
    bundle_hash = document.get("bundle_hash")
    if not isinstance(bundle_hash, str) or not _HEX64.fullmatch(bundle_hash):
        raise PromptBundleError("root_bundle_hash_invalid")
    if sha256(canonical_json(body).encode("utf-8")).hexdigest() != bundle_hash:
        raise PromptBundleError("root_bundle_hash_mismatch")
    return RootBundle(
        root_prompt_version=root_prompt_version,
        bundle_hash=bundle_hash,
        children=refs,
        route_binding=route_binding,
    )


def _child_payload(snapshot: PromptSnapshot) -> dict[str, object]:
    return {
        "canonical_hash": snapshot.canonical_hash,
        "config": snapshot.config,
        "name": snapshot.name,
        "prompt": snapshot.prompt,
        "prompt_type": snapshot.prompt_type,
        "version": snapshot.version,
    }


def _snapshot_from_payload(
    value: object,
    *,
    source: Literal["langfuse_production", "verified_promoted_snapshot"],
) -> PromptSnapshot:
    if not isinstance(value, Mapping) or set(value) != {
        "canonical_hash",
        "config",
        "name",
        "prompt",
        "prompt_type",
        "version",
    }:
        raise PromptBundleError("root_bundle_child_export_invalid")
    try:
        snapshot = validate_prompt_snapshot(
            name=str(value["name"]),
            version=int(value["version"]),
            prompt_type=str(value["prompt_type"]),
            prompt=value["prompt"],
            config=value["config"],
            source=source,
        )
    except (TypeError, ValueError) as exc:
        raise PromptBundleError("root_bundle_child_export_invalid") from exc
    if snapshot.canonical_hash != value["canonical_hash"]:
        raise PromptBundleError("root_bundle_child_hash_mismatch")
    return snapshot


def _bind(snapshot: PromptSnapshot, root: RootBundle) -> PromptSnapshot:
    if root.children.get(snapshot.name) != (snapshot.version, snapshot.canonical_hash):
        raise PromptBundleError("root_bundle_child_mismatch")
    return replace(
        snapshot,
        root_bundle_hash=root.bundle_hash,
        root_prompt_version=root.root_prompt_version,
        route_binding_hash=root.route_binding_hash,
        route_binding=root.route_binding,
    )


def snapshot_bundle_metadata(snapshot: PromptSnapshot) -> dict[str, object] | None:
    """Return the durable binding needed to replay a root-authorized child."""

    values = (
        snapshot.root_bundle_hash,
        snapshot.root_prompt_version,
        snapshot.route_binding_hash,
        snapshot.route_binding,
    )
    if all(value is None for value in values):
        return None
    if (
        not isinstance(snapshot.root_bundle_hash, str)
        or not _HEX64.fullmatch(snapshot.root_bundle_hash)
        or not isinstance(snapshot.root_prompt_version, int)
        or snapshot.root_prompt_version < 1
        or not isinstance(snapshot.route_binding_hash, str)
        or not _HEX64.fullmatch(snapshot.route_binding_hash)
        or not isinstance(snapshot.route_binding, Mapping)
    ):
        raise PromptBundleError("root_bundle_binding_invalid")
    return {
        "root_bundle_hash": snapshot.root_bundle_hash,
        "root_prompt_version": snapshot.root_prompt_version,
        "route_binding_hash": snapshot.route_binding_hash,
        "route_binding": dict(snapshot.route_binding),
    }


def bind_snapshot_from_metadata(snapshot: PromptSnapshot, value: object) -> PromptSnapshot:
    """Restore and validate a child binding stored with a candidate attempt."""

    if not isinstance(value, Mapping) or set(value) != {
        "root_bundle_hash",
        "root_prompt_version",
        "route_binding_hash",
        "route_binding",
    }:
        raise PromptBundleError("root_bundle_binding_invalid")
    root_bundle_hash = value["root_bundle_hash"]
    root_prompt_version = value["root_prompt_version"]
    route_hash = value["route_binding_hash"]
    if (
        not isinstance(root_bundle_hash, str)
        or not _HEX64.fullmatch(root_bundle_hash)
        or not isinstance(root_prompt_version, int)
        or root_prompt_version < 1
        or not isinstance(route_hash, str)
        or not _HEX64.fullmatch(route_hash)
    ):
        raise PromptBundleError("root_bundle_binding_invalid")
    route = _validate_route_binding(value["route_binding"])
    if route["binding_hash"] != route_hash:
        raise PromptBundleError("root_bundle_binding_invalid")
    return replace(
        snapshot,
        root_bundle_hash=root_bundle_hash,
        root_prompt_version=root_prompt_version,
        route_binding_hash=route_hash,
        route_binding=route,
    )


def build_root_export(bundle: ResolvedPromptBundle) -> tuple[str, bytes, str]:
    payload = {
        "bundle": {
            "bundle_hash": bundle.root.bundle_hash,
            "children": [
                {"hash": digest, "name": name, "version": version}
                for name, (version, digest) in sorted(bundle.root.children.items())
            ],
            "route_binding": bundle.root.route_binding,
            "root_prompt_version": bundle.root.root_prompt_version,
            "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
        },
        "children": {
            name: _child_payload(snapshot)
            for name, snapshot in sorted(bundle.children.items())
        },
        "schema_version": ROOT_BUNDLE_EXPORT_SCHEMA_VERSION,
    }
    encoded = canonical_json(payload).encode("utf-8")
    key = f"{ROOT_BUNDLE_OBJECT_PREFIX}/{bundle.root.bundle_hash}.json"
    return key, encoded, sha256(encoded).hexdigest()


def persist_root_bundle(storage: Any, bundle: ResolvedPromptBundle) -> str:
    key, payload, export_hash = build_root_export(bundle)
    storage.put_stream(key, BytesIO(payload), len(payload))
    readback = _load_export(storage, key, source="verified_promoted_snapshot")
    if readback.root.bundle_hash != bundle.root.bundle_hash:
        raise PromptBundleError("root_bundle_export_postverify_failed")
    pointer_key = f"{ROOT_BUNDLE_OBJECT_PREFIX}/last-known-good.json"
    pointer = canonical_json(
        {
            "export_hash": export_hash,
            "export_key": key,
            "schema_version": ROOT_BUNDLE_EXPORT_SCHEMA_VERSION,
        }
    ).encode("utf-8")
    storage.put_stream(pointer_key, BytesIO(pointer), len(pointer))
    return key


def load_last_known_good_root_bundle(storage: Any) -> ResolvedPromptBundle:
    pointer_key = f"{ROOT_BUNDLE_OBJECT_PREFIX}/last-known-good.json"
    try:
        pointer = json.loads(storage.get_bytes(pointer_key))
        if not isinstance(pointer, Mapping) or set(pointer) != {
            "export_hash",
            "export_key",
            "schema_version",
        }:
            raise PromptBundleError("root_bundle_pointer_invalid")
        if pointer["schema_version"] != ROOT_BUNDLE_EXPORT_SCHEMA_VERSION:
            raise PromptBundleError("root_bundle_pointer_invalid")
        export_key = pointer["export_key"]
        if not isinstance(export_key, str) or not export_key.startswith(
            f"{ROOT_BUNDLE_OBJECT_PREFIX}/"
        ):
            raise PromptBundleError("root_bundle_pointer_invalid")
        raw = storage.get_bytes(export_key)
        if sha256(raw).hexdigest() != pointer["export_hash"]:
            raise PromptBundleError("root_bundle_export_hash_mismatch")
    except PromptBundleError:
        raise
    except Exception as exc:
        raise PromptBundleError("root_bundle_lkg_unavailable") from exc
    return _load_export(storage, export_key, source="verified_promoted_snapshot")


def _load_export(
    storage: Any,
    key: str,
    *,
    source: Literal["langfuse_production", "verified_promoted_snapshot"],
) -> ResolvedPromptBundle:
    try:
        payload = json.loads(storage.get_bytes(key))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromptBundleError("root_bundle_export_invalid") from exc
    if not isinstance(payload, Mapping) or set(payload) != {
        "bundle",
        "children",
        "schema_version",
    }:
        raise PromptBundleError("root_bundle_export_invalid")
    if payload["schema_version"] != ROOT_BUNDLE_EXPORT_SCHEMA_VERSION:
        raise PromptBundleError("root_bundle_export_invalid")
    document = payload["bundle"]
    if not isinstance(document, Mapping):
        raise PromptBundleError("root_bundle_export_invalid")
    root_version = document.get("root_prompt_version")
    root = validate_root_bundle_document(
        {
            "bundle_hash": document.get("bundle_hash"),
            "children": document.get("children"),
            "route_binding": document.get("route_binding"),
            "schema_version": document.get("schema_version"),
        },
        root_prompt_version=root_version if isinstance(root_version, int) else 0,
    )
    children_value = payload["children"]
    if not isinstance(children_value, Mapping) or set(children_value) != set(root.children):
        raise PromptBundleError("root_bundle_children_invalid")
    children: dict[str, PromptSnapshot] = {}
    for name in sorted(root.children):
        snapshot = _snapshot_from_payload(children_value[name], source=source)
        version, digest = root.children[name]
        if snapshot.name != name or snapshot.version != version or snapshot.canonical_hash != digest:
            raise PromptBundleError("root_bundle_child_mismatch")
        children[name] = _bind(snapshot, root)
    return ResolvedPromptBundle(root=root, children=children, source=source)


def fetch_root_bundle_by_label(
    client: Any,
    *,
    label: str = ROOT_BUNDLE_LABEL,
    expected_children: frozenset[str] = OUTCOME_PROMPT_NAMES,
) -> ResolvedPromptBundle:
    if label != ROOT_BUNDLE_LABEL:
        raise PromptBundleError("root_bundle_label_invalid")
    root_prompt = client.get_prompt(
        ROOT_BUNDLE_PROMPT_NAME,
        label=label,
        type="text",
        cache_ttl_seconds=0,
        max_retries=0,
        fetch_timeout_seconds=10,
    )
    if not isinstance(root_prompt.prompt, str):
        raise PromptBundleError("root_bundle_prompt_invalid")
    try:
        document = json.loads(root_prompt.prompt)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromptBundleError("root_bundle_prompt_invalid") from exc
    root = validate_root_bundle_document(
        document,
        root_prompt_version=int(root_prompt.version),
        expected_children=expected_children,
    )
    children: dict[str, PromptSnapshot] = {}
    for name, (version, digest) in sorted(root.children.items()):
        child = client.get_prompt(
            name,
            version=version,
            type="chat",
            cache_ttl_seconds=0,
            max_retries=0,
            fetch_timeout_seconds=10,
        )
        try:
            snapshot = validate_prompt_snapshot(
                name=name,
                version=int(child.version),
                prompt_type="chat",
                prompt=child.prompt,
                config=child.config or {},
                source="langfuse_production",
            )
        except (TypeError, ValueError) as exc:
            raise PromptBundleError("root_bundle_child_invalid") from exc
        if snapshot.version != version or snapshot.canonical_hash != digest:
            raise PromptBundleError("root_bundle_child_mismatch")
        children[name] = _bind(snapshot, root)
    return ResolvedPromptBundle(
        root=root,
        children=children,
        source="langfuse_production",
    )


def promote_root_bundle_label(
    client: Any,
    *,
    expected_source_version: int,
    target_version: int,
    protected_label_capability_verified: bool,
    snapshot_storage: Any | None = None,
) -> ResolvedPromptBundle:
    """Move the one protected root label and verify the complete bundle."""

    if not protected_label_capability_verified:
        raise PromptBundleError("protected_label_capability_unavailable")
    try:
        current = client.get_prompt(
            ROOT_BUNDLE_PROMPT_NAME,
            label=ROOT_BUNDLE_LABEL,
            type="text",
            cache_ttl_seconds=0,
            max_retries=0,
            fetch_timeout_seconds=10,
        )
        target = client.get_prompt(
            ROOT_BUNDLE_PROMPT_NAME,
            version=target_version,
            type="text",
            cache_ttl_seconds=0,
            max_retries=0,
            fetch_timeout_seconds=10,
        )
        if int(current.version) not in {expected_source_version, target_version}:
            raise PromptBundleError("root_bundle_source_conflict")
        if not isinstance(target.prompt, str):
            raise PromptBundleError("root_bundle_prompt_invalid")
        document = json.loads(target.prompt)
        validate_root_bundle_document(
            document,
            root_prompt_version=int(target.version),
        )
        if int(current.version) != target_version:
            client.update_prompt(
                name=ROOT_BUNDLE_PROMPT_NAME,
                version=target_version,
                new_labels=[ROOT_BUNDLE_LABEL],
            )
        client.clear_prompt_cache()
        promoted = fetch_root_bundle_by_label(client)
        if promoted.root.root_prompt_version != target_version:
            raise PromptBundleError("root_bundle_label_readback_mismatch")
        if snapshot_storage is not None:
            persist_root_bundle(snapshot_storage, promoted)
        return promoted
    except PromptBundleError:
        raise
    except Exception as exc:
        raise PromptBundleError("root_bundle_promotion_reconciliation_required") from exc


def load_root_export_bytes(
    raw: bytes,
    *,
    source: Literal["langfuse_production", "verified_promoted_snapshot"] = "verified_promoted_snapshot",
) -> ResolvedPromptBundle:
    """Parse a root export without a storage client; useful for contract tests."""

    class _MemoryStorage:
        def __init__(self, value: bytes) -> None:
            self.value = value

        def get_bytes(self, _key: str) -> bytes:
            return self.value

    return _load_export(_MemoryStorage(raw), "memory", source=source)
