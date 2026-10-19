# F099/#7647: независимое ревью реализации защиты попытки

Дата: 2026-10-17. Reviewer: `review_f290_infra`; skill: `code-reviewer`.
Ветка: `codex/099-normalization-attempt-fencing`.
База: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Полоса проверки: **high-risk-product**, локальная реализация до commit/PR.

## Результат

**Approved для проверенного локального изменения: P0/P1/P2 замечаний нет.**
Собственный запуск restart: **29 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, 31.747 s.
Расширенный запуск основного агента сверён по XML/журналу:
**126 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, 89.325 s; restart29 входят в эти
126, отдельный повтор reviewer не объявляется новым уникальным покрытием.
Дополнительный receipt state/RLS сверён:41 PASS/0 FAIL/0 ERROR/0 SKIP,
3.221 s; пересечение идентификаторов с126 отсутствует, всего167 различных PASS.

Это ревью кода и локальные PostgreSQL проверки. Требования100/0,
T125–T127 [X] и T128 [ ], состояние issue, commit, точный SHA PR, merge, frozen Full и
производственная приёмка F290 — отдельные доказательства. Reviewer их не
закрывал и не выдаёт эту проверку за живое восстановление Temporal/production.

## Прочитано и проверено

Прочитаны полные изменения `normalization/service.py` и restart tests,
F99.yaml, актуальные spec/plan/contracts/tasks и собственный requirements
report. Сопоставлены оба runtime caller `record_normalization_failure`:
run_normalization_job и recovery expired job. Прослежены общая cleanup,
job-wide cleanup, maintenance pickup, discard-unowned и losing publisher;
повторно сопоставлен transient purge с обратным порядком Attempt → Job.
Изменений schema/dependency/deletion.py/dispatch handoff/native app нет.

1. **Причина поздней ошибки.** Прежний catch использовал только job_id и
   мог записать ошибку уже новой B. Теперь run сохраняет scalar номер
   подготовленной A, owner hash и immutable ID до rollback. Failure под
   Job lock проверяет count, допустимое состояние, owner и будущую lease.
   Повторяемое имя worker не заменяет номер попытки. Несовпадение даёт
   Deferred до изменения state/reason/due/counters/reservation/audit B.
2. **Ошибка до prepare.** Исходный count читается до prepare; отсутствие
   собственного owner допускает только queued/retry_wait и отсутствие
   LOCAL_PREPARING/UPLOADED attempt. Матрица покрывает B до снимка и B
   после снимка в обоих состояниях. Если сам count не прочитан, run не
   вызывает unfenced failure: возвращается существующая retryable
   DATABASE_UNAVAILABLE. Прямой guard проверен также для другого owner,
   истёкшей lease, неподходящего состояния и queued с активной attempt.
3. **Recovery и обычная ошибка.** Существующий expired recovery проверяет
   job под своей блокировкой и оставляет прежний unfenced внутренний
   вызов; интерфейс исторических прямых tests сохранён. Перенос prepare
   в run не меняет успешный pipeline; единственный runtime caller
   _execute передаёт prepared. Настоящий mkdir отказ при work_directory,
   занятом обычным файлом, сохраняет retry_wait/due, очищает lease и
   временную A, не меняя source. FFmpeg в этом опыте не исполнялся:
   ошибка возникает раньше его вызова.
4. **Причина поздней очистки.** Обычная direct cleanup повторно читает
   Job/Attempt под обоими locks и защищает latest running/publishing
   attempt с будущей lease. Старую immutable A можно очистить; после
   expiry B снова допускает обычную очистку. Защита находится в общей
   функции, поэтому direct/job-wide/maintenance caller не зависят только
   от selector. B local_preparing и uploaded/reservation покрыты.
5. **Пропуск занятых строк.** Оба новых захвата Job → Attempt используют
   SKIP LOCKED внутри savepoint. Missing/contended row и active B вызывают
   rollback savepoint до False. При пропущенной Attempt отдельно доказан
   NOWAIT захват Job другой сессией; Job contention и успешное повторение
   после release также покрыты. Внешний storage I/O начинается после
   commit cleanup_pending, как и прежде. Получение locks не ждёт чужую
   Attempt при удержанном новым cleanup Job, цикл с purge не вводится.
6. **Stale failure → discard.** После Deferred выполняются rollback и
   rehydrate до ожидания Attempt; при неуспехе rollback/rehydrate discard
   не вызывается. Чистится только scalar ID подготовленной A. Тест с
   отдельным держателем старой Attempt доказывает NOWAIT Job после
   входа в discard, затем успешное завершение после release. B и её
   reservation/object/source сохраняются.
