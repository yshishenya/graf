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
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from twobrain_rec_server.outcomes.models import ProtocolObject
from twobrain_rec_server.outcomes.prompts import (
    EXTRACTOR_PROMPT_NAME,
    VERIFIER_PROMPT_NAME,
    PromptSnapshot,
    canonical_json,
    prompt_snapshot_hash,
    validate_prompt_snapshot,
)
from twobrain_rec_server.outcomes.templates import BUILT_IN_TEMPLATES

ROOT_BUNDLE_PROMPT_NAME = "graf/meeting-outcome/root-bundle"
ROOT_BUNDLE_SCHEMA_VERSION = "graf-outcome-root-bundle-v4"
ROOT_BUNDLE_EXPORT_SCHEMA_VERSION = "graf-outcome-root-bundle-export-v3"
ROOT_BUNDLE_LABEL = "production"
ROOT_BUNDLE_OBJECT_PREFIX = "_system/prompts/verified-production-root"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

OUTCOME_PROMPT_NAMES = frozenset(
    [definition.prompt_name for definition in BUILT_IN_TEMPLATES]
    + ["graf/meeting-outcome/custom", EXTRACTOR_PROMPT_NAME, VERIFIER_PROMPT_NAME]
)


class PromptBundleError(ValueError):
    """The root or one of its exact children cannot authorize execution."""


Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Identifier = Annotated[str, Field(min_length=1, max_length=240)]
PositiveVersion = Annotated[int, Field(gt=0)]


class ArtifactBinding(ProtocolObject):
    artifact_id: Identifier
    schema_version: Literal[
        "graf-outcome-root-bundle-export-v3", "graf-outcome-activation-v1",
        "graf-outcome-qualification-v1", "graf-outcome-promotion-event-v1",
    ]
    artifact_version: Literal[1]
    hash: Digest

    @field_validator("artifact_version", mode="before")
    @classmethod
    def check_version_type(cls, value):
        if type(value) is not int:
            raise ValueError("artifact_version_invalid")
        return value

    @model_validator(mode="after")
    def check_id(self):
        UUID(self.artifact_id)
        return self


class CandidateRoot(ProtocolObject):
    project_id: Identifier
    root_name: Literal["graf/meeting-outcome/root-bundle"]
    root_version: PositiveVersion
    root_export: ArtifactBinding
    activation: ArtifactBinding

    @model_validator(mode="after")
    def check_bindings(self):
        if (self.root_export.schema_version != ROOT_BUNDLE_EXPORT_SCHEMA_VERSION
                or self.activation.schema_version != "graf-outcome-activation-v1"
                or self.root_export.artifact_id != self.activation.artifact_id):
            raise ValueError("root_authority_binding_invalid")
        return self


class ProductionAuthority(ProtocolObject):
    kind: Literal["production"]
    candidate_root: CandidateRoot
    event: ArtifactBinding

    @model_validator(mode="after")
    def check_event(self):
        if (self.event.schema_version != "graf-outcome-promotion-event-v1"
                or self.event.artifact_id != self.candidate_root.root_export.artifact_id):
            raise ValueError("root_authority_binding_invalid")
        return self


class EvaluationAuthority(ProtocolObject):
    kind: Literal["evaluation"]
    schema_version: Literal["graf-outcome-evaluation-authority-v1"]
    project_id: Identifier
    root_name: Literal["graf/meeting-outcome/root-bundle"]
    root_version: PositiveVersion
    root_export_hash: Digest
    activation_hash: Digest
    runtime_hash: Digest
    run_id: Identifier
    database: Identifier
    queue: Identifier
    publication_sink: Literal["evaluation_only"]
    sample_manifest_hash: Digest | None = None

    @model_validator(mode="after")
    def check_isolation(self):
        run = UUID(self.run_id)
        if self.database != f"graf_protocol_eval_{run.hex}" or self.queue != f"graf-protocol-eval-{run.hex}":
            raise ValueError("evaluation_isolation_required")
        return self


class CallBinding(ProtocolObject):
    call_id: Identifier
    validated_result_hash: Digest


class CorpusSource(ProtocolObject):
    meeting_id: Identifier
    source_hash: Digest
    selection_status: Literal["available", "partial", "deleted", "inaccessible", "source_unavailable", "transcript_unavailable"]


class RepresentativeSample(ProtocolObject):
    schema_version: Literal["graf-outcome-sample-v1"]
    run_id: Identifier
    root_export_hash: Digest
    inventory_hash: Digest
    real_sources: Annotated[list[CorpusSource], Field(min_length=3, max_length=3)]
    long_meeting_id: Identifier
    controls: dict[str, Identifier]

    @model_validator(mode="after")
    def check_sample(self):
        from twobrain_rec_server.cli.meeting_protocol_eval import CONTROL_CASES

        UUID(self.run_id)
        identifiers = {row.meeting_id for row in self.real_sources}
        if (len(identifiers) != 3 or self.long_meeting_id not in identifiers
                or any(row.selection_status not in {"available", "partial"} for row in self.real_sources)
                or set(self.controls) != set(CONTROL_CASES)
                or len(set(self.controls.values())) != 7
                or identifiers & set(self.controls.values())):
            raise ValueError("evaluation_sample_invalid")
        for identifier in [*identifiers, *self.controls.values()]:
            if str(UUID(identifier)) != identifier:
                raise ValueError("evaluation_sample_invalid")
        return self


class CorpusReview(ProtocolObject):
    meeting_id: Identifier
    source_hash: Digest
    candidate_id: Identifier
    output_hash: Digest
    calls: Annotated[list[CallBinding], Field(min_length=3, max_length=3)]
    criteria: dict[str, Literal["pass"]]


