from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import Final, Literal
from uuid import UUID

from twobrain_rec_server.outcomes.models import (
    PROTOCOL_VERSION,
    MeetingProtocol,
    OutcomeSourceReference,
    OutcomeTranscriptSegment,
)
from twobrain_rec_server.outcomes.templates import OUTCOME_CATEGORIES

CONFIG_CONTRACT_VERSION: Final = 1
PROMPT_LABEL: Final = "production"
CONTROL_GATE_CONFIG_KEY: Final = "graf_control_gate"
MAX_PROMPT_BYTES: Final = 65_536
MAX_CONFIG_BYTES: Final = 65_536
MAX_SCHEMA_BYTES: Final = 49_152
MAX_PROTOCOL_BYTES: Final = 2 * 1024 * 1024
MAX_CONFIG_DEPTH: Final = 24
MAX_CONFIG_NODES: Final = 1024
PROTOCOL_REQUEST_KEYS: Final = {
    "temperature", "top_p", "presence_penalty", "frequency_penalty", "seed", "stop",
    "max_tokens", "max_completion_tokens", "reasoning_effort", "response_format",
}
ALLOWED_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
PROMPT_VARIABLE_RE = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
GENERIC_OWNER_LABEL_RE = re.compile(
    r"^(?:UNKNOWN|REMOTE|LOCAL|SPEAKER(?:[_ -]?[A-Z0-9]+)?|SPEAKER\s+\d+)$",
    re.IGNORECASE,
)
OUTCOME_CONFIG_KEYS_WITH_LIMIT: Final = {
    "config_contract_version",
    "model",
    "temperature",
    "response_format",
}
OUTCOME_CONFIG_KEYS_WITHOUT_LIMIT: Final = OUTCOME_CONFIG_KEYS_WITH_LIMIT - {
    "max_completion_tokens"
}
REFLECTION_CONFIG_KEYS: Final = OUTCOME_CONFIG_KEYS_WITHOUT_LIMIT - {"response_format"}
REFLECTION_CONFIG_KEYS_WITHOUT_LIMIT: Final = OUTCOME_CONFIG_KEYS_WITHOUT_LIMIT - {
    "response_format"
}
OUTCOME_VARIABLES: Final = {
    "transcript_json",
    "output_language",
    "detail_level",
    "template_sections_json",
}
JUDGE_VARIABLES: Final = {
    "graf/evaluation/meeting-outcome-faithfulness": {
        "source_segments_json",
        "candidate_outcome_json",
    },
    "graf/evaluation/meeting-outcome-action-items": {
        "source_segments_json",
        "candidate_outcome_json",
    },
    "graf/evaluation/meeting-outcome-completeness": {
        "source_segments_json",
        "candidate_outcome_json",
        "required_categories_json",
    },
}


def meeting_protocol_schema() -> dict[str, object]:
    schema = MeetingProtocol.model_json_schema()
    definitions = schema.pop("$defs", {})

    def inline(value):
        if isinstance(value, dict):
            if "$ref" in value:
                return inline(definitions[value["$ref"].rsplit("/", 1)[-1]])
            if "const" in value:
                value = {**value, "enum": [value["const"]]}
                del value["const"]
            return {key: inline(child) for key, child in value.items()
                    if not (key == "title" and isinstance(child, str))}
        if isinstance(value, list):
            return [inline(child) for child in value]
        return value

    return inline(schema)


