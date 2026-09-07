from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Final, Literal

from pydantic import BaseModel, ValidationError

from twobrain_rec_server.outcomes.models import (
    PROTOCOL_SECTIONS,
    FactualExtraction,
    MeetingProtocol,
    OutcomeTranscriptSegment,
    ProtocolVerification,
)

CONFIG_CONTRACT_VERSION: Final = 5
PROMPT_LABEL: Final = "production"
VERIFIER_PROMPT_NAME: Final = "graf/meeting-outcome/verify"
EXTRACTOR_PROMPT_NAME: Final = "graf/meeting-outcome/extract"
CONTROL_GATE_CONFIG_KEY: Final = "graf_control_gate"
MAX_PROMPT_BYTES: Final = 65_536
MAX_CONFIG_BYTES: Final = 65_536
MAX_SCHEMA_BYTES: Final = 49_152
MAX_CONFIG_DEPTH: Final = 20
MAX_CONFIG_NODES: Final = 2048
ALLOWED_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
PROMPT_VARIABLE_RE = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
GENERIC_OWNER_LABEL_RE = re.compile(
    r"^(?:UNKNOWN|REMOTE|LOCAL|SPEAKER(?:[_ -]?[A-Z0-9]+)?|SPEAKER\s+\d+|(?:УЧАСТНИК|СПИКЕР)(?:[_ -]?[\w]+)?)$",
    re.IGNORECASE,
)
MODEL_PARAMETER_KEYS: Final = {
    "temperature",
    "top_p",
    "reasoning_effort",
    "max_tokens",
    "max_completion_tokens",
    "seed",
}
SOURCE_VARIABLES: Final = {
    "transcript_json",
    "output_language",
    "detail_level",
    "template_sections_json",
}
OUTCOME_VARIABLES: Final = SOURCE_VARIABLES | {"extraction_json"}
VERIFIER_VARIABLES: Final = SOURCE_VARIABLES | {"draft_json"}
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


def _inline_schema(model: type[BaseModel]) -> dict[str, object]:
    # Only expand our own generated schema; untrusted prompt configs forbid refs.
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def expand(value):
        if isinstance(value, list):
            return [expand(child) for child in value]
        if isinstance(value, dict):
            if "$ref" in value:
                return expand(definitions[value["$ref"].removeprefix("#/$defs/")])
            return {
                key: {name: expand(field) for name, field in child.items()}
                if key == "properties" else expand(child)
                # Large nested maxItems make Gemini reject the schema before
                # generation. Pydantic still enforces every local array limit.
                for key, child in value.items() if key not in {"title", "maxItems"}
            }
        return value

    return expand(schema)


def outcome_schema() -> dict[str, object]:
    return _inline_schema(MeetingProtocol)


def verification_schema() -> dict[str, object]:
    return _inline_schema(ProtocolVerification)


def extraction_schema() -> dict[str, object]:
    return _inline_schema(FactualExtraction)


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


def outcome_config(*, schema_name: str) -> dict[str, object]:
    """Schema template only; execution settings must come from Langfuse."""
    return {
        "config_contract_version": CONFIG_CONTRACT_VERSION,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": outcome_schema()},
        },
    }


def judge_config(*, schema_name: str) -> dict[str, object]:
    config = outcome_config(schema_name=schema_name)
    config["response_format"] = {
        "type": "json_schema",
        "json_schema": {"name": schema_name, "strict": True, "schema": judge_schema()},
    }
    return config


def verification_config() -> dict[str, object]:
    config = outcome_config(schema_name="graf_meeting_protocol_verification")
    config["response_format"]["json_schema"]["schema"] = verification_schema()
    return config


def extraction_config() -> dict[str, object]:
    config = outcome_config(schema_name="graf_meeting_factual_extraction")
    config["response_format"]["json_schema"]["schema"] = extraction_schema()
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
    root_document: dict[str, object] | None = None

    @property
    def model(self) -> str:
        return str(self.config["model"])

    @property
    def model_parameters(self) -> dict[str, object]:
        return model_parameters(self.config)

    def litellm_request(self, messages: Sequence[Mapping[str, str]]) -> dict[str, object]:
        return {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            **self.model_parameters,
        }


