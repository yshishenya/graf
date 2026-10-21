# F099/#7647: независимая текущая проверка

Дата: 19.10.2026. Reviewer: `f228_checklists_review`; навык `code-reviewer`.
Ветка: `codex/099-normalization-attempt-fencing`.
HEAD/база локального изменения: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Полоса проверки: **high-risk-product**, существующий срез T125–T128.

## Решение

**APPROVE локальной реализации и PASS качества требований. P0/P1/P2 замечаний
нет.** Текущие контрольные списки: **100 проверено / 0 непроверено**.
Отметки не менялись. Состояние T125–T127 `[X]`, T128 `[ ]` сохранено.

Новый запуск основного агента независимо сверён по законченному журналу и
JUnit XML: **201 различная проверка PASS / 0 FAIL / 0 ERROR / 0 SKIP**,
106.54 с pytest, focused runner112с. В журнале подтверждены
`postgres_test_result=pass` и `postgres_test_cleanup=isolated_container_removed`.
Reviewer повторно тесты не запускал; это проверка результата основного агента,
а не второй независимый запуск201 теста.

## Прочитано и сопоставлено

Проверены AGENTS и карта guidance, конституция7.1.0, spec-kit-flow,
product-gates, актуальные правила обязательных PR-проверок и относящиеся к
артефактам/удалению/F099 разделы PRD и current-product-status. Прочитаны
активные spec, plan, tasks, quickstart, все шесть контрольных списков,
уточнения research/data-model/lifecycle-operations-contract, fragment F99 и
три прежних отчёта владения попыткой. Пререквизиты указывают F099; физическое
имя worktree не использовано как источник области работ.

Просмотрены полные изменения service/restart tests, подготовка, исполнение,
оба runtime caller записи ошибки и все пути общей очистки. Дополнительно
сверены maintenance pickup, publish/discard/losing publisher и обратный
порядок блокировок в transient purge. Прямых production caller записи ошибки
за пределами run/recovery и нового внешнего caller late_object_arrival нет.

1. Номер подготовленной A, owner hash и immutable ID сохраняются scalar
   значениями до rollback. Failure получает Job lock, повторно читает строку
   и отклоняет несовпадение номера/владельца/активного состояния/lease до
   изменения B. Одинаковое имя worker не заменяет номер попытки.
2. До prepare ошибка ограничена исходным count, queued/retry_wait и
   отсутствием LOCAL_PREPARING/UPLOADED попытки. Уже работающая B защищена
   как до, так и после исходного снимка. Непрочитанный count даёт retryable
   DATABASE_UNAVAILABLE без неограниченной записи ошибки job. Обычный
   source_missing и locked expired recovery сохраняют прежний результат.
3. Обычная очистка получает Job→Attempt через SKIP LOCKED внутри savepoint.
   Занятый/исчезнувший row и текущая активная B дают rollback savepoint и
   False без очистки. Двухсессионные тесты проверяют фактическое освобождение
   нового Job lock посредством NOWAIT, а затем успешное повторение. Это
   устраняет новое ожидание Attempt при Job, которое иначе конфликтовало бы
   с существующим transient purge Attempt→Job. Существующие caller locks
   до savepoint не объявляются освобождёнными этим rollback.
4. После stale failure Job lock освобождается rollback до ожидания старой
   Attempt; rehydrate должен завершиться перед discard. Чистится только
   immutable ID собственной A. Существующий late-object путь сохраняет
   Attempt-only lock и повторную очистку CLEANED/PURGED, поэтому поздний PUT
   A не остаётся из-за нового обычного SKIP LOCKED. PUBLISHED защищён.
5. Новые тесты проверяют local_preparing и uploaded/publishing B, повторный
   owner, reservation/object/source snapshot, pre-prepare границы, expiry,
   contention и реальный отказ mkdir. Из старых проверок сохранены READY
   winner, deletion-wins, поздний upload, retry/recovery и tenant boundaries.
   Реальные PostgreSQL транзакции и locks отделены от synthetic
   pipeline/storage/часов; mkdir-сценарий не запускает FFmpeg.
6. Новый `Legacy Impact: untouched` описывает только T125–T128/#7647.
   Код не вводит совместимых псевдонимов, старых режимов, миграции, зависимости
   или параллельный service. API, canonical playback, accepted-source,
   retry/backfill/deletion и dispatch handoff сохранены. Раздел не выдаёт
   историческую приёмку F099 за завершение текущей производственной F290.