def validate_meeting_protocol(
    result: object, *, segments: Sequence[OutcomeTranscriptSegment], processing_result_id: UUID,
) -> dict[str, object]:
    if len(canonical_json(result).encode("utf-8")) > MAX_PROTOCOL_BYTES:
        raise ValueError("protocol size exceeds 2 MiB")
    protocol = MeetingProtocol.model_validate(result).model_dump()
    resolved_size = len(canonical_json(protocol).encode("utf-8"))
    by_sequence = {segment.sequence: segment for segment in segments}
    if len(by_sequence) != len(segments):
        raise ValueError("source sequences are not unique")

    def resolve(node):
        nonlocal resolved_size
        if isinstance(node, dict):
            for key, child in node.items():
                if key != "source_refs":
                    resolve(child)
                    continue
                refs = []
                seen = set()
                for ref in child:
                    segment = by_sequence.get(ref["sequence"])
                    if segment is None or ref["sequence"] in seen:
                        raise ValueError("source reference is unknown or duplicate")
                    seen.add(ref["sequence"])
                    if ref["quote"] is not None and ref["quote"] not in segment.text:
                        raise ValueError("source quote is not literal")
                    canonical_ref = {
                        **OutcomeSourceReference(
                            transcript_segment_id=segment.segment_id,
                            sequence=segment.sequence,
                            start_seconds=float(segment.start_seconds),
                            end_seconds=float(segment.end_seconds),
                            speaker_label=segment.speaker_label, source_role=segment.source_role,
                        ).as_json(),
                        "processing_result_id": str(processing_result_id), "quote": ref["quote"],
                    }
                    resolved_size += (
                        len(canonical_json(canonical_ref).encode("utf-8"))
                        - len(canonical_json(ref).encode("utf-8"))
                    )
                    if resolved_size > MAX_PROTOCOL_BYTES:
                        raise ValueError("resolved protocol size exceeds 2 MiB")
                    refs.append(canonical_ref)
                node[key] = refs
        elif isinstance(node, list):
            for child in node:
                resolve(child)

    resolve(protocol)
    groups = {category: [] for category in OUTCOME_CATEGORIES}
    groups["summary"] = protocol["executive_summary"] + protocol["objectives"]
    for topic in protocol["topics"]:
        statements = [item for key in ("context", "discussion", "proposals", "outcome")
                      for item in topic[key]]
        refs = {ref["sequence"]: ref for item in statements for ref in item["source_refs"]}
        groups["key_points"].append({"text": topic["title"], "source_refs": list(refs.values())})
        groups["key_points"].extend(statements)
    for category, field in (("decisions", "decisions"), ("action_items", "action_items"),
                            ("followups", "next_steps"), ("questions", "open_questions"),
                            ("evidence", "notes")):
        groups[category] = protocol[field]
    items = [
        {"category": category, "sequence": index, "text": item.get("text", item.get("task")),
         "owner_text": item.get("owner_text"), "due_date_text": item.get("due_date_text"),
         "truth_label": "supported", "source_refs": item["source_refs"]}
        for category, rows in groups.items() for index, item in enumerate(rows)
    ]
    states = {key: "available" if rows else "not_found" for key, rows in groups.items()}
    states["risks"] = "unavailable"  # Risks stay in topics; no semantic extraction.
    validated = {"protocol": protocol, "category_states": states, "items": items}
    if len(canonical_json(validated).encode("utf-8")) > MAX_PROTOCOL_BYTES:
        raise ValueError("resolved protocol size exceeds 2 MiB")
    return validated


def meeting_protocol_config(*, model: str, **parameters: object) -> dict[str, object]:
    config = {
        "contract_version": PROTOCOL_VERSION, "model": model,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "graf_meeting_protocol_v1", "strict": True,
            "schema": meeting_protocol_schema(),
        }},
        **parameters,
    }
    _validate_protocol_config(config)
    return config


def _validate_protocol_config(
    config: Mapping[str, object], *, require_current_schema: bool = True,
) -> None:
    required = {"contract_version", "model", "response_format"}
    if (not required <= config.keys() or config.keys() - required - PROTOCOL_REQUEST_KEYS
            or config["contract_version"] != PROTOCOL_VERSION):
        raise ValueError("protocol config keys or version are invalid")
    if not isinstance(config["model"], str) or not config["model"].strip():
        raise ValueError("model must be explicitly selected")
    for key, (low, high) in {
        "temperature": (0, 2), "top_p": (0, 1),
        "presence_penalty": (-2, 2), "frequency_penalty": (-2, 2),
    }.items():
        if key in config and (type(config[key]) not in (int, float)
                              or not math.isfinite(config[key])
                              or not low <= config[key] <= high):
            raise ValueError(f"{key} is invalid")
    for key in ("seed", "max_tokens", "max_completion_tokens"):
        if key in config and (type(config[key]) is not int
                              or (key != "seed" and config[key] <= 0)):
            raise ValueError(f"{key} is invalid")
    if "max_tokens" in config and "max_completion_tokens" in config:
        raise ValueError("token limits are mutually exclusive")
    if "reasoning_effort" in config and (
        not isinstance(config["reasoning_effort"], str) or not config["reasoning_effort"].strip()
    ):
        raise ValueError("reasoning_effort is invalid")
    if "stop" in config:
        stop = config["stop"]
        if not (isinstance(stop, str) and stop or isinstance(stop, list) and stop
                and all(isinstance(item, str) and item for item in stop)):
            raise ValueError("stop is invalid")
    response = config["response_format"]
    if not isinstance(response, dict) or set(response) != {"type", "json_schema"}:
        raise ValueError("protocol response_format is invalid")
    descriptor = response["json_schema"]
    if (response["type"] != "json_schema" or not isinstance(descriptor, dict)
            or set(descriptor) != {"name", "strict", "schema"}
            or descriptor["strict"] is not True
            or not isinstance(descriptor["name"], str)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", descriptor["name"])
            or not isinstance(descriptor["schema"], dict)
            or (require_current_schema and descriptor["schema"] != meeting_protocol_schema())):
        raise ValueError("protocol response schema does not match contract")