def model_parameters(config: Mapping[str, object]) -> dict[str, object]:
    return {
        key: _ordered_schema(config[key]) if key == "response_format" else config[key]
        for key in sorted(MODEL_PARAMETER_KEYS | {"response_format"})
        if key in config
    }


def _ordered_schema(value):
    """Recover generation order after JSON storage without changing canonical hashes."""
    if isinstance(value, list):
        return [_ordered_schema(child) for child in value]
    if isinstance(value, dict):
        result = {key: _ordered_schema(child) for key, child in value.items()}
        properties = result.get("properties")
        if isinstance(properties, dict):
            result["properties"] = {
                key: properties[key] for key in result["required"]
            }
        return result
    return value


def canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def prompt_variables(value: str) -> list[str]:
    variables = PROMPT_VARIABLE_RE.findall(value)
    remainder = PROMPT_VARIABLE_RE.sub("", value)
    if "{{" in remainder or "}}" in remainder:
        raise ValueError("prompt contains an invalid variable")
    return variables


def prompt_snapshot_hash(*, prompt: object, config: Mapping[str, object]) -> str:
    payload = canonical_json({"config": config, "prompt": prompt}).encode("utf-8")
    return sha256(payload).hexdigest()


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
) -> PromptSnapshot:
    if type(version) is not int or version < 1:
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
        verifier = name == VERIFIER_PROMPT_NAME
        extractor = name == EXTRACTOR_PROMPT_NAME
        _validate_outcome_config(config_copy, judge=False, verifier=verifier, extractor=extractor)
        variables = SOURCE_VARIABLES if extractor else VERIFIER_VARIABLES if verifier else OUTCOME_VARIABLES
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


def _validated_document(model: type[BaseModel], result: object) -> dict[str, object]:
    try:
        return model.model_validate(result).model_dump(mode="json")
    except ValidationError:
        # Pydantic errors contain the rejected input: never leak meeting content.
        raise ValueError("protocol_shape_invalid") from None


def _validate_document_refs(
    document: dict[str, object], segments: Sequence[OutcomeTranscriptSegment]
) -> None:
    by_sequence = {segment.sequence: segment for segment in segments}
    if (
        not segments
        or len({segment.segment_id for segment in segments}) != len(segments)
        or len(by_sequence) != len(segments)
        or any(
            type(segment.sequence) is not int
            or segment.sequence < 0
            or not segment.start_seconds.is_finite()
            or not segment.end_seconds.is_finite()
            or not 0 <= segment.start_seconds <= segment.end_seconds
            for segment in segments
        )
    ):
        raise ValueError("protocol_source_invalid")

    def visit(value: object) -> None:
        if isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, dict):
            for key, child in value.items():
                if key.endswith("source_refs"):
                    seen: set[int] = set()
                    for ref in child:
                        sequence = ref["sequence"]
                        segment = by_sequence.get(sequence)
                        if segment is None:
                            raise ValueError("protocol_reference_invalid")
                        if sequence in seen:
                            raise ValueError("protocol_reference_duplicate")
                        seen.add(sequence)
                        quote = ref["quote"]
                        if quote is not None and (not quote.strip() or quote not in segment.text):
                            raise ValueError("protocol_quote_invalid")
                else:
                    visit(child)

    visit(document)


