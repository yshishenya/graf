from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from html import escape
from uuid import uuid4

import pytest
from openpyxl import load_workbook

from tests.fixtures.cabinet_exports import SyntheticExportFixture
from tests.fixtures.meeting_protocol import protocol_outcome, protocol_result
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.cabinet.exports import (
    CSV_COLUMNS,
    SCHEMA_VERSION,
    TURN_POLICY_VERSION,
    CanonicalExportTurn,
    ExportSelection,
    ExportSnapshot,
    SummaryExportRevision,
    canonical_export_turns,
    canonical_raw_segments,
    human_display_groups,
    render_content_export,
)
from twobrain_rec_server.db.models import DiarizationSegment, TranscriptSegment
from twobrain_rec_server.domain.speaker_turns import stable_speaker_key


def _snapshot(
    fixture: SyntheticExportFixture,
    *,
    format: str,
    scope: str = "transcript",
    include_speaker_labels: bool = True,
    include_timestamps: bool = True,
) -> ExportSnapshot:
    raw = canonical_raw_segments(list(fixture.transcript_rows))
    turns = canonical_export_turns(
        list(fixture.transcript_rows),
        diarization_rows=list(fixture.diarization_rows),
        processing_result_id=fixture.result_id,
        speaker_names={stable_speaker_key(fixture.result_id, "speaker-a"): "Анна"},
    )
    summary = None
    outcome_set_id = None
    if scope in {"summary", "combined"}:
        outcome_set_id = uuid4()
        document = protocol_outcome().protocol_json
        ref = document["executive_summary"][0]["source_refs"][0]
        ref.update(transcript_segment_id=raw[0].segment_id, start_seconds=12.5, end_seconds=18.0)
        document["executive_summary"][0]["text"] = "Сохранённое саммари: аргументы, варианты и ограничения."
        document["action_items"] = [{
            "task": "@подготовить отчёт", "owner_text": "=Иван", "due_date_text": "2026-07-30",
            "task_source_refs": [ref], "owner_source_refs": [ref], "due_date_source_refs": [ref],
        }]
        summary = SummaryExportRevision(
            outcome_set_id=str(outcome_set_id), processing_result_id=str(fixture.result_id),
            revision_token=f"{outcome_set_id}:hash:protocol", status="available",
            source_kind="litellm", generator_kind="litellm", generator_version="meeting-protocol-v2",
            content_hash="fixture-content-hash", protocol=document,
        )
    return ExportSnapshot(
        selection=ExportSelection(
            content_scope=scope,  # type: ignore[arg-type]
            format=format,  # type: ignore[arg-type]
            processing_result_id=fixture.result_id,
            outcome_set_id=outcome_set_id,
            include_speaker_labels=include_speaker_labels,
            include_timestamps=include_timestamps,
        ),
        meeting_id="12000000-0000-0000-0000-000000000120",
        meeting_title="Синтетическая встреча <без HTML>",
        language="ru",
        duration_seconds=3702,
        processing_result_id=str(fixture.result_id),
        processing_result_version=3,
        media_revision_id=str(uuid4()),
        raw_segments=raw,
        canonical_turns=turns,
        summary=summary,
    )


def test_canonical_turns_preserve_boundaries_unknown_and_long_gaps(export_fixture) -> None:
    snapshot = _snapshot(export_fixture, format="json")

    assert len(snapshot.raw_segments) == 7
    assert len(snapshot.canonical_turns) == 7
    assert snapshot.raw_segments[3].attribution_state == "uncertain"
    assert snapshot.canonical_turns[3].speaker_label == "Спикер не определён"
    assert snapshot.canonical_turns[0].speaker_label == "Анна"
    assert snapshot.canonical_turns[2].speaker_label == "Анна"
    assert snapshot.canonical_turns[0].turn_id != snapshot.canonical_turns[2].turn_id
    assert all("pause" not in turn.text.lower() for turn in snapshot.canonical_turns)


def test_txt_and_markdown_keep_russian_timestamps_and_escape_markup(export_fixture) -> None:
    txt = render_content_export(_snapshot(export_fixture, format="txt")).body.decode()
    markdown = render_content_export(_snapshot(export_fixture, format="md")).body.decode()

    assert "Привет, GRAF." in txt
    assert "[01:01:40.100]" in txt
    assert "Пауза" not in txt
    assert "&lt;без HTML&gt;" in markdown
    assert "Синтетическая встреча <без HTML>" not in markdown