def outcome_schema() -> dict[str, object]:
    states = {
        category: {"type": "string", "enum": ["available", "not_found", "not_inferable"]}
        for category in OUTCOME_CATEGORIES
    }
    return {
        "type": "object",
        "properties": {
            "category_states": {
                "type": "object",
                "properties": states,
                "required": list(OUTCOME_CATEGORIES),
                "additionalProperties": False,
            },
            "items": {
                "type": "array",
                "maxItems": 100,
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": list(OUTCOME_CATEGORIES)},
                        "sequence": {"type": "integer", "minimum": 0, "maximum": 99},
                        "text": {"type": "string", "minLength": 1, "maxLength": 4000},
                        "owner_text": {
                            "anyOf": [{"type": "string", "maxLength": 240}, {"type": "null"}]
                        },
                        "due_date_text": {
                            "anyOf": [{"type": "string", "maxLength": 120}, {"type": "null"}]
                        },
                        "truth_label": {"type": "string", "enum": ["supported"]},
                        "source_refs": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "transcript_segment_id": {"type": "string", "format": "uuid"},
                                    "sequence": {"type": "integer", "minimum": 0},
                                },
                                "required": ["transcript_segment_id", "sequence"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "category",
                        "sequence",
                        "text",
                        "owner_text",
                        "due_date_text",
                        "truth_label",
                        "source_refs",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["category_states", "items"],
        "additionalProperties": False,
    }


def judge_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "score": {"type": "number", "minimum": 0, "maximum": 1},
            "verdict": {"type": "string", "enum": ["pass", "fail"]},
            "feedback": {"type": "string", "maxLength": 4000},
        },
        "required": ["score", "verdict", "feedback"],
        "additionalProperties": False,
    }


def outcome_config(*, schema_name: str, model: str = "gpt-5.6-luna") -> dict[str, object]:
    return {
        "config_contract_version": 2,
        "model": model,
        "temperature": 1,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": outcome_schema()},
        },
    }


def judge_config(*, schema_name: str, model: str = "gpt-5.6-luna") -> dict[str, object]:
    config = outcome_config(schema_name=schema_name, model=model)
    config["config_contract_version"] = 3
    config["temperature"] = 1
    config["response_format"] = {
        "type": "json_schema",
        "json_schema": {"name": schema_name, "strict": True, "schema": judge_schema()},
    }
    return config


@dataclass(frozen=True, slots=True)
class PromptSnapshot:
    name: str
    version: int
    prompt_type: Literal["chat", "text"]
    prompt: object
    config: dict[str, object]
    source: Literal[
        "langfuse_production", "langfuse_evaluation", "verified_promoted_snapshot"
    ]
    canonical_hash: str
    # Set only after the snapshot has been authorized by the immutable root
    # bundle. A child prompt without these bindings is not production-ready.
    root_bundle_hash: str | None = None
    root_prompt_version: int | None = None
    route_binding_hash: str | None = None
    route_binding: dict[str, object] | None = None

    @property
    def model(self) -> str:
        return str(self.config["model"])

    def litellm_request(self, messages: Sequence[Mapping[str, str]]) -> dict[str, object]:
        request: dict[str, object] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
        }
        request.update(self.request_parameters)
        return request

    @property
    def request_parameters(self) -> dict[str, object]:
        return {key: value for key, value in self.config.items() if key in PROTOCOL_REQUEST_KEYS}


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def prompt_variables(value: str) -> list[str]:
    variables = PROMPT_VARIABLE_RE.findall(value)
    remainder = PROMPT_VARIABLE_RE.sub("", value)
    if "{{" in remainder or "}}" in remainder:
        raise ValueError("prompt contains an invalid variable")
    return variables