class CorpusExclusion(ProtocolObject):
    meeting_id: Identifier
    source_hash: Digest
    reason: Literal["deleted", "inaccessible", "source_unavailable", "transcript_unavailable", "no_meaningful_speech", "unintelligible_speech"]


class ControlReview(ProtocolObject):
    case_id: Literal[
        "informal_commitment", "conditional_commitment", "refused_commitment",
        "third_party_guess", "later_correction", "prompt_injection", "unknown_owner_and_due",
    ]
    candidate_id: Identifier
    source_hash: Digest
    output_hash: Digest
    calls: Annotated[list[CallBinding], Field(min_length=3, max_length=3)]
    verdict: Literal["pass"]


class PrivacyReview(ProtocolObject):
    checked_at: Identifier
    reviewer: Identifier
    verdict: Literal["pass"]


class FinalCorpusReport(ProtocolObject):
    schema_version: Literal["graf-outcome-corpus-report-v1"]
    run_id: Identifier
    project_id: Identifier
    root_name: Literal["graf/meeting-outcome/root-bundle"]
    root_version: PositiveVersion
    root_export_hash: Digest
    activation_hash: Digest
    runtime_hash: Digest
    cutoff_at: Identifier
    inventory: Annotated[list[CorpusSource], Field(min_length=1)]
    reviews: Annotated[list[CorpusReview], Field(min_length=1)]
    exclusions: list[CorpusExclusion]
    controls: Annotated[list[ControlReview], Field(min_length=7, max_length=7)]
    privacy: PrivacyReview
    complete: Literal[True]
    errors: dict[str, int]
    evaluation_scope: Literal["full", "representative"] = "full"
    sample_manifest: RepresentativeSample | None = None
    sample_long_duration_seconds: Annotated[float, Field(ge=3600, allow_inf_nan=False)] | None = None
    not_evaluated: list[CorpusSource] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_complete(self):
        from twobrain_rec_server.cli.meeting_protocol_eval import REVIEW_CRITERIA

        UUID(self.run_id)
        inventory = {row.meeting_id: row for row in self.inventory}
        checked = [*self.reviews, *self.exclusions]
        expected = set(inventory)
        if self.evaluation_scope == "representative":
            sample = self.sample_manifest
            if (sample is None or sample.run_id != self.run_id
                    or sample.root_export_hash != self.root_export_hash
                    or self.sample_long_duration_seconds is None or self.exclusions):
                raise ValueError("root_qualification_report_invalid")
            expected = {row.meeting_id for row in sample.real_sources}
            if (not expected <= set(inventory)
                    or any(inventory[row.meeting_id] != row for row in sample.real_sources)
                    or len(self.not_evaluated) != len(inventory) - 3
                    or {row.meeting_id for row in self.not_evaluated} != set(inventory) - expected
                    or any(inventory[row.meeting_id] != row for row in self.not_evaluated)):
                raise ValueError("root_qualification_report_invalid")
        elif self.sample_manifest is not None or self.not_evaluated or self.sample_long_duration_seconds is not None:
            raise ValueError("root_qualification_report_invalid")
        if (self.errors or len(inventory) != len(self.inventory)
                or len(checked) != len(expected)
                or len({row.meeting_id for row in checked}) != len(checked)
                or {row.meeting_id for row in checked} != expected
                or len({row.case_id for row in self.controls}) != 7):
            raise ValueError("root_qualification_report_invalid")
        for row in checked:
            if row.source_hash != inventory[row.meeting_id].source_hash:
                raise ValueError("root_qualification_report_invalid")
        for row in self.reviews:
            if set(row.criteria) != set(REVIEW_CRITERIA) or inventory[row.meeting_id].selection_status not in {"available", "partial"}:
                raise ValueError("root_qualification_report_invalid")
        for row in self.exclusions:
            source_status = inventory[row.meeting_id].selection_status
            if row.reason in {"no_meaningful_speech", "unintelligible_speech"}:
                if source_status not in {"available", "partial"}:
                    raise ValueError("root_qualification_report_invalid")
            elif row.reason != source_status:
                raise ValueError("root_qualification_report_invalid")
        calls = [call.call_id for row in [*self.reviews, *self.controls] for call in row.calls]
        if len(calls) != len(set(calls)):
            raise ValueError("root_qualification_report_invalid")
        return self


class OperatorCheck(ProtocolObject):
    method: Identifier
    checked_at: Identifier
    checked_by: Identifier
    result: Literal["pass"]


class Qualification(ProtocolObject):
    schema_version: Literal["graf-outcome-qualification-v1"]
    candidate_root: CandidateRoot
    report: FinalCorpusReport
    report_hash: Digest
    operator_actor: Identifier
    approved_at: Identifier
    operation_kind: Literal["initial_activation", "promotion"]
    expected_source_version: PositiveVersion
    previous_event: ArtifactBinding | None
    protected_label: OperatorCheck
    sole_mutation_credential: OperatorCheck
    safe_exit: Literal["disable_new_ai"]

    @model_validator(mode="after")
    def check_initial(self):
        if (self.operation_kind == "initial_activation") != (self.previous_event is None):
            raise ValueError("root_qualification_previous_invalid")
        if self.previous_event is not None and self.previous_event.schema_version != "graf-outcome-promotion-event-v1":
            raise ValueError("root_qualification_previous_invalid")
        report = self.report
        candidate = self.candidate_root
        if (self.report_hash != _digest(report.model_dump(mode="json"))
                or report.project_id != candidate.project_id or report.root_name != candidate.root_name
                or report.root_version != candidate.root_version or report.root_export_hash != candidate.root_export.hash
                or report.activation_hash != candidate.activation.hash):
            raise ValueError("root_qualification_report_mismatch")
        return self


