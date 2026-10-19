# F099: независимое ревью требований защиты попытки

Дата: 2026-10-17. Reviewer: `review_f290_infra`.
Ветка: `codex/099-normalization-attempt-fencing`.
HEAD: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Risk/validation lane: **high-risk-product**, требования до реализации.

## Текущий результат

**PASS требований: новый checklist — 12 checked / 0 unchecked.**
Отметки подтверждают качество требований, не выполнение исправления.
T125–T128 добавлены, прочитаны и согласованы с уточнённым plan; все четыре
пока открыты и ссылаются на issue #7647. Данный отчёт подтверждает
requirements gate; актуальные analyze/issue sync перед кодом проверяет
основной агент отдельно. Состояние issue на GitHub reviewer не проверял.

## Прочитанные артефакты

Прочитаны Session2026-10-17 в spec и новые разделы plan/quickstart,
research/data-model/lifecycle-operations-contract, существующие FR035/044,
SC016/024, tasks и все шесть checklist. Prerequisites подтвердил активную
`099-review-m4a-normalization`; фактическая Git ветка указана выше.

Применены AGENTS, constitution7.1.0 (особенно III/IV/VI), guidance README,
codex-worktrees, spec-kit-flow, product-gates, release-and-validation,
относящиеся продуктовые границы PRD/current-product-status и reviewer gate
`speckit-implement`. Новые поля схемы, внешние зависимости, публичный API,
native/capture/UI и production не входят. Релизные полномочия не расширены.

Сопоставлены неизменённые функции service.py: подготовка, запись failure,
direct/job-wide cleanup, discard-unowned и losing publisher; также обычный
selector и transient purge из deletion/service.py. Тесты/сервер/приложение
reviewer не запускал. Исторические runtime результаты не переаттестованы.

## Обоснование нового checklist

| Пункт | Состояние | Основание |
|---|---|---|
| CHK001 | checked | Session определяет неизменность state/counters/reason/due/lease/reservation B при поздней ошибке A. |
| CHK002 | checked | Plan/data-model используют монотонный attempt_count вместе с owner; совпадающий owner отдельно включён в матрицу. Сброс cycle_attempt_count не сбрасывает attempt_count. |
| CHK003 | checked | Потеря владения даёт существующий Deferred без failure/incident/cleanup B; правила Temporal и handoff не меняются. |
| CHK004 | checked | После замечания plan требует для pre-prepare ошибки не только исходный scalar count, но queued/retry_wait и отсутствие активной LOCAL_PREPARING/UPLOADED; уже running/publishing B защищена даже при отказе prepare до проверки state. source_missing и locked expired recovery сохраняются. |
| CHK005 | checked | Обновлённый FR044 и общий guard защищают текущую B и в direct cleanup, и в sweep; только selector недостаточен. |
| CHK006 | checked | Текущая попытка определяется номером job.attempt_count и активной будущей lease; старую A можно чистить по immutable ID; expiry/non-active остаются допустимыми. |
| CHK007 | checked | Plan явно сохраняет READY canonical winner, deletion, purged tombstones, late PUT и reservation границы; late_object_arrival=True остаётся внутренним fenced путём только собственной immutable A, не обычной очисткой B. |
| CHK008 | checked | Обычная cleanup: оба новых захвата Job → Attempt через SKIP LOCKED/savepoint и False после rollback при пропуске. Fenced late-object: прежний Attempt-only lock; перед новым вызовом из stale failure обязательны rollback+rehydrate и проверка NOWAIT. cleanup_pending commit до I/O сохраняется. |
| CHK009 | checked | Quickstart и plan определяют оба RED→PASS порядка, B local_preparing/uploaded, повторный owner, reservation/object/source неизменность и bounded барьеры. |
| CHK010 | checked | Управляемые часы, pipeline/storage/Temporal doubles явно не равны живому recovery/post-deploy; PG17 одноразовый и production запись исключена. |
| CHK011 | checked | Scoped owned paths service.py/restart tests, документы F099 и fragment; high-risk lane; review/analyze/sync/converge, отдельные commit/merge и exact-SHA PR/Full/CD gates названы. |
| CHK012 | checked | SE03 не доказанный дефект; dispatch → activity и Temporal retry policy явно исключены. |