def test_degraded_state_is_visible_in_human_and_structured_exports(export_fixture) -> None:
    base = _snapshot(export_fixture, format="txt")
    degraded = replace(
        base,
        attribution_result_state="degraded_provider_result",
        attribution_reason_codes=("unknown_tiny_identity",),
        raw_segments=tuple(
            replace(row, result_state="degraded_provider_result") for row in base.raw_segments
        ),
        canonical_turns=tuple(
            replace(turn, result_state="degraded_provider_result")
            for turn in base.canonical_turns
        ),
    )

    text = render_content_export(degraded).body.decode()
    workbook = load_workbook(
        io.BytesIO(render_content_export(replace(degraded, selection=replace(degraded.selection, format="xlsx"))).body),
        read_only=False,
        data_only=False,
    )
    metadata = {row[0].value: row[1].value for row in workbook["Metadata"].iter_rows(min_row=2)}

    assert (
        "Разделение по спикерам: частично готово; фрагменты без имени отмечены как "
        "«Спикер не определён»"
    ) in text
    assert all(row.result_state == "degraded_provider_result" for row in degraded.raw_segments)
    assert metadata["attribution_result_state"] == "degraded_provider_result"
    assert json.loads(metadata["attribution_reason_codes"]) == ["unknown_tiny_identity"]


def test_markdown_neutralizes_line_markers_links_and_raw_html(export_fixture) -> None:
    snapshot = _snapshot(export_fixture, format="md")
    malicious = replace(
        snapshot.canonical_turns[0],
        text="# Заголовок\n- список\n1. пункт\n[ссылка](https://example.test)\n<script>x</script>",
    )
    body = render_content_export(
        replace(snapshot, canonical_turns=(malicious, *snapshot.canonical_turns[1:]))
    ).body.decode()

    assert "\\# Заголовок" in body
    assert "\\- список" in body
    assert "1\\. пункт" in body
    assert "\\[ссылка\\](https\\://example.test)" in body
    assert "&lt;script&gt;x&lt;/script&gt;" in body
    assert "\n# Заголовок" not in body
    assert "\n- список" not in body


@pytest.mark.parametrize("scope", ["summary", "combined"])
def test_protocol_markdown_keeps_tilde_fences_inside_literal_text(export_fixture, scope):
    snapshot = _snapshot(export_fixture, format="md", scope=scope)
    document = snapshot.summary.protocol
    document["executive_summary"][0]["text"] = "Первый итог.\n\n~~~python\nВторой итог."

    body = render_content_export(snapshot).body.decode()

    assert not re.search(r"(?m)^ {0,3}~{3,}", body)
    assert "Второй итог." in body
    assert "\n## Принятые решения\n" in body


def test_csv_has_stable_columns_crlf_bom_and_inert_formula_cells(export_fixture) -> None:
    body = render_content_export(_snapshot(export_fixture, format="csv")).body
    assert body.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in body
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"), newline="")))

    assert tuple(rows[0]) == CSV_COLUMNS
    assert len(rows) == 7
    assert rows[1]["text"].startswith("'=")
    assert json.loads(rows[0]["source_segment_ids"])
    assert rows[3]["attribution_state"] == "unknown"
    assert rows[0]["provider_speaker_key"] == "speaker-a"
    assert rows[0]["result_state"] == "accepted"


def test_json_is_versioned_deterministic_raw_fidelity_without_provider_secrets(
    export_fixture,
) -> None:
    snapshot = _snapshot(export_fixture, format="json")
    first = render_content_export(snapshot).body
    second = render_content_export(snapshot).body
    payload = json.loads(first)

    assert first == second
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["provenance"]["turn_policy_version"] == TURN_POLICY_VERSION
    assert len(payload["transcript"]["raw_segments"]) == 7
    assert payload["transcript"]["raw_segments"][3]["text"] == "Неизвестная атрибуция."
    assert "mediascribe_job_id" not in first.decode()
    assert "storage_object_key" not in first.decode()
    assert "api_key" not in first.decode()


