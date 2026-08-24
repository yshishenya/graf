from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid5

import pytest

from twobrain_rec_server.db.models import DiarizationSegment, TranscriptSegment

FIXTURE_NAMESPACE = UUID("12000000-0000-0000-0000-000000000120")
WORKSPACE_ID = uuid5(FIXTURE_NAMESPACE, "workspace")
MEETING_ID = uuid5(FIXTURE_NAMESPACE, "meeting")
RESULT_ID = uuid5(FIXTURE_NAMESPACE, "result")


@dataclass(frozen=True, slots=True)
class SyntheticExportFixture:
    result_id: UUID
    transcript_rows: tuple[TranscriptSegment, ...]
    diarization_rows: tuple[DiarizationSegment, ...]


def synthetic_export_fixture() -> SyntheticExportFixture:
    starts = ("0.000", "1.900", "4.000", "8.100", "60.100", "199.100", "3700.100")
    ends = ("1.000", "3.000", "5.000", "9.100", "61.100", "200.100", "3701.100")
    texts = (
        "Привет, GRAF.",
        "=НЕ_ВЫПОЛНЯТЬ()",
        "Возврат к первому спикеру.",
        "Неизвестная атрибуция.",
        "После 51 секунды.",
        "После 138 секунд.",
        "Реплика после часа.",
    )
    roles = ("mic", "mic", "mic", "incoming", "incoming", "incoming", "incoming")
    transcripts = tuple(
        TranscriptSegment(
            id=uuid5(FIXTURE_NAMESPACE, f"transcript-{index}"),
            processing_result_id=RESULT_ID,
            workspace_id=WORKSPACE_ID,
            meeting_id=MEETING_ID,
            sequence=index,
            start_seconds=Decimal(start),
            end_seconds=Decimal(end),
            text=text,
            source_role=role,
            source_role_original=role,
        )
        for index, (start, end, text, role) in enumerate(
            zip(starts, ends, texts, roles, strict=True)
        )
    )
    diarization = tuple(
        DiarizationSegment(
            id=uuid5(FIXTURE_NAMESPACE, f"diarization-{index}"),
            processing_result_id=RESULT_ID,
            workspace_id=WORKSPACE_ID,
            meeting_id=MEETING_ID,
            sequence=index,
            start_seconds=transcripts[index].start_seconds,
            end_seconds=transcripts[index].end_seconds,
            speaker_label=("speaker-a" if index in {0, 2} else "speaker-b"),
            text=transcripts[index].text,
            source_role=transcripts[index].source_role,
        )
        for index in range(7)
    )
    diarization[3].speaker_label = "UNKNOWN"
    return SyntheticExportFixture(
        result_id=RESULT_ID,
        transcript_rows=transcripts,
        diarization_rows=diarization,
    )


@pytest.fixture
def export_fixture() -> SyntheticExportFixture:
    return synthetic_export_fixture()
