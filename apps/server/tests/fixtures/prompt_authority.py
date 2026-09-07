"""Complete synthetic admission records; no operator or evaluation side effects."""

import json
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4

from tests.fixtures.outcome_prompts import desired_prompts
from twobrain_rec_server.cli.meeting_protocol_eval import REVIEW_CRITERIA
from twobrain_rec_server.db.models import PromptRootPromotion
from twobrain_rec_server.outcomes.prompt_bundle import (
    OUTCOME_PROMPT_NAMES,
    ROOT_BUNDLE_EXPORT_SCHEMA_VERSION,
    ROOT_BUNDLE_PROMPT_NAME,
    FinalCorpusReport,
    ResolvedPromptBundle,
    build_root_bundle_document,
    build_root_export,
    validate_root_bundle_document,
)
from twobrain_rec_server.outcomes.prompts import canonical_json, validate_prompt_snapshot


def digest(value):
    return sha256(canonical_json(value).encode()).hexdigest()


def prompt_bundle(*, root_version=42):
    prompts = desired_prompts()
    children = {}
    for version, name in enumerate(sorted(OUTCOME_PROMPT_NAMES), 1):
        kind, prompt, config = prompts[name]
        children[name] = validate_prompt_snapshot(
            name=name, version=version, prompt_type=kind, prompt=prompt, config=config,
        )
    root = validate_root_bundle_document(
        build_root_bundle_document(children), root_prompt_version=root_version,
    )
    return ResolvedPromptBundle(root=root, children=children, source="langfuse_production")


def artifact_binding(row, kind):
    schemas = {
        "root_export": ROOT_BUNDLE_EXPORT_SCHEMA_VERSION,
        "activation": "graf-outcome-activation-v1",
        "qualification": "graf-outcome-qualification-v1",
        "event": "graf-outcome-promotion-event-v1",
    }
    return dict(artifact_id=str(row.id), schema_version=schemas[kind], artifact_version=1,
                hash=getattr(row, f"{kind}_hash"))


def promotion_row(*, root_version=42, previous=None, runtime_hash=None,
                  project_id="synthetic-project", is_current=True):
    """Return an unpersisted successful ORM row, with all hashes and full bodies.

    `previous` binds a real synthetic predecessor. `runtime_hash` simulates an
    earlier implementation with the same artifact schemas, never a live bypass.
    """
    _, encoded, _ = build_root_export(prompt_bundle(root_version=root_version))
    export = json.loads(encoded)
    root = export["bundle"]
    if runtime_hash is not None:
        root["runtime_contract_hash"] = runtime_hash
        root["activation"]["runtime_contract_hash"] = runtime_hash
        root["activation_hash"] = digest(root["activation"])
        root["bundle_hash"] = digest({
            key: value for key, value in root.items()
            if key not in {"bundle_hash", "root_prompt_version"}
        })
    row = PromptRootPromotion(
        id=uuid4(), project_id=project_id, root_name=ROOT_BUNDLE_PROMPT_NAME,
        operation_kind="initial_activation" if previous is None else "promotion",
        expected_source_version=(1 if previous is None else
                                 previous.event_json["target"]["root_version"]),
        root_export_json=export, root_export_hash=digest(export),
        activation_json=deepcopy(root["activation"]), activation_hash=root["activation_hash"],
        state="succeeded", is_current=is_current,
    )
    candidate = dict(project_id=project_id, root_name=row.root_name, root_version=root_version,
                     root_export=artifact_binding(row, "root_export"),
                     activation=artifact_binding(row, "activation"))

    def calls():
        return [dict(call_id=str(uuid4()), validated_result_hash="a" * 64) for _ in range(3)]

    controls = (
        "informal_commitment", "conditional_commitment", "refused_commitment",
        "third_party_guess", "later_correction", "prompt_injection", "unknown_owner_and_due",
    )
    timestamp = "2026-09-07T00:00:00Z"
    meeting_id = str(uuid4())
    report = FinalCorpusReport.model_validate({
        "schema_version": "graf-outcome-corpus-report-v1", "run_id": str(uuid4()),
        "project_id": project_id, "root_name": row.root_name, "root_version": root_version,
        "root_export_hash": row.root_export_hash, "activation_hash": row.activation_hash,
        "runtime_hash": root["runtime_contract_hash"], "cutoff_at": timestamp,
        "inventory": [dict(meeting_id=meeting_id, source_hash="b" * 64, selection_status="available")],
        "reviews": [dict(meeting_id=meeting_id, source_hash="b" * 64, candidate_id=str(uuid4()),
                           output_hash="c" * 64, calls=calls(), criteria=dict.fromkeys(REVIEW_CRITERIA, "pass"))],
        "exclusions": [],
        "controls": [dict(case_id=case, candidate_id=str(uuid4()), source_hash="d" * 64,
                          output_hash="e" * 64, calls=calls(), verdict="pass") for case in controls],
        "privacy": dict(checked_at=timestamp, reviewer="synthetic-reviewer", verdict="pass"),
        "complete": True, "errors": {},
    }).model_dump(mode="json")
    check = dict(method="synthetic-check", checked_at=timestamp,
                 checked_by="synthetic-operator", result="pass")
    row.qualification_json = dict(
        schema_version="graf-outcome-qualification-v1", candidate_root=deepcopy(candidate),
        report=report, report_hash=digest(report), operator_actor="synthetic-operator",
        approved_at=timestamp, operation_kind=row.operation_kind,
        expected_source_version=row.expected_source_version,
        previous_event=None if previous is None else artifact_binding(previous, "event"),
        protected_label=deepcopy(check), sole_mutation_credential=deepcopy(check),
        safe_exit="disable_new_ai",
    )
    row.qualification_hash = digest(row.qualification_json)
    row.event_json = dict(
        schema_version="graf-outcome-promotion-event-v1", operation_id=str(row.id),
        operator_actor="synthetic-operator", completed_at=timestamp,
        qualification=artifact_binding(row, "qualification"),
        expected_source_version=row.expected_source_version,
        target=deepcopy(candidate), readback=deepcopy(candidate), result="pass",
    )
    row.event_hash = digest(row.event_json)
    return row
