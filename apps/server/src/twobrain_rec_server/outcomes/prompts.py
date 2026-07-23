from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Final, Literal

from twobrain_rec_server.outcomes.templates import OUTCOME_CATEGORIES

CONFIG_CONTRACT_VERSION: Final = 1
PROMPT_LABEL: Final = "production"
CONTROL_GATE_CONFIG_KEY: Final = "graf_control_gate"
MAX_PROMPT_BYTES: Final = 65_536
MAX_CONFIG_BYTES: Final = 65_536
MAX_SCHEMA_BYTES: Final = 49_152
MAX_CONFIG_DEPTH: Final = 12
MAX_CONFIG_NODES: Final = 256
ALLOWED_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
PROMPT_VARIABLE_RE = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
OUTCOME_CONFIG_KEYS: Final = {
    "config_contract_version",
    "model",
    "temperature",
    "max_completion_tokens",
    "response_format",
}
REFLECTION_CONFIG_KEYS: Final = OUTCOME_CONFIG_KEYS - {"response_format"}
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
        "config_contract_version": 1,
        "model": model,
        "temperature": 1,
        "max_completion_tokens": 4096,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": outcome_schema()},
        },
    }


def judge_config(*, schema_name: str, model: str = "gpt-5.6-luna") -> dict[str, object]:
    config = outcome_config(schema_name=schema_name, model=model)
    config["config_contract_version"] = 2
    config["temperature"] = 1
    config["max_completion_tokens"] = 2048
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
    source: Literal["langfuse_production", "verified_promoted_snapshot"]
    canonical_hash: str

    @property
    def model(self) -> str:
        return str(self.config["model"])

    def litellm_request(self, messages: Sequence[Mapping[str, str]]) -> dict[str, object]:
        request: dict[str, object] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "temperature": self.config["temperature"],
            "max_completion_tokens": self.config["max_completion_tokens"],
        }
        if "response_format" in self.config:
            request["response_format"] = self.config["response_format"]
        return request


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
    if version < 1:
        raise ValueError("prompt version must be positive")
    if source not in {"langfuse_production", "verified_promoted_snapshot"}:
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
        _validate_outcome_config(config_copy, judge=False)
        _validate_prompt_variables(prompt, OUTCOME_VARIABLES)
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
        not isinstance(value.get("agreement"), (int, float))
        or isinstance(value.get("agreement"), bool)
        or float(value["agreement"]) < 0.9
        or not isinstance(value.get("agreement_threshold"), (int, float))
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
        if category != "action_items" and (
            item["owner_text"] is not None or item["due_date_text"] is not None
        ):
            raise ValueError("owner and due date are only valid for action items")
        refs = item["source_refs"]
        if not isinstance(refs, list) or len(refs) > 8:
            raise ValueError("source references are invalid")
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != {"transcript_segment_id", "sequence"}:
                raise ValueError("source reference is invalid")
            if str(ref["transcript_segment_id"]) not in allowed_segment_ids:
                raise ValueError("source reference is outside the pinned transcript")
            if (
                not isinstance(ref["sequence"], int)
                or isinstance(ref["sequence"], bool)
                or ref["sequence"] < 0
            ):
                raise ValueError("source reference sequence is invalid")
            if (
                allowed_segment_sequences is not None
                and int(ref["sequence"])
                != allowed_segment_sequences.get(str(ref["transcript_segment_id"]))
            ):
                raise ValueError("source reference sequence does not match the pinned transcript")
        normalized_items.append(
            {
                **item,
                "source_refs": [
                    {**ref, "evidence_kind": "segment"}
                    for ref in refs
                ],
            }
        )
        counts[category] += 1
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
    max_tokens = config.get("max_completion_tokens")
    if not isinstance(model, str) or not ALLOWED_MODEL_RE.fullmatch(model):
        raise ValueError("model route is invalid")
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not 0 <= temperature <= 2
    ):
        raise ValueError("temperature is invalid")
    if (
        isinstance(max_tokens, bool)
        or not isinstance(max_tokens, int)
        or not 1 <= max_tokens <= 8192
    ):
        raise ValueError("max_completion_tokens is invalid")


def _validate_outcome_config(config: Mapping[str, object], *, judge: bool) -> None:
    _validate_base_config(
        config,
        OUTCOME_CONFIG_KEYS,
        contract_versions={1, 2} if judge else {1},
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
        expected_temperature = 0 if config["config_contract_version"] == 1 else 1
        if config["temperature"] != expected_temperature or config["max_completion_tokens"] != 2048:
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
