from __future__ import annotations

import csv
import io
import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from urllib.parse import quote, urlsplit
from uuid import UUID

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import CONTENT_EXPORT_FORMATS_BY_SCOPE, MeetingProtocolView
from twobrain_rec_server.cabinet.speakers import speaker_names_for_result
from twobrain_rec_server.cabinet.view_models import (
    meeting_protocol_view,
    protocol_header_rows,
    source_role_label,
)
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaRevision,
    Meeting,
    MeetingOutcomeSet,
    MeetingSpeakerName,
    MeetingSummarySlot,
    ProcessingResult,
    TranscriptSegment,
)
from twobrain_rec_server.domain.speaker_turns import (
    CanonicalSpeakerModel,
    canonical_speaker_model,
    canonical_speech_available,
)
from twobrain_rec_server.domain.statuses import (
    MediaRevisionStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
)
from twobrain_rec_server.outcomes.models import (
    PROTOCOL_LABELS,
    PROTOCOL_SECTIONS,
    SPEAKER_IDENTITY_NOTE,
    protocol_without_evidence,
)
from twobrain_rec_server.outcomes.service import (
    load_egress_default_outcome,
    load_pinned_egress_outcome,
)
from twobrain_rec_server.processing.results import effective_processing_result_query

ExportScope = Literal["transcript", "summary", "combined"]
ExportFormat = Literal["txt", "md", "csv", "xlsx", "json", "srt", "vtt"]
AttributionState = Literal["confirmed", "unconfirmed", "unknown", "mixed", "uncertain"]

SCHEMA_VERSION = "graf.transcript-export.v2"
RENDERER_VERSION = "meeting-protocol-export-v2"
TURN_POLICY_VERSION = "canonical-provider-turns-v4"
UNKNOWN_SPEAKER_LABEL = "Спикер не определён"
FORMAT_COMPATIBILITY = CONTENT_EXPORT_FORMATS_BY_SCOPE
MEDIA_TYPES: dict[ExportFormat, str] = {
    "txt": "text/plain; charset=utf-8",
    "md": "text/markdown; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json; charset=utf-8",
    "srt": "application/x-subrip; charset=utf-8",
    "vtt": "text/vtt; charset=utf-8",
}
CSV_COLUMNS = (
    "sequence",
    "turn_id",
    "start_ms",
    "end_ms",
    "start_time",
    "end_time",
    "speaker_key",
    "speaker_label",
    "provider_speaker_key",
    "attribution_state",
    "result_state",
    "source_role",
    "text",
    "overlap",
    "source_segment_ids",
    "processing_result_id",
    "turn_policy_version",
)


@dataclass(frozen=True, slots=True)
class ExportSelection:
    content_scope: ExportScope
    format: ExportFormat
    processing_result_id: UUID
    outcome_set_id: UUID | None = None
    include_speaker_labels: bool = True
    include_timestamps: bool = True
    include_evidence: bool = True


@dataclass(frozen=True, slots=True)
class RawExportSegment:
    segment_id: str
    sequence: int
    start_ms: int
    end_ms: int
    text: str
    source_role: str
    source_role_original: str | None
    speaker_key: str
    speaker_label: str
    attribution_state: AttributionState
    timing_state: Literal["valid", "invalid"]
    omission_reason: str | None
    provider_speaker_key: str | None = None
    result_state: Literal["accepted", "degraded_provider_result"] = "accepted"


@dataclass(frozen=True, slots=True)
class CanonicalExportTurn:
    turn_id: str
    sequence: int
    start_ms: int
    end_ms: int
    text: str
    speaker_key: str
    speaker_label: str
    attribution_state: AttributionState
    source_role: str
    source_segment_ids: tuple[str, ...]
    overlap: bool
    provider_speaker_key: str | None = None
    result_state: Literal["accepted", "degraded_provider_result"] = "accepted"
    timing_state: Literal["valid", "invalid"] = "valid"


@dataclass(frozen=True, slots=True)
class SummaryExportRevision:
    outcome_set_id: str
    processing_result_id: str
    revision_token: str
    status: str
    source_kind: str
    generator_kind: str
    generator_version: str
    content_hash: str | None
    protocol: dict[str, object]


@dataclass(frozen=True, slots=True)
class ExportSnapshot:
    selection: ExportSelection
    meeting_id: str
    meeting_title: str
    language: str | None
    duration_seconds: int
    processing_result_id: str
    processing_result_version: int
    media_revision_id: str | None
    raw_segments: tuple[RawExportSegment, ...]
    canonical_turns: tuple[CanonicalExportTurn, ...]
    summary: SummaryExportRevision | None
    source_base_url: str | None = None
    source_workspace_id: str | None = None
    attribution_result_state: Literal["accepted", "degraded_provider_result"] = "accepted"
    attribution_reason_codes: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION
    renderer_version: str = RENDERER_VERSION
    turn_policy_version: str = TURN_POLICY_VERSION


@dataclass(frozen=True, slots=True)
class GeneratedContentExport:
    filename: str
    media_type: str
    body: bytes

    @property
    def byte_length(self) -> int:
        return len(self.body)


