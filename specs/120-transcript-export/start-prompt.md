# Стартовый промпт для Feature 120

Продолжи работу над GRAF в чистой ветке `120-transcript-export`.

Задача: спроектировать и затем реализовать полноценный экспорт транскрипта и
саммари. Сначала прочитай `AGENTS.md`, `docs/agent-guidance/README.md`,
`docs/agent-guidance/spec-kit-flow.md`, constitution, PRD и текущий статус.
После этого внимательно изучи `specs/113-transcript-speaker-turns`,
`specs/118-interactive-playback-timeline`, `specs/017-access-sharing-downloads`
и реальный код transcript assembly, summary/outcomes, cabinet egress, API
routes, templates, schemas и tests. Не начинай реализацию до завершения полного
Spec Kit цикла: clarify → plan/research → checklist → tasks → analyze.

Feature 120 уже содержит `spec.md`. Используй его как источник требований и
не создавай дубликат. Если обнаружишь противоречие между spec и кодом, сначала
зафиксируй evidence и уточни spec, а не добавляй локальный обход.

Поддерживаемые пользовательские форматы:

- TXT — чистый человекочитаемый текст;
- MD — аккуратно структурированный и сверстанный Markdown для заметок и
  knowledge-base;
- CSV — одна каноническая реплика на строку;
- XLSX — удобная книга с листами Transcript, Summary, Action Items и Metadata;
- JSON — versioned provider-neutral snapshot с raw source fidelity,
  canonical turns, summary revisions и provenance;
- SRT — один subtitle cue на каноническую реплику.

PDF и DOCX в этой feature не реализуются. Не добавляй ZIP, batch export,
интеграции, публичные ссылки, аудиоэкспорт, перевод или повторную
транскрибацию без отдельного согласования.

Обязательная семантика:

- raw segments остаются источником истины;
- canonical speaker turns строятся сервером и привязаны к выбранной revision;
- UI display groups не являются источником CSV/XLSX/JSON/SRT;
- короткие технические фрагменты можно группировать только в человекочитаемых
  форматах;
- длинные паузы остаются временными разрывами и никогда не превращаются в
  строки `Пауза`, `[pause]` или другой придуманный текст;
- нельзя группировать только по видимому label: учитывай stable speaker key,
  attribution state, source role, result/revision, overlap и unknown;
- `UNKNOWN` нельзя автоматически превращать в подтвержденный `SPEAKER_00`;
- summary экспортируется из текущей сохраненной summary revision и не запускает
  генерацию заново;
- transcript, summary и combined export имеют отдельные policy, readiness,
  audit и deletion truth;
- export должен оставаться рабочим при замене облачного STT-провайдера.

Проведи актуальное исследование лучших практик и первичных материалов Krisp,
Otter, Descript, Fireflies, Fathom и Zoom. Сравни не только форматы, но и
экспортные настройки, preview, speaker/timestamp options, summary separation,
permissions, partial states, lifecycle, caption behavior и UX IA. Используй
публичные источники и запиши ссылки и выводы в `research.md`; не копируй
конкурентные UI, тексты, цвета, иконки или приватные скриншоты.

В плане отдельно опиши:

1. единый export snapshot и revision pinning;
2. хранение on-demand и short-lived generated artifacts;
3. форматные serializers и escaping для русского текста, CSV, Markdown и SRT;
4. summary model и ссылки на transcript turns;
5. API/egress/policy/audit/deletion contract;
6. UI/UX/IA meeting detail, Files panel, export dialog, preview, progress,
   failure and accessibility states;
7. quickstart и fixture matrix: 0.9/1.1/3/51/138 секунд gaps, A→B→A,
   unknown, source boundary, overlap, partial, missing summary, >1 hour,
   access denied и deletion in progress.

Применяй Ponytail: переиспользуй существующий egress/policy/audit и
canonical-turn helpers, не добавляй новую таблицу или зависимость без
доказанной необходимости, но не упрощай security, accessibility, lifecycle и
revision truth. Перед implementation добейся чистого `$speckit-analyze`.
