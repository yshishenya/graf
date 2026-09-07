"""All content is synthetic; exact calls, not semantic rewriting, authorize reuse."""

from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.fixtures.meeting_protocol import (
    extraction_result,
    pin_protocol_prompts,
    protocol_outcome,
    protocol_result,
)
from twobrain_rec_server.outcomes import ai_service
from twobrain_rec_server.outcomes.generator import canonical_transcript
from twobrain_rec_server.outcomes.models import OutcomeTranscriptSegment
from twobrain_rec_server.outcomes.prompts import canonical_json


def chain():
    segment = OutcomeTranscriptSegment(
        segment_id=uuid4(), sequence=0, start_seconds=Decimal(0), end_seconds=Decimal(3),
        text="Обсудили пилот.", speaker_label="Участник 1", source_role="incoming_system",
    )
    attempt = SimpleNamespace(
        prompt_name="graf/meeting-outcome/auto", template_key="graf-auto-v1", template_id=None,
        template_version=2, output_language="ru", detail_level="detailed", metadata_json={},
        header_snapshot_json=protocol_outcome().protocol_json["header"],
    )
    # Resolve the actual built-in name, not a fixture-specific execution branch.
    from twobrain_rec_server.outcomes.templates import prompt_name_for_template
    attempt.prompt_name = prompt_name_for_template(attempt.template_key, built_in=True)
    pin_protocol_prompts(attempt)
    attempt.metadata_json["execution_authority"] = {"synthetic": True}
    transcript = canonical_transcript([segment])
    extraction, draft = extraction_result([segment]), protocol_result([segment])
    calls = []
    for sequence, output in enumerate([extraction, draft, {"verdict": "pass", "findings": []}], 1):
        snapshot = ai_service._stage_snapshot(attempt, sequence)
        request = snapshot.litellm_request(ai_service._protocol_messages(
            snapshot, attempt, transcript, draft if sequence == 3 else None,
            extraction=extraction if sequence == 2 else None,
        ))
        validated = output if sequence < 3 else {
            "verification": output, "protocol": ai_service._enrich_protocol(draft, attempt.header_snapshot_json, [segment]),
            "draft_hash": ai_service._content_hash(draft), "extraction_hash": ai_service._content_hash(extraction),
        }
        raw = {"model": snapshot.model, "provider": "synthetic", "choices": [{
            "finish_reason": "stop", "message": {"content": canonical_json(output)},
        }]}
        calls.append(SimpleNamespace(
            id=uuid4(), call_sequence=sequence, call_state="completed", request_json=request,
            request_hash=ai_service._content_hash(request), transcript_text=transcript,
            transcript_hash=__import__("hashlib").sha256(transcript.encode()).hexdigest(),
            raw_response_json=raw, raw_response_hash=ai_service._content_hash(raw),
            validated_result_json=validated, validated_result_hash=ai_service._content_hash(validated),
            actual_model=snapshot.model, actual_provider="synthetic",
            predecessor_call_id=calls[-1].id if calls else None,
            predecessor_result_hash=calls[-1].validated_result_hash if calls else None,
            header_snapshot_hash=ai_service._content_hash(attempt.header_snapshot_json),
            execution_authority_json=attempt.metadata_json["execution_authority"],
            execution_authority_hash=ai_service._content_hash(attempt.metadata_json["execution_authority"]),
        ))
    return attempt, [segment], transcript, calls


@pytest.mark.parametrize("mutation", [None, "missing", "predecessor", "raw", "authority", "header", "request"])
def test_full_chain_reparses_raw_and_rejects_tamper(mutation):
    attempt, segments, transcript, calls = chain()
    if mutation == "missing":
        calls.pop(0)
    elif mutation == "predecessor":
        calls[1].predecessor_call_id = uuid4()
    elif mutation == "raw":
        calls[0].raw_response_json["choices"][0]["message"]["content"] = '{"facts":[],"actions":[]}'
        calls[0].raw_response_hash = ai_service._content_hash(calls[0].raw_response_json)
    elif mutation == "authority":
        calls[1].execution_authority_json = {"synthetic": False}
        calls[1].execution_authority_hash = ai_service._content_hash(calls[1].execution_authority_json)
    elif mutation == "header":
        attempt.header_snapshot_json["title"] = "Подменённый заголовок"
    elif mutation == "request":
        calls[1].request_json["messages"] = []
        calls[1].request_hash = ai_service._content_hash(calls[1].request_json)
    before = deepcopy([call.validated_result_json for call in calls])
    if mutation:
        with pytest.raises((ai_service.OutcomeGenerationTerminalError, ValueError)):
            ai_service._validate_protocol_chain(attempt, calls, segments, transcript)
    else:
        ai_service._validate_protocol_chain(attempt, calls, segments, transcript)
    assert [call.validated_result_json for call in calls] == before