def test_provider_speaker_labels_do_not_change_graf_canonical_semantics(export_fixture) -> None:
    adapter_rows = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=row.processing_result_id,
            meeting_id=row.meeting_id,
            workspace_id=row.workspace_id,
            sequence=row.sequence,
            start_seconds=row.start_seconds,
            end_seconds=row.end_seconds,
            text=row.text,
            speaker_label={"speaker-a": "remote-7", "speaker-b": "remote-2", "UNKNOWN": "UNKNOWN"}[
                row.speaker_label
            ],
            source_role=row.source_role,
        )
        for row in export_fixture.diarization_rows
    ]
    original_turns = canonical_export_turns(
        list(export_fixture.transcript_rows),
        diarization_rows=list(export_fixture.diarization_rows),
        processing_result_id=export_fixture.result_id,
    )
    adapter_turns = canonical_export_turns(
        list(export_fixture.transcript_rows),
        diarization_rows=adapter_rows,
        processing_result_id=export_fixture.result_id,
    )

    assert [
        turn.canonical_label if hasattr(turn, "canonical_label") else turn.speaker_label
        for turn in original_turns
    ] == [turn.speaker_label for turn in adapter_turns]
    assert [turn.provider_speaker_key for turn in original_turns] != [
        turn.provider_speaker_key for turn in adapter_turns
    ]
    assert [turn.text for turn in original_turns] == [turn.text for turn in adapter_turns]


def test_srt_uses_one_turn_per_cue_preserves_hour_and_has_no_pause(export_fixture) -> None:
    body = render_content_export(_snapshot(export_fixture, format="srt")).body.decode()

    assert body.count(" --> ") == 7
    assert "01:01:40,100 --> 01:01:41,100" in body
    assert "Спикер не определён: Неизвестная атрибуция." in body
    assert "Пауза" not in body


def test_xlsx_has_fixed_safe_sheets_columns_and_literal_cells(export_fixture) -> None:
    body = render_content_export(_snapshot(export_fixture, format="xlsx", scope="combined")).body
    workbook = load_workbook(io.BytesIO(body), read_only=False, data_only=False)

    assert workbook.sheetnames == ["Transcript", "Summary", "Action Items", "Metadata"]
    transcript = workbook["Transcript"]
    assert tuple(cell.value for cell in transcript[1]) == CSV_COLUMNS
    assert transcript.freeze_panes == "A2"
    assert transcript.column_dimensions["M"].width == 72
    assert transcript["M2"].alignment.wrap_text is True
    assert transcript["M3"].value.startswith("'=")
    summary = workbook["Summary"]
    assert tuple(cell.value for cell in summary[1]) == ("section", "topic", "part", "text", "source_refs")
    assert "topics" in [cell.value for cell in summary["A"][1:]]
    assert "executive_summary" in [cell.value for cell in summary["A"][1:]]
    action = workbook["Action Items"]
    assert action["A2"].value.startswith("'@")
    assert action["B2"].value.startswith("'=")
    metadata = {row[0].value: row[1].value for row in workbook["Metadata"].iter_rows(min_row=2)}
    assert metadata["summary_revision_token"]
    assert metadata["summary_source_kind"] == "litellm"
    assert metadata["summary_generator_version"] == "meeting-protocol-v2"
    assert metadata["protocol_schema_version"] == "graf-meeting-protocol-v2"
    assert not any(
        isinstance(cell.value, str) and cell.value.startswith("=")
        for sheet in workbook.worksheets
        for row in sheet.iter_rows()
        for cell in row
    )


def test_xlsx_marks_unselected_sheets_and_honors_evidence_option(export_fixture) -> None:
    snapshot = _snapshot(export_fixture, format="xlsx", scope="summary")
    snapshot = replace(
        snapshot,
        selection=replace(snapshot.selection, include_evidence=False),
    )
    workbook = load_workbook(
        io.BytesIO(render_content_export(snapshot).body),
        read_only=False,
        data_only=False,
    )

    transcript = workbook["Transcript"]
    assert transcript["B2"].value == "status:not_selected"
    summary = workbook["Summary"]
    assert all(cell.value == "[]" for cell in summary["E"][1:])
    assert all(cell.value == "[]" for row in workbook["Action Items"].iter_rows(min_row=2, min_col=4) for cell in row)