def prompt_snapshot_hash(*, prompt: object, config: Mapping[str, object]) -> str:
    payload = canonical_json({"config": config, "prompt": prompt}).encode("utf-8")
    return sha256(payload).hexdigest()


def prompt_cache_key(*, project_identity: str, name: str, label: str) -> str:
    digest = sha256(canonical_json([project_identity, name, label]).encode()).hexdigest()
    return f"_system/prompts/label-snapshots/{digest}.json"


def persist_prompt_snapshot(storage, *, key: str, snapshot: PromptSnapshot) -> None:
    payload = canonical_json({
        "key": key, "name": snapshot.name, "version": snapshot.version,
        "prompt": snapshot.prompt, "config": snapshot.config,
        "canonical_hash": snapshot.canonical_hash,
    }).encode("utf-8")
    storage.put_stream(key, BytesIO(payload), len(payload))


def load_prompt_snapshot(storage, *, key: str, name: str) -> PromptSnapshot:
    payload = storage.get_bytes(key)
    if len(payload) > MAX_PROMPT_BYTES + MAX_CONFIG_BYTES + 4096:
        raise ValueError("prompt cache size is invalid")
    data = json.loads(payload)
    if (not isinstance(data, dict) or set(data) != {
        "key", "name", "version", "prompt", "config", "canonical_hash",
    } or data["key"] != key or data["name"] != name):
        raise ValueError("prompt cache identity mismatch")
    snapshot = validate_prompt_snapshot(
        name=name, version=data["version"], prompt_type="chat", prompt=data["prompt"],
        config=data["config"], source="verified_promoted_snapshot",
    )
    if snapshot.canonical_hash != data["canonical_hash"]:
        raise ValueError("prompt cache hash mismatch")
    return snapshot


def normalize_langfuse_prompt(prompt: object) -> object:
    """Keep the persisted prompt contract stable across Langfuse SDK wire enums."""
    if not isinstance(prompt, list):
        return prompt
    normalized: list[object] = []
    for item in prompt:
        if isinstance(item, dict) and item.get("type") == "chatmessage":
            normalized.append({**item, "type": "message"})
        else:
            normalized.append(item)
    return normalized


def langfuse_prompt_payload(prompt: object) -> object:
    """Translate the stable GRAF chat-message type to Langfuse v4's API enum."""
    if not isinstance(prompt, list):
        return prompt
    payload: list[object] = []
    for item in prompt:
        if isinstance(item, dict) and item.get("type") == "message":
            payload.append({**item, "type": "chatmessage"})
        else:
            payload.append(item)
    return payload