def validate_export_selection(selection: ExportSelection) -> None:
    if selection.format not in FORMAT_COMPATIBILITY[selection.content_scope]:
        raise ProblemDetail(
            status=422,
            code="unsupported_export_combination",
            title="Unsupported export combination",
        )
    summary_requested = selection.content_scope in {"summary", "combined"}
    if summary_requested != (selection.outcome_set_id is not None):
        raise ProblemDetail(
            status=422,
            code="invalid_export_selection",
            title="Invalid export selection",
        )


async def build_export_snapshot(
    db: AsyncSession,
    *,
    meeting: Meeting,
    result: ProcessingResult,
    selection: ExportSelection,
    pinned_summary_revision: tuple[str, UUID] | None = None,
    source_base_url: str | None = None,
) -> ExportSnapshot:
    validate_export_selection(selection)
    selection = _effective_export_selection(selection)
    transcript_requested = selection.content_scope in {"transcript", "combined"}
    current_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == meeting.workspace_id,
            MediaRevision.meeting_id == meeting.id,
            MediaRevision.status == MediaRevisionStatus.ACCEPTED.value,
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    effective_result = await db.scalar(
        effective_processing_result_query(
            workspace_id=meeting.workspace_id,
            meeting_id=meeting.id,
            media_revision_id=current_revision.id if current_revision is not None else None,
        )
    )
    if (
        result.id != selection.processing_result_id
        or result.workspace_id != meeting.workspace_id
        or result.meeting_id != meeting.id
        or current_revision is None
        or result.media_revision_id != current_revision.id
        or result.processing_workflow_id is None
        or (transcript_requested and (effective_result is None or effective_result.id != result.id))
        or result.status != ProcessingResultStatus.IMPORTED.value
        or (
            transcript_requested
            and (
                not canonical_speech_available(result)
                or
                result.transcript_status != ProcessingAvailabilityStatus.AVAILABLE.value
                or result.segment_count <= 0
                or result.diarization_status != ProcessingAvailabilityStatus.AVAILABLE.value
                or result.diarization_segment_count <= 0
            )
        )
    ):
        raise _stale_selection()

    transcript_rows = list(
        (
            await db.scalars(
                select(TranscriptSegment)
                .where(
                    TranscriptSegment.workspace_id == meeting.workspace_id,
                    TranscriptSegment.meeting_id == meeting.id,
                    TranscriptSegment.processing_result_id == result.id,
                )
                .order_by(TranscriptSegment.sequence.asc(), TranscriptSegment.start_seconds.asc())
            )
        ).all()
    )
    diarization_rows = list(
        (
            await db.scalars(
                select(DiarizationSegment)
                .where(
                    DiarizationSegment.workspace_id == meeting.workspace_id,
                    DiarizationSegment.meeting_id == meeting.id,
                    DiarizationSegment.processing_result_id == result.id,
                )
                .order_by(DiarizationSegment.start_seconds.asc(), DiarizationSegment.sequence.asc())
            )
        ).all()
    )
    transcript_rows_match = _same_processing_result_rows(
        transcript_rows, expected_result_id=result.id
    )
    diarization_rows_match = _same_processing_result_rows(
        diarization_rows, expected_result_id=result.id
    )
    transcript_visible = bool(
        result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.segment_count > 0
        and result.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.diarization_segment_count > 0
        and transcript_rows
        and transcript_rows_match
        and diarization_rows
        and diarization_rows_match
    )
    if transcript_requested and not transcript_visible:
        raise ProblemDetail(status=409, code="export_unavailable", title="Export unavailable")
    # Summary is an independent value stream.  It may be exported while the
    # transcript remains an internal transcript-only/diarization-pending result;
    # do not manufacture transcript evidence in that case.
    if not transcript_requested or not transcript_visible:
        transcript_rows = []
        diarization_rows = []
    speaker_names = speaker_names_for_result(
        (
            await db.scalars(
                select(MeetingSpeakerName).where(
                    MeetingSpeakerName.workspace_id == meeting.workspace_id,
                    MeetingSpeakerName.meeting_id == meeting.id,
                )
            )
        ).all(),
        result_imported_at=result.imported_at,
    )
    model = canonical_speaker_model(
        transcript_rows,
        diarization_rows,
        processing_result_id=result.id,
        speaker_names=speaker_names,
        source_result_hash=result.source_result_hash,
    )
    raw_segments = canonical_raw_segments(
        transcript_rows,
        result_state=model.result_state,
    )
    turns = _export_turns_from_model(model)
    summary = await _load_summary_revision(
        db,
        meeting=meeting,
        result=result,
        outcome_set_id=selection.outcome_set_id,
        pinned_summary_revision=pinned_summary_revision,
        require_matching_result=selection.content_scope == "combined",
    )
    metadata_result = result
    if (
        selection.content_scope == "summary"
        and summary is not None
        and summary.processing_result_id != str(result.id)
    ):
        metadata_result = await db.scalar(
            select(ProcessingResult).where(
                ProcessingResult.id == UUID(summary.processing_result_id),
                ProcessingResult.workspace_id == meeting.workspace_id,
                ProcessingResult.meeting_id == meeting.id,
            )
        )
        if metadata_result is None:
            raise _stale_selection()
    return ExportSnapshot(
        selection=selection,
        meeting_id=str(meeting.id),
        meeting_title=(meeting.title or "Встреча GRAF")
        if meeting.title_source == "user_confirmed"
        else _safe_title(meeting.title),
        language=metadata_result.language,
        duration_seconds=max(meeting.duration_seconds, 0),
        processing_result_id=str(metadata_result.id),
        processing_result_version=metadata_result.result_version,
        media_revision_id=(
            str(metadata_result.media_revision_id) if metadata_result.media_revision_id else None
        ),
        raw_segments=raw_segments,
        canonical_turns=turns,
        summary=summary,
        source_base_url=(
            source_base_url if transcript_visible and summary is not None
            and summary.processing_result_id == str(result.id) else None
        ),
        source_workspace_id=str(meeting.workspace_id),
        attribution_result_state=model.result_state,
        attribution_reason_codes=model.diagnostics.reason_codes,
    )