class PromotionEvent(ProtocolObject):
    schema_version: Literal["graf-outcome-promotion-event-v1"]
    operation_id: Identifier
    operator_actor: Identifier
    completed_at: Identifier
    qualification: ArtifactBinding
    expected_source_version: PositiveVersion
    target: CandidateRoot
    readback: CandidateRoot
    result: Literal["pass"]

    @model_validator(mode="after")
    def check_readback(self):
        if (self.target != self.readback or self.operation_id != self.qualification.artifact_id
                or self.operation_id != self.target.root_export.artifact_id
                or self.qualification.schema_version != "graf-outcome-qualification-v1"):
            raise ValueError("root_promotion_event_invalid")
        return self


def _digest(value: object) -> str:
    return sha256(canonical_json(value).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RootBundle:
    root_prompt_version: int
    bundle_hash: str
    children: dict[str, tuple[int, str]]
    runtime_contract_hash: str


@dataclass(frozen=True, slots=True)
class ResolvedPromptBundle:
    root: RootBundle
    children: dict[str, PromptSnapshot]
    source: Literal["langfuse_production", "langfuse_evaluation", "verified_promoted_snapshot"]

    def child(self, name: str) -> PromptSnapshot:
        try:
            return self.children[name]
        except KeyError as exc:
            raise PromptBundleError("root_bundle_child_missing") from exc


def runtime_contract_hash() -> str:
    """Bind schema, validators, compiler, publication and renderers to this code."""
    package = Path(__file__).parent.parent
    files = (
        "outcomes/models.py", "outcomes/prompts.py", "outcomes/generator.py",
        "outcomes/ai_service.py", "outcomes/templates.py", "cabinet/rendering.py",
        "cabinet/exports.py", "cabinet/egress.py", "cabinet/view_models.py",
        "cabinet/access.py", "cabinet/web_routes/browser.py", "api/schemas.py",
        "outcomes/service.py", "outcomes/store.py",
        "outcomes/prompt_bundle.py",
        "config.py", "db/models/outcomes.py",
        "db/migrations/versions/0087_prompt_root_promotion.py",
        "cli/meeting_protocol_eval.py", "cli/meeting_protocol_eval_runtime.py",
    )
    return sha256(canonical_json({
        name: sha256((package / name).read_bytes()).hexdigest() for name in files
    }).encode("utf-8")).hexdigest()


def activation_manifest() -> dict[str, object]:
    return {
        "schema_version": "graf-outcome-activation-v1",
        "runtime_contract_hash": runtime_contract_hash(),
        "stages": [
            {"role": "extraction", "prompts": [EXTRACTOR_PROMPT_NAME]},
            {"role": "synthesis", "prompts": sorted(OUTCOME_PROMPT_NAMES - {EXTRACTOR_PROMPT_NAME, VERIFIER_PROMPT_NAME})},
            {"role": "verification", "prompts": [VERIFIER_PROMPT_NAME]},
        ],
    }


def _activation_fields() -> dict[str, object]:
    activation = activation_manifest()
    return {"activation": activation, "activation_hash": sha256(canonical_json(activation).encode()).hexdigest()}


def root_bundle_document(root: RootBundle) -> dict[str, object]:
    return {
        **_activation_fields(),
        "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
        "bundle_hash": root.bundle_hash,
        "children": [
            {"hash": digest, "name": name, "version": version}
            for name, (version, digest) in sorted(root.children.items())
        ],
        "runtime_contract_hash": root.runtime_contract_hash,
    }


def validate_root_bundle_document(
    document: object,
    *,
    root_prompt_version: int,
    expected_children: frozenset[str] = OUTCOME_PROMPT_NAMES,
) -> RootBundle:
    root = _validate_root_bundle_integrity(
        document, root_prompt_version=root_prompt_version, expected_children=expected_children,
    )
    if root.runtime_contract_hash != runtime_contract_hash():
        raise PromptBundleError("root_bundle_runtime_contract_mismatch")
    if any(document[key] != value for key, value in _activation_fields().items()):
        raise PromptBundleError("root_bundle_activation_mismatch")
    return root


def _activation_prompt_names(value: object) -> frozenset[str]:
    """Read a historical manifest's closed shape, without approving its runtime."""
    if (not isinstance(value, dict)
            or set(value) != {"schema_version", "runtime_contract_hash", "stages"}
            or value["schema_version"] != "graf-outcome-activation-v1"
            or not isinstance(value["runtime_contract_hash"], str)
            or not _HEX64.fullmatch(value["runtime_contract_hash"])):
        raise PromptBundleError("root_bundle_activation_mismatch")
    stages = value["stages"]
    if not isinstance(stages, list) or len(stages) != 3:
        raise PromptBundleError("root_bundle_activation_mismatch")
    names = []
    for stage, role in zip(stages, ("extraction", "synthesis", "verification"), strict=True):
        if (not isinstance(stage, dict) or set(stage) != {"role", "prompts"}
                or stage["role"] != role or not isinstance(stage["prompts"], list)
                or not stage["prompts"]
                or any(not isinstance(name, str) or not name for name in stage["prompts"])):
            raise PromptBundleError("root_bundle_activation_mismatch")
        names.extend(stage["prompts"])
    if len(names) != len(set(names)):
        raise PromptBundleError("root_bundle_activation_mismatch")
    return frozenset(names)


def _validate_root_bundle_integrity(
    document: object, *, root_prompt_version: int, expected_children: frozenset[str],
) -> RootBundle:
    if not isinstance(document, Mapping):
        raise PromptBundleError("root_bundle_invalid")
    expected = {"bundle_hash", "children", "schema_version", "runtime_contract_hash", "activation", "activation_hash"}
    if set(document) != expected or document.get("schema_version") != ROOT_BUNDLE_SCHEMA_VERSION:
        raise PromptBundleError("root_bundle_invalid")
    if type(root_prompt_version) is not int or root_prompt_version < 1:
        raise PromptBundleError("root_bundle_version_invalid")
    _activation_prompt_names(document["activation"])
    if document["runtime_contract_hash"] != document["activation"]["runtime_contract_hash"]:
        raise PromptBundleError("root_bundle_runtime_contract_mismatch")
    if document["activation_hash"] != _digest(document["activation"]):
        raise PromptBundleError("root_bundle_activation_mismatch")
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
            or type(version) is not int
            or version < 1
            or not isinstance(digest, str)
            or not _HEX64.fullmatch(digest)
        ):
            raise PromptBundleError("root_bundle_child_invalid")
        refs[name] = (version, digest)
    if set(refs) != set(expected_children):
        raise PromptBundleError("root_bundle_children_invalid")
    body = {
        "activation": document["activation"],
        "activation_hash": document["activation_hash"],
        "children": [
            {"hash": digest, "name": name, "version": version}
            for name, (version, digest) in sorted(refs.items())
        ],
        "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
        "runtime_contract_hash": document["runtime_contract_hash"],
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
        runtime_contract_hash=str(document["runtime_contract_hash"]),
    )


