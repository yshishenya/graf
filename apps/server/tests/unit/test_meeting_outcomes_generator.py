from __future__ import annotations

import importlib
import json
from decimal import Decimal
from uuid import uuid4


def _generator_module():
    try:
        return importlib.import_module("twobrain_rec_server.outcomes.generator")
    except ModuleNotFoundError as exc:
        raise AssertionError("outcome generator module is missing") from exc




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
