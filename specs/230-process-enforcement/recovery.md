# F230: восстановление источника задач

Это реконструкция по текущим публичным issues. Оригинальные байты старых
spec/plan/tasks не найдены; файл не утверждает обратного. Все двадцать исходных
номеров и тексты результатов сохранены. T000/#6314 — главная issue.

| Task | Issue | Исходный результат | Решение / владелец |
|---|---|---|---|
| T001 | #6315 | [P] Зафиксировать allocator и enforcement contracts, data model и exact base SHA. | Активная задача; #6315 |
| T002 | #6316 | [P] Добавить metadata-only changelog fragment `changes/unreleased/F230.yaml`. | Активная задача; #6316 |
| T003 | #6317 | [P] Добавить synthetic fixtures для branch self-collision, timeout, PR/manual/merge_group и stale receipt. | NOT_PLANNED duplicate; F227 T003/T007/T015 — #6210; F234 T002 — #6375 |
| T004 | #6318 | Исправить `scripts/claim-feature.py`, чтобы requested branch не считался внешней коллизией. | NOT_PLANNED duplicate; F234 T001/T002 — #6374/#6375 |
| T005 | #6319 | Добавить bounded GitHub scan с различением `free`, `occupied` и `blocked` и без ложной записи при timeout. | NOT_PLANNED duplicate; F234 T001/T002 — #6374/#6375 |
| T006 | #6320 | Добавить parallel/idempotent regression tests и проверить shared lock/atomic claim state. | NOT_PLANNED duplicate; F234 T001/T002 — #6374/#6375 |
| T007 | #6321 | Привязать claim к umbrella issue/label и active `.specify/feature.json`. | NOT_PLANNED duplicate; F216 T005/T007 — #6092/#6097; F235 T001 — #6400 |
| T008 | #6322 | Укрепить receipt validator для requested/start/end SHA, conclusion, cancellation и workflow identity. | NOT_PLANNED duplicate; F227 T005/T007/T014 — #6212 |
| T009 | #6323 | Укрепить PR metadata validator/template для Feature ID, umbrella, task IDs, lane, SHA и Legacy Impact. | NOT_PLANNED duplicate; F227 T016/T025 — #6223 |
| T010 | #6324 | Добавить negative tests для stale, partial, changed-tree и mismatched base/event. | NOT_PLANNED duplicate; F227 T007/T013/T015 — #6222 |
| T011 | #6325 | Проверить workflow contract для PR, manual и merge_group exact checkout/concurrency. | NOT_PLANNED duplicate; F227 T008–T012 — #6218 |
| T012 | #6326 | Проверить authoritative merge-group mapping и fail-closed API errors. | NOT_PLANNED duplicate; F227 T010/T011 — #6217 |
| T013 | #6327 | Подготовить observe-only rehearsal report и explicit rollback procedure; required checks не включать автоматически. | Активная задача; #6327 |
| T014 | #6328 | Проверить root-router size, active pointer fail-closed и отсутствие mtime fallback. | NOT_PLANNED duplicate; F216 T007/T008/T009 — #6097/#6099/#6098 |
| T015 | #6329 | Обновить generic harness schemas/templates/skill только portable правилами, без GRAF data. | NOT_PLANNED duplicate; F216 T032 — #6121 |
| T016 | #6330 | Добавить инструкции для subagents: read-only explorers возвращают summary/evidence, write agents имеют один owner/worktree. | Активная задача; #6330 |
| T017 | #6331 | Запустить speckit-analyze, устранить Critical/High findings, не меняя reviewer-owned checklists. | Активная задача; #6331 |
| T018 | #6332 | Запустить speckit-taskstoissues, проверить canonical labels/titles и отсутствие дубликатов. | Активная задача; #6332 |
| T019 | #6333 | Запустить quickstart, governance tests и `infra/scripts/ci-local.sh --fast` на финальном exact SHA. | Активная задача; #6333 |
| T020 | #6334 | Запустить speckit-converge append-only и зафиксировать оставшиеся operator-owned gates. | Активная задача; #6334 |

Отменённые задачи не имеют checkbox [X] и не входят в новый список исполняемых
задач. Решения already closed сохраняются; повторное принятие всего объёма их
преемников здесь не заявлено. Состояния преемников и исходные подробные closure
comments остаются в GitHub. План F230 не повторяет их код.

Восьми активным task IDs соответствуют восемь прежних открытых issues; никакой
новый номер не назначается. По #6314 действуют все исходные критерии: allocator,
связи metadata, stale protection, наблюдаемый операторский переход и стабильный root.

Реальный rehearsal T013 и окончательные T019/T020 не объявляются выполненными
наличием этого документа. Отмена дубликатов требует отдельной семантики closeout,
которую текущий completed-validator не поддерживает; перед итоговым feature-closeout
нужно согласованное общее решение, а не фиктивные completed rows или исключение F230.
