# F290: четыре послерелизные проверки

Дата подготовки: 2026-10-17. Владелец исполнения и остатка: оператор выпуска
GRAF, issue #6501. Связь: T009–T011, FR007/008/011, SC003. Режим — существующий
high-risk-product; этот документ не разрешает production-запись.

## Статус и границы

Это проект процедур и проверяемая изолированная часть. Три живые процедуры
пока не имеют безопасного синтетического исполнителя; T009/T010/T011 не
объявлены завершёнными. Прежние четыре `required_post_deploy` сохраняются.
Нельзя заменить их результатом локальных тестов или здоровым media worker.

| Сценарий | Изолированная команда | Живая процедура сейчас |
|---|---|---|
| automatic_retry | retry + restart + priority ниже | blocked: нет отказа, ограниченного только синтетической задачей |
| backfill_inventory | backfill + priority ниже | доступно отдельное чтение; новый цикл inventory — запись и пока blocked |
| range_playback | cabinet_playback_route ниже | blocked: нет удерживаемого синтетического сеанса до browser receipt |
| normalization_cleanup | deletion + restart + worker ниже | blocked: нет ограниченного синтетического незавершённого attempt |

В протокол каждого исполнения входят полный source SHA, digest исполняемых
файлов, UTC начала/конца, оператор, среда, предусловия, фактические проверки,
результат, cleanup и владелец остатка. Идентификаторы пользователя/встречи,
ключи объектов, токен, URL с параметрами, сырое аудио и содержимое встреч в
отчёт не входят. Частная связь синтетического run с его объектами хранится
только до подтверждённой очистки в закрытом временном каталоге.

`not-run` — статус процедуры, а не значение GateResult. При переносе в
`PlaybackNormalizationDeploymentEvidence` not-run соответствует `blocked`.
Поле CD `normalization_cleanup_result` соответствует полю модели
`cleanup_result`. Для `readiness_state=ready` нужны все девять pass:
migration_0022, image_capability, profile_contract, media_worker,
automatic_retry, backfill_inventory, range_playback, cleanup и
forbidden_metadata. Четыре результата US3 не заменяют остальные пять.

### Пределы будущего синтетического исполнителя

Это обязательные верхние пределы проекта, ещё не проверенная команда.
Каждый сценарий получает собственный run, максимум два synthetic workspace,
четыре встречи и четыре normalization jobs, кроме inventory: там 101 известная
запись нужна для проверки страницы 100 и продолжения, верхний предел — 128
встреч/jobs. Источник каждой встречи — до двух секунд, суммарный размер
создаваемых объектов — до 16 MiB на обычный run и 256 MiB на inventory;
исполнитель обязан учитывать каждый объект и остановить создание до
превышения лимита. Для retry допустимы один искусственный отказ и не более
двух фактических попыток. Для inventory — четыре заранее известных actions;
для cleanup — один unpublished и один active контрольный attempt. Нельзя
заменять продолжение страницы чтением чужого legacy backlog.

Один run ограничен 900 секундами: новые действия прекращаются не позднее
420 секунд, адресная очистка занимает не более 120 секунд, затем наблюдение
поздних записей — не менее 180 секунд и положительное наблюдение трёх
завершённых циклов reconciliation. Sleep60 идёт после работы, поэтому
180 секунд сами по себе не доказывают три цикла. Если циклы нельзя подтвердить
в пределах общих 900 секунд, результат blocked. Оставшееся время — на
предусловия и итоговый отчёт. Отдельный HTTP
запрос — до 30 секунд, браузерная часть — до 120 секунд, ожидание automatic
retry/ready — до 180 секунд. Auth TTL — существующие 600 секунд без продления;
истечение срока до завершения нужного действия даёт blocked, не новый token.
Любой предел или потеря доказанной принадлежности прекращает сценарий:
только адресная очистка и фиксация остатка; не повторять run автоматически.

## Предусловия общей изолированной проверки

Запускать из корня этой рабочей копии на текущем исходнике. Проверить
свободное место: запас 80 ГБ; при менее 50 ГБ не начинать тяжёлую проверку.
Использовать существующий PostgreSQL runner: он создаёт уникальный контейнер
и тестовые БД, сбрасывает унаследованные адреса операторских БД и удаляет
свой контейнер при выходе. Не использовать production `.env` или Compose.

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_playback_normalization_retry.py \
  tests/integration/test_playback_normalization_restart.py \
  tests/integration/test_playback_normalization_backfill.py \
  tests/integration/test_playback_normalization_priority.py \
  tests/integration/test_playback_normalization_deletion.py \
  tests/integration/test_cabinet_playback_route.py \
  tests/integration/test_deployment_readiness_gates.py \
  tests/unit/test_playback_normalization_worker.py