def canonical_export_turns(
    transcript_rows: list[TranscriptSegment],
    *,
    diarization_rows: list[DiarizationSegment],
    processing_result_id: UUID,
    speaker_names: dict[str, str] | None = None,
) -> tuple[CanonicalExportTurn, ...]:
    model = canonical_speaker_model(
        transcript_rows,
        diarization_rows,
        processing_result_id=processing_result_id,
        speaker_names=speaker_names,
    )
    return _export_turns_from_model(model)


def _export_turns_from_model(model: CanonicalSpeakerModel) -> tuple[CanonicalExportTurn, ...]:
    return tuple(
        CanonicalExportTurn(
            turn_id=turn.turn_id,
            sequence=turn.sequence,
            start_ms=_milliseconds(turn.start_seconds),
            end_ms=_milliseconds(turn.end_seconds),
            text=turn.text,
            speaker_key=turn.speaker_key,
            speaker_label=turn.speaker_label,
            provider_speaker_key=turn.provider_speaker_key,
            attribution_state=turn.attribution_state,
            result_state=turn.result_state,
            source_role=source_role_label(turn.source_role),
            source_segment_ids=(turn.source_segment_id,),
            overlap=turn.overlap,
        )
        for turn in model.turns
    )


def _same_processing_result_rows(
    rows: list[TranscriptSegment] | list[DiarizationSegment],
    *,
    expected_result_id: UUID,
) -> bool:
    result_ids = {row.processing_result_id for row in rows}
    return bool(result_ids) and result_ids == {expected_result_id}


def canonical_raw_segments(
    transcript_rows: list[TranscriptSegment],
    *,
    result_state: Literal["accepted", "degraded_provider_result"] = "accepted",
) -> tuple[RawExportSegment, ...]:
    output: list[RawExportSegment] = []
    for row in transcript_rows:
        valid_timing = row.start_seconds >= 0 and row.end_seconds > row.start_seconds
        omission_reason = None
        if not valid_timing:
            omission_reason = "invalid_timing"
        elif not row.text.strip():
            omission_reason = "empty_text"
        output.append(
            RawExportSegment(
                segment_id=str(row.id),
                sequence=row.sequence,
                start_ms=_milliseconds(row.start_seconds),
                end_ms=_milliseconds(row.end_seconds),
                text=row.text,
                source_role=source_role_label(row.source_role),
                source_role_original=row.source_role_original,
                speaker_key=f"evidence:{row.processing_result_id.hex}",
                speaker_label=UNKNOWN_SPEAKER_LABEL,
                attribution_state="uncertain",
                result_state=result_state,
                timing_state="valid" if valid_timing else "invalid",
                omission_reason=omission_reason,
            )
        )
    return tuple(output)


