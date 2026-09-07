import json
from copy import deepcopy
from dataclasses import replace
from io import BytesIO

from openpyxl import load_workbook

from tests.unit.test_meeting_protocol import protocol_fixture, validate
from tests.unit.test_transcript_exports import _snapshot
from twobrain_rec_server.cabinet.access import narrow_summary_projection
from twobrain_rec_server.cabinet.exports import render_content_export
from twobrain_rec_server.cabinet.meeting_protocol import protocol_lines, without_protocol_evidence
from twobrain_rec_server.cabinet.rendering import _render_full_protocol


def test_full_protocol_rendering_has_sections_task_table_and_canonical_links():
    document = validate(protocol_fixture())["protocol"]
    text = "\n".join(protocol_lines(document, markdown=True, include_evidence=True,
                                    meeting_url="https://graf.example/cabinet/meetings/synthetic"))
    assert "## Ключевые обсуждения" in text
    assert "### Макет" in text
    assert "| Задача | Ответственный | Срок |" in text
    assert "наверное, завтра" in text
    assert "[00:12](https://graf.example/cabinet/meetings/synthetic#graf-source=" in text
    assert "макет\\," not in text
    html = _render_full_protocol(document, source_destination_available=True)
    assert '<table' in html and '<th scope="col">Ответственный</th>' in html
    assert 'data-seek-seconds="12.25"' in html
    assert 'data-source-segment="00000000-0000-0000-0000-000000000002"' in html
    assert "Риски не найдены" not in html


def test_protocol_escapes_unsafe_output_and_does_not_mutate_evidence():
    document = validate(protocol_fixture())["protocol"]
    document["title"] = '<script>alert(1)</script> ![image](https://evil.example)'
    original = deepcopy(document)
    html = _render_full_protocol(document, source_destination_available=False)
    assert "<script>" not in html and "<img" not in html
    assert "data-seek-seconds" not in html
    text = "\n".join(protocol_lines(document, markdown=True, include_evidence=False, meeting_url=""))
    assert "![image]" not in text and "#graf-source" not in text
    stripped = without_protocol_evidence(document)
    assert "source_refs" not in str(stripped) and "quote" not in str(stripped)
    assert document == original


def test_empty_states_and_unknown_task_fields():
    document = protocol_fixture()
    document["action_items"] = []
    text = "\n".join(protocol_lines(validate(document)["protocol"], markdown=True,
                                    include_evidence=False, meeting_url=""))
    assert "Принятые решения в транскрипте не зафиксированы." in text
    assert "| Задачи не зафиксированы | Не назначен | Не указан |" in text
    assert "Открытые вопросы не зафиксированы." in text


def test_saved_protocol_exports_preserve_words_and_hide_evidence(export_fixture):
    document = validate(protocol_fixture())["protocol"]
    document["title"] = "=SUM(1,2)"
    for format in ("md", "txt", "json", "xlsx"):
        snapshot = _snapshot(export_fixture, scope="summary", format=format)
        snapshot = replace(snapshot, summary=replace(snapshot.summary, protocol=document),
                           selection=replace(snapshot.selection, include_evidence=False))
        exported = render_content_export(snapshot).body
        if format == "json":
            parsed = json.loads(exported)
            assert "source_refs" not in json.dumps(parsed["summary"]["protocol"])
            assert parsed["summary"]["protocol"]["title"] == document["title"]
        elif format == "xlsx":
            sheet = load_workbook(BytesIO(exported))["Протокол"]
            assert all(cell.data_type != "f" for row in sheet for cell in row)
            values = list(sheet.values)
            assert any(row[1] == "Принятые решения в транскрипте не зафиксированы." for row in values)
            assert any(row[1] == "Сделать макет" and row[2] == "Участник 1" for row in values)
            assert all(not row[4] for row in values[1:])
        else:
            text = exported.decode()
            assert "Сделать макет" in text and "наверное, завтра" in text
            assert "Источник сохраненной ревизии" not in text and "graf-source" not in text
    assert document["action_items"][0]["source_refs"]
    snapshot = _snapshot(export_fixture, scope="summary", format="xlsx")
    snapshot = replace(snapshot, summary=replace(snapshot.summary, protocol=document))
    sheet = load_workbook(BytesIO(render_content_export(snapshot).body))["Протокол"]
    links = [cell.hyperlink for row in sheet for cell in row if cell.hyperlink]
    assert links and all("#graf-source=00000000-0000-0000-0000-000000000002" in link.target for link in links)


def test_summary_only_share_has_complete_protocol_without_transcript_refs():
    from datetime import UTC, datetime
    document = validate(protocol_fixture())["protocol"]
    shared = narrow_summary_projection(meeting_label="Встреча", occurred_at=datetime.now(UTC),
                                       duration_seconds=30, summary_sections=[], protocol=document)
    assert shared["protocol"]["topics"][0]["title"] == "Макет"
    assert "source_refs" not in json.dumps(shared["protocol"]) and "quote" not in json.dumps(shared["protocol"])
    html = _render_full_protocol(shared["protocol"], source_destination_available=False)
    assert "Сделать макет" in html and "data-source-segment" not in html
