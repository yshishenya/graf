# Draft Meeting Minutes

## Workflow

1. If input is raw audio/video, run or request transcription first.
2. Read all material before writing.
3. Classify input: `Запись`, `Транскрипт`, `Заметки`, `Смешанный материал`, or `Не определено`.
4. Classify meeting and adapt ToV/detail: work=business/detailed; official=audit-ready; customer=customer-centered; HR=tactful/confidential; brainstorm=options/parking lot; retro/incident=blameless timeline/learnings; interview=themes/evidence; personal=calm/simple; high-risk=facts only/no advice; mixed=neutral/uncertain.
5. Name speakers only with unambiguous evidence; otherwise use `Участник 1`, `Участник 2`.
6. Cluster themes while preserving substantive facts: arguments, constraints, objections, alternatives, risks, dependencies, numbers, dates, decisions, tasks.
7. Decisions require explicit approval/agreement/final selection/commitment. Never convert proposals into decisions.
8. Action items need task, owner, deadline; never guess owner/deadline; split compound tasks when needed.
9. Appendix: cleaned transcript only if requested/useful for archive or research; for formal, HR, high-risk, or private meetings prefer short evidence excerpts/timestamps.
10. Output only the final protocol unless the user asks for analysis.

## Rules

- Default detailed: compress wording, not meaning.
- Remove filler, repetition, small talk, ASR artifacts, and timestamps unless meaningful.
- For long transcripts, silently scan chronologically before clustering so commitments are not dropped.
- For unclear fields use `Не указано`, `Не назначен`, `Не определено`, or neutral speaker labels.
- Do not use current system date as meeting date unless the user says the meeting happened today.
- In `Примечания`, mention noise, gaps, unclear speech, overlap, inconsistent labels.
- Cleaned transcript: preserve meaning/order, standardize labels, remove filler/ASR noise, keep uncertainty markers, do not polish into prose.

## Output Contract

Use Russian Markdown headings unless asked otherwise. Header fields: `Название встречи/проекта`, `Дата и время`, `Тип входных данных`, `Тип встречи`, `Участники`.

Sections: `Executive Summary (Ключевые итоги)`, `Цели встречи`, `Ключевые обсуждения`, `Принятые решения`, `Задачи (Action Items)`, `Открытые вопросы и следующие шаги`, `Примечания`. For each theme include `Контекст`, `Обсуждение`, `Предложения`, `Итог`. Action item columns: `Задача | Ответственный | Срок`.

Optional appendices after `Примечания`: `Evidence Appendix (выдержки и таймкоды)` for disputed/high-stakes decisions/actions; `Очищенный транскрипт` only if requested or useful for searchable archive.

Empty states: no decisions -> `Принятые решения в транскрипте не зафиксированы.`; no tasks -> `| Задачи не зафиксированы | Не назначен | Не указан |`; no open questions -> `Открытые вопросы не зафиксированы.`

Always include in notes: `Имена спикеров указаны только в случаях их однозначной идентификации в транскрипте.`

## Final Checks

Verify evidence-based classification, matching tone/detail, separated decisions/proposals/options, specific action owners/deadlines, and preserved objections/constraints/risks/dependencies/alternatives.