async def _load_summary_revision(
    db: AsyncSession,
    *,
    meeting: Meeting,
    result: ProcessingResult,
    outcome_set_id: UUID | None,
    pinned_summary_revision: tuple[str, UUID] | None = None,
    require_matching_result: bool = False,
) -> SummaryExportRevision | None:
    if outcome_set_id is None:
        return None
    if pinned_summary_revision is not None:
        template_key, pinned_outcome_id = pinned_summary_revision
        if pinned_outcome_id != outcome_set_id:
            raise _stale_selection()
        outcome_set = await load_pinned_egress_outcome(
            db,
            meeting=meeting,
            template_key=template_key,
            outcome_set_id=pinned_outcome_id,
        )
        if outcome_set is None:
            raise _stale_selection()
        default_slot = None
        current_pointer_id = outcome_set.id
    else:
        default_slot = await db.scalar(
            select(MeetingSummarySlot).where(
                MeetingSummarySlot.workspace_id == meeting.workspace_id,
                MeetingSummarySlot.meeting_id == meeting.id,
                MeetingSummarySlot.is_meeting_default.is_(True),
            )
        )
        if default_slot is not None:
            current_pointer_id = default_slot.current_outcome_set_id
        else:
            current_pointer_id = None
        if current_pointer_id != outcome_set_id:
            raise _stale_selection()
        if default_slot is not None:
            pinned_outcome = await load_egress_default_outcome(
                db,
                meeting=meeting,
                slot=default_slot,
            )
            if pinned_outcome is None or pinned_outcome.id != outcome_set_id:
                raise _stale_selection()
        outcome_set = await db.scalar(
            select(MeetingOutcomeSet).where(
                MeetingOutcomeSet.id == outcome_set_id,
                MeetingOutcomeSet.workspace_id == meeting.workspace_id,
                MeetingOutcomeSet.meeting_id == meeting.id,
                MeetingOutcomeSet.lifecycle_state == "active",
                or_(
                    MeetingOutcomeSet.revision_state.is_(None),
                    MeetingOutcomeSet.revision_state == "accepted",
                ),
            )
        )
    if outcome_set is None or (
        require_matching_result and outcome_set.processing_result_id != result.id
    ):
        raise _stale_selection()
    if meeting_protocol_view(outcome_set) is None:
        raise ProblemDetail(status=409, code="summary_protocol_unavailable", title="Сформируйте новую версию итогов")
    return SummaryExportRevision(
        outcome_set_id=str(outcome_set.id), processing_result_id=str(outcome_set.processing_result_id),
        revision_token=f"{outcome_set.id}:{outcome_set.content_hash}:{outcome_set.generator_version}",
        status=outcome_set.status, source_kind=outcome_set.source_kind,
        generator_kind=outcome_set.generator_kind, generator_version=outcome_set.generator_version,
        content_hash=outcome_set.content_hash, protocol=deepcopy(outcome_set.protocol_json),
    )


def render_content_export(snapshot: ExportSnapshot) -> GeneratedContentExport:
    snapshot = replace(
        snapshot,
        selection=_effective_export_selection(snapshot.selection),
    )
    if snapshot.selection.format in {"srt", "vtt"} and any(
        turn.end_ms <= turn.start_ms for turn in snapshot.canonical_turns
    ):
        raise ProblemDetail(
            status=409,
            code="subtitle_timing_unavailable",
            title="Subtitle timing unavailable",
        )
    renderer = {
        "txt": _render_txt,
        "md": _render_markdown,
        "csv": _render_csv,
        "xlsx": _render_xlsx,
        "json": _render_json,
        "srt": _render_srt,
        "vtt": _render_vtt,
    }[snapshot.selection.format]
    try:
        body = renderer(snapshot)
    except ProblemDetail:
        raise
    except Exception as exc:
        raise ProblemDetail(
            status=503,
            code="export_generation_failed",
            title="Export generation failed",
        ) from exc
    filename = (
        f"graf-meeting-{snapshot.meeting_id[:8]}-"
        f"{snapshot.selection.content_scope}-r{snapshot.processing_result_version}."
        f"{snapshot.selection.format}"
    )
    return GeneratedContentExport(
        filename=filename,
        media_type=MEDIA_TYPES[snapshot.selection.format],
        body=body,
    )


def _render_txt(snapshot: ExportSnapshot) -> bytes:
    if snapshot.selection.content_scope in {"summary", "combined"}:
        lines = _summary_lines(snapshot, markdown=False)
        if snapshot.selection.content_scope == "combined":
            lines.extend(("Транскрипт", "===========", ""))
            lines.extend(_human_transcript_lines(snapshot, markdown=False))
        return ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    lines = [
        snapshot.meeting_title,
        f"Состав: {_scope_label(snapshot.selection.content_scope)}",
        f"Версия расшифровки: {snapshot.processing_result_version}",
        f"Язык: {snapshot.language or 'не указан'}",
        f"Длительность: {_human_time(snapshot.duration_seconds * 1000)}",
        f"Разделение по спикерам: {_attribution_status_label(snapshot)}",
        "",
    ]
    lines.extend(_human_transcript_lines(snapshot, markdown=False))
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _render_markdown(snapshot: ExportSnapshot) -> bytes:
    if snapshot.selection.content_scope in {"summary", "combined"}:
        lines = _summary_lines(snapshot, markdown=True)
        if snapshot.selection.content_scope == "combined":
            lines.extend(("## Транскрипт", ""))
            lines.extend(_human_transcript_lines(snapshot, markdown=True))
        return ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    lines = [
        f"# {_markdown_escape(snapshot.meeting_title)}",
        "",
        f"- Состав: {_scope_label(snapshot.selection.content_scope)}",
        f"- Версия расшифровки: {snapshot.processing_result_version}",
        f"- Язык: {_markdown_escape(snapshot.language or 'не указан')}",
        f"- Длительность: {_human_time(snapshot.duration_seconds * 1000)}",
        f"- Разделение по спикерам: {_markdown_escape(_attribution_status_label(snapshot))}",
        "",
    ]
    lines.extend(_human_transcript_lines(snapshot, markdown=True))
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _human_transcript_lines(snapshot: ExportSnapshot, *, markdown: bool) -> list[str]:
    lines: list[str] = []
    for group in human_display_groups(
        snapshot.canonical_turns,
        raw_segments=snapshot.raw_segments,
    ):
        first = group[0]
        heading = first.speaker_label if snapshot.selection.include_speaker_labels else "Реплики"
        if markdown:
            lines.extend((f"### {_markdown_escape(heading)}", ""))
        else:
            lines.append(heading)
        for turn in group:
            timestamp = (
                f"[{_human_time(turn.start_ms)}] " if snapshot.selection.include_timestamps else ""
            )
            text = _markdown_escape(turn.text) if markdown else turn.text
            lines.append(f"{timestamp}{text}")
        lines.append("")
    return lines