## Контрольные списки

| Файл | Проверено | Непроверено | Текущая применимость |
|---|---:|---:|---|
| attempt-ownership.md | 12 | 0 | CHK001–012 подтверждены уточнениями и матрицей выше. |
| requirements.md | 16 | 0 | Границы и измеримые исходы F099 сохранены. |
| media.md | 20 | 0 | Профиль, выбор треков и ресурсные лимиты не меняются. |
| automation.md | 22 | 0 | Сохраняются lineage и автоматические повторы без действий пользователя. |
| lifecycle.md | 22 | 0 | Разделены source/attempt/canonical; deletion/RLS/evidence не ослаблены. |
| worker-restart-recovery.md | 8 | 0 | Startup исключение worker_interrupted не расширено. |
| **Всего** | **100** | **0** | Качество требований; не утверждение выпуска. |

Исторические упоминания80 относятся к четырём первоначальным спискам;
88 — к ним с worker recovery; актуальный итог с attempt-ownership равен100.
Новых незавершённых требований в проверенном срезе не обнаружено.

## Текущий запуск и тождество исходников

Идентификаторы всех167 прежних случаев присутствуют в новом XML. Добавлены
ровно34 случая test_rls_postgres_policies.py из-за выбора всего файла;
пропавших случаев0. Restart29 входят в201 и отдельно не прибавляются.
Одно предупреждение о повторном pytest assertion rewriting не является
ошибкой/пропуском. Числа201 и167 описывают разные запуски, их сумма не
представляется дополнительным покрытием.

До редактирования reviewer сверил14 записей исторического manifest:
runtime service, restart tests, fragment и остальные прежние артефакты
совпали; spec уже получил Legacy Impact, основной отчёт получил текущий
результат. Поэтому старый manifest остаётся историческим. В собственном
старом отчёте по поручению основного агента заменены только два абсолютных
локальных пути на placeholders; команды, результаты и хеши журналов
сохранены. Этот отчёт и текущий spec имеют новые хеши.

| Артефакт | SHA256 |
|---|---|
| service.py | 4af2cffeb4c76782f3a802bd0ba7e2619a885008d10f45ae233f8604bdfa259f |
| test_playback_normalization_restart.py | aeb81d567315823e4f7a06726742dcd3a64d5dd71bbed56105316657ad090736 |
| changes/unreleased/F99.yaml | 5694ab8a297ff52b08c83d7bef993961e088b1b5fe744ca8d3cc1bee9cb7224f |
| spec.md с Legacy Impact | 6155624107687685513a09a2c7eefa7cbe6c178e039f71ab3ef3f9cae8f8e4cf |
| прежний code-review после замены путей | acca9c5052c490b7de7436876a5cc04c38118e251c90ae23cab3c1f879e81ca5 |
| current-167.log | 36138f45fc40c438610170a652b699d7ff85385a7a9f8955ac44f51ce914ffe7 |
| current-167.xml | 70dc1e1e67104df1686c8ce5c45efd8a0fd886e13476d61fa5b08ccde73622f9 |
| current-validation-receipt.json | 3bc2a9ae5106af88809531f83a560efd8c6322009c3d6bc888ff5b1e213b538f |
| selected-files.json | 378364633ccceeb5c360b1fc53f1e79dc9ec255d19f3166acb842361c0391a4c |

Текущие результаты находятся во внешнем каталоге доказательств
`2026-10-19/f099-current-preflight`; слово167 в имени файлов — историческое
имя повторного запуска, а не фактическое число тестов. Старые RED/167
результаты сохраняются в `2026-10-16/graf-issue-by-issue`.

## Границы решения

APPROVE относится к перечисленным исходникам и локальным доказательствам.
Reviewer не изменял код, tests, spec/plan/tasks, отметки списков, GitHub,
commits или сервер; не запускал сборку/тесты/GRAF Dev/production. Изменены
только собственный прежний отчёт (два пути) и этот новый отчёт.
`git diff --check` выполнен, оформление новых отчётов проверено.

Новый commit меняет точный SHA; до принятия PR обязательны три актуальные
GitHub checks (`governance-fast`, `macos-pr`, `pr-metadata`) с checked base
и общим validate-pr-checks. Это ревью не разрешает merge/release, не закрывает
T128/#7647 и не заменяет frozen Full, deploy и производственную приёмку F290.
Согласованное удержание слияний на окно F280 сохраняется.
