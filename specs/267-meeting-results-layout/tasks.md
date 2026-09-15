# Tasks: Спокойная страница итогов встречи

**Feature**: 267-meeting-results-layout · **Lane**: high-risk-product
**Input**: spec.md, plan.md, research.md, data-model.md, contracts/presentation.md, quickstart.md.
**Gate**: requirements 16/16, UX 11/11, infra 5/5; отдельный reviewer Cicero, 2026-09-15. Отметки checklist не являются готовностью реализации.

## Phase 1: Setup

- [X] T001 Зафиксировать исходные проверки, границу GRAF Dev и матрицу приёмки в specs/267-meeting-results-layout/quickstart.md; использовать существующие locked pytest/Playwright без новых зависимостей. FR-016.

## Phase 2: Foundation

- [X] T002 Добавить сначала регрессии новой/старой конфигурации и сохранения/replay в apps/server/tests/unit/test_outcome_prompts.py и apps/server/tests/integration/test_meeting_protocol_generation.py; затем уточнить adapter/desired_prompts/sync_prompts в apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py и descriptor/provenance в outcomes/{models.py,prompts.py,ai_service.py}. meeting_minutes.md, схема и глобальная AI_GENERATOR_VERSION неизменны; источник — integrity-checked pinned snapshot. FR-002, FR-005, FR-013, FR-015, SC-005.

## Phase 3: US1 — одна шапка (P1)

Цель: актуальное название, честная подпись описания, локальное время и участники.
Независимая проверка: новые/старые/unknown версии, переименование, граница суток, upload-only, shared scope.

- [X] T003 [US1] Проверить и реализовать единую шапку в apps/server/tests/unit/test_meeting_protocol_rendering.py, apps/server/src/twobrain_rec_server/cabinet/rendering.py и templates/cabinet/pages/{meeting_detail_content.html,shared_meeting_summary_content.html}; передать сохранённую версию из cabinet/web_routes/browser.py и всех HTML callers api/cabinet.py без расширения narrow_summary_projection. FR-001–003, FR-015, SC-001.

## Phase 4: US2 — результат до деталей (P1)

Цель: Главное → решения → задачи → вопросы → темы → примечания.
Независимая проверка: начальная закрытость, одно раскрытие с итогом первым, пустые/длинные данные, экспорт полного документа.

- [X] T004 [US2] Добавить проверки порядка, пустых состояний и сохранения слов в apps/server/tests/unit/test_meeting_protocol_rendering.py; перестроить _render_full_protocol в cabinet/rendering.py и существующие стили cabinet/static/cabinet/cabinet.css. Скрыть цели/input_type и свернуть темы/примечания; не менять cabinet/meeting_protocol.py и полный copy/export. Неизвестные owner/due остаются null и отображаются «Не назначен»/«Не указан». FR-004, FR-006–008, FR-014, SC-002, SC-005.

## Phase 5: US3 — источники и чтение (P2)

Цель: один видимый источник, остальные вертикально, без потери навигации.
Независимая проверка: 0/1/4 источника, mismatch ревизии, текст без аудио, клавиатура/возврат.

- [X] T005 [US3] Проверить compact source controls в apps/server/tests/unit/test_meeting_protocol_rendering.py и tests/browser/protocol-source.test.cjs; изменить общий _render_outcome_item в cabinet/rendering.py и CSS раскрытия в cabinet/static/cabinet/cabinet.css, сохраняя revision/access guard и существующий JavaScript перехода/возврата. Источник продолжает текст перед дополнительными сведениями, новая мысль начинается отдельным абзацем; проверить геометрию в tests/browser/meeting-results.test.cjs. FR-009–011, SC-003.

## Phase 6: Polish and cross-cutting validation

- [X] T006 Проверить настоящий серверный HTML через apps/server/tests/fixtures/meeting_results.py и apps/server/tests/browser/meeting-results.test.cjs: 320/390/768/1024/1440, light/dark, browser/embedded/shared, 200% text, клавиатура, длинные/пустые/legacy данные, контраст ≥4.5, цели ≥24px, строки ≥1.45 и отсутствие горизонтального переполнения. Прочитать синтетический результат и снимки output/playwright/f267; исправить найденные дефекты. FR-011–012, FR-015–016, SC-001–006.
- [X] T007 Выполнить review/converge и focused generation/shared/export регрессии, Ruff и git diff --check; записать проверенное и отдельные commit/Dev/live-prompt/PR границы в specs/267-meeting-results-layout/quickstart.md и changes/unreleased/F267.yaml. FR-013–016, SC-005–006.

## Dependencies and parallel work

T001 → T002 → T003 → T004 → T005 → T006 → T007.
Изменения renderer/CSS последовательны. В US1 проверки header и shared читаются независимо; в US2 export regression можно запускать параллельно CSS-проверкам; в US3 браузерные source и unit regression могут выполняться параллельно. Маркер [P] для связанных реализаций не используется.

## Implementation strategy

Первый проверяемый срез — provenance + US1. Затем US2, US3 и общая матрица. Реализуются все семь задач, не только первый срез. Тесты контрактов добавляются до соответствующего кода. GitHub issues закрываются только после требуемого merged/evidence; локальные [X] не означают релиз.