def human_display_groups(
    turns: tuple[CanonicalExportTurn, ...],
    *,
    raw_segments: tuple[RawExportSegment, ...] = (),
) -> tuple[tuple[CanonicalExportTurn, ...], ...]:
    source_boundaries = {
        row.segment_id: row.source_role_original or row.source_role for row in raw_segments
    }

    def source_boundary(turn: CanonicalExportTurn) -> str:
        return source_boundaries.get(turn.source_segment_ids[0], turn.source_role)

    groups: list[list[CanonicalExportTurn]] = []
    for turn in turns:
        previous = groups[-1][-1] if groups else None
        if (
            previous is not None
            and turn.attribution_state == "confirmed"
            and previous.attribution_state == "confirmed"
            and turn.speaker_key == previous.speaker_key
            and source_boundary(turn) == source_boundary(previous)
            and not turn.overlap
            and not previous.overlap
            and 0 <= turn.start_ms - previous.end_ms <= 3000
        ):
            groups[-1].append(turn)
        else:
            groups.append([turn])
    return tuple(tuple(group) for group in groups)


def _protocol_evidence(snapshot, refs, *, markdown):
    if not snapshot.selection.include_evidence or not snapshot.selection.include_timestamps:
        return ""
    values = []
    seen = set()
    for ref in refs:
        key = ref.transcript_segment_id
        if key in seen or ref.start_seconds is None:
            continue
        seen.add(key)
        total = int(ref.start_seconds)
        hours, rest = divmod(total, 3600)
        minutes, seconds = divmod(rest, 60)
        time = f"{hours:02}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"
        label = f"[{time}]"
        if markdown and snapshot.source_base_url and snapshot.summary and key:
            base = urlsplit(snapshot.source_base_url)
            if base.scheme == "https" and base.netloc and not base.username and not base.password and not base.query and not base.fragment:
                path = "/cabinet/meetings/" + quote(snapshot.meeting_id, safe="") + "/sources/" + quote(snapshot.summary.outcome_set_id, safe="") + "/" + quote(str(key), safe="")
                if snapshot.source_workspace_id:
                    path += "?workspace_id=" + quote(snapshot.source_workspace_id, safe="")
                    label += f"({base.scheme}://{base.netloc}{path})"
        values.append(label)
    return " ".join(values)


def _summary_lines(snapshot: ExportSnapshot, *, markdown: bool) -> list[str]:
    if snapshot.summary is None:
        return ["Нужно сформировать новую версию итогов."]
    protocol = MeetingProtocolView.model_validate(snapshot.summary.protocol)
    language = int(protocol.header.get("output_language") == "en")
    literal = _markdown_escape if markdown else str
    lines = []

    def heading(text, level=2):
        lines.extend((f"{'#' * level} {literal(text)}" if markdown else text, ""))

    def statement(row):
        refs = row.source_refs + getattr(row, "acceptance_source_refs", [])
        return f"{literal(row.text)} {_protocol_evidence(snapshot, refs, markdown=markdown)}".strip()

    header = protocol_header_rows(protocol)
    heading(header[0][1], 1)
    for label, value in header[1:]:
        lines.append(f"{literal(label)}: {literal(value)}")
    lines.append("")
    selected = [key for key in protocol.header.get("sections", PROTOCOL_SECTIONS) if key in PROTOCOL_SECTIONS]
    if "notes" not in selected:
        selected.append("notes")
    for key in selected:
        heading(PROTOCOL_LABELS[key][language])
        rows = getattr(protocol, key)
        uncertain = key in protocol.uncertain_sections
        missing = ("Не удалось надёжно установить по доступной расшифровке.", "Cannot reliably establish from the available transcript.")[language] if uncertain else ("Не зафиксировано.", "Not recorded.")[language]
        if key == "topics":
            for topic in rows:
                heading(topic.title, 3)
                for part in ("context", "discussion", "proposals_and_alternatives", "outcome"):
                    values = getattr(topic, part)
                    if values:
                        heading(PROTOCOL_LABELS[part][language], 4)
                        lines.extend(f"- {statement(row)}" for row in values)
                        lines.append("")
            if not rows:
                lines.append(missing)
        elif key == "action_items":
            columns = ("Задача", "Ответственный", "Срок") if language == 0 else ("Task", "Owner", "Deadline")
            lines.append("| " + " | ".join(columns) + " |")
            if markdown:
                lines.append("| --- | --- | --- |")
            for task in rows:
                cells = []
                for text, refs in (
                    (task.task, task.task_source_refs),
                    (task.owner_text or ("Не назначен", "Not assigned")[language], task.owner_source_refs),
                    (task.due_date_text or ("Не указан", "Not specified")[language], task.due_date_source_refs),
                ):
                    value = literal(" ".join(text.splitlines()))
                    if markdown:
                        value = value.replace("|", "\\|")
                    cells.append(f"{value} {_protocol_evidence(snapshot, refs, markdown=markdown)}".strip())
                lines.append("| " + " | ".join(cells) + " |")
            if not rows:
                text = missing if uncertain else ("Задачи не зафиксированы", "No action items recorded")[language]
                lines.append(f"| {text} | {('Не назначен', 'Not assigned')[language]} | {('Не указан', 'Not specified')[language]} |")
        elif key == "executive_summary":
            lines.append(" ".join(statement(row) for row in rows) if rows else missing)
        elif key == "notes":
            lines.extend(f"- {statement(row)}" for row in rows)
            lines.append(SPEAKER_IDENTITY_NOTE[language])
        else:
            lines.extend(f"- {statement(row)}" for row in rows)
            if not rows:
                if not uncertain:
                    missing = {
                        "decisions": ("Принятые решения в расшифровке не зафиксированы.", "No adopted decisions recorded."),
                        "open_questions": ("Открытые вопросы не зафиксированы.", "No open questions recorded."),
                    }.get(key, (missing, missing))[language]
                lines.append(missing)
        lines.append("")
    return lines




