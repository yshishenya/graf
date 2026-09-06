# T036/T043 runtime and evidence classification

Дата проверки: 2026-08-25. Проверка выполнена в worktree Feature 183 на
ветке `codex/183-trusted-outcome-lifecycle`. Внешние записи, приватные
материалы, credentials и screenshots в evidence не использовались.

## Результат

Runtime больше не читает `Meeting.current_outcome_set_id` для выбора или
публикации результата. Все обычные read/export/share paths используют
`MeetingSummarySlot` и точную пару `template_key` + `current_outcome_set_id`.
Отсутствующий slot/default возвращает bounded no-result/egress-denied state;
runtime не создаёт slot на GET, share или export.

Операторская проверка вынесена в
  `apps/server/src/twobrain_rec_server/cli/summary_slots.py`. Она читает только
metadata columns, не выбирает содержимое items и не изменяет БД.
`apps/server/scripts/reconcile_initial_outcomes.py` оставлен только как
совместимый вход в этот command; прежняя генерация baseline и поиск по
meeting-global pointer удалены. `prove_meeting_outcome_live.py` выполняет
только health + slot-backed summary read.

## Закрытый allowlist для `current_outcome_set_id`

| Класс | Пути/назначение | Решение |
|---|---|---|
| Модельный контракт | `db/models/meeting.py`, `api/schemas.py` | Историческое поле/DTO оставлены для schema и deletion compatibility; не участвуют в runtime selection. |
| Slot contract | `db/models/outcomes.py`, `outcomes/ai_service.py`, `outcomes/service.py`, `outcomes/dispatch.py`, `workflows/temporal_client.py`, `api/cabinet.py`, `cabinet/egress.py`, `cabinet/exports.py`, `cabinet/rendering.py` | Разрешены только slot-scoped current/revision identity, CAS, workflow binding и response projection. Meeting-global read fallback отсутствует. |
| Historical migrations | `db/migrations/versions/0031_*`, `0032_*`, `0076_meeting_summary_slots.py` | Исторические schema/backfill/verifier SQL; не runtime. |
| Deletion compatibility | `deletion/service.py` | При начале удаления очищается старый meeting-global pointer; slot/deletion fence остаются отдельной truth boundary. |
| Operator reconciliation | `cli/summary_slots.py`, wrapper `scripts/reconcile_initial_outcomes.py`, live proof field projection | Metadata-only inspection и exact slot-backed read; нет генерации, accept или content output. |
| Historical acceptance surface | Deprecated routes в `api/cabinet.py`, fail-closed `resolve_summary_candidate` в `outcomes/ai_service.py`, `accepted_by_user_id` model/migration fields | Оставлены только для compatibility/schema fixtures; decision helper завершается `summary_candidate_deprecated` до DB access, preview DTO/builder удалены, user accept/reject не меняет state и не публикует результат. |

Новых runtime owners вне этого списка нет.

## `MeetingOutcomeSet`/newest-row inventory

Проверены все 51 файл, найденный по `MeetingOutcomeSet|meeting_outcome_sets`.
Результат классификации:

- current result reads: `cabinet/queries.py` теперь вызывает
  `_current_outcome_set`, который делегирует slot-backed
  `cabinet/egress.py`; `created_at`/`generated_at` ordering используется только
  для processing-result/attempt history и не выбирает outcome revision;
- publication/CAS: `outcomes/ai_service.py` проверяет target slot и expected
  current identity; meeting-global pointer не изменяется;
- export/share/browser: exact pinned slot/revision либо honest denial;
- migration/model/deletion/fixtures: исторические или явно названные
  compatibility cases из migration and slot tests;
- operational scripts: baseline reconciler больше не содержит SQL-поиск
  `m.current_outcome_set_id is null`; live proof не вызывает candidate list,
  preview, accept или reject.

Легитимные `latest_processing_result`/`_latest_result` и media-revision queries
выбирают источник транскрипции, а не summary outcome; это не newest-outcome
fallback.

## Exact scan receipt (aggregate only)

Команды из `quickstart.md` выполнены после T036:

| Scan | Aggregate |
|---|---:|
| `current_outcome_set_id` assignments across `apps/server` | 146 historical/fixture/slot-contract matches; no unclassified runtime selection writer |
| `current_outcome_set_id` references across `apps/server` | 339, all classified above or in named tests/fixtures |
| summary candidate accept surfaces | 19, all deprecated route/failed-closed helper/tests or unrelated accepted-domain vocabulary; no active user publication route |
| `accepted_by_user_id` assignments across `apps/server` | 1 test-contract text match; no active publication owner |
| named newest/latest outcome-summary matches | 5; remaining matches are source/media/attempt history or API vocabulary, not outcome-row selection |
| `MeetingOutcomeSet|meeting_outcome_sets` inventory files | 51, manually classified by path and query owner |
| forbidden content/evidence path scan in feature validation | 0 (the literal scan command in `quickstart.md` is excluded from the result) |
| `git diff --check` | pass |
| operational-script pointer/accept/newest scan | 0 |
| Ruff source/test/script scan | pass |

This receipt intentionally records counts and path classes only. It does not
copy command output, IDs, private titles, external payloads or local evidence
paths.
