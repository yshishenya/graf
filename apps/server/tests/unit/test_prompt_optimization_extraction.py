"""Synthetic requests through the real optimizer compiler and gateway decoder."""

import json
from types import SimpleNamespace

import httpx
import pytest

from tests.fixtures.meeting_protocol import extraction_result, protocol_bundle, protocol_result
from tests.unit.test_gepa_prompt_optimizer import _example, _snapshot, _synthetic_segments
from twobrain_rec_server.outcomes import prompt_optimization as optimizer
from twobrain_rec_server.outcomes.prompts import EXTRACTOR_PROMPT_NAME, canonical_json


def resolved_contract():
    bundle = protocol_bundle()
    return {
        "source_prompt": optimizer._snapshot_payload(bundle.child("graf/meeting-outcome/auto")),
        "extractor_prompt": optimizer._snapshot_payload(bundle.child(EXTRACTOR_PROMPT_NAME)),
        "reflection_prompt": optimizer._snapshot_payload(_snapshot("graf/prompt-optimization/reflection")),
        "judge_prompts": {name: optimizer._snapshot_payload(_snapshot(name)) for name in optimizer.JUDGE_NAMES},
    }


def test_contract_pins_root_extractor_but_not_controls():
    contract = optimizer._contract_from_resolved(resolved_contract())
    assert contract.extractor.root_bundle_hash == contract.source.root_bundle_hash
    assert contract.extractor.name == EXTRACTOR_PROMPT_NAME
    assert contract.reflection.root_bundle_hash is None
    assert all(item.root_bundle_hash is None for item in contract.judges.values())


def test_real_synthesis_executor_accepts_validated_extraction(monkeypatch, tmp_path):
    snapshot = protocol_bundle().child("graf/meeting-outcome/auto")
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "model": "synthetic-provider/model", "choices": [{"finish_reason": "stop", "message": {
                "content": canonical_json(protocol_result(_synthetic_segments()))}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        })

    client_type = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client_type(
        **kwargs, transport=httpx.MockTransport(respond)))
    key = tmp_path / "synthetic-key"
    key.write_text("synthetic-only")
    executor = optimizer._ProductionModelExecutor(settings=SimpleNamespace(
        litellm_base_url="https://synthetic.invalid", litellm_api_key_file=key,
        litellm_request_timeout_seconds=1,
    ))
    extraction = extraction_result(_synthetic_segments())
    variables = {**optimizer.task_model_variables(_example("compiler").transcript_json),
                 "extraction_json": canonical_json(extraction)}
    result = executor(phase="task", snapshot=snapshot,
                      prompt_text=canonical_json(snapshot.prompt), variables=variables)
    assert result.validated_result == protocol_result(_synthetic_segments())
    assert canonical_json(extraction) in canonical_json(requests[0]["messages"]).replace('\\"', '"')
    assert requests[0]["model"] == snapshot.model


@pytest.mark.parametrize("name,variables", [
    ("graf/evaluation/meeting-outcome-faithfulness", {"source_segments_json": "{{candidate_outcome_json}}", "candidate_outcome_json": "unchanged"}),
    ("graf/prompt-optimization/reflection", {"curr_param": "<side_info>", "side_info": "unchanged"}),
])
def test_compiler_substitutes_only_template_not_inserted_data(name, variables):
    snapshot = _snapshot(name)
    messages = optimizer._compile_optimization_messages(snapshot, variables)
    assert next(iter(variables.values())) in canonical_json(messages)
