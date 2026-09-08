# Tasks: Чистая реализация F239

Input: [spec.md](spec.md), [plan.md](plan.md), [quickstart.md](quickstart.md).
Lane: high-risk-feature. PR без merge/deploy. Новая схема заменяет прежний
план #6787; задачи старой схемы не считаются выполненными. Номера T071+
продолжают историю фичи, не переопределяют старые T001–T070.

## Phase 1: Setup

- [X] T071 Согласовать новую проверку требований и связи GitHub в specs/239-full-meeting-minutes/requirements-review.md и tasks.md.

## Phase 2: Foundation

- [X] T072 Добавить проверки контракта и хранения в apps/server/tests/unit/test_meeting_protocol.py и apps/server/tests/integration/test_meeting_protocol_generation.py до изменения генерации.

## Phase 3: US1 — полный документ

Independent test: один документ со всеми разделами, точными ссылками и
неизменными текстами; отсутствие решений/сроков не создаёт выдуманные поля.

- [X] T073 [US1] Определить документ и проверку refs в apps/server/src/twobrain_rec_server/outcomes/models.py и prompts.py, одно поле в db/models/outcomes.py и миграцию после текущего head в db/migrations/versions/.
- [X] T074 [US1] Заменить исходящий промпт исходным draft-meeting-minutes с адаптером JSON/refs в apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py без смысловых исправлений GRAF.
- [X] T075 [US1] Проверить и реализовать полный вывод/таблицу/таймкоды/выгрузки в apps/server/src/twobrain_rec_server/cabinet/rendering.py, view_models.py, exports.py и api/schemas.py; добавить apps/server/tests/unit/test_meeting_protocol_rendering.py.

## Phase 4: US2 — надёжный результат

Independent test: HTTP/Temporal публикация, повтор без inference, запрет
публикации после потери актуальности при сохранении ответа.

- [X] T076 [US2] Сохранить один вызов и полный протокол в apps/server/src/twobrain_rec_server/outcomes/ai_service.py; покрыть expiry/cancel/deletion/source/access races и независимость observability в apps/server/tests/integration/test_meeting_protocol_generation.py.

## Phase 5: US3 — настройки модели

Independent test: две модели через настройки Langfuse, неизменная попытка,
dev не читает production fallback, авторизация шлюза и retries сохранены.

- [X] T077 [US3] Проверить и убрать ограничения модели/route-binding/root из обычной генерации в apps/server/src/twobrain_rec_server/outcomes/generator.py, prompts.py, ai_service.py и config.py; настройки модели только Langfuse, обновить связанные unit tests. Выбор текущей метки в observability/langfuse.py не использует stale SDK cache; проверенный резервный snapshot сохранён.

## Phase 6: Проверка и PR

- [X] T078 Провести GRAF HTTP/Temporal прогоны трёх реальных встреч и семи controls, полностью прочитать результаты и источники, проверить вторую модель и записать безопасные агрегаты в specs/239-full-meeting-minutes/validation.md.
- [X] T079 Выполнить converge и проверку diff/сложности/приватности, подготовить changes/unreleased/F239.yaml и specs/239-full-meeting-minutes/quickstart.md с точными релизными предпосылками, устранить обязательные замечания.
- [X] T080 После проверки и разрешения коммита создать PR, дождаться governance-fast на точном SHA, проверить mergeability и metadata; записать ссылки в specs/239-full-meeting-minutes/validation.md, не merge/deploy.

## Dependencies / Strategy

T071 → T072 → T073 → T074/T075 → T076 → T077 → T078 → T079 → T080.
Тесты каждой истории пишутся до её кода. T074 и тесты вывода T075 могут
разрабатываться независимо после модели, но нет необходимости делить
реализацию на новые сервисы. Минимальный MVP — US1; PR требует все истории.

## Issue ownership

T071–T080 имеют явного открытого владельца: существующий umbrella
https://github.com/yshishenya/graf/issues/6503, поле `Spec Kit task IDs`.
Проверен полный список F239 (open и closed); новых дублей не создано.
T001–T070 относятся к прежнему плану #6787, не отмечаются выполненными.
Их окончательное согласование с заменяющим PR входит в T079–T080.

Текущий checkpoint и подтверждение T072/T073/T074/T076:
[validation.md](validation.md). T071–T080 оформлены в PR #6789; итоговая проверка
каждого нового SHA обязательна и фиксируется в GitHub checks и комментарии PR.
Umbrella остаётся открытым до отдельного релиза и согласования прежней истории.
Старые T001–T070/#6787 остаются историей прежней схемы, их технические gates
не заменяют приёмку чистого перезапуска. В новом PR используется Refs #6503;
закрытие всей исторической группы не заявляется.


## Phase 7: Convergence — общий выпуск 2026-09-08

- [X] T081 Исправить замечания ревью #6789 перед общим выпуском: чтение большого ModelCall, закреплённые ссылки источников, объявление нового формата XLSX, достоверные названия/часовой пояс и сохранение validation_error при повторе. Область: outcomes/ai_service.py, outcomes/prompt_optimization.py, cabinet/exports.py, cabinet/meeting_protocol.py, cabinet/queries.py, cabinet/web_routes/browser.py, cabinet/rendering.py и существующие unit/integration проверки. Владелец — существующий #6503, FR-006/008/011/012 и SC-003/004. Подтверждение — validation.md, отдельный release PR.

- [X] T082 Устранить замечания общего релизного PR #6790: связывать переходы к источникам с показанной редакцией и сегментом; сохранять summary_failed при ошибке протокола, поставщика, публикации и повторе после сбоя финализации. Владелец — существующий #6503; проверка — test_meeting_protocol_generation.py и test_meeting_protocol_rendering.py.

- [X] T083 Согласовать OpenAPI и строгие проверки публичной проекции с полем protocol; сохранить отсутствие source_refs/quote в доступе только к итогам. Владелец — #6503. Целевые серверные проверки: 111 PASS; полный CI нового кандидата остаётся отдельным релизным gate.