@pytest.mark.parametrize("scope", ["summary", "combined"])
@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("uncertain", [False, True])
def test_xlsx_preserves_unknown_versus_absent_tasks(export_fixture, scope, language, uncertain):
    snapshot = _snapshot(export_fixture, format="xlsx", scope=scope)
    snapshot = replace(snapshot, selection=replace(snapshot.selection, include_evidence=False))
    document = snapshot.summary.protocol
    document["header"]["output_language"] = language
    document["action_items"] = []
    document["uncertain_sections"] = ["action_items"] if uncertain else []

    workbook = load_workbook(io.BytesIO(render_content_export(snapshot).body))
    row = tuple(workbook["Action Items"].values)[1]
    expected = (
        ("Не удалось надёжно установить по доступной расшифровке.", "Cannot reliably establish from the available transcript.")
        if uncertain else ("Задачи не зафиксированы", "No action items recorded")
    )[language == "en"]
    assert row[0] == expected
    assert row[3:] == ("[]", "[]", "[]")
    markdown = render_content_export(replace(snapshot, selection=replace(snapshot.selection, format="md"))).body.decode()
    assert expected in markdown


def test_xlsx_neutralizes_formula_prefixes_in_summary_metadata(export_fixture) -> None:
    snapshot = _snapshot(export_fixture, format="xlsx", scope="summary")
    assert snapshot.summary is not None
    snapshot = replace(
        snapshot,
        summary=replace(snapshot.summary, generator_kind="=UNTRUSTED_METADATA"),
    )
    workbook = load_workbook(
        io.BytesIO(render_content_export(snapshot).body),
        read_only=False,
        data_only=False,
    )
    metadata = {row[0].value: row[1].value for row in workbook["Metadata"].iter_rows(min_row=2)}

    assert metadata["summary_generator_kind"] == "'=UNTRUSTED_METADATA"
    assert not any(cell.data_type == "f" for row in workbook["Metadata"] for cell in row)


def test_summary_only_and_combined_do_not_regenerate_or_invent_fields(export_fixture) -> None:
    summary_json = json.loads(
        render_content_export(_snapshot(export_fixture, format="json", scope="summary")).body
    )
    combined = render_content_export(
        _snapshot(export_fixture, format="txt", scope="combined")
    ).body.decode()

    assert summary_json["transcript"] is None
    assert summary_json["summary"]["generator_version"] == "meeting-protocol-v2"
    assert summary_json["summary"]["protocol"]["action_items"][0]["owner_text"] == "=Иван"
    assert "Транскрипт" in combined
    assert "Ключевые итоги" in combined
    assert "Сохранённое саммари:" in combined


def test_protocol_markdown_is_a_readable_document_with_inline_timestamps(export_fixture):
    snapshot = _snapshot(export_fixture, format="md", scope="summary")
    body = render_content_export(snapshot).body.decode()
    assert "## Ключевые итоги" in body and "## Ключевые обсуждения" in body
    assert "Сохранённое саммари: аргументы, варианты и ограничения." in body
    assert "[00:12]" in body
    assert "| Задача | Ответственный | Срок |" in body
    assert "Генератор:" not in body and "Статус сохраненной ревизии" not in body
    assert "\\," not in body and "\\." not in body and "\\:" not in body


