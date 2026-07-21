# Research: Детальный metadata-only отчёт поддержки

## Decision 1: Версионировать payload как v2, но принимать v1

**Decision**: macOS отправляет `desktop-support-incident.v2`; server redaction
принимает и `desktop-support-incident.v1`, и v2, добавляя серверные поля и
fingerprints одинаково.

**Rationale**: v2 явно сигнализирует появление новых полей, а переходная v1
совместимость не ломает отчёты уже установленных macOS сборок и pending
incidents. Поля остаются flat allowlist плюс bounded nested lists, поэтому
сервер может безопасно заполнить отсутствующие значения `unknown`.

**Alternatives considered**:

- Оставить v1 навсегда — скрывает смену контракта и усложняет поддержку.
- Сразу отклонять v1 — ломает обновление приложения и оставленные offline
  reports; отклонено из-за release/update границы.

## Decision 2: Переиспользовать sync-state, не добавлять новый запрос

**Decision**: расширить уже существующий decoder
`/api/v1/desktop/recordings/{local_recording_id}/sync-state` безопасными
`deletion_state`, `access_state`, upload/processing/review status и conflict
reason/next_action; workflow IDs и URLs не передавать, только bounded codes/
booleans/fingerprints.

**Rationale**: endpoint уже является server-authoritative источником для
reconciliation и возвращает требуемую truth. Второй запрос создавал бы гонки,
лишнюю latency и новый auth surface.

**Alternatives considered**:

- Собирать только локальную очередь — уже доказано недостаточным для stale
  `uploaded` после server deletion.
- Добавить отдельный diagnostics endpoint — дублировал бы sync-state и
  увеличивал privacy/CSRF surface.

## Decision 3: Канонический stage и truth precedence

**Decision**: report строит `canonical_stage` из server deletion/access/conflict
перед локальным custody state; `server_copy_state` имеет значения
`confirmed`, `deleted`, `blocked`, `unknown`, а `server_copy_known` остаётся
совместимым boolean (`true` только для `confirmed`). `problem_code` проверяет
sync conflict/deletion до owner policy.

**Rationale**: устаревший `finalizedAt` не должен маскировать последующее
удаление; stage/problem должны объяснять причину, а не только ответственного.

**Alternatives considered**: вычислять truth только из `item.state == uploaded`
или `finalizedAt != nil` — отклонено, это источник текущего ложного low-risk
сценария.

## Decision 4: Ограниченный timeline/retry history

**Decision**: включать ключевые безопасные timestamps и не более пяти последних
retry events; из failureReason извлекать только safe problem code и numeric HTTP
status, не передавая исходную строку.

**Rationale**: support получает порядок событий и последнюю причину без raw
logs. Лимит защищает clipboard/server body от unbounded queue history.

**Alternatives considered**: отправлять весь retry ledger/raw error — нарушает
metadata-only и payload bound; отправлять только общий attempt count — теряет
временную динамику.

## Decision 5: Issue canon для runtime reports

**Decision**: новые runtime Issues получают `[114][P*][support/custody] T000:`
title, labels `feature:114`, priority, type/area/privacy/source и private body
с state matrix, timeline, retry summary и full redacted JSON. `T000` означает
runtime incident, не задачу реализации; Spec Kit task issues используют свои
`T###`.

**Rationale**: так issue находится по feature/stage/problem/correlation и
соответствует русскому GitHub issue canon, не выдавая raw IDs.

**Alternatives considered**: сохранить `[061]` и старые labels — ломает
фильтрацию новой фичи и канон; оставить свободный title без T000 — нарушает
project canon для manually created issues.

## Decision 6: Один подробный fallback

**Decision**: queue service строит тот же `DesktopSupportIncidentReport` для
submission и clipboard; view получает текст через callback и только затем
пишет его в NSPasteboard. Старый `DesktopUploadCustodySafeReport` остаётся для
совместимости native summary, но больше не является support fallback.

**Rationale**: исключает расхождение между отправленным и скопированным
отчётом и не тащит AppKit в queue core.

**Alternatives considered**: расширить старую короткую сводку вручную — два
разных payload surface неизбежно расходятся; копировать raw queue JSON —
запрещено privacy gate.

## Decision 7: Без миграции базы

**Decision**: не добавлять колонок/миграций; существующее
`latest_safe_report_json` хранит v2, а серверные вычисленные correlation и
redaction version остаются в том же JSON/модели.

**Rationale**: контракт JSON уже является source of truth, а миграция не даёт
пользы для поиска, который идёт по private Issue labels/body.

## Decision 8: Проверка и rollout boundary

**Decision**: добавить focused Swift/Python/contract tests, negative privacy
assertions и quickstart; пройти `infra/scripts/ci-local.sh`. Deploy и release
не выполнять в этом slice без отдельного approval.

**Rationale**: feature затрагивает высокорисковые shared paths, но пользователь
сейчас просил перепроверку и исправление отчёта, а не production rollout.
