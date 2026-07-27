# Спецификация: быстрый и достоверный test pipeline

## Контекст

Серверные тесты используют временную замену production database. Продукт
работает на PostgreSQL, а текущая замена скрывает ошибки в RLS, миграциях,
индексах, типах, блокировках и PostgreSQL-функциях. Полный CI также запускает
все тесты одним непрозрачным шагом, поэтому маленькое изменение проходит тот
же долгий путь, что и большой релиз.

## Цель

Ускорить локальную разработку без потери уверенности в production-поведении:

1. запускать DB-зависимые тесты на изолированном loopback-only PostgreSQL;
2. дать быстрый lane для тестов, которым БД не нужна;
3. сохранить полный lane, RLS и миграционные проверки;
4. показывать безопасные агрегированные timings и состав покрытия;
5. убрать test-only legacy, отделить runtime/evidence проверки и восстановить
   скачивание аудио владельцем по умолчанию.

## Требования

### R1. PostgreSQL-only

- Обычные тесты получают схему через Alembic `head`, а не через
  `Base.metadata.create_all`.
- PostgreSQL для тестов должен быть отдельным disposable target на loopback;
  production URL и production database name должны отклоняться.

### R2. Изоляция

- Каждый pytest/xdist worker получает отдельную сгенерированную базу.
- Между тестами данные сбрасываются bounded `TRUNCATE ... RESTART IDENTITY
  CASCADE` по таблицам текущей ORM-модели и восстанавливается детерминированный
  seed.
- Тесты чистой схемы получают отдельную пустую базу и не могут повредить
  seeded database.
- Runner удаляет контейнер и временные базы при успехе, ошибке и SIGINT.

Точечные behavior-preserving исправления PostgreSQL-совместимости в production
queries/auth error mapping допускаются только если они обнаружены этим lane и
сохраняют уже проверяемый контракт приложения.

### R3. Lanes

- `ci-local.sh --fast` запускает тесты, не требующие PostgreSQL, исключая
  strict RLS/governance/spike markers, а также lint и compile-проверки; он не
  поднимает БД.
- `ci-local.sh --full` запускает весь собранный server suite через
  PostgreSQL runner; это обязательный closeout gate.
- Governance/readiness и строгие RLS-проверки имеют явные markers/команды и не
  маскируются под fast lane.
- Опциональные macOS hardware/spike проверки не запускаются обычным server
  lane и вызываются отдельными скриптами.

### R4. Достоверность

- Fast lane не является доказательством PostgreSQL/RLS поведения.
- Full lane сравнивает baseline collection с фактически выполненными фазами и
  завершается ошибкой при потере node id.
- Не разрешается добавлять `skip`, `xfail`, постоянный `ignore`, `-k` или
  уменьшать assertions ради скорости.
- Вывод и evidence содержат только counts, phase timings, durations и digest;
  URL, пароли, аудио, transcript и private content не выводятся.

### R5. Обратная совместимость workflow

- Прямой запуск DB-теста без подготовленного disposable PostgreSQL завершается
  понятной ошибкой с командой запуска runner.
- Существующие fake Temporal/MediaScribe/MinIO остаются fake-зависимостями
  обычного server suite.
- Изменение не меняет product/runtime topology и не требует deploy.

### R6. Скачивание аудио владельцем

- Если для встречи нет явной artifact policy, владелец может скачать готовое
  аудио через server-mediated endpoint без отдельного разрешения.
- Такая default policy не открывает аудио для team/shared viewer; для них
  требуется явная policy.
- Явно сохранённая `disabled` policy остаётся запретом.
- API detail и web/desktop review показывают доступное скачивание только когда
  оно действительно доступно.

### R7. Живые тесты и порядок фаз

- HTTP/API-сценарии размещаются в `tests/integration`, pure workflow checks —
  в `tests/unit`; historical evidence явно помечается `governance`.
- Full lane запускает ordinary, затем governance, затем serial strict RLS;
  optional spike tests исключены из baseline и full lane.
- Test-only код, не имеющий production callers и проверяющий устаревшие
  placeholders, удаляется вместе с тестом.

## Не входит в scope

- удаление PostgreSQL integration/RLS тестов;
- изменение сохранённых artifact policies, схемы или доступа других viewers;
- изменение macOS продукта;
- возврат legacy audio-routing implementation;
- автоматическая публикация релиза.

## Критерии приёмки

- Все DB-зависимые server tests используют общий disposable PostgreSQL
  boundary;
- fast lane проходит без Docker/PostgreSQL;
- focused audio/download suite и полный PostgreSQL lane проходят;
- collection union полного lane совпадает с baseline;
- `ruff`, compile, Compose config и локальный CI проходят;
- cleanup disposable PostgreSQL подтверждён после pass и failure path.
- владелец готовой встречи скачивает аудио без явной policy, а shared viewer
  без policy получает отказ;
- full lane покрывает каждый non-spike node id ровно одной из фаз ordinary,
  governance или strict RLS.
