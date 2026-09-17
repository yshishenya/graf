from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests.unit.test_meeting_protocol import protocol_fixture, source_fixture
from twobrain_rec_server.cli.langfuse_prompts import desired_prompts
from twobrain_rec_server.outcomes.generator import canonical_transcript
from twobrain_rec_server.outcomes.prompt_optimization import (
    ModelCall,
    PromptOptimizationAdapter,
    PromptOptimizationError,
    SyntheticExample,
    _ProductionModelExecutor,
    task_model_variables,
    validate_judge_result,
)
from twobrain_rec_server.outcomes.prompts import (
    JUDGE_VARIABLES,
    canonical_json,
    outcome_config,
    validate_prompt_snapshot,
)
from twobrain_rec_server.outcomes.templates import OUTCOME_CATEGORIES


def _task_snapshot(protocol=True):
    name = "graf/meeting-outcome/auto"
    if protocol:
        prompt_type, prompt, config = desired_prompts(model="synthetic-model")[name]
    else:
        prompt_type = "chat"
        prompt = [{"role": "user", "content": (
            "{{transcript_json}} {{output_language}} {{detail_level}} {{template_sections_json}}"
        )}]
        config = outcome_config(schema_name="graf_meeting_outcome_auto_v1")
    return validate_prompt_snapshot(
        name=name, version=1, prompt_type=prompt_type, prompt=prompt, config=config,
    )


def _evaluate_task(snapshot, example, output):
    calls = []
    judges = []

    class Gateway:
        async def generate(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                request=kwargs["messages"], raw_response={"content": output},
                parsed_content=output, token_usage=None, cost_details=None,
                actual_model=None, actual_provider=None,
            )

    executor = _ProductionModelExecutor.__new__(_ProductionModelExecutor)
    executor.gateway = Gateway()
    adapter = PromptOptimizationAdapter.__new__(PromptOptimizationAdapter)
    adapter.contract = SimpleNamespace(source=snapshot, judges=dict.fromkeys(JUDGE_VARIABLES))

    def call(**kwargs):
        if kwargs["phase"] == "task":
            return executor(**{key: kwargs[key] for key in (
                "phase", "snapshot", "prompt_text", "variables",
            )})
        judges.append(kwargs["variables"])
        result = {"score": 1, "verdict": "pass", "feedback": "supported"}
        return ModelCall(request={}, raw_response=result, validated_result=result)

    adapter._call = call
    result = adapter.evaluate(
        [example], {"outcome_prompt": canonical_json(snapshot.prompt)}, capture_traces=True,
    )
    return result, calls, judges


@pytest.mark.parametrize("input_shape", ["canonical", "legacy_id", "text_only"])
def test_optimizer_protocol_inputs_and_strict_canonical_validation(input_shape):
    segment = source_fixture()[0]
    if input_shape == "canonical":
        transcript = canonical_transcript([segment])
        ids = frozenset({str(segment.segment_id)})
    else:
        row = {"text": segment.text}
        if input_shape == "legacy_id":
            row["id"] = str(segment.segment_id)
        transcript = canonical_json([row])
        ids = frozenset({str(segment.segment_id)}) if "id" in row else frozenset()
    example = SyntheticExample(
        id="protocol-offline", transcript_json=transcript, segment_ids=ids,
        required_categories=tuple(OUTCOME_CATEGORIES),
    )
    document = protocol_fixture()
    result, calls, judges = _evaluate_task(_task_snapshot(), example, document)
    assert len(calls) == 1 and len(judges) == 3
    assert result.scores == [1.0]
    validated = result.outputs[0]
    assert validated["protocol"]["action_items"][0]["task"] == document["action_items"][0]["task"]
    ref = validated["protocol"]["action_items"][0]["source_refs"][0]
    assert ref["sequence"] == 0 and ref["quote"] == segment.text
    assert ref["processing_result_id"]
    if input_shape != "text_only":
        assert ref["transcript_segment_id"] == str(segment.segment_id)
    if input_shape == "canonical":
        assert ref["start_seconds"] == float(segment.start_seconds)
        assert ref["end_seconds"] == float(segment.end_seconds)
        assert ref["source_role"] == segment.source_role
    assert all(item["candidate_outcome_json"] == canonical_json(validated) for item in judges)
    assert all(ref["transcript_segment_id"] in item["source_segments_json"] for item in judges)
    assert result.trajectories[0].transcript_json == judges[0]["source_segments_json"]
    messages = calls[0]["messages"]
    assert all("{{meeting_metadata_json}}" not in item["content"] for item in messages)
    assert task_model_variables(transcript, protocol=True)["meeting_metadata_json"] == "{}"
    assert example.transcript_json == transcript


