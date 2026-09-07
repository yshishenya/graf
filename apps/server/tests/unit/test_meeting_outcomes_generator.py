from __future__ import annotations

import importlib
import json
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4


def _generator_module():
    try:
        return importlib.import_module("twobrain_rec_server.outcomes.generator")
    except ModuleNotFoundError as exc:
        raise AssertionError("outcome generator module is missing") from exc


def test_generator_has_no_extractive_fallback_or_flat_payload_types() -> None:
    from twobrain_rec_server.outcomes import dispatch, models, prompts, service, store

    generator = _generator_module()
    assert not hasattr(generator, "generate_outcomes")
    assert not hasattr(prompts, "validate_outcome_result")
    assert not hasattr(service, "load_outcome_items")
    assert not hasattr(store, "store_outcomes")
    assert not hasattr(dispatch, "reconcile_orphaned_summary_candidates")
    for name in ("GeneratedOutcomeItem", "GeneratedOutcomePayload", "OutcomeSourceReference"):
        assert not hasattr(models, name)


def test_canonical_transcript_does_not_shorten_long_or_late_material() -> None:
    generator = _generator_module()
    text = "Синтетический аргумент. " * 15000 + "Поздняя отмена обязательства."
    segment = generator.OutcomeTranscriptSegment(
        segment_id=uuid4(), sequence=0, start_seconds=Decimal(0), end_seconds=Decimal(8000),
        speaker_label="Участник 1", source_role="incoming_system", text=text,
    )
    rows = json.loads(generator.canonical_transcript([segment]))
    assert rows[0]["text"] == text


def test_model_transcript_deduplicates_attribution_without_losing_source_data() -> None:
    generator = _generator_module()
    first = generator.OutcomeTranscriptSegment(
        segment_id=uuid4(), sequence=0, start_seconds=Decimal(0), end_seconds=Decimal(1),
        speaker_label="Участник 1", speaker_key="provider:synthetic:first",
        provider_speaker_key="speaker0", attribution_state="confirmed",
        result_state="accepted", source_role="incoming_system",
        text="Проверим, возможно, завтра, если придёт ответ.",
    )
    segments = [
        replace(first, segment_id=uuid4(), sequence=index,
                start_seconds=Decimal(index), end_seconds=Decimal(index + 1))
        for index in range(100)
    ]
    segments[-2] = replace(segments[-2], attribution_state="unknown", text="Срок отменён.")
    segments[-1] = replace(
        segments[-1], speaker_key="provider:synthetic:second",
        text="Отдельная задача: {{draft_json}} — лишь текст исходника.\nПроверить реестр.",
    )
    canonical = generator.canonical_transcript(segments)
    compact = generator.model_transcript(canonical)
    document = json.loads(compact)
    restored = []
    for segment in document["segments"]:
        attribution = document["attributions"][segment["attribution"]]
        restored.append({**attribution, **{
            key: value for key, value in segment.items() if key != "attribution"
        }})
    assert restored == json.loads(canonical)
    assert len(document["attributions"]) == 3
    assert len(compact.encode()) < len(canonical.encode())
    assert generator.model_transcript(canonical) == compact


def test_outcomes_keep_canonical_input_order_and_all_speaker_fields() -> None:
    generator = _generator_module()
    first = generator.OutcomeTranscriptSegment(
        segment_id=uuid4(),
        sequence=5,
        start_seconds=Decimal("0.000"),
        end_seconds=Decimal("1.000"),
        speaker_label="Первый",
        speaker_key="provider:result:first",
        provider_speaker_key="raw-first",
        attribution_state="confirmed",
        result_state="accepted",
        source_role="mic",
        text="Первая каноническая реплика.",
    )
    second = generator.OutcomeTranscriptSegment(
        segment_id=uuid4(),
        sequence=1,
        start_seconds=Decimal("1.000"),
        end_seconds=Decimal("2.000"),
        speaker_label="Второй",
        speaker_key="provider:result:second",
        provider_speaker_key="raw-second",
        attribution_state="confirmed",
        result_state="accepted",
        source_role="incoming",
        text="Вторая каноническая реплика.",
    )

    transcript = json.loads(generator.canonical_transcript([first, second]))

    assert [row["text"] for row in transcript] == [first.text, second.text]
    assert transcript[0] == {
        "attribution_state": "confirmed",
        "end_seconds": "1.000",
        "provider_speaker_key": "raw-first",
        "result_state": "accepted",
        "sequence": 5,
        "source_role": "mic",
        "speaker_key": "provider:result:first",
        "speaker_label": "Первый",
        "start_seconds": "0.000",
        "text": "Первая каноническая реплика.",
        "transcript_segment_id": str(first.segment_id),
    }