def build_root_bundle_document(
    children: Mapping[str, PromptSnapshot],
    *,
    expected_children: frozenset[str] = OUTCOME_PROMPT_NAMES,
) -> dict[str, object]:
    """Build a root document from already validated exact child snapshots."""

    if set(children) != set(expected_children):
        raise PromptBundleError("root_bundle_children_invalid")
    refs = {
        name: (snapshot.version, snapshot.canonical_hash)
        for name, snapshot in children.items()
    }
    body = {
        **_activation_fields(),
        "children": [
            {"hash": digest, "name": name, "version": version}
            for name, (version, digest) in sorted(refs.items())
        ],
        "schema_version": ROOT_BUNDLE_SCHEMA_VERSION,
        "runtime_contract_hash": runtime_contract_hash(),
    }
    document = {
        **body,
        "bundle_hash": sha256(canonical_json(body).encode("utf-8")).hexdigest(),
    }
    validate_root_bundle_document(
        document,
        root_prompt_version=1,
        expected_children=expected_children,
    )
    return document


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
    source: Literal["langfuse_production", "langfuse_evaluation", "verified_promoted_snapshot"],
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
            version=value["version"],
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
        root_document=root_bundle_document(root),
    )


def snapshot_bundle_metadata(snapshot: PromptSnapshot) -> dict[str, object] | None:
    """Return the durable binding needed to replay a root-authorized child."""

    values = (
        snapshot.root_bundle_hash,
        snapshot.root_prompt_version,
    )
    if all(value is None for value in values):
        return None
    if (
        not isinstance(snapshot.root_bundle_hash, str)
        or not _HEX64.fullmatch(snapshot.root_bundle_hash)
        or type(snapshot.root_prompt_version) is not int
        or snapshot.root_prompt_version < 1
    ):
        raise PromptBundleError("root_bundle_binding_invalid")
    return {
        "root_bundle_hash": snapshot.root_bundle_hash,
        "root_prompt_version": snapshot.root_prompt_version,
        "root_document": snapshot.root_document,
    }


def bind_snapshot_from_metadata(snapshot: PromptSnapshot, value: object) -> PromptSnapshot:
    """Restore and validate a child binding stored with a candidate attempt."""

    if not isinstance(value, Mapping) or set(value) != {
        "root_bundle_hash",
        "root_prompt_version",
        "root_document",
    }:
        raise PromptBundleError("root_bundle_binding_invalid")
    root_bundle_hash = value["root_bundle_hash"]
    root_prompt_version = value["root_prompt_version"]
    if (
        not isinstance(root_bundle_hash, str)
        or not _HEX64.fullmatch(root_bundle_hash)
        or type(root_prompt_version) is not int
        or root_prompt_version < 1
    ):
        raise PromptBundleError("root_bundle_binding_invalid")
    root = validate_root_bundle_document(value["root_document"], root_prompt_version=root_prompt_version)
    if root.bundle_hash != root_bundle_hash:
        raise PromptBundleError("root_bundle_binding_invalid")
    return _bind(snapshot, root)