## Устранённое замечание AO01/P1 — инверсия блокировок

В `reconcile_transient_media_purges`, deletion/service.py:1070–1088,
сначала выбираются PlaybackNormalizationAttempt FOR UPDATE, затем
PlaybackNormalizationJob FOR UPDATE. Первоначально предложенная общая
cleanup брала Job → Attempt с возможным ожиданием. Возможное чередование:

1. Cleanup удерживает Job и ждёт Attempt.
2. Transient purge удерживает тот Attempt и ждёт Job.

Обычный meeting deletion путь использует правильный Meeting → Job → Attempt,
но это не отменяет другой существующий путь. Предварительного чтения job_id
без блокировки и отсутствия внешнего I/O под lock недостаточно, чтобы
устранить цикл. Простой дополнительный Meeting lock только в cleanup тоже
не обоснован для всех случаев: для nonterminal processing workflow вызов
`set_workflow_status` в purge делает commit до чтения attempts/jobs и
освобождает прежний Meeting lock; terminal ветка этот вызов пропускает.

Актуальный plan устраняет это ожидание без расширения owned paths:
оба новых захвата Job → Attempt используют SKIP LOCKED внутри savepoint.
Если Job или Attempt занят либо исчез, rollback savepoint освобождает
новые locks; caller transaction не откатывается, результат — честный False
без изменения данных, storage delete или ложного cleaned. Поэтому cleanup
не может ждать занятую Attempt, удерживая захваченный им Job, независимо
от того, сохранила terminal/nonterminal ветка purge прежний Meeting lock.
Существующие блокировки caller до savepoint не объявлены новыми: их
жизненный цикл остаётся ответственностью caller. В recovery failure уже
делает commit до вызова cleanup; это сверено с текущим кодом.

Матрица plan требует детерминированный двухсессионный сценарий: другая
session держит Attempt; cleanup пропускает без изменения/storage I/O;
после возврата cleanup та session получает Job без ожидания. Отдельно
проверяется занятый Job; после освобождения штатная cleanup должна
завершиться. Эти проверки должны доказать реальный rollback savepoint и
отсутствие оставшегося нового Job lock, а не только значение False.
Это достаточное требование перед реализацией, ещё не runtime PASS.
Повторная rehydrate-проверка current state под обоими locks и commit
cleanup_pending до storage I/O сохраняют границы B и late PUT.

## Дополнительное ревью fenced late-object пути и T125–T128

После первоначального PASS plan уточнён для существующего
`late_object_arrival=True` / `_discard_unowned_attempt`. Прежний путь
сохраняет блокирующий захват только Attempt, без нового Job/SKIP LOCKED,
и использует immutable ID своей A после установленной утраты владения
или удаления. Это требуется, чтобы поздний PUT уже CLEANED/PURGED A
не потерял единственную непосредственную очистку из-за нового no-op.
Текущий код действительно разрешает повторную очистку CLEANED только
с этим флагом и очищает cleaned_at у PURGED при позднем объекте;
PUBLISHED остаётся защищённым ранним возвратом.

Первое описание нового caller после stale failure оставляло важную
неясность: проверка failure уже могла удерживать Job, а последующий
Attempt-only discard ждать чужую Attempt. Так возвращался бы AO01,
несмотря на отсутствие нового Job lock внутри discard. Актуальный plan
теперь явно требует rollback транзакции проверки failure и rehydrate
контекста ДО discard, в том числе после Deferred. ID A сохраняется scalar
до rollback; для pre-prepare без собственной A этот вызов не добавляется.
Обязательный двухсессионный тест должен доказать, что держатель Attempt
получает Job NOWAIT, затем после release discard завершает очистку A,
сохраняя B и source. Уточнение достаточно на уровне требований; фактическое
освобождение locks проверяется только после реализации в PostgreSQL.