```

Сохранить команду, код возврата, collection digest, число pass/fail/skip и
журнал штатной очистки; дополнительно проверить отсутствие именно созданного
контейнера. Не удалять другие контейнеры, образы, тома или рабочие копии.
Тесты используют подмены storage, Temporal и media pipeline. Они проверяют
контракты с настоящим PostgreSQL, но не доказывают работу живого FFmpeg,
внешнего HTTP или запущенного production worker.

## 1. automatic_retry

Изолированная опора — `test_playback_normalization_retry.py`,
`test_playback_normalization_restart.py`, `test_playback_normalization_priority.py`.
Проверить временный отказ, расписание 30/60/120 секунд в коротком цикле и
15 минут/1 час/6 часов/24 часа после исчерпания, постоянный отказ без цикла,
очистку попытки, сохранность accepted source, expired lease, duplicate pickup,
защиту активной попытки и приоритет нового материала над backfill.

Будущее живое исполнение обязано:

1. Подтвердить source API/media worker и исходную работоспособность очереди.
2. Создать новую bounded synthetic identity через существующие smoke helpers;
   положительно доказать принадлежность каждой записи этому run.
3. Вызвать ровно один временный отказ только у его normalization attempt.
   Причина должна быть retryable, accepted source остаётся пригодным.
4. Прекратить искусственный отказ, затем только наблюдать обычный worker до
   durable retry и ready с одной canonical artifact. Не вызывать ручной retry,
   `activate_due_normalization_retry`, изменение due time или второй finalize.
5. Проверить источник/число артефактов и очистить только свой synthetic run.

**Недостаёт:** принятого способа выполнить шаг 3 без воздействия на общую
службу. Нулевой active snapshot не исключает новый пользовательский job.
Поэтому остановка/перезапуск общего `rec-media-worker`, изменение общей
настройки, блокировка сети/хранилища или shared очереди не являются процедурой
F290. `verify_playback_normalization_worker_ready.py --control` создаёт workflow,
но не такой отказ. До отдельного design/review узкого исполнителя результат
blocked; производственных действий и выдачи разрешения здесь нет.

Откат: снять только собственный источник отказа; не редактировать состояние
обычной задачи. Если исключительность отказа/cleanup не доказана — остановить
проверку, оставить blocked с оператором остатка, не записывать pass.

## 2. backfill_inventory

Изолированная опора — `test_playback_normalization_backfill.py` и priority:
нулевой допустимый набор, все четыре planned actions, страница 100, durable
cursor, возобновление только по новому watermark и запрет dispatch до
inventory_complete. `inventory_playback_backfill_page` создаёт/меняет run/jobs,
audit и делает commit: не вызывать её для чтения production.

Разрешённая отдельная живая часть — только SELECT в одной транзакции
`REPEATABLE READ READ ONLY`. Использовать действующий разрешённый серверный
путь оператора, не новый секрет и не отключение RLS. Положительно проверить
полноту видимости; выборка, скрытая политикой RLS, не доказывает отсутствие
нарушений. Не сохранять workspace/job IDs или малые группы пользователей.

Конкретный контекст — существующий `rec-postgres` контейнер и операторский
`psql -X --set=ON_ERROR_STOP=1` с уже выданной ролью; имя БД и роль берутся
из существующего закрытого окружения контейнера, без печати значений.
Не использовать app/media роль и не выдавать новые права. Перед SELECT
в той же транзакции подтвердить `rolsuper OR rolbypassrls` для `current_user`
и `has_table_privilege(..., 'SELECT')` для обеих таблиц. Сохранить только
boolean результаты этих проверок, не имена ролей. Если подтверждения нет,
прекратить чтение как blocked. Не применять `SET ROLE`, `row_security=off`
или изменения политик. Ошибка SQL, timeout либо ненулевой exit psql — failed;
успешный пустой вывод также не pass. Этот операторский контекст пока не
проверен живым запросом и не заменяет разрешения на будущую запись.

```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT
  EXISTS (SELECT 1 FROM playback_backfill_runs) AS any_run,
  NOT EXISTS (
    SELECT 1 FROM playback_backfill_runs r
    WHERE r.state IN ('inventory_complete', 'dispatching', 'complete')
      AND r.inventory_completed_at IS NULL
  ) AS completed_inventory_has_timestamp,
  NOT EXISTS (
    SELECT 1 FROM playback_normalization_jobs j
    LEFT JOIN playback_backfill_runs r ON r.id = j.backfill_run_id
    WHERE j.trigger_kind = 'legacy_backfill'
      AND j.state IN ('running', 'publishing')
      AND (r.id IS NULL OR r.inventory_completed_at IS NULL
           OR r.state NOT IN ('inventory_complete', 'dispatching', 'complete'))
  ) AS active_legacy_respects_inventory_gate,
  NOT EXISTS (
    SELECT 1 FROM playback_backfill_runs r
    WHERE r.evaluated_count != r.preserve_valid_count
      + r.validate_candidate_count + r.normalize_source_count
      + r.unavailable_source_count
  ) AS action_counters_reconcile;