@pytest.mark.parametrize("fault", ["unknown_ref", "duplicate_ref", "quote", "extra", "flat"])
def test_optimizer_protocol_rejects_invalid_model_output(fault):
    document = protocol_fixture()
    refs = document["action_items"][0]["source_refs"]
    if fault == "unknown_ref":
        refs[0]["sequence"] = 99
    elif fault == "duplicate_ref":
        refs.append(dict(refs[0]))
    elif fault == "quote":
        refs[0]["quote"] = "Invented quote"
    elif fault == "extra":
        document["untrusted_extra"] = True
    else:
        document = {"category_states": {}, "items": []}
    example = SyntheticExample(
        id="invalid-protocol", transcript_json=canonical_transcript(source_fixture()),
        segment_ids=frozenset({str(source_fixture()[0].segment_id)}),
        required_categories=tuple(OUTCOME_CATEGORIES),
    )
    with pytest.raises(ValueError):
        _evaluate_task(_task_snapshot(), example, document)


def test_optimizer_retains_legacy_flat_inputs_and_output():
    transcript = '[{"text":"Synthetic legacy input"}]'
    example = SyntheticExample(
        id="legacy-offline", transcript_json=transcript, segment_ids=frozenset(),
        required_categories=tuple(OUTCOME_CATEGORIES),
    )
    output = {
        "category_states": {category: "not_found" for category in OUTCOME_CATEGORIES},
        "items": [],
    }
    result, calls, _judges = _evaluate_task(_task_snapshot(False), example, output)
    assert result.outputs == [output]
    assert len(calls) == 1
    assert set(task_model_variables(transcript)) == {
        "transcript_json", "output_language", "detail_level", "template_sections_json",
    }
    assert transcript in calls[0]["messages"][0]["content"]


@pytest.mark.parametrize("protocol", [False, True])
def test_optimizer_executor_rejects_wrong_task_variable_contract(protocol):
    executor = _ProductionModelExecutor.__new__(_ProductionModelExecutor)
    snapshot = _task_snapshot(protocol)
    with pytest.raises(PromptOptimizationError, match="optimization_task_variables_invalid"):
        executor(
            phase="task", snapshot=snapshot, prompt_text=canonical_json(snapshot.prompt),
            variables=task_model_variables("[]", protocol=not protocol),
        )


def test_validation_retry_uses_distinct_observable_call_key() -> None:
    adapter = PromptOptimizationAdapter.__new__(PromptOptimizationAdapter)
    calls: list[str] = []

    def fake_call(**kwargs):
        calls.append(str(kwargs["example_id"]))
        return SimpleNamespace(validated_result={"attempt": len(calls)})

    adapter._call = fake_call  # type: ignore[method-assign]

    def validator(value: object) -> dict[str, int]:
        if value == {"attempt": 1}:
            raise ValueError("semantic contract is temporarily invalid")
        return value  # type: ignore[return-value]

    call, result = adapter._call_with_validation_retry(
        phase="task",
        snapshot=SimpleNamespace(),
        prompt_text="{}",
        variables={},
        example_id="example-1",
        validator=validator,
    )

    assert calls == ["example-1", "example-1:validation-retry-1"]
    assert call.validated_result == {"attempt": 2}
    assert result == {"attempt": 2}


def test_judge_fail_or_inconsistent_verdict_is_a_per_example_hard_failure() -> None:
    assert validate_judge_result(
        {"score": 0.75, "verdict": "fail", "feedback": "bounded feedback"}
    ) == {"score": 0.0, "verdict": "fail", "feedback": "bounded feedback"}
    assert validate_judge_result(
        {"score": 0.4, "verdict": "fail", "feedback": "bounded feedback"}
    ) == {"score": 0.0, "verdict": "fail", "feedback": "bounded feedback"}