T125 задаёт исходный RED и обе гонки с повторным owner/pre-prepare и
uploaded/reservation. T126 ограничивает failure и сохраняет штатные
source_missing/recovery/Deferred. T127 содержит обычную cleanup с
SKIP LOCKED/savepoint, сохранение fenced late-object пути и двухсессионные
проверки. T128 требует focused PostgreSQL, независимое ревью/converge,
evidence/fragment и отдельные commit/PR/merge/exact-SHA gates. Зависимости
T125 → T126 → T127 → T128 последовательны, [P] нет, пути принадлежат
заявленному срезу. Новых публичных параметров, схемы или dispatch policy
задачи не требуют. Блокеров требований/покрытия tasks не осталось.

## Уже устранённые уточнения

1. Изначальный scalar count для ошибки до prepare был недостаточен: вызов
   мог увидеть уже running B и упасть до проверки её state. Plan теперь
   задаёт проверку допустимого состояния/отсутствия активной попытки и
   отдельный сценарий. Это достаточное требование, ещё не рабочий код.
2. Старый FR044 буквально запрещал чистить любую попытку при активном job,
   хотя новая Session разрешала старую A при B. FR044 теперь явно защищает
   current attempt и допускает older immutable cleanup. SC024 относится
   к active/unexpired попытке; противоречие устранено. Более консервативный
   неизменяемый sweep selector допустим и не обязан выбирать старую A сразу.

Supporting data-model/contract содержат более краткое описание; подробные
pre-prepare условия берутся из новой plan. При реализации неизвестный scalar
или неуспешное получение снимка не должны превращаться в безусловный failure
чужой попытки; это проверяется вместе с указанной pre-prepare границей.
Последнее уточнение plan явно задаёт этот безопасный отказ: если исходный
count не прочитан из-за ошибки БД, существующий DATABASE_UNAVAILABLE/retry
возвращается без durable mutation и без вызова unfenced failure(job_id).
Это соответствует CHK003/004 и не создаёт нового состояния или механизма
повтора. Отдельно от отсутствующего count по ошибке БД сохраняется ранее
определённый source_missing путь с успешно полученным исходным снимком.

## Исторические checklist

Все прежние checklist прочитаны, отметки и содержимое не менялись:

| Checklist | Checked | Unchecked | Применимость и противоречия |
|---|---:|---:|---|
| requirements.md | 16 | 0 | Качество spec; новое уточнение не вводит API/UX/новый продуктовый выбор. |
| media.md | 20 | 0 | Профиль/FFmpeg/source не меняются; каноническая публикация сохраняется. |
| automation.md | 22 | 0 | Автоматика/lineage/нет пользовательского retry сохраняются; Deferred не выдаётся за новую ошибку B. |
| lifecycle.md | 22 | 0 | Deletion-wins, immutable artifacts, RLS и metadata-only сохраняются; AO01 — текущий design blocker порядка locks, не основание переотмечать исторический документ. |
| worker-restart-recovery.md | 8 | 0 | Только startup worker_interrupted может обойти долгую паузу; plan этого не меняет. |

Итого прежних **88 checked / 0 unchecked**; вместе с новым состоянием —
**100 checked / 0 unchecked**. Старое упоминание80 пунктов относится к четырём
исходным checklist до добавления restart recovery и не является текущим
полным итогом. Противоречий требованиям этих документов после уточнения
FR044 не найдено; AO01 снят только после уточнения неблокирующих захватов
и обязательной двухсессионной проверки в новом plan.

Reviewer изменил только новый attempt-ownership.md и этот отчёт. Код,
spec/plan/tasks, исторические checklist, F290 frozen23, GitHub и сервер не менял.
Перед передачей результата новый checklist перечитан; проверка оформления
не является runtime validation или разрешением commit/release.
