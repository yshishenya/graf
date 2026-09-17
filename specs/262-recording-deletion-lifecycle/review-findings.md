# Независимая проверка требований F262

Дата: 2026-09-09. Проверяющий: `server_delete_analysis` — отдельный агент, не автор продуктовой реализации. Область: требования и архитектура до реализации, reviewer-owned checklists. Продуктовый код не изменялся.

**Результат: CRITICAL 0 · HIGH 0.** Проверка требований пройдена. Это не проверка готовой реализации и не замена analyze, issue sync, convergence или release gates.

## Проверенные источники

- `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/lifecycle.md`, `scenarios.md`, `quickstart.md`, `tasks.md` этого каталога.
- `.specify/memory/constitution.md`, раздел IV Deletion Truth; `docs/agent-guidance/product-gates.md`, Deletion Truth; `docs/prd-voice-layer-final.md`, MVP deletion scope; `docs/agent-guidance/spec-kit-flow.md`, Checklist/Analyze/Implement.
- Существующие серверные границы: `ingest/meetings.py` (идемпотентность по origin), `ingest/store.py` (сохраняемый identity), `ingest/parts.py` и `ingest/finalize.py` (проверки deletion epoch после I/O), `deletion/service.py` (commit tombstone до внешней очистки), `deletion/local_purge.py` и `db/models/deletion.py` (task identity, terminal ACK и обязательные FK), `api/cabinet.py` (различие content/lifecycle доступа), `ingest/desktop_sync.py` (origin lookup и отдельный deletion state).

## Основания отметок

| Критерий | Основание в требованиях и проекте |
|---|---|
| CHK001 | `data-model.md`, Идентичность: ExecutionScope отдельно от target creator; local_unbound отдельно от legacy_unknown. S46/S47/S49 покрывают server-only, local без входа и manager-delete. |
| CHK002 | FR-002/004–008; независимые оси intent/accepted/purge; разрешение неоднозначного ответа через receipt/report без вывода по 404. |
| CHK003 | Origin cancellation без фиктивной Meeting; общий transaction-level origin lock для всех create callers; существующие epoch/fence сохраняются. S10–S14 требуют оба порядка гонки и запрет поздней публикации. |
| CHK004 | FR-007/013/014; durable-before-effect; безопасные пути и проверка пакета; поздний verified ACK с историей; accepted не снимается при файловой ошибке. |
| CHK005 | FR-010–012/017; immutable bulk target, максимум 100, отдельные результаты, переход фокуса и пустое состояние. Ошибки остаются доступны через индекс удалений. |
| CHK006 | Origin и meeting_id lookup разделены по полномочиям; unavailable закрывает контент без физического purge; native сохраняет offline intent, web не обещает долговечную очередь вкладки. |
| CHK007 | Управляемая AVFoundation session отзывается; внешний экспорт не отзывается; retained Generation Call/Langfuse/Temporal явно исключены из удаления. |
| CHK008 | Миграция ownership, unknown schema/recovery gate, сохранение tombstones, недопустимость передачи нового store несовместимому старому бинарнику. |
| CHK009 | SC-002/003/006 и quickstart отдельно задают измерение реакции, проверки после сети, объём файлов и исключения недоступной среды. Числа названы целями, а не результатами. |
| CHK010 | FR-016, S15/S16: capture/saving нельзя скрыто остановить/удалить; ручной Stop сохраняется. |

Спецификация описывает ценность и пользовательские результаты; технические механизмы вынесены в модель и контракт. FR-001–022 проверяемы через S01–S51. Положительные/отрицательные/конкурентные сценарии и пределы очистки сформулированы. Противоречий обязательным нормам конституции в выбранном объёме не обнаружено. Неизвестные runtime-результаты явно оставлены будущей приёмке.

## Повторная проверка ранее найденных пробелов

1. Server-only pending operations теперь принадлежат документу очереди и переживают удаление аудиопакета. Нет фиктивного audio item и двух конкурирующих состояний intent.
2. `origin_cancellation` имеет отдельный receipt и локальный результат текущего Mac. Существующие обязательные FK LocalPurgeTask не обходятся вымышленными Meeting/DeletionRequest.
3. Исполнитель не приравнивается к создателю; manager-delete сохраняет исходный execution scope и повторную проверку прав.
4. Server-only/чужие встречи согласовываются по meeting_id с lifecycle/access resolver, а не через owner-only origin lookup.
5. Доверенная новая local_unbound запись отличается от legacy_unknown; текущий login сам по себе не доказывает принадлежность старого пакета.

Общая блокировка origin и одна новая таблица обоснованы реальной гонкой cancel-before-create. Существующий `request_meeting_deletion` фиксирует tombstone до обращения к хранилищу; этот commit является допустимой границей освобождения origin lock. Реализация должна сохранить именно эту последовательность, а не удерживать lock до окончания purge.

## Обязательные ограничения дальнейшего исполнения

- Все T002–T021 остаются открытыми до своих доказательств; этот review подтверждает только проверку требований в T001. Решение о полном закрытии T001 принадлежит общему analyze после его завершения.
- Server create/cancel проверяется настоящими конкурирующими PostgreSQL транзакциями, включая старые API callers; одно последовательное SQLite-тестирование не доказывает сериализацию.
- Проверка origin-cancellation не должна создавать content/revision/calendar/job до guard. Отклонённые и поздние ответы не снимают сохранённый барьер.
- Обычные web-вкладки, native bridge, no-JS и несовместимый bridge требуют отдельных проверок; выполнение native delete не должно одновременно запускать JS fetch.
- Смена scope, atomic-save failure, новая регистрация устройства, потерянные ответы и миграция проверяются до закрытия связанных задач. Совпадение состояния UI не заменяет проверку файлов/очереди/server identity.
- T019 содержит всю матрицу S01–S51, T020 — convergence, T021 — SHA-bound проверки и installed-app gates. Непроверенные, заблокированные и прерванные результаты не считаются PASS.

На этом этапе тесты приложения, файловая очистка, новые API, миграция, production и полный CI не запускались. Независимая приёмка готового продукта ещё не выполнена.