@pytest.mark.parametrize("format", ["json", "txt", "md"])
def test_protocol_preserves_llm_words_through_validation_render_and_export(export_fixture, format):
    from twobrain_rec_server.api.schemas import MeetingProtocolView
    from twobrain_rec_server.cabinet.rendering import render_meeting_protocol
    from twobrain_rec_server.outcomes.ai_service import _enrich_protocol
    from twobrain_rec_server.outcomes.models import (
        OutcomeTranscriptSegment,
        protocol_without_evidence,
    )
    from twobrain_rec_server.outcomes.prompts import validate_protocol_result

    snapshot = _snapshot(export_fixture, format=format, scope="summary")
    source = OutcomeTranscriptSegment(
        segment_id=uuid4(), sequence=0, start_seconds=Decimal("12.5"), end_seconds=Decimal("18"),
        speaker_label="Участник 1", source_role="incoming_system",
        text="Наверное, завтра — если получится. Не утвердили: обсуждаем.",
    )
    draft = deepcopy(protocol_result([source]))
    statement = draft["executive_summary"][0]
    ref = statement["source_refs"][0]
    # Repetition and awkward wording belong to the LLM, not a server editor.
    draft["executive_summary"].append(deepcopy(statement))
    for section in ("objectives", "open_questions", "next_steps", "risks_and_constraints", "notes"):
        draft[section] = [{"text": f"{section}: возможно, но не подтверждено.", "source_refs": [ref]}]
    topic = draft["topics"][0]
    topic["title"] = "Пилот «А» & «Б»: стоимость < 2,5 млн ₽?"
    for part in ("context", "proposals_and_alternatives", "outcome"):
        topic[part] = [{"text": f"{part}: это лишь вариант, не обязательство.", "source_refs": [ref]}]
    draft["decisions"] = [{
        "text": "Решили не запускать второй этап без отдельного согласования.",
        "source_refs": [ref], "acceptance_source_refs": [ref],
    }]
    draft["action_items"] = [{
        "task": "Уточнить предел бюджета.\nНе заказывать второй этап.",
        "owner_text": "Анна-Мария", "due_date_text": "после ответа, не раньше пятницы",
        "task_source_refs": [ref], "owner_source_refs": [ref], "due_date_source_refs": [ref],
    }, {
        "task": "Запросить условия пилота, не подписывать договор.",
        "owner_text": None, "due_date_text": None,
        "task_source_refs": [ref], "owner_source_refs": [], "due_date_source_refs": [],
    }]
    original = deepcopy(draft)
    validated = validate_protocol_result(draft, segments=[source])
    assert validated == original
    enriched = _enrich_protocol(validated, snapshot.summary.protocol["header"], [source])
    view = MeetingProtocolView.model_validate(enriched)
    for document in (enriched, view.model_dump(mode="json")):
        assert protocol_without_evidence({key: document[key] for key in draft}) == protocol_without_evidence(original)

    def text_fields(value):
        if isinstance(value, list):
            for child in value:
                yield from text_fields(child)
        elif isinstance(value, dict):
            for key, child in value.items():
                if key in {"text", "title", "task", "owner_text", "due_date_text"} and child is not None:
                    yield child
                elif not key.endswith("source_refs"):
                    yield from text_fields(child)

    page = render_meeting_protocol(view, source_segment_ids={str(source.segment_id)})
    for text, count in Counter(text_fields(original)).items():
        assert page.count(escape(text)) == count
    without_controls = re.sub(r'<button type="button" class="notes-source-link"[^>]*>[^<]*</button>', "", page)
    assert f'<li>{escape(original["decisions"][0]["text"])} </li>' in without_controls
    action = original["action_items"][0]
    assert (
        "<tr>" + "".join(f"<td>{escape(action[field])} </td>" for field in ("task", "owner_text", "due_date_text")) + "</tr>"
    ) in without_controls
    assert 'data-seek-seconds="12.5"' in page
    assert "Не назначен" in page and "Не указан" in page

    exported = replace(snapshot, summary=replace(snapshot.summary, protocol=enriched))
    body = render_content_export(exported).body.decode()
    if format == "json":
        assert json.loads(body)["summary"]["protocol"] == enriched
    else:
        for text, count in Counter(text_fields(original)).items():
            # Only table line breaks and safe markup encoding may differ.
            expected = " ".join(text.splitlines())
            if format == "md":
                expected = escape(expected, quote=False).replace("_", "\\_")
            assert body.count(expected) == count
        assert "Не назначен" in body and "Не указан" in body
        assert "[00:12]" in body
    assert draft == original


def test_protocol_json_evidence_off_removes_every_nested_source_without_mutation(export_fixture):
    snapshot = _snapshot(export_fixture, format="json", scope="summary")
    original = json.dumps(snapshot.summary.protocol, sort_keys=True)
    hidden = replace(snapshot, selection=replace(snapshot.selection, include_evidence=False))
    payload = json.loads(render_content_export(hidden).body)
    document = json.dumps(payload["summary"]["protocol"])
    assert "source_refs" not in document and "quote" not in document
    assert "source_result_id" not in document and "transcript_segment_id" not in document
    assert "start_seconds" not in document
    assert json.dumps(snapshot.summary.protocol, sort_keys=True) == original