def validate_prompt_snapshot(
    *,
    name: str,
    version: int,
    prompt_type: str,
    prompt: object,
    config: Mapping[str, object],
    source: str = "langfuse_production",
    require_current_schema: bool = True,
) -> PromptSnapshot:
    if version < 1:
        raise ValueError("prompt version must be positive")
    if source not in {
        "langfuse_production",
        "langfuse_evaluation",
        "verified_promoted_snapshot",
    }:
        raise ValueError("unsupported prompt source")
    if prompt_type not in {"chat", "text"}:
        raise ValueError("unsupported prompt type")
    prompt = normalize_langfuse_prompt(prompt)
    if len(canonical_json(prompt).encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ValueError("prompt exceeds 64 KiB")
    config_copy = dict(config)
    _validate_json_limits(config_copy)
    control_gate = config_copy.pop(CONTROL_GATE_CONFIG_KEY, None)
    if control_gate is not None:
        _validate_control_gate_config(name, control_gate)
    if name == "graf/prompt-optimization/reflection":
        _validate_reflection_prompt(prompt_type, prompt, config_copy)
    elif name in JUDGE_VARIABLES:
        _validate_outcome_config(config_copy, judge=True)
        _validate_prompt_variables(prompt, JUDGE_VARIABLES[name])
    elif name.startswith("graf/meeting-outcome/"):
        if config_copy.get("contract_version") == PROTOCOL_VERSION:
            _validate_protocol_config(config_copy, require_current_schema=require_current_schema)
            variables = OUTCOME_VARIABLES | {"meeting_metadata_json"}
        else:
            # Offline historical evaluations still read their pinned flat schema.
            _validate_outcome_config(config_copy, judge=False)
            variables = OUTCOME_VARIABLES
        _validate_prompt_variables(prompt, variables)
        if prompt_type != "chat":
            raise ValueError("outcome prompt must be chat")
    else:
        raise ValueError("prompt name is not allowlisted")
    if control_gate is not None:
        config_copy[CONTROL_GATE_CONFIG_KEY] = control_gate
    return PromptSnapshot(
        name=name,
        version=version,
        prompt_type=prompt_type,  # type: ignore[arg-type]
        prompt=prompt,
        config=config_copy,
        source=source,  # type: ignore[arg-type]
        canonical_hash=prompt_snapshot_hash(prompt=prompt, config=config_copy),
    )


def _validate_control_gate_config(name: str, value: object) -> None:
    if name == "graf/prompt-optimization/reflection":
        expected = {
            "evaluator_version",
            "evidence_hash",
            "gate",
            "gate_version",
            "operator_actor_id",
            "operator_approved",
            "passed",
        }
        gate = "reflection"
    elif name in JUDGE_VARIABLES:
        expected = {
            "agreement",
            "agreement_threshold",
            "calibration_manifest_hash",
            "evaluator_version",
            "evidence_hash",
            "gate",
            "gate_version",
            "operator_actor_id",
            "operator_approved",
            "passed",
            "valid_rows",
        }
        gate = "judge"
    else:
        raise ValueError("control gate is only valid for control prompts")
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("control prompt gate config is invalid")
    if (
        value.get("gate_version") != 1
        or value.get("gate") != gate
        or value.get("passed") is not True
        or value.get("operator_approved") is not True
        or not isinstance(value.get("operator_actor_id"), str)
        or not str(value["operator_actor_id"]).strip()
        or not isinstance(value.get("evaluator_version"), str)
        or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", str(value["evaluator_version"]))
        or not isinstance(value.get("evidence_hash"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(value["evidence_hash"]))
    ):
        raise ValueError("control prompt gate config is invalid")
    if gate == "judge" and (
        not isinstance(value.get("agreement"), int | float)
        or isinstance(value.get("agreement"), bool)
        or float(value["agreement"]) < 0.9
        or not isinstance(value.get("agreement_threshold"), int | float)
        or isinstance(value.get("agreement_threshold"), bool)
        or float(value["agreement_threshold"]) < 0.9
        or not isinstance(value.get("valid_rows"), int)
        or isinstance(value.get("valid_rows"), bool)
        or int(value["valid_rows"]) < 10
        or not isinstance(value.get("calibration_manifest_hash"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(value["calibration_manifest_hash"]))
    ):
        raise ValueError("control prompt gate config is invalid")


def validate_outcome_result(
    result: object,
    *,
    allowed_categories: Sequence[str],
    allowed_segment_ids: set[str],
    allowed_segment_sequences: Mapping[str, int] | None = None,
    repair_source_refs: bool = False,
) -> dict[str, object]:
    if not isinstance(result, dict) or set(result) != {"category_states", "items"}:
        raise ValueError("outcome result must contain category_states and items only")
    states = result["category_states"]
    items = result["items"]
    categories = tuple(allowed_categories)
    if not categories or any(category not in OUTCOME_CATEGORIES for category in categories):
        raise ValueError("unsupported outcome category")
    if not isinstance(states, dict) or set(states) != set(OUTCOME_CATEGORIES):
        raise ValueError("category states do not match the closed outcome schema")
    allowed_states = {"available", "not_found", "not_inferable"}
    if any(state not in allowed_states for state in states.values()):
        raise ValueError("invalid category state")
    if not isinstance(items, list) or len(items) > 100:
        raise ValueError("outcome items must be a bounded list")
    seen: set[tuple[str, int]] = set()
    counts = {category: 0 for category in OUTCOME_CATEGORIES}
    normalized_items: list[dict[str, object]] = []
    sequence_to_segment: dict[int, str] = {}
    duplicate_sequences: set[int] = set()
    if allowed_segment_sequences is not None:
        for segment_id, segment_sequence in allowed_segment_sequences.items():
            if segment_sequence in sequence_to_segment:
                duplicate_sequences.add(segment_sequence)
            else:
                sequence_to_segment[segment_sequence] = segment_id
        for segment_sequence in duplicate_sequences:
            sequence_to_segment.pop(segment_sequence, None)
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("outcome item must be an object")
        required = {
            "category",
            "sequence",
            "text",
            "owner_text",
            "due_date_text",
            "truth_label",
            "source_refs",
        }
        if set(item) != required:
            raise ValueError("outcome item has unknown or missing fields")
        category = item["category"]
        sequence = item["sequence"]
        if (
            category not in categories
            or not isinstance(sequence, int)
            or isinstance(sequence, bool)
            or not 0 <= sequence <= 99
        ):
            raise ValueError("outcome item category or sequence is invalid")
        key = (category, sequence)
        if key in seen:
            raise ValueError("outcome item category/sequence must be unique")
        seen.add(key)
        text = item["text"]
        if not isinstance(text, str) or not 1 <= len(text) <= 4000:
            raise ValueError("outcome item text is invalid")
        if item["truth_label"] != "supported":
            raise ValueError("outcome item must be supported")
        owner_text = item["owner_text"] if category == "action_items" else None
        due_date_text = item["due_date_text"] if category == "action_items" else None
        if isinstance(owner_text, str) and GENERIC_OWNER_LABEL_RE.fullmatch(
            owner_text.strip()
        ):
            raise ValueError("generic speaker label cannot be an action owner")
        refs = item["source_refs"]
        if not isinstance(refs, list) or len(refs) > 8:
            raise ValueError("outcome item requires at least one source reference")
        normalized_refs: list[dict[str, object]] = []
        seen_refs: set[tuple[str, int]] = set()
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != {"transcript_segment_id", "sequence"}:
                if repair_source_refs:
                    continue
                raise ValueError("source reference is invalid")
            segment_id = str(ref["transcript_segment_id"])
            if (
                not isinstance(ref["sequence"], int)
                or isinstance(ref["sequence"], bool)
                or ref["sequence"] < 0
            ):
                if repair_source_refs:
                    continue
                raise ValueError("source reference sequence is invalid")
            provided_sequence = int(ref["sequence"])
            canonical_sequence = provided_sequence
            if allowed_segment_sequences is not None:
                canonical_sequence = allowed_segment_sequences.get(segment_id)
                if canonical_sequence is None:
                    if repair_source_refs:
                        # Some gateways preserve the segment position but
                        # rewrite or omit the UUID. Recover only when that
                        # position maps to exactly one pinned segment; never
                        # invent evidence for an unknown position.
                        segment_id = sequence_to_segment.get(provided_sequence)
                        if segment_id is None:
                            continue
                        canonical_sequence = provided_sequence
                    else:
                        raise ValueError("source reference is outside the pinned transcript")
                elif provided_sequence != canonical_sequence and not repair_source_refs:
                    raise ValueError("source reference sequence does not match pinned transcript")
            elif segment_id not in allowed_segment_ids:
                if repair_source_refs:
                    continue
                raise ValueError("source reference is outside the pinned transcript")
            ref_key = (segment_id, canonical_sequence)
            if ref_key in seen_refs:
                if repair_source_refs:
                    continue
                raise ValueError("source references must be unique")
            seen_refs.add(ref_key)
            normalized_refs.append(
                {
                    "transcript_segment_id": segment_id,
                    "sequence": canonical_sequence,
                    "evidence_kind": "segment",
                }
            )
        if not normalized_refs:
            if repair_source_refs:
                # A model item without a verifiable source is not safe to
                # publish. Keep the rest of the response when possible.
                continue
            raise ValueError("outcome item requires at least one source reference")
        normalized_items.append(
            {
                **item,
                "owner_text": owner_text,
                "due_date_text": due_date_text,
                "source_refs": normalized_refs,
            }
        )
        counts[category] += 1
    if repair_source_refs:
        normalized_states = dict(states)
        for category in OUTCOME_CATEGORIES:
            if counts[category] > 0:
                normalized_states[category] = "available"
            elif normalized_states[category] == "available":
                normalized_states[category] = "not_inferable"
        return {"category_states": normalized_states, "items": normalized_items}
    for category, state in states.items():
        if (state == "available") != (counts[category] > 0):
            raise ValueError("category state and item count disagree")
    return {"category_states": dict(states), "items": normalized_items}


def _validate_json_limits(config: Mapping[str, object]) -> None:
    encoded = canonical_json(config).encode("utf-8")
    if len(encoded) > MAX_CONFIG_BYTES:
        raise ValueError("prompt config exceeds 64 KiB")
    nodes = 0

    def visit(value: object, depth: int) -> None:
        nonlocal nodes
        if isinstance(value, dict):
            if depth > MAX_CONFIG_DEPTH:
                raise ValueError("prompt config nesting is too deep")
            if "$ref" in value:
                raise ValueError("prompt config cannot contain $ref")
            for child in value.values():
                nodes += 1
                visit(child, depth + 1)
        elif isinstance(value, list):
            if depth > MAX_CONFIG_DEPTH:
                raise ValueError("prompt config nesting is too deep")
            for child in value:
                nodes += 1
                visit(child, depth + 1)
        if nodes > MAX_CONFIG_NODES:
            raise ValueError("prompt config contains too many nodes")

    visit(config, 1)


def _validate_base_config(
    config: Mapping[str, object],
    expected_keys: set[str],
    *,
    contract_versions: Sequence[int] = (1,),
) -> None:
    if (
        set(config) != expected_keys
        or config.get("config_contract_version") not in contract_versions
    ):
        contract_label = (
            "contract v1" if tuple(contract_versions) == (1,) else "judge contract v1 or v2"
        )
        raise ValueError(f"prompt config does not match {contract_label}")
    model = config.get("model")
    temperature = config.get("temperature")
    if not isinstance(model, str) or not ALLOWED_MODEL_RE.fullmatch(model):
        raise ValueError("model route is invalid")
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, int | float)
        or not 0 <= temperature <= 2
    ):
        raise ValueError("temperature is invalid")
    if "max_completion_tokens" in config:
        max_tokens = config["max_completion_tokens"]
        if (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or not 1 <= max_tokens <= 8192
        ):
            raise ValueError("max_completion_tokens is invalid")

def _validate_outcome_config(config: Mapping[str, object], *, judge: bool) -> None:
    version = config.get("config_contract_version")
    _validate_base_config(
        config,
        OUTCOME_CONFIG_KEYS_WITHOUT_LIMIT,
        contract_versions={1, 2, 3} if judge else {1, 2},
    )
    response_format = config.get("response_format")
    if not isinstance(response_format, dict) or set(response_format) != {"type", "json_schema"}:
        raise ValueError("response_format must be an inline strict JSON schema")
    if response_format.get("type") != "json_schema":
        raise ValueError("response_format type must be json_schema")
    descriptor = response_format.get("json_schema")
    if not isinstance(descriptor, dict) or set(descriptor) != {"name", "strict", "schema"}:
        raise ValueError("json_schema descriptor is invalid")
    if descriptor.get("strict") is not True:
        raise ValueError("json_schema must be strict")
    name = descriptor.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name):
        raise ValueError("json_schema name is invalid")
    if len(canonical_json(descriptor.get("schema")).encode("utf-8")) > MAX_SCHEMA_BYTES:
        raise ValueError("response schema exceeds 48 KiB")
    expected_schema = judge_schema() if judge else outcome_schema()
    if descriptor.get("schema") != expected_schema:
        raise ValueError("response schema does not match the closed contract v1")
    if judge:
        expected_temperature = 0 if version == 1 else 1
        if config["temperature"] != expected_temperature:
            raise ValueError("judge settings do not match the config contract")


def _validate_reflection_prompt(
    prompt_type: str, prompt: object, config: Mapping[str, object]
) -> None:
    if prompt_type != "text" or not isinstance(prompt, str):
        raise ValueError("reflection prompt must be text")
    _validate_base_config(config, REFLECTION_CONFIG_KEYS)
    for variable in ("<curr_param>", "<side_info>"):
        if prompt.count(variable) != 1:
            raise ValueError(f"reflection prompt must contain {variable} exactly once")
    if "{{" in prompt or "}}" in prompt:
        raise ValueError("reflection prompt contains a legacy placeholder")
    if prompt.count("```") != 2:
        raise ValueError("reflection prompt must define one unlabelled fence")


def _validate_prompt_variables(prompt: object, expected: set[str]) -> None:
    body = canonical_json(prompt) if not isinstance(prompt, str) else prompt
    variables = prompt_variables(body)
    if set(variables) != expected or any(variables.count(name) != 1 for name in expected):
        raise ValueError("prompt variables must each appear exactly once")
