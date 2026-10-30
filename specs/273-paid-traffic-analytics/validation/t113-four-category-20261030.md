# F273/T113: удаление и повтор четырёх локальных категорий

База `7b83ec21998cc24c2d4dc8a59a9d2c2edfcebe65`, ветка
`codex/f273-local-period-20261029`, `high-risk-product`, T113/#7804.
[Независимый проект и анализ](t113-four-category-design-review-20261030.md)
прошли до изменения кода, 117/0 вопросов; это не рабочее включение.

## Изменение

Одна закрытая карта категорий переиспользуется catalog/parser/replay.
Реестр v2 принимает account_closure и ровно четыре local category/all.
Каждый случай исполняется собственной категорией/сроком. Отзыв уровня требует
всех его категорий, даже если таблицы пусты; provider-удаление не объявляется
исполненным локально. Старые v1 остаются отзывами без разрешения replay.

`client_acquisition_attribute` теперь удаляет отдельную строку полностью,
включая bridge, путь и времена. Прежние шесть NULL сохраняли связь с аккаунтом
и не доказывали полное обезличивание. Сам `user_identities` сохраняется.
Finalizer и восстановление используют один точный account helper. Finalizer
записывает отдельные acquisition time/count в той же транзакции, что ledger
и completion. Late writer берёт блокировку той же identity и отказывает
закрытому аккаунту; ошибка второго удаления откатывает всю финализацию.

Source читает все принятые удаления в одном RR readonly reduced соединении.
Closure и ledger требуют ENABLE/FORCE RLS/SELECT/точные policies; три старые
аналитические таблицы — отсутствие RLS/policies и SELECT по0094/0095.
Category/all проверяется EXISTS всей таблицы; ledger/acquisition также
проверяются по точным completed accounts. Метаданные исполнения не заменяют
фактическое отсутствие. Legacy без acquisition metadata подтверждает только
текущую postcondition; частичный/повреждённый present result даёт HOLD.
Новые count/time не приравниваются ledger либо первоначальному удалению;
исторические сроки остаются unverified. Completed не исправляется задним числом,
source-reader не удаляет данные и не требует category/all ради одного аккаунта.

Учебный replay сохраняет собственные UUID/OID/password/владение и прежнюю
предварительную native-сверку ledger. Полные survivors всех четырёх категорий
сравниваются до COMMIT и новым соединением после него. Источник не меняется.
Неизвестный commit/readback/cleanup не разрешает успех; оба unconditional HOLD
сохранены. Новых библиотек, сервисов, миграций или рабочих grants нет.

## Проверки

- Unit RED: три неподдержанных scope, несовместимый будущий аргумент и
  отсутствующий helper; 5 failures, а не пять доказанных утечек.
- Причинный native RED старого finalizer: acquisition9 вместо ожидаемых8,
  с ненулевым bridge; отдельная строка закрытого аккаунта действительно оставалась.
- Причинный native RED прежнего шести-NULL исполнения, подставленного только
  в собственном процессе теста: после action остались acquisition rows,
  действующий source-check дал lifecycle_remnants. Рабочий код не откатывался.
- Native проверяет настоящий finalizer, rollback/позднюю запись с фактическим
  ожиданием блокировки, отдельные metadata, early completed без переписывания,
  old dump и точный account replay, каждый scope и полное покрытие,
  idempotence, snapshots чужих строк и сохранность identity.
- Native source дополнительно проверяет legacy/partial/string metadata,
  account remnant, actual category remnants, accepted без результата даже
  на пустой таблице, hidden policies/enable RLS/no SELECT и полное withdrawal
  coverage. Прежние source chronology и coherent backup проверки сохранены.

Журналы лежат в ignored `.dev/growth/t113-four-category-*-20261030.log`.
Окончательный штатный общий профиль: **392 passed,37 skipped,48 deselected,
2 прежних warnings**,279,73с. Все429 выбранных случаев завершены;37 пропусков
относятся к прежним Linux root/proc/memfd/ACL границам на Mac. Их наличие
не объявляется новым Linux PASS. Общая учебная PostgreSQL удалена штатной
оболочкой (`postgres_test_cleanup=isolated_container_removed`).

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q --tb=short \
  tests/unit/test_activation_restore_replay.py \
  tests/unit/test_product_analytics_legal_basis_lifecycle.py \
  tests/unit/test_activation_operator.py \
  tests/unit/test_local_retention.py \
  tests/unit/test_product_analytics_legal_basis_gate.py \
  tests/unit/test_product_analytics_auth_attribution.py \
  tests/integration/test_activation_restore_replay.py \
  tests/integration/test_product_analytics_legal_basis_erasure.py \
  tests/contract/test_product_analytics_registration_handoff_contract.py \
  -k 'not postgres or source_lifecycle or old_copy_replays or category_case_erases or coherent_copy_is_native_and_can_be_restored or all_four_categories or acquisition_finalizer'
```

Дополнительно: полный unit-профиль378PASS/37SKIP/2warnings; targeted55PASS/
40deselected; отдельно штатный erasure/registration-handoff20PASS/2warnings
и cleanup PASS; retention rules12PASS/2warnings. Это перекрывающиеся наборы,
их суммы не являются количеством уникальных проверок. Ruff с прежним
исключением E721, Spec Kit governance, development-process, fragments,
whitespace и локальные ссылки изменённых Markdown пройдены.

Неуспешная диагностика сохранена:

- `profile`:420PASS/37SKIP/1FAIL/19ERROR. FAIL вызван устаревшим test spy без
  scalar после нового account-status read; spy исправлен, полный unit и общий
  профиль повторены.19 setup errors вызваны моим запуском shared-PG тестов без
  штатной оболочки/TWOBRAIN_DATABASE_URL; правильный отдельный и общий повторы
  зелёные. Этот журнал не является общим PASS.
- `final-profile`:391PASS/37SKIP/48deselected/1ERROR: Docker отказал при создании
  сети в setup `corrupt_copy`. Точный stderr/первопричина не доказаны. При
  последующем полном штатном прогоне этот сценарий и весь выбранный набор PASS.

[Независимая проверка кода](t113-four-category-code-review-20261030.md)
принадлежит проверяющему; её окончательное решение хранится в самом отчёте.
Окончательные контрольные суммы исходников, тестов, документов и журналов —
ignored `.dev/growth/t113-four-category-final-hashes-20261030.json`.
Локальный профиль проверяет изменённые байты, не заменяет exact-SHA GitHub CI.

## Границы приёмки

Это часть существующей открытой T113 с зависимостями T109/T110/T111; новых
задач или закрытий нет. Полный executable/functions/jobs catalog, верхние
initial/backup/verify/actual restore/resume, shell/CD/rollback, T112, общий
выпуск и рабочее измерение остаются открытыми. Полный converge F273 здесь
не выполнялся. Выявленный объём уже покрыт этими задачами; дубли не добавлены.
Обновлены действующие модель/operations/реестр/quickstart; исторические отчёты
шести NULL сохранены и не объявляются доказательством новой реализации.

T0 не установлен, аналитика/IP не включены, Dev и production не менялись.
Коммерческие AC01–AC06 плана роста остаются открытыми. Публичный read-only
замер30.10: robots.txt и sitemap.xml HTTP200, в карте17 URL; это не доказательство
индексации, кликов, регистраций или продаж.