def test_protocol_export_links_use_only_authorized_server_origin(export_fixture):
    snapshot = _snapshot(export_fixture, format="md", scope="summary")
    linked = replace(snapshot, source_base_url="https://graf.example", source_workspace_id=str(uuid4()))
    body = render_content_export(linked).body.decode()
    assert "[00:12](https://graf.example/cabinet/meetings/" in body
    hidden = replace(linked, selection=replace(linked.selection, include_evidence=False))
    hidden_body = render_content_export(hidden).body.decode()
    assert "/sources/" not in hidden_body and "[00:12]" not in hidden_body
    assert "?workspace_id=" in render_content_export(linked).body.decode("utf-8")
    unsafe = replace(linked, source_base_url="javascript:alert(1)")
    assert "javascript:" not in render_content_export(unsafe).body.decode()


def test_presentation_options_do_not_change_machine_formats(export_fixture) -> None:
    base = _snapshot(export_fixture, format="json")
    toggled = replace(
        base,
        selection=replace(
            base.selection,
            include_speaker_labels=False,
            include_timestamps=False,
        ),
    )

    base_payload = json.loads(render_content_export(base).body)
    toggled_payload = json.loads(render_content_export(toggled).body)
    assert (
        base_payload["transcript"]["canonical_turns"]
        == toggled_payload["transcript"]["canonical_turns"]
    )
    assert toggled_payload["selection"] == {
        "content_scope": "transcript",
        "format": "json",
        "include_evidence": False,
        "include_speaker_labels": True,
        "include_timestamps": True,
    }


def test_human_groups_may_join_short_fragments_but_keep_canonical_children() -> None:
    first = CanonicalExportTurn(
        turn_id="turn-a",
        sequence=0,
        start_ms=0,
        end_ms=1000,
        text="Короткий фрагмент.",
        speaker_key="speaker-a",
        speaker_label="Анна",
        attribution_state="confirmed",
        source_role="local_microphone",
        source_segment_ids=("raw-a",),
        overlap=False,
    )
    second = replace(
        first,
        turn_id="turn-b",
        sequence=1,
        start_ms=4000,
        end_ms=5000,
        text="Второй фрагмент.",
        source_segment_ids=("raw-b",),
    )
    unknown = replace(
        second,
        turn_id="turn-unknown",
        sequence=2,
        start_ms=5000,
        end_ms=5500,
        speaker_key="unknown:raw-c",
        speaker_label="UNKNOWN",
        attribution_state="unknown",
        source_segment_ids=("raw-c",),
    )

    groups = human_display_groups((first, second, unknown))

    assert [[turn.turn_id for turn in group] for group in groups] == [
        ["turn-a", "turn-b"],
        ["turn-unknown"],
    ]


def test_vtt_uses_canonical_turn_boundaries(export_fixture) -> None:
    body = render_content_export(_snapshot(export_fixture, format="vtt")).body.decode()

    assert body.startswith("WEBVTT\n\n")
    assert body.count(" --> ") == 7
    assert "01:01:40.100 --> 01:01:41.100" in body
    assert "Спикер не определён: Неизвестная атрибуция." in body


@pytest.mark.parametrize("format", ["srt", "vtt"])
def test_subtitle_export_fails_closed_for_non_positive_rounded_timing(
    export_fixture,
    format: str,
) -> None:
    snapshot = _snapshot(export_fixture, format=format)
    first, *remaining = snapshot.canonical_turns
    invalid = replace(
        snapshot,
        canonical_turns=(replace(first, end_ms=first.start_ms), *remaining),
    )

    with pytest.raises(ProblemDetail) as exc_info:
        render_content_export(invalid)

    assert exc_info.value.status == 409
    assert exc_info.value.code == "subtitle_timing_unavailable"


def test_zero_duration_raw_evidence_is_marked_invalid(export_fixture) -> None:
    source = export_fixture.transcript_rows[0]
    row = TranscriptSegment(
        id=source.id,
        processing_result_id=source.processing_result_id,
        workspace_id=source.workspace_id,
        meeting_id=source.meeting_id,
        sequence=source.sequence,
        start_seconds=source.start_seconds,
        end_seconds=Decimal(export_fixture.transcript_rows[0].start_seconds),
        text=source.text,
        source_role=source.source_role,
        source_role_original=source.source_role_original,
    )

    segment = canonical_raw_segments([row])[0]

    assert segment.timing_state == "invalid"
    assert segment.omission_reason == "invalid_timing"