def validate_protocol_result(
    result: object,
    *,
    segments: Sequence[OutcomeTranscriptSegment],
    sections: Sequence[str] = PROTOCOL_SECTIONS,
) -> dict[str, object]:
    document = _validated_document(MeetingProtocol, result)
    selected = set(sections)
    uncertain = document["uncertain_sections"]
    if (
        not selected
        or selected - set(PROTOCOL_SECTIONS)
        or len(selected) != len(sections)
        or len(set(uncertain)) != len(uncertain)
        or set(uncertain) - selected
        or any(document[section] for section in set(PROTOCOL_SECTIONS) - selected)
    ):
        raise ValueError("protocol_sections_invalid")
    for core in ("executive_summary", "topics"):
        if core in selected and not document[core] and core not in uncertain:
            raise ValueError("protocol_core_empty")
    count = sum(len(document[section]) for section in PROTOCOL_SECTIONS if section != "topics")
    count += sum(
        len(topic[field])
        for topic in document["topics"]
        for field in ("context", "discussion", "proposals_and_alternatives", "outcome")
    )
    if count > 500:
        raise ValueError("protocol_statement_limit")
    for action in document["action_items"]:
        if action["owner_text"] and GENERIC_OWNER_LABEL_RE.fullmatch(action["owner_text"]):
            raise ValueError("protocol_generic_owner")
    _validate_document_refs(document, segments)
    return document


def validate_protocol_verification(
    result: object, *, segments: Sequence[OutcomeTranscriptSegment]
) -> dict[str, object]:
    document = _validated_document(ProtocolVerification, result)
    _validate_document_refs(document, segments)
    return document


def validate_factual_extraction(
    result: object, *, segments: Sequence[OutcomeTranscriptSegment]
) -> dict[str, object]:
    document = _validated_document(FactualExtraction, result)
    _validate_document_refs(document, segments)
    for action in document["actions"]:
        if action["owner_text"] and GENERIC_OWNER_LABEL_RE.fullmatch(action["owner_text"]):
            raise ValueError("protocol_generic_owner")
    return document



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
    *,
    structured: bool,
) -> None:
    required = {"config_contract_version", "model"}
    if structured:
        required.add("response_format")
    if (
        not required <= set(config) <= required | MODEL_PARAMETER_KEYS
        or type(config.get("config_contract_version")) is not int
        or config["config_contract_version"] != CONFIG_CONTRACT_VERSION
    ):
        raise ValueError("prompt config does not match contract v5")
    model = config.get("model")
    if not isinstance(model, str) or not ALLOWED_MODEL_RE.fullmatch(model):
        raise ValueError("model route is invalid")
    for key, maximum in (("temperature", 2), ("top_p", 1)):
        if key in config and (
            type(config[key]) not in (int, float) or not 0 <= config[key] <= maximum
        ):
            raise ValueError(f"{key} is invalid")
    for key in ("max_tokens", "max_completion_tokens"):
        if key in config and (type(config[key]) is not int or config[key] < 1):
            raise ValueError(f"{key} is invalid")
    if "max_tokens" in config and "max_completion_tokens" in config:
        raise ValueError("only one token limit may be set")
    if "seed" in config and (
        type(config["seed"]) is not int or not -(2**63) <= config["seed"] < 2**63
    ):
        raise ValueError("seed is invalid")
    if "reasoning_effort" in config and (
        not isinstance(config["reasoning_effort"], str)
        or config["reasoning_effort"] not in {"none", "minimal", "low", "medium", "high", "xhigh"}
    ):
        raise ValueError("reasoning_effort is invalid")

def _validate_outcome_config(
    config: Mapping[str, object], *, judge: bool, verifier: bool = False, extractor: bool = False
) -> None:
    _validate_base_config(config, structured=True)
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
    expected_schema = (
        judge_schema() if judge else extraction_schema() if extractor
        else verification_schema() if verifier else outcome_schema()
    )
    if descriptor.get("schema") != expected_schema:
        raise ValueError("response schema does not match the closed contract v1")


def _validate_reflection_prompt(
    prompt_type: str, prompt: object, config: Mapping[str, object]
) -> None:
    if prompt_type != "text" or not isinstance(prompt, str):
        raise ValueError("reflection prompt must be text")
    _validate_base_config(config, structured=False)
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
