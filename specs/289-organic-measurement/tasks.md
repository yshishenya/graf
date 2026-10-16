# Tasks: Измерение поисковых входов

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/public-measurement.md, quickstart.md.

## Phase 1: Требования и gates

- [X] T001 [US1] Получить независимый PASS specs/289-organic-measurement/checklists/security.md, проверить analyze и связать задачи с GitHub в specs/289-organic-measurement/evidence/preflight.md.

## Phase 2: Проверка до реализации

- [X] T002 [US1] Добавить проверку четырёх входов, privacy/kill switch/legal/DB отказов в apps/server/tests/contract/test_public_organic_measurement.py и обновить границу Zoom в apps/server/tests/contract/test_public_zoom_recording_guide.py; обновить инвентарь в apps/server/tests/unit/test_product_analytics_anonymous_aggregate.py; подтвердить падение на прежней реализации.

## Phase 3: US1 — Обезличенные входы

- [X] T003 [US1] Подключить четыре поверхности только уровня 1 в apps/server/src/twobrain_rec_server/public/content.py и apps/server/src/twobrain_rec_server/product_analytics/anonymous_aggregate.py; режим anonymous_only и два обработчика в apps/server/src/twobrain_rec_server/public/web.py по FR-001–005,008; общие бюджеты БД и изоляция счётчиков от auth-транзакции в public/web.py, public/downloads.py и cabinet/web_routes/auth.py.

## Phase 4: US2 — План и проверка

- [X] T004 [US2] Сохранить актуальный аудит docs/growth/audit-2026-10-16.md, план docs/growth/organic-growth-plan.md и read-only SQL docs/growth/baseline-2026-10-16.sql по FR-006.
- [X] T005 [US1] Выполнить quickstart, независимый review/converge, записать результат в specs/289-organic-measurement/evidence/validation.md и добавить changes/unreleased/F289.yaml; публикацию/рост не заявлять.

## Dependencies

T001 → T002 → T003 → T004 → T005. Перед T002: independent checklist PASS, analyze critical/high 0, issue sync. Персональные события и runtime F273 не входят. Issues открыты до приёмки/merge; commit/release — после явного разрешения по проверенному результату.

## GitHub mapping

- T001: https://github.com/yshishenya/graf/issues/7601
- T002: https://github.com/yshishenya/graf/issues/7602
- T003: https://github.com/yshishenya/graf/issues/7603
- T004: https://github.com/yshishenya/graf/issues/7604
- T005: https://github.com/yshishenya/graf/issues/7605

Umbrella: https://github.com/yshishenya/graf/issues/7593. Issues остаются открытыми до приёмки.
