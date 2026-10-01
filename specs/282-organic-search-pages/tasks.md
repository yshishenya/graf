# Tasks: 282 — Поисковые страницы ГРАФ

**Lane**: significant-feature. Implementation scope — подготовка и локальная проверка; merge/release и постпубликационный рост остаются отдельными воротами.

## Phase 1: Setup

- [X] T001 Зафиксировать исходную техническую проверку и план измерения FR-008/SC-003–005 в specs/282-organic-search-pages/evidence/baseline.md и evidence/measurement-plan.md; unknown не заменять нулём.

## Phase 2: Foundational

- [X] T002 Добавить целевую проверку HTTP/SEO/canonical/404 и сохранения исходного лендинга FR-003–005/FR-007 в apps/server/tests/contract/test_public_search_pages.py и specs/282-organic-search-pages/scripts/check_landing_preserved.py (точное сравнение только для текущей приёмки); первоначально подтвердить отсутствие новых маршрутов.

## Phase 3: US1 — Самостоятельные страницы

- [X] T003 [US1] Добавить три фиксированных маршрута FR-001/002/004–007 в apps/server/src/twobrain_rec_server/public/web.py, apps/server/src/twobrain_rec_server/public/templates/public/search_guide.html и apps/server/src/twobrain_rec_server/public/static/public/search-guide.css; сохранить shared response, исключить новые analytics scripts, новые внешние ресурсы и обещание доступной Windows.

## Phase 4: US2 — Главная и discovery

- [X] T004 [US2] Добавить ровно три ссылки в footer apps/server/src/twobrain_rec_server/public/templates/public/landing.html и три URL в sitemap apps/server/src/twobrain_rec_server/public/web.py по FR-003/004; первый экран, metadata и общие CSS/JS не изменять.

## Phase 5: US3 — Проверка и готовность

- [X] T005 [US3] Выполнить quickstart и независимую проверку, записать результаты/ограничения/converge в specs/282-organic-search-pages/evidence/validation.md, создать changes/unreleased/F282.yaml; подтвердить FR-001–008/SC-001–003, оставить реальные SC-004/005 неизмеренными до публикации и отчётов.

## Dependencies and gates

T001 → T002 → T003 → T004 → T005. Reviewer-owned checklist PASS, analyze critical/high 0 и taskstoissues обязательны до T002/T003. Задачи отмечаются после локальной проверки; issues остаются открыты до merge и требуемого evidence. Публикация не включена в executable tasks этой подготовки.

## GitHub mapping

- T001 — Issue #7394: https://github.com/yshishenya/graf/issues/7394
- T002 — Issue #7395: https://github.com/yshishenya/graf/issues/7395
- T003 — Issue #7396: https://github.com/yshishenya/graf/issues/7396
- T004 — Issue #7397: https://github.com/yshishenya/graf/issues/7397
- T005 — Issue #7398: https://github.com/yshishenya/graf/issues/7398

Umbrella / feature reservation: Issue #7392 — https://github.com/yshishenya/graf/issues/7392 (allocator-created T000; remains open, not a task owner).
