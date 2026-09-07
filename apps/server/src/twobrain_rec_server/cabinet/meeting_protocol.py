"""Presentation of the saved protocol; never infer or rewrite its content."""

import re
from html import escape

TASK_HEADING = "Задачи (Action Items)"
EMPTY = {
    "Принятые решения": "Принятые решения в транскрипте не зафиксированы.",
    "Открытые вопросы и следующие шаги": "Открытые вопросы не зафиксированы.",
}


def protocol_blocks(document):
    for heading, text in (
        ("Название встречи/проекта", document["title"]),
        ("Дата и время", document["date_and_time"] or "Не указано"),
        ("Тип входных данных", document["input_type"]),
        ("Тип встречи", document["meeting_type"]),
        ("Участники", ", ".join(document["participants"]) or "Не определено"),
    ):
        yield 1, heading, [{"text": text, "source_refs": []}]
    yield 2, "Executive Summary (Ключевые итоги)", document["executive_summary"]
    yield 2, "Цели встречи", document["objectives"]
    yield 2, "Ключевые обсуждения", []
    for topic in document["topics"]:
        yield 3, topic["title"], []
        for key, heading in (("context", "Контекст"), ("discussion", "Обсуждение"),
                             ("proposals", "Предложения"), ("outcome", "Итог")):
            yield 4, heading, topic[key]
    yield 2, "Принятые решения", document["decisions"]
    yield 2, TASK_HEADING, document["action_items"]
    yield 2, "Открытые вопросы и следующие шаги", document["open_questions"] + document["next_steps"]
    yield 2, "Примечания", document["notes"]


def protocol_markdown_text(text):
    # Escape only Markdown/HTML syntax, not ordinary commas, dots or colons.
    text = escape(text, quote=False)
    text = re.sub(r"([\\`*_{}\[\]|])", r"\\\1", text)
    return re.sub(r"(?m)^(\s*)([#>+\-]|\d+[.)])(?=\s)", r"\1\\\2", text)


def protocol_timecode(seconds):
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def protocol_lines(document, *, markdown, include_evidence, meeting_url):
    def literal(text):
        return protocol_markdown_text(text) if markdown else text

    def refs(row):
        if not include_evidence:
            return ""
        values = []
        for ref in row.get("source_refs", []):
            time = protocol_timecode(ref["start_seconds"])
            url = f"{meeting_url}#graf-source={ref['transcript_segment_id']}"
            values.append(f"[{time}]({url})" if markdown else f"{time} ({url})")
        return (" " + " ".join(values)) if values else ""

    for level, heading, rows in protocol_blocks(document):
        yield ("#" * level + " " if markdown else "") + literal(heading)
        yield ""
        if heading == TASK_HEADING and level == 2:
            yield "| Задача | Ответственный | Срок |" if markdown else "Задача | Ответственный | Срок"
            if markdown:
                yield "| --- | --- | --- |"
            if not rows:
                yield "| Задачи не зафиксированы | Не назначен | Не указан |"
            for row in rows:
                cells = [literal(row["task"]) + refs(row), literal(row["owner_text"] or "Не назначен"),
                         literal(row["due_date_text"] or "Не указан")]
                if markdown:
                    cells = [cell.replace("\n", "<br>") for cell in cells]
                yield "| " + " | ".join(cells) + " |"
        else:
            for row in rows:
                yield literal(row["text"]) + refs(row)
                yield ""
            if not rows and heading in EMPTY and level == 2:
                yield EMPTY[heading]
        yield ""


def without_protocol_evidence(value):
    if isinstance(value, dict):
        return {key: without_protocol_evidence(child) for key, child in value.items()
                if key not in {"source_refs", "quote"}}
    if isinstance(value, list):
        return [without_protocol_evidence(child) for child in value]
    return value