def _render_csv(snapshot: ExportSnapshot) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    for turn in snapshot.canonical_turns:
        writer.writerow(_turn_row(snapshot, turn, safe_cells=True))
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def _render_json(snapshot: ExportSnapshot) -> bytes:
    transcript = None
    if snapshot.selection.content_scope in {"transcript", "combined"}:
        transcript = {
            "status": snapshot.attribution_result_state,
            "reason_codes": snapshot.attribution_reason_codes,
            "raw_segments": [asdict(row) for row in snapshot.raw_segments],
            "canonical_turns": [asdict(turn) for turn in snapshot.canonical_turns],
        }
    summary = None
    if snapshot.selection.content_scope in {"summary", "combined"} and snapshot.summary:
        summary = asdict(snapshot.summary)
        if not snapshot.selection.include_evidence:
            summary["protocol"] = protocol_without_evidence(summary["protocol"])
    payload = {
        "schema_version": snapshot.schema_version,
        "renderer_version": snapshot.renderer_version,
        "meeting": {
            "meeting_id": snapshot.meeting_id,
            "title": snapshot.meeting_title,
            "language": snapshot.language,
            "duration_seconds": snapshot.duration_seconds,
        },
        "selection": {
            "content_scope": snapshot.selection.content_scope,
            "format": snapshot.selection.format,
            "include_speaker_labels": snapshot.selection.include_speaker_labels,
            "include_timestamps": snapshot.selection.include_timestamps,
            "include_evidence": snapshot.selection.include_evidence,
        },
        "revisions": {
            "processing_result_id": snapshot.processing_result_id,
            "processing_result_version": snapshot.processing_result_version,
            "media_revision_id": snapshot.media_revision_id,
            "outcome_set_id": snapshot.summary.outcome_set_id if snapshot.summary else None,
        },
        "transcript": transcript,
        "summary": summary,
        "provenance": {
            "turn_policy_version": snapshot.turn_policy_version,
            "provider_neutral": True,
        },
    }
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _render_srt(snapshot: ExportSnapshot) -> bytes:
    blocks = []
    for counter, turn in enumerate(snapshot.canonical_turns, start=1):
        text = _subtitle_literal(turn.text)
        if snapshot.selection.include_speaker_labels:
            text = f"{_subtitle_literal(turn.speaker_label)}: {text}"
        blocks.append(f"{counter}\n{_srt_time(turn.start_ms)} --> {_srt_time(turn.end_ms)}\n{text}")
    return ("\n\n".join(blocks) + ("\n" if blocks else "")).encode("utf-8")


def _render_vtt(snapshot: ExportSnapshot) -> bytes:
    blocks = []
    for turn in snapshot.canonical_turns:
        text = _subtitle_literal(turn.text)
        if snapshot.selection.include_speaker_labels:
            text = f"{_subtitle_literal(turn.speaker_label)}: {text}"
        blocks.append(f"{_vtt_time(turn.start_ms)} --> {_vtt_time(turn.end_ms)}\n{text}")
    body = "WEBVTT\n\n" + "\n\n".join(blocks)
    return (body + ("\n" if blocks else "")).encode("utf-8")