ROLLBACK;
```

Любой false или неполная видимость — blocked/failed с объяснением. Даже все
true дают только текущий снимок этих четырёх условий: они не доказывают
полноту legacy-перечня, причину blocked, backlog drain, reconciliation job
counts или фактическую новую обработку страниц. Нулевой any_run не pass.

Полная будущая процедура требует ожидаемого synthetic набора, наблюдения
страницы/курсора/четырёх actions, повторной сверки с persisted jobs и готовыми
артефактами, неизменности source/title/transcript, blocked reasons и bounded
бюджетов. Только read-only снимок не завершает её. Новое синтетическое
наполнение/inventory — отдельный согласованный записывающий запуск после
проверки исполнителя, не административная команда backfill для пользователей.
Откат чтения — ROLLBACK; cleanup нового run ограничен его synthetic identity.

## 3. range_playback

Изолированная опора — `test_cabinet_playback_route.py`: owner/shared playback,
200/206, точные байты и длина диапазона, неполное чтение storage, 416 для
непригодного диапазона, отказ чужому workspace, deleting/failed states,
отсутствие раскрытия storage URL и независимость playback от download policy.

Будущее живое исполнение: новая короткая синтетика; дождаться ready, затем
через установленный `httpx.Client(follow_redirects=False)` и обычный разрешённый browser session
проверить 200 без Range, 206 для `bytes=0-63`, согласованность Content-Range,
Content-Length/Accept-Ranges/audio MIME и 416 для заведомо выходящего диапазона.
Отказ без авторизации и чужому синтетическому workspace проверять отдельными
синтетическими сеансами. Токены читаются из private token-file, не аргумента
`--token`; origin и token-file проверяются существующими `validate_origin`
и `read_private_auth_material(..., expected_run_id=...)` из `smoke_target.py`.
Читать raw response, статус и заголовки, не декодировать аудио как JSON;
416 проверять как ожидаемый ответ. Любой redirect отклонять до второго
запроса. Существующий `JsonHttpClient` имеет только POST/PUT, декодирует JSON
и отклоняет 416: для этой проверки он непригоден. Тело ответа не публиковать.

Затем воспроизвести и перемотать ту же синтетику в согласованном браузере;
зафиксировать факт 206 и движение currentTime без URL/ID/content. Проверка
встроенного macOS пути выполняется только единственным GRAF Dev через штатный
harness и требует доступного незанятого Mac. Browser receipt не доказывает
embedded receipt. Остановить воспроизведение, закрыть synthetic session и
выполнить адресную очистку с residue check.

**Недостаёт:** проверенного исполнителя удержания synthetic сеанса на время
HTTP/browser части. `run-production-smoke.sh` сразу очищает auth/artifacts
после upload и не ждёт эти проверки. Не добавлять ему небезопасный keep-флаг,
не читать пользовательскую встречу и не оставлять временный token бессрочно.
До существующего или независимо проверенного узкого исполнителя — blocked.
Общий smoke `infra_smoke_ready` не является результатом range_playback.

## 4. normalization_cleanup

Изолированная опора — deletion/restart suites и worker unit tests: удаление
на каждой границе, late output, retry cleanup при storage failure, защита
active lease/canonical winner, очистка только собственных временных каталогов
и запрет небезопасного work directory.

Будущая живая процедура использует только собственную synthetic identity,
для которой заранее создано известное число unpublished attempts и отдельный
active контрольный attempt. Наблюдать обычную reconciliation/cleanup; затем
сверить DB states, точные ожидаемые objects и temp directories с baseline.
Источник accepted, canonical winner и active lease должны сохраниться.
Простое отсутствие кандидатов/каталогов не положительный сценарий очистки.

После положительной проверки сохранности active контроля дождаться его
обычного завершения либо штатно отменить только собственную synthetic
встречу через существующий путь удаления. Перед окончательной smoke cleanup
доказать отсутствие живого lease, выполняющегося workflow и ожидающей
попытки этого run. Если этого нельзя доказать за отведённые 420 секунд,
не удалять его записи из-под worker: результат blocked с владельцем остатка.
После адресной очистки и отзыва auth наблюдать ещё 180 секунд; повторная
запись или объект означает failed/residue, а не повторную общую очистку.

**Недостаёт:** проверенного способа создать именно эти ограниченные fixtures
без общего worker interruption и чужих объектов. Нельзя напрямую вызывать
`cleanup_normalization_attempt` по найденным пользовательским IDs или удалять
общий work directory. До узкого synthetic исполнителя — blocked.

После каждого записывающего запуска переиспользовать проверенный
`cleanup_smoke_auth_session.py` и `cleanup_smoke_artifacts.py` с точным run-id
и доказанными принадлежностями. Auth cleanup и DB/object cleanup — разные
результаты. Общая очистка smoke не доказывает исходный normalization cleanup.
Не стирать Temporal/Langfuse history: их операторское хранение отдельно.
При residue сохранить безопасные количества и назначенного оператора;
cleanup_result != pass запрещает готовность. Новое удаление/production run
потребует отдельного согласия на конкретный объём после проверки процедуры.

## Следующая работа

Сначала независимо проверить этот проект и изолированные команды. Затем
уточнить T009/T010 для узкого synthetic исполнителя с явными owned paths,
положительной проверкой run ownership, bounded lifetime, отказом без cleanup
и без общих runtime-настроек. До design/checklist/analyze и исполнимых
регрессий такого инструмента код не писать. Выпуск/Full/CD старого кандидата
не повторять. После подготовки запросить отдельное разрешение на точную
production-запись; никакого согласия этот документ не подразумевает.
