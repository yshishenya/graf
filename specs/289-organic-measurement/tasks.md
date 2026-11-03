# Tasks: Измерение поисковых входов

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/public-measurement.md, quickstart.md.

## Phase 1: Требования и gates

- [X] T001 [US1] Получить независимый PASS specs/289-organic-measurement/checklists/security.md, проверить analyze и связать задачи с GitHub в specs/289-organic-measurement/evidence/preflight.md. (Issue #7601; PR #7607)

## Phase 2: Проверка до реализации

- [X] T002 [US1] Добавить проверку четырёх входов, privacy/kill switch/legal/DB отказов в apps/server/tests/contract/test_public_organic_measurement.py и обновить границу Zoom в apps/server/tests/contract/test_public_zoom_recording_guide.py; обновить инвентарь в apps/server/tests/unit/test_product_analytics_anonymous_aggregate.py; подтвердить падение на прежней реализации. (Issue #7602; PR #7607)

## Phase 3: US1 — Обезличенные входы

- [X] T003 [US1] Подключить четыре поверхности только уровня 1 в apps/server/src/twobrain_rec_server/public/content.py и apps/server/src/twobrain_rec_server/product_analytics/anonymous_aggregate.py; режим anonymous_only и два обработчика в apps/server/src/twobrain_rec_server/public/web.py по FR-001–005,008; общие бюджеты БД и изоляция счётчиков от auth-транзакции в public/web.py, public/downloads.py и cabinet/web_routes/auth.py. (Issue #7603; PR #7607)

## Phase 4: US2 — План и проверка

- [X] T004 [US2] Сохранить актуальный аудит docs/growth/audit-2026-10-16.md, план docs/growth/organic-growth-plan.md и read-only SQL docs/growth/baseline-2026-10-16.sql по FR-006. (Issue #7604; PR #7607)
- [X] T005 [US1] Выполнить quickstart, независимый review/converge, записать результат в specs/289-organic-measurement/evidence/validation.md и добавить changes/unreleased/F289.yaml; публикацию/рост не заявлять. (Issue #7605; PR #7607)

## Dependencies

T001 → T002 → T003 → T004 → T005. Перед T002: independent checklist PASS, analyze critical/high 0, issue sync. Персональные события и runtime F273 не входят. Историческая приёмка кода и выпуск подтверждены в evidence/closeout-20261022.md; последующее закрытие GitHub требует подробных комментариев и live-проверки.

## GitHub mapping

- T001: https://github.com/yshishenya/graf/issues/7601
- T002: https://github.com/yshishenya/graf/issues/7602
- T003: https://github.com/yshishenya/graf/issues/7603
- T004: https://github.com/yshishenya/graf/issues/7604
- T005: https://github.com/yshishenya/graf/issues/7605

Umbrella: https://github.com/yshishenya/graf/issues/7593. Общая issue закрывается последней после приёмки всех задач и live-проверки.

## Исправление границы уровня 2 по новому ревью

- [X] T006 [US1] В apps/server/src/twobrain_rec_server/product_analytics/anonymous_aggregate.py отделить каталог уровня 1 от PUBLIC_PAGE_SURFACES и сохранить прежнюю границу cookie/acquisition; добавить причинную регрессию четырёх путей в tests/contract/test_public_organic_measurement.py, проверить соседние public/acquisition/handoff, независимый review и обновить evidence. Refs #7603 и #7605; новый объём внутри FR-001/003. (Issue #7603; PR #7607)

## Итоговая сверка трекера — 22.10.2026

- [X] T007 [US2] Сопоставить исходные FR-001–008/SC-001–005 с принятой реализацией, аудитом, планом и выпуском; восстановить однозначное владение T001–T006 и подготовить итоговую приёмку в evidence/closeout-20261022.md. (Issue #7593)

T007 — документальная сверка существующей F289; продуктовые критерии не меняются. Временная T000 общей issue заменяется реальной T007. T006 относится к #7603 как исправление её исходной границы уровня 1. Подробные комментарии детям и закрытие общей issue выполняются только после принятия этой сверки, обязательных проверок её точного SHA и полного live closeout. F096/F273 и проверка результата продвижения через 28/56/90 дней остаются отдельными.