def _render_xlsx(snapshot: ExportSnapshot) -> bytes:
    workbook = Workbook(write_only=True)
    transcript = workbook.create_sheet("Transcript")
    summary_sheet = workbook.create_sheet("Summary")
    action_items = workbook.create_sheet("Action Items")
    metadata = workbook.create_sheet("Metadata")
    _configure_sheet(transcript, CSV_COLUMNS)
    if snapshot.selection.content_scope in {"transcript", "combined"}:
        for turn in snapshot.canonical_turns:
            row = _turn_row(snapshot, turn, safe_cells=True)
            _append_sheet_row(transcript, [row[column] for column in CSV_COLUMNS])
    else:
        status_row = {column: "" for column in CSV_COLUMNS}
        status_row["turn_id"] = "status:not_selected"
        status_row["text"] = "not_selected"
        _append_sheet_row(transcript, [status_row[column] for column in CSV_COLUMNS])
    _configure_sheet(summary_sheet, ("section", "topic", "part", "text", "source_refs"))
    _configure_sheet(action_items, ("task", "owner", "deadline", "task_sources", "owner_sources", "deadline_sources"))

    def evidence(refs):
        return json.dumps([ref.model_dump(mode="json") for ref in refs], ensure_ascii=False) if snapshot.selection.include_evidence else "[]"

    if snapshot.summary is None:
        _append_sheet_row(summary_sheet, ("status", "", "", "not_selected", "[]"))
        _append_sheet_row(action_items, ("not_selected", "", "", "[]", "[]", "[]"))
    else:
        protocol = MeetingProtocolView.model_validate(snapshot.summary.protocol)
        language = int(protocol.header.get("output_language") == "en")
        for title, text in protocol_header_rows(protocol):
            _append_sheet_row(summary_sheet, ("header", "", title, text, "[]"))
        selected = [key for key in protocol.header.get("sections", PROTOCOL_SECTIONS) if key in PROTOCOL_SECTIONS]
        for section in selected:
            rows = getattr(protocol, section)
            if section == "topics":
                for topic in rows:
                    for part in ("context", "discussion", "proposals_and_alternatives", "outcome"):
                        for row in getattr(topic, part):
                            _append_sheet_row(summary_sheet, (section, topic.title, part, row.text, evidence(row.source_refs)))
            elif section == "action_items":
                for task in rows:
                    _append_sheet_row(action_items, (
                        task.task, task.owner_text or ("Не назначен", "Not assigned")[language],
                        task.due_date_text or ("Не указан", "Not specified")[language],
                        evidence(task.task_source_refs), evidence(task.owner_source_refs), evidence(task.due_date_source_refs),
                    ))
                if not rows:
                    _append_sheet_row(action_items, (
                        (("Не удалось надёжно установить по доступной расшифровке.", "Cannot reliably establish from the available transcript.")
                         if section in protocol.uncertain_sections else ("Задачи не зафиксированы", "No action items recorded"))[language],
                        ("Не назначен", "Not assigned")[language], ("Не указан", "Not specified")[language], "[]", "[]", "[]",
                    ))
            else:
                for row in rows:
                    _append_sheet_row(summary_sheet, (section, "", "", row.text, evidence(row.source_refs + getattr(row, "acceptance_source_refs", []))))
            if not rows and section != "action_items":
                state = "not_inferable" if section in protocol.uncertain_sections else "not_found"
                _append_sheet_row(summary_sheet, (section, "", state, "", "[]"))
        _append_sheet_row(summary_sheet, ("notes", "", "system", SPEAKER_IDENTITY_NOTE[language], "[]"))
    _configure_sheet(metadata, ("key", "value"))
    metadata_rows = (
        ("schema_version", snapshot.schema_version),
        ("renderer_version", snapshot.renderer_version),
        ("turn_policy_version", snapshot.turn_policy_version),
        ("meeting_id", snapshot.meeting_id),
        ("processing_result_id", snapshot.processing_result_id),
        ("processing_result_version", snapshot.processing_result_version),
        ("media_revision_id", snapshot.media_revision_id or ""),
        ("outcome_set_id", snapshot.summary.outcome_set_id if snapshot.summary else ""),
        (
            "summary_revision_token",
            snapshot.summary.revision_token if snapshot.summary else "",
        ),
        ("summary_source_kind", snapshot.summary.source_kind if snapshot.summary else ""),
        ("summary_generator_kind", snapshot.summary.generator_kind if snapshot.summary else ""),
        (
            "summary_generator_version",
            snapshot.summary.generator_version if snapshot.summary else "",
        ),
        ("summary_content_hash", snapshot.summary.content_hash or "" if snapshot.summary else ""),
        (
            "protocol_schema_version",
            snapshot.summary.protocol["schema_version"]
            if snapshot.summary
            else "",
        ),
        ("content_scope", snapshot.selection.content_scope),
        ("language", snapshot.language or ""),
        ("duration_seconds", snapshot.duration_seconds),
        ("attribution_result_state", snapshot.attribution_result_state),
        (
            "attribution_reason_codes",
            json.dumps(snapshot.attribution_reason_codes, ensure_ascii=False),
        ),
        ("summary_status", snapshot.summary.status if snapshot.summary else "not_selected"),
    )
    for row in metadata_rows:
        _append_sheet_row(metadata, row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _configure_sheet(sheet: object, columns: tuple[str, ...]) -> None:
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(columns))}1"
    widths = {
        "text": 72,
        "source_references": 48,
        "unresolved_references": 48,
        "evidence_turn_ids": 42,
        "source_segment_ids": 42,
        "speaker_label": 24,
        "speaker_key": 28,
        "turn_id": 30,
        "processing_result_id": 38,
        "value": 64,
    }
    for index, column in enumerate(columns, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = widths.get(column, 18)
    cells = []
    for value in columns:
        cell = WriteOnlyCell(sheet, value=value)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cells.append(cell)
    sheet.append(cells)




def _append_sheet_row(sheet: object, values: object) -> None:
    cells = []
    for value in values:
        if isinstance(value, str):
            value = _safe_spreadsheet_text(value)
        cell = WriteOnlyCell(sheet, value=value)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cells.append(cell)
    sheet.append(cells)


def _turn_row(
    snapshot: ExportSnapshot,
    turn: CanonicalExportTurn,
    *,
    safe_cells: bool,
) -> dict[str, object]:
    clean = _safe_spreadsheet_text if safe_cells else lambda value: value
    return {
        "sequence": turn.sequence,
        "turn_id": turn.turn_id,
        "start_ms": turn.start_ms,
        "end_ms": turn.end_ms,
        "start_time": _human_time(turn.start_ms),
        "end_time": _human_time(turn.end_ms),
        "speaker_key": clean(turn.speaker_key),
        "speaker_label": clean(turn.speaker_label),
        "provider_speaker_key": clean(turn.provider_speaker_key),
        "attribution_state": turn.attribution_state,
        "result_state": turn.result_state,
        "source_role": turn.source_role,
        "text": clean(turn.text),
        "overlap": turn.overlap,
        "source_segment_ids": json.dumps(turn.source_segment_ids, ensure_ascii=False),
        "processing_result_id": snapshot.processing_result_id,
        "turn_policy_version": snapshot.turn_policy_version,
    }


def _safe_spreadsheet_text(value: str | None) -> str:
    if value is None:
        return ""
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def _markdown_escape(value: str) -> str:
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = re.sub(r"([\\\[\]*_`~])", r"\\\1", value)
    value = re.sub(r"(?m)^(\s{0,3})([#>+\-])(?=\s)", r"\1\\\2", value)
    value = re.sub(r"(?m)^(\s{0,3}\d+)([.)])(?=\s)", r"\1\\\2", value)
    # Keep source URLs inert without escaping ordinary sentence punctuation.
    value = re.sub(r"(?i)\b(https?|ftp|mailto):", r"\1\\:", value)
    value = re.sub(r"(?i)\bwww\.", r"www\\.", value)
    return re.sub(r"(?<=\w)@(?=\w)", r"\\@", value)


def _subtitle_literal(value: str) -> str:
    return " ".join(value.replace("<", "&lt;").replace(">", "&gt;").split())


def _milliseconds(value: Decimal) -> int:
    return int((value * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _human_time(milliseconds: int) -> str:
    total_seconds, millis = divmod(max(milliseconds, 0), 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


def _srt_time(milliseconds: int) -> str:
    total_seconds, millis = divmod(max(milliseconds, 0), 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _vtt_time(milliseconds: int) -> str:
    return _srt_time(milliseconds).replace(",", ".")


def _safe_title(title: str | None) -> str:
    clean = " ".join((title or "Встреча GRAF").split())
    return clean[:160] or "Встреча GRAF"


def _scope_label(scope: ExportScope) -> str:
    return {"transcript": "расшифровка", "summary": "итоги", "combined": "расшифровка и итоги"}[
        scope
    ]


def _attribution_status_label(snapshot: ExportSnapshot) -> str:
    if snapshot.attribution_result_state == "accepted":
        return "готово"
    confirmed = any(turn.attribution_state == "confirmed" for turn in snapshot.canonical_turns)
    unconfirmed = any(turn.attribution_state != "confirmed" for turn in snapshot.canonical_turns)
    if confirmed and unconfirmed:
        return "частично готово; фрагменты без имени отмечены как «Спикер не определён»"
    if confirmed:
        return "показано по доступным данным; текст сохранён"
    return "без имён; текст сохранён"


def _effective_export_selection(selection: ExportSelection) -> ExportSelection:
    structural = selection.format in {"csv", "xlsx", "json"}
    return replace(
        selection,
        include_speaker_labels=True if structural else selection.include_speaker_labels,
        include_timestamps=(
            True
            if structural or selection.format in {"srt", "vtt"}
            else selection.include_timestamps
        ),
        include_evidence=(
            False if selection.content_scope == "transcript" else selection.include_evidence
        ),
    )


def _stale_selection() -> ProblemDetail:
    return ProblemDetail(
        status=409,
        code="export_revision_stale",
        title="Export revision is stale",
    )