7. **Поздний PUT.** Существующий late_object_arrival путь сохраняет
   Attempt-only блокировку и повторную очистку CLEANED/PURGED; новый
   SKIP LOCKED на этот путь не перенесён. Тест late failure кладёт поздний
   объект уже CLEANED A после recovery, затем проверяет его удаление
   вместе с сохранностью B. В расширенном наборе 7 deletion cases
   подтверждают deletion-wins, позднюю загрузку и долговечный PURGED
   tombstone. Published winner по-прежнему защищён ранним возвратом;
   duplicate-loser/READY recovery покрыты историческими restart cases.

Source проверяется сравнением словаря fake storage с исходным набором
байтов и отдельно объектом новой B; owner/state/reason/due/counters/lease/
heartbeat/canonical snapshot, состояние B и reservation сравниваются
после гонки. Synthetic pipeline/storage и управляемые часы обозначены
как doubles; row locking и транзакции выполняются на настоящем PostgreSQL17.

## Проверки и ограничения доказательств

Сверён исправленный исходный RED receipt:
`F099-regression-baseline-red-corrected-20261017.xml` — 15 tests,
15 failures, 0 errors, 0 skips. Ошибки соответствуют прежним нарушениям:
ошибочный NormalizationExecutionFailure вместо Deferred, удалённая B,
счётчик очищенных2 вместо1 и bounded timeout при lock contention.
Reviewer исходный RED повторно не запускал и source не подменял.

Расширенный126 receipt включает restart29, retry3, workflow6, deletion7,
incidents1, audit persistence3, postgres31, idempotency3, failures15,
dispatch3, reuse3, backfill5, priority2, contract3, RLS contract4,
no-secret-egress8. Журнал заканчивается pass и удалением изолированного
контейнера. Единственное warning — уже импортированный pytest fixture
module (assert rewrite); ошибок или skips нет.

Независимая команда reviewer:

```sh
UV_PROJECT_ENVIRONMENT=<canonical-server-venv> UV_NO_SYNC=1 apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_playback_normalization_restart.py --junitxml=/tmp/F099-independent-restart-20261017.xml
```

Перед запуском свободно90GiB. Использована каноническая среда без sync,
штатный runner создал и удалил отдельный PG контейнер; в журнале
`postgres_test_result=pass` и
`postgres_test_cleanup=isolated_container_removed`. Барьеры новых гонок
ограничены timeout3/5/10s; ожидание закрытого контейнера завершилось.
Production, GRAF Dev и сторонние рабочие данные не затрагивались.

## Контрольные суммы

SHA256 текущих файлов совпал до и после собственного запуска с внешним
`F099-implementation-owned-files-20261017.json`:

| Файл | SHA256 |
|---|---|
| apps/server/src/twobrain_rec_server/normalization/service.py | 4af2cffeb4c76782f3a802bd0ba7e2619a885008d10f45ae233f8604bdfa259f |
| apps/server/tests/integration/test_playback_normalization_restart.py | aeb81d567315823e4f7a06726742dcd3a64d5dd71bbed56105316657ad090736 |
| changes/unreleased/F99.yaml | 5694ab8a297ff52b08c83d7bef993961e088b1b5fe744ca8d3cc1bee9cb7224f |

Evidence из внешнего каталога
`2026-10-16/graf-issue-by-issue` (относительно внешнего каталога доказательств):

| Evidence | SHA256 |
|---|---|
| F099-regression-baseline-red-corrected-20261017.xml | 6f9b08d8edcc261dc9bb2d40951a62ff09377566f782af050bc98ddad5b7de24 |
| F099-focused-regression-20261017.xml | a880d840f8907e9078e31bfe6256ee39fc6fbee126990befab6142b13c7378ad |
| F099-state-and-rls-20261017.xml | cc9830e6203d836bdced6f8c9c3715777f67a000bcbc42dbad9f44458b17fa86 |
| /tmp/F099-independent-restart-20261017.log | 2571a4095b641ea017f21f7ab309e61fc1a5b835d670a40c77654295df1c22de |
| /tmp/F099-independent-restart-20261017.xml | 107a1335883872a6636ac8f0f413b796a7a35dfdd68d6f6f0e9198892d67541b |

## Requirements gate и полномочия

Все checklist перечитаны и пересчитаны: attempt-ownership12/0,
requirements16/0, media20/0, automation22/0, lifecycle22/0,
worker-restart-recovery8/0. Итого **100 checked / 0 unchecked**;
отметки качества требований не заменяют runtime proof выше.

Reviewer создал только этот отчёт. Код, tests, spec/plan/tasks,
requirements checklist/report, GitHub, commits, frozen F290 и сервер
не менялись reviewer. `git diff --check` и отдельная проверка пробелов
нового отчёта выполнены. Дальнейшие converge/явное разрешение commit/
exact-SHA PR checks/merge и release остаются основному агенту.
