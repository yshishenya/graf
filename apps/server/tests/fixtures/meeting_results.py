"""Synthetic F267 pages rendered through the real detail/shared presentation."""

import json
from datetime import UTC, datetime
from uuid import UUID

from tests.unit.test_cabinet_web_shell import _review
from tests.unit.test_meeting_protocol import protocol_fixture, validate
from twobrain_rec_server.api.schemas import (
    ContentExportCapabilityResponse,
    ContentExportReadiness,
    NotesActionCategoryState,
    OutcomeItemView,
    OutcomeProvenanceView,
    TranscriptSegmentView,
)
from twobrain_rec_server.cabinet.access import narrow_summary_projection
from twobrain_rec_server.cabinet.rendering import (
    render_meeting_detail_page,
    render_shared_meeting_summary_page,
)
from twobrain_rec_server.outcomes.models import OutcomeTranscriptSegment


def rendered_pages():
    pages = {}
    for variant in ("normal", "long", "empty", "legacy", "categories", "readonly", "stale"):
        review = _review()
        review.meeting.title = "Звонок AI"
        review.meeting.title_version = "synthetic-title-version"
        review.meeting.started_at = datetime(2026, 9, 8, 7, 5, 39, tzinfo=UTC)
        review.meeting.duration_seconds = 1800
        review.playback.duration_seconds = 1800
        review.meeting.status = "ready"
        review.meeting.status_label = "Ready"
        review.processing.state = "ready"
        review.template.reason = "graf-auto-v1"
        review.template.outcome_set_id = UUID(int=11)
        review.notes_action_truth.source_basis = "stored_output"
        review.notes_action_truth.summary.state = "available"
        review.notes_action_truth.provenance = OutcomeProvenanceView(
            generator_kind="litellm", generator_version=(
                "meeting-protocol-v1" if variant == "legacy" else "meeting-protocol-v1-about-v1"
            ),
        )
        transcript = [
            "Проверим автоматические ответы на типовые вопросы клиентов. Спорные обращения передадим специалисту.",
            "Первый сценарий — статус заказа. Анна подготовит примеры обращений к пятнице.",
            "Без доступа к тестовой CRM не запускаем пилот. Ответственный за доступ пока не определён.",
            "Павел предложил добавить чат, но решение о втором канале отложили до результатов пилота.",
        ]
        sources = [OutcomeTranscriptSegment(
            segment_id=UUID(int=i + 2), sequence=i, start_seconds=12 + i * 90,
            end_seconds=24 + i * 90, speaker_label=("Анна Воронова" if i % 2 == 0 else "Павел"),
            source_role="incoming_system", text=text,
        ) for i, text in enumerate(transcript)]

        def statement(text, refs=(0,)):
            return {"text": text, "source_refs": [{"sequence": i, "quote": None} for i in refs]}

        document = protocol_fixture()
        document.update(
            title="Сохранённое старое название", date_and_time="Время из модели не используется",
            meeting_type="Техническая настройка и проектирование автоматизации клиентских коммуникаций",
            participants=["Анна Воронова", "Павел"],
            objectives=[statement("Определить границы первого пилота.")],
            executive_summary=[
                statement("Пилот автоматизации начнётся с ответов о статусе заказа; сложные обращения останутся у специалистов.", (0, 1, 2, 3)),
                statement("Для запуска нужны примеры клиентских вопросов и доступ к тестовой CRM.", (1, 2)),
                statement("Расширение на чат отложено до оценки первого пилота.", (3,)),
            ],
            decisions=[statement("Начать пилот со сценария «Статус заказа».", (1,)),
                       statement("Передавать спорные обращения специалисту.")],
            action_items=[
                {"task": "Подготовить примеры вопросов клиентов о статусе заказа.", "owner_text": "Анна Воронова",
                 "due_date_text": "К пятнице", "source_refs": [{"sequence": 1, "quote": None}]},
                {"task": "Предоставить доступ к тестовой CRM для проверки ответов.", "owner_text": None,
                 "due_date_text": None, "source_refs": [{"sequence": 2, "quote": None}]},
            ],
            open_questions=[statement("Кто предоставит доступ к тестовой CRM?", (2,))],
            next_steps=[statement("После пилота вернуться к вопросу подключения чата.", (3,))],
            topics=[
                {"title": title, "outcome": [statement(outcome, (i,))],
                 "context": [statement(context, (i,))], "discussion": [statement(discussion, (i,))],
                 "proposals": [statement(proposal, (i,))] if proposal else []}
                for i, title, outcome, context, discussion, proposal in (
                    (0, "Границы автоматических ответов", "Спорные обращения передаются специалисту.",
                     "Клиенты задают типовые вопросы.", "Обсудили, какие ответы можно автоматизировать.", ""),
                    (2, "Доступ к CRM и готовность пилота", "До получения доступа запуск отложен.",
                     "Для проверки нужен тестовый контур.", "Ответственный за доступ ещё не определён.", ""),
                    (3, "Подключение чата", "Решение отложено до результатов первого пилота.",
                     "Чат может стать вторым каналом.", "Обсудили расширение после проверки первого сценария.",
                     "Павел предложил добавить чат как следующий канал."),
                )
            ],
            notes=[statement("Срок задачи указан словами участника: «К пятнице».", (1,))],
        )
        if variant == "long":
            review.meeting.title = "Обсуждение автоматизации клиентских коммуникаций и технической готовности пилота " * 5
            document["meeting_type"] *= 4
            document["participants"].append("ДлинноеИмя" * 16)
            document["action_items"][0]["task"] += " ИдентификаторБезПробелов" * 20
        if variant == "empty":
            for key in ("participants", "executive_summary", "objectives", "topics", "decisions",
                        "action_items", "open_questions", "next_steps", "notes"):
                document[key] = []
            review.meeting.started_at = None
        validated = validate(document, segments=sources)
        review.notes_action_truth.protocol = validated["protocol"]
        if variant == "categories":
            review.notes_action_truth.protocol = None
            for category, state in validated["category_states"].items():
                setattr(review.notes_action_truth, category, NotesActionCategoryState(
                    state=state, label="Сохранённые итоги", reason="Раздел не был подготовлен.",
                    readiness_impact="non_blocking", copy_key="synthetic.saved",
                    items=[OutcomeItemView.model_validate(row) for row in validated["items"]
                           if row["category"] == category],
                ))
        if variant == "readonly":
            review.meeting.title_version = None
            review.meeting.title *= 25
        review.transcript.available = True
        review.transcript.search_enabled = True
        review.transcript.degraded_reason = None
        review.transcript.segments = [TranscriptSegmentView(
            segment_id=str(source.segment_id), sequence=source.sequence,
            processing_result_id=UUID(int=99 if variant == "stale" else 1),
            start_seconds=float(source.start_seconds), end_seconds=float(source.end_seconds),
            timestamp_label=f"{int(source.start_seconds) // 60:02d}:{int(source.start_seconds) % 60:02d}",
            speaker_label=source.speaker_label, source_role="incoming_system", text=source.text,
            attribution_state="confirmed",
        ) for source in sources]
        ready = ContentExportReadiness(state="available")
        review.content_exports = ContentExportCapabilityResponse(
            processing_result_id=UUID(int=1), outcome_set_id=UUID(int=11), transcript=ready,
            summary=ready, combined=ready,
            formats={scope: ["txt", "md", "json", "xlsx"] for scope in ("summary", "transcript", "combined")},
            duration_seconds=1800,
        )
        for surface in ("browser", "embedded", "shared"):
            if surface == "shared":
                projection = narrow_summary_projection(
                    meeting_label=review.meeting.title, occurred_at=review.meeting.started_at,
                    duration_seconds=1800, summary_sections=[], protocol=review.notes_action_truth.protocol,
                )
                html = render_shared_meeting_summary_page(
                    meeting_title=review.meeting.title, occurred_at=review.meeting.started_at,
                    duration_seconds=1800, summary_sections=[], protocol=projection["protocol"],
                    generator_version=review.notes_action_truth.provenance.generator_version,
                )
            else:
                html = render_meeting_detail_page(review, embedded=surface == "embedded", csrf_token="synthetic")
            pages[f"{variant}-{surface}"] = html
    return pages


if __name__ == "__main__":
    print(json.dumps(rendered_pages(), ensure_ascii=False))