def build_root_export(bundle: ResolvedPromptBundle) -> tuple[str, bytes, str]:
    payload = {
        "bundle": {
            **root_bundle_document(bundle.root),
            "root_prompt_version": bundle.root.root_prompt_version,
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


def load_root_export_bytes(
    raw: bytes,
    *,
    source: Literal["langfuse_production", "langfuse_evaluation", "verified_promoted_snapshot"] = "verified_promoted_snapshot",
) -> ResolvedPromptBundle:
    """Parse and validate a pinned root export without a storage wrapper."""
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromptBundleError("root_bundle_export_invalid") from exc
    root = _root_export_integrity(payload)
    document = payload["bundle"]
    validate_root_bundle_document(
        {key: value for key, value in document.items() if key != "root_prompt_version"},
        root_prompt_version=root.root_prompt_version,
    )
    children: dict[str, PromptSnapshot] = {}
    for name in sorted(root.children):
        snapshot = _snapshot_from_payload(payload["children"][name], source=source)
        children[name] = _bind(snapshot, root)
    return ResolvedPromptBundle(root=root, children=children, source=source)


def _root_export_integrity(payload: object) -> RootBundle:
    """Re-hash full stored bodies only; do not return executable child snapshots."""
    if not isinstance(payload, Mapping) or set(payload) != {
        "bundle",
        "children",
        "schema_version",
    }:
        raise PromptBundleError("root_bundle_export_invalid")
    if payload["schema_version"] != ROOT_BUNDLE_EXPORT_SCHEMA_VERSION:
        raise PromptBundleError("root_bundle_export_invalid")
    document = payload["bundle"]
    if not isinstance(document, Mapping) or set(document) != {
        "bundle_hash", "children", "root_prompt_version", "schema_version", "runtime_contract_hash",
        "activation", "activation_hash",
    }:
        raise PromptBundleError("root_bundle_export_invalid")
    root_version = document.get("root_prompt_version")
    root = _validate_root_bundle_integrity(
        {
            "activation": document.get("activation"),
            "activation_hash": document.get("activation_hash"),
            "bundle_hash": document.get("bundle_hash"),
            "children": document.get("children"),
            "schema_version": document.get("schema_version"),
            "runtime_contract_hash": document.get("runtime_contract_hash"),
        },
        root_prompt_version=root_version if isinstance(root_version, int) else 0,
        expected_children=_activation_prompt_names(document["activation"]),
    )
    children_value = payload["children"]
    if not isinstance(children_value, Mapping) or set(children_value) != set(root.children):
        raise PromptBundleError("root_bundle_children_invalid")
    for name in sorted(root.children):
        child = children_value[name]
        if (not isinstance(child, dict) or set(child) != {
                "canonical_hash", "config", "name", "prompt", "prompt_type", "version"}
                or not isinstance(child["config"], dict)
                or child["prompt_type"] not in {"chat", "text"}
                or not isinstance(child["prompt"], (str, list))):
            raise PromptBundleError("root_bundle_child_export_invalid")
        version, digest = root.children[name]
        if (child["name"] != name or type(child["version"]) is not int
                or child["version"] != version or child["canonical_hash"] != digest
                or prompt_snapshot_hash(prompt=child["prompt"], config=child["config"]) != digest):
            raise PromptBundleError("root_bundle_child_mismatch")
    return root


def fetch_root_bundle_by_label(
    client: Any,
    *,
    label: str = ROOT_BUNDLE_LABEL,
    expected_children: frozenset[str] = OUTCOME_PROMPT_NAMES,
) -> ResolvedPromptBundle:
    if label not in {ROOT_BUNDLE_LABEL, "dev"}:
        raise PromptBundleError("root_bundle_label_invalid")
    return _fetch_root_bundle(client, selector={"label": label}, expected_children=expected_children)


def fetch_root_bundle_by_version(client: Any, *, version: int) -> ResolvedPromptBundle:
    if type(version) is not int or version < 1:
        raise PromptBundleError("root_bundle_version_invalid")
    return _fetch_root_bundle(client, selector={"version": version})


def _fetch_root_bundle(
    client: Any, *, selector: dict[str, object],
    expected_children: frozenset[str] = OUTCOME_PROMPT_NAMES,
) -> ResolvedPromptBundle:
    source = "langfuse_evaluation" if "version" in selector or selector.get("label") == "dev" else "langfuse_production"
    root_prompt = client.get_prompt(
        ROOT_BUNDLE_PROMPT_NAME,
        **selector,
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
    if "version" in selector and root.root_prompt_version != selector["version"]:
        raise PromptBundleError("root_bundle_version_mismatch")
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
                source=source,
            )
        except (TypeError, ValueError) as exc:
            raise PromptBundleError("root_bundle_child_invalid") from exc
        if snapshot.version != version or snapshot.canonical_hash != digest:
            raise PromptBundleError("root_bundle_child_mismatch")
        children[name] = _bind(snapshot, root)
    return ResolvedPromptBundle(
        root=root,
        children=children,
        source=source,
    )


def build_evaluation_snapshot(bundle: ResolvedPromptBundle, *, project_id: str, run_id: UUID,
                              sample_manifest: dict | None = None) -> dict:
    _, encoded, digest = build_root_export(bundle)
    if sample_manifest is not None:
        sample = RepresentativeSample.model_validate(sample_manifest)
        if sample.run_id != str(run_id) or sample.root_export_hash != digest:
            raise ValueError("evaluation_sample_invalid")
        sample_manifest = sample.model_dump(mode="json")
    authority = EvaluationAuthority(
        kind="evaluation", schema_version="graf-outcome-evaluation-authority-v1",
        project_id=project_id, root_name=ROOT_BUNDLE_PROMPT_NAME, root_version=bundle.root.root_prompt_version,
        root_export_hash=digest, activation_hash=_activation_fields()["activation_hash"],
        runtime_hash=bundle.root.runtime_contract_hash, run_id=str(run_id),
        database=f"graf_protocol_eval_{run_id.hex}", queue=f"graf-protocol-eval-{run_id.hex}",
        publication_sink="evaluation_only",
        sample_manifest_hash=_digest(sample_manifest) if sample_manifest is not None else None,
    )
    return {"authority": authority.model_dump(mode="json"), "export": json.loads(encoded),
            **({"sample_manifest": sample_manifest} if sample_manifest is not None else {})}


def validate_evaluation_snapshot(value: object) -> tuple[ResolvedPromptBundle, dict]:
    try:
        if not isinstance(value, dict) or set(value) not in ({"authority", "export"}, {"authority", "export", "sample_manifest"}):
            raise ValueError
        authority = EvaluationAuthority.model_validate(value["authority"])
        sample = value.get("sample_manifest")
        if authority.sample_manifest_hash is not None:
            sample = RepresentativeSample.model_validate(sample)
            if (_digest(sample.model_dump(mode="json")) != authority.sample_manifest_hash
                    or sample.run_id != authority.run_id or sample.root_export_hash != authority.root_export_hash):
                raise ValueError
        elif "sample_manifest" in value:
            raise ValueError
        encoded = canonical_json(value["export"]).encode()
        if _digest(value["export"]) != authority.root_export_hash:
            raise ValueError
        bundle = load_root_export_bytes(encoded, source="langfuse_evaluation")
        if (bundle.root.root_prompt_version != authority.root_version
                or bundle.root.runtime_contract_hash != authority.runtime_hash
                or _activation_fields()["activation_hash"] != authority.activation_hash):
            raise ValueError
        return bundle, authority.model_dump(mode="json")
    except (ValueError, KeyError, TypeError):
        raise PromptBundleError("evaluation_authority_invalid") from None


def _artifact_binding(row, schema_version: str, digest: str) -> dict:
    return ArtifactBinding(
        artifact_id=str(row.id), schema_version=schema_version, artifact_version=1, hash=digest,
    ).model_dump(mode="json")


def _candidate_root(row, root: RootBundle) -> dict:
    return CandidateRoot(
        project_id=row.project_id, root_name=row.root_name, root_version=root.root_prompt_version,
        root_export=ArtifactBinding.model_validate(_artifact_binding(row, ROOT_BUNDLE_EXPORT_SCHEMA_VERSION, row.root_export_hash)),
        activation=ArtifactBinding.model_validate(_artifact_binding(row, "graf-outcome-activation-v1", row.activation_hash)),
    ).model_dump(mode="json")


def validate_promotion_row_artifacts(row) -> PromotionEvent:
    """Verify full historical receipts. The returned event cannot execute a model."""
    try:
        if row.state != "succeeded" or row.event_json is None:
            raise ValueError
        for field in ("root_export", "activation", "qualification", "event"):
            if _digest(getattr(row, f"{field}_json")) != getattr(row, f"{field}_hash"):
                raise ValueError
        root = _root_export_integrity(row.root_export_json)
        candidate = _candidate_root(row, root)
        qualification = Qualification.model_validate(row.qualification_json)
        event = PromotionEvent.model_validate(row.event_json)
        if (row.activation_json != row.root_export_json["bundle"]["activation"]
                or qualification.candidate_root.model_dump(mode="json") != candidate
                or qualification.operation_kind != row.operation_kind
                or qualification.expected_source_version != row.expected_source_version
                or qualification.report.runtime_hash != root.runtime_contract_hash
                or event.target.model_dump(mode="json") != candidate
                or event.operator_actor != qualification.operator_actor
                or event.expected_source_version != row.expected_source_version
                or event.qualification.model_dump(mode="json") != _artifact_binding(
                    row, "graf-outcome-qualification-v1", row.qualification_hash)):
            raise ValueError
        return event
    except (ValueError, TypeError, KeyError, AttributeError):
        raise PromptBundleError("root_authority_invalid") from None


def validate_promotion_row(row) -> tuple[ResolvedPromptBundle, dict]:
    """Authorize only this runtime; historical integrity never bypasses this gate."""
    event = validate_promotion_row_artifacts(row)
    bundle = load_root_export_bytes(canonical_json(row.root_export_json).encode())
    authority = {"kind": "production", "candidate_root": event.target.model_dump(mode="json"),
                 "event": _artifact_binding(row, "graf-outcome-promotion-event-v1", row.event_hash)}
    return bundle, ProductionAuthority.model_validate(authority).model_dump(mode="json")


async def load_execution_authority(db, settings, *, pinned: object | None = None):
    from sqlalchemy import select, text

    from twobrain_rec_server.db.models import PromptRootPromotion

    try:
        if not settings.langfuse_project_id:
            raise ValueError
        if settings.env == "protocol-evaluation":
            from twobrain_rec_server.cli.meeting_protocol_eval import PrivateWorkdir

            if settings.outcome_evaluation_workdir is None or settings.langfuse_environment != "protocol-evaluation":
                raise ValueError
            bundle, authority = validate_evaluation_snapshot(
                PrivateWorkdir(settings.outcome_evaluation_workdir).read_json("root-authority.json")
            )
            if (authority["project_id"] != settings.langfuse_project_id
                    or authority["root_version"] != settings.outcome_root_prompt_version
                    or authority["database"] != await db.scalar(text("select current_database()"))
                    or authority["queue"] != settings.temporal_task_queue
                    or settings.prompt_optimization_enabled):
                raise ValueError
        else:
            if settings.outcome_root_prompt_version is not None or settings.outcome_prompt_label != ROOT_BUNDLE_LABEL:
                raise ValueError
            query = select(PromptRootPromotion).where(
                PromptRootPromotion.project_id == settings.langfuse_project_id,
                PromptRootPromotion.root_name == ROOT_BUNDLE_PROMPT_NAME,
            ).execution_options(populate_existing=True)
            if pinned is None:
                query = query.where(PromptRootPromotion.is_current.is_(True))
            else:
                parsed = ProductionAuthority.model_validate(pinned)
                query = query.where(PromptRootPromotion.id == UUID(parsed.event.artifact_id))
            row = await db.scalar(query)
            if row is None:
                raise ValueError
            bundle, authority = validate_promotion_row(row)
            previous = Qualification.model_validate(row.qualification_json).previous_event
            if previous is not None:
                prior = await db.get(PromptRootPromotion, UUID(previous.artifact_id), populate_existing=True)
                prior_event = validate_promotion_row_artifacts(prior)
                if (prior.project_id != row.project_id or prior.root_name != row.root_name
                        or previous.model_dump(mode="json") != _artifact_binding(
                            prior, "graf-outcome-promotion-event-v1", prior.event_hash)
                        or prior_event.target.root_version != row.expected_source_version):
                    raise ValueError
        if pinned is not None and authority != pinned:
            raise ValueError
        return bundle, authority
    except PromptBundleError:
        raise
    except Exception:
        # Private paths and Pydantic/SQL input values must not enter ordinary failures.
        raise PromptBundleError("root_authority_unavailable") from None


async def promote_root_bundle(
    sessionmaker, *, settings, client, operation_id: UUID, expected_source_version: int,
    operator_actor: str, approved_at: str, protected_label: dict, sole_mutation_credential: dict,
    evaluation_settings, evaluation_sessionmaker, source_reader, workdir, run_id: UUID,
) -> PromotionEvent:
    """Operator-only single writer. Never imports a qualification or a PASS report.

    A separate transaction holds the project lock across the durable prepared
    write, one external mutation and the atomic event/current commit. An
    interrupted prepared operation cannot infer who moved a label or retry it.
    """
    from datetime import UTC, datetime
    from urllib.parse import quote

    from sqlalchemy import select, text

    from twobrain_rec_server.cli.meeting_protocol_eval import finalize_run
    from twobrain_rec_server.db.models import PromptRootPromotion
    from twobrain_rec_server.db.session import verify_prompt_optimization_database_identity
    from twobrain_rec_server.outcomes.prompt_optimization import (
        _complete_async_operation_until_quiescent,
        _quiescent_session_scope,
        _run_thread_until_quiescent,
    )

    mutation_possible = False
    try:
        await verify_prompt_optimization_database_identity(sessionmaker)
        operation_id, run_id = UUID(str(operation_id)), UUID(str(run_id))
        project_id = settings.langfuse_project_id
        if not project_id or settings.env == "protocol-evaluation" or type(expected_source_version) is not int or expected_source_version < 1:
            raise PromptBundleError("root_operator_arguments_invalid")
        options = {"timeout_in_seconds": 30, "max_retries": 0}

        async def network(function, **kwargs):
            return await _run_thread_until_quiescent(function, on_cancel=lambda: None, **kwargs)

        def current_version():
            prompt = client.get_prompt(
                ROOT_BUNDLE_PROMPT_NAME, label=ROOT_BUNDLE_LABEL, type="text",
                cache_ttl_seconds=0, max_retries=0, fetch_timeout_seconds=10,
            )
            if type(prompt.version) is not int or prompt.version < 1:
                raise PromptBundleError("root_bundle_version_invalid")
            return prompt.version

        async with _quiescent_session_scope(sessionmaker(), complete_after_cancel=True) as lock_db:
            await lock_db.execute(text("select pg_advisory_xact_lock(hashtextextended(:name, 0))"), {
                "name": canonical_json([project_id, ROOT_BUNDLE_PROMPT_NAME, ROOT_BUNDLE_LABEL]),
            })
            async with sessionmaker() as db:
                existing = await db.get(PromptRootPromotion, operation_id)
                if existing is not None:
                    if (existing.project_id != project_id or existing.root_name != ROOT_BUNDLE_PROMPT_NAME
                            or existing.expected_source_version != expected_source_version):
                        raise PromptBundleError("root_operation_conflict")
                    if existing.state == "succeeded":
                        event = validate_promotion_row_artifacts(existing)
                        if (event.operator_actor != operator_actor
                                or existing.qualification_json["report"]["run_id"] != str(run_id)):
                            raise PromptBundleError("root_operation_conflict")
                        return event  # Historical receipt only; no live fetch or second movement.
                    if existing.state == "cancelled" and existing.failure_code == "root_bundle_source_conflict":
                        raise PromptBundleError("root_bundle_source_conflict")
                    raise PromptBundleError("root_promotion_reconciliation_required")
                query = select(PromptRootPromotion).where(
                    PromptRootPromotion.project_id == project_id,
                    PromptRootPromotion.root_name == ROOT_BUNDLE_PROMPT_NAME,
                )
                if await db.scalar(query.where(PromptRootPromotion.state.in_(["prepared", "reconciliation_required"]))):
                    raise PromptBundleError("root_promotion_reconciliation_required")
                prior = await db.scalar(query.where(PromptRootPromotion.is_current.is_(True)))
                previous = None
                if prior is not None:
                    prior_event = validate_promotion_row_artifacts(prior)
                    if prior_event.target.root_version != expected_source_version:
                        raise PromptBundleError("root_bundle_source_conflict")
                    previous = _artifact_binding(prior, "graf-outcome-promotion-event-v1", prior.event_hash)

            try:
                approved = datetime.fromisoformat(approved_at)
                checks = [OperatorCheck.model_validate(value) for value in (protected_label, sole_mutation_credential)]
                if (not operator_actor.strip() or approved.tzinfo is None or approved > datetime.now(UTC)
                        or any(not check.method.strip() or not check.checked_by.strip()
                               or datetime.fromisoformat(check.checked_at).tzinfo is None
                               or datetime.fromisoformat(check.checked_at) > approved for check in checks)):
                    raise PromptBundleError("root_operator_evidence_invalid")
            except (ValueError, TypeError, AttributeError):
                raise PromptBundleError("root_operator_evidence_invalid") from None
            projects = await network(client.api.projects.get, request_options=options)
            if {project.id for project in projects.data} != {project_id}:
                raise PromptBundleError("root_project_mismatch")
            bundle, authority = validate_evaluation_snapshot(workdir.read_json("root-authority.json"))
            if authority["project_id"] != project_id or authority["run_id"] != str(run_id):
                raise PromptBundleError("root_qualification_report_mismatch")
            checked = await finalize_run(evaluation_settings, evaluation_sessionmaker, source_reader, workdir, run_id)
            if checked.get("complete") is not True or "qualification_report" not in checked:
                raise PromptBundleError("root_qualification_incomplete")
            report = FinalCorpusReport.model_validate(checked["qualification_report"])
            _, encoded, export_hash = build_root_export(bundle)
            row = PromptRootPromotion(
                id=operation_id, project_id=project_id, root_name=ROOT_BUNDLE_PROMPT_NAME,
                operation_kind="initial_activation" if prior is None else "promotion",
                expected_source_version=expected_source_version,
                root_export_json=json.loads(encoded), root_export_hash=export_hash,
                activation_json=root_bundle_document(bundle.root)["activation"],
                activation_hash=authority["activation_hash"], state="prepared", is_current=False,
            )
            candidate = _candidate_root(row, bundle.root)
            qualification = Qualification(
                schema_version="graf-outcome-qualification-v1", candidate_root=candidate,
                report=report, report_hash=_digest(report.model_dump(mode="json")),
                operator_actor=operator_actor, approved_at=approved_at, operation_kind=row.operation_kind,
                expected_source_version=expected_source_version, previous_event=previous,
                protected_label=checks[0], sole_mutation_credential=checks[1], safe_exit="disable_new_ai",
            )
            row.qualification_json = qualification.model_dump(mode="json")
            row.qualification_hash = _digest(row.qualification_json)
            target = await network(fetch_root_bundle_by_version, client=client, version=bundle.root.root_prompt_version)
            if build_root_export(target)[2] != export_hash or await network(current_version) != expected_source_version:
                raise PromptBundleError("root_bundle_source_conflict")

            async def finish():
                nonlocal mutation_possible
                # From the durable prepared boundary cancellation waits for completion.
                # A process crash leaves prepared, which requires explicit reconciliation.
                try:
                    async with sessionmaker() as db:
                        db.add(row)
                        await db.commit()
                    if await network(current_version) != expected_source_version:
                        async with sessionmaker() as db:
                            saved = await db.get(PromptRootPromotion, operation_id)
                            saved.state, saved.failure_code = "cancelled", "root_bundle_source_conflict"
                            await db.commit()
                        raise PromptBundleError("root_bundle_source_conflict")
                    # SDK update_prompt has implicit retries. Use its public API with
                    # retries disabled so a timeout cannot issue a second mutation.
                    mutation_possible = True
                    await network(client.api.prompt_version.update, name=quote(ROOT_BUNDLE_PROMPT_NAME, safe=""),
                                  version=bundle.root.root_prompt_version, new_labels=[ROOT_BUNDLE_LABEL],
                                  request_options=options)
                    readback = await network(fetch_root_bundle_by_label, client=client)
                    if build_root_export(readback)[2] != export_hash:
                        raise PromptBundleError("root_bundle_label_readback_mismatch")
                    event = PromotionEvent(
                        schema_version="graf-outcome-promotion-event-v1", operation_id=str(operation_id),
                        operator_actor=operator_actor, completed_at=datetime.now(UTC).isoformat(),
                        qualification=_artifact_binding(row, "graf-outcome-qualification-v1", row.qualification_hash),
                        expected_source_version=expected_source_version, target=candidate, readback=candidate, result="pass",
                    )
                    async with sessionmaker() as db:
                        if prior is not None:
                            old = await db.get(PromptRootPromotion, prior.id)
                            old.is_current = False
                            await db.flush()
                        saved = await db.get(PromptRootPromotion, operation_id)
                        saved.event_json = event.model_dump(mode="json")
                        saved.event_hash = _digest(saved.event_json)
                        saved.state, saved.is_current = "succeeded", True
                        validate_promotion_row(saved)
                        await db.commit()
                    return event
                except Exception:
                    failure_code = "root_promotion_reconciliation_required"
                    try:
                        async with sessionmaker() as db:
                            saved = await db.get(PromptRootPromotion, operation_id)
                            if saved is not None:
                                if saved.state == "cancelled" and saved.failure_code == "root_bundle_source_conflict":
                                    failure_code = "root_bundle_source_conflict"
                                elif saved.state == "prepared":
                                    saved.state = "reconciliation_required"
                                    saved.failure_code = failure_code
                                    await db.commit()
                    except Exception:
                        # The durable prepared row still fences retries if reconciliation cannot be saved.
                        failure_code = "root_promotion_reconciliation_required"
                    raise PromptBundleError(failure_code) from None

            return await _complete_async_operation_until_quiescent(finish(), complete_after_cancel=True)
    except PromptBundleError as exc:
        raise PromptBundleError(str(exc)) from None
    except Exception:
        raise PromptBundleError(
            "root_promotion_reconciliation_required" if mutation_possible else "root_promotion_unavailable"
        ) from None
