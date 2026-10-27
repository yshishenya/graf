# Общий авторизованный приём T113 — 28.10.2026

Lane: active high-risk Spec Kit slice F273, продолжение T113/FR-025 и T106/FR-048/049,
узкая часть T112/FR-021. Основа: merged PR #7774,
`4604cb2a616374903773a200330e8606deae59c1`. Ветка `codex/273-activation-ingress`.
Это промежуточная реализация, не закрытие T113 или всей F273.

## Результат

Оба прежних HTTP-формата (`/events`, `/posthog-desktop-capture`) и background
server-auth используют один `ingest_authenticated`. Аккаунт выбирает только
существующий проверенный principal/завершённая серверная авторизация; тело
запроса не может выбрать другого владельца. Существующая сессия БД создаётся
отдельно от транзакции входа, получает точный tenant context и фиксирует
решение только успешным commit. Повтор возвращает первоначальный snapshot
вместо замены кампании/времени. Нет счёта в памяти, provider dispatch или
резервной отправки при сбое БД. Прежний синхронный метод лишь проверяет форму
и возвращает `trusted_context_required`, без принятия или транспорта.

Серверный desktop-вход передаёт собственную фабрику сессий и проверенные
organization/workspace/user; обычный браузерный вход не создаёт desktop-веху.
Первый запуск без доверенного install key и клиентские result/value события
не принимаются. Точный видимый owner/ready/result-триггер T112 ещё предстоит.

Приложение переносит прежние auth headers в desktop-прокси только после
сравнения scheme/host/effective port, точного пути и запрета userinfo/query/
fragment. Конструктор origin сохраняет явный порт. Нового login или секрета нет.
Swift содержит положительный и отрицательные проверки адресов; локальный
native build/app/dev-harness не запускались. Исполнение этих проверок требуется
от отдельного GitHub `macos-pr` на окончательном SHA.

## Свежие основания и намерения

Новый writer требует текущие включение/основание/раскрытие, читаемый реестр без
ошибок, отсутствие отзыва уровня2 и operations readiness. Реестр сообщает
ошибку непригодной/повторной распознанной записи. Общий paid-campaign bool не
используется как право локальной записи. До GRAF DB recovery verifier всегда
остаётся `activation_recovery_unverified`: успешный PostHog receipt не может
разрешить запись новой relation, в том числе отсутствующей после старой копии.

После ожидания account lock и прямо перед INSERT вызывается узкий callback:
он перечитывает writer gate и заново вычисляет разрешённые provider intents.
Yandex дополнительно требует текущую `transfer_decision(event)` существующего
exporter, без сетевой передачи. Отзыв только рекламной цели не удаляет
допустимую локальную веху и не создаёт Yandex pending. `accepted_at` берётся
после ожидания. Не запрошенные при admission получатели не получают скрытый
backfill после последующего включения.

## Проверки

До кода независимый requirements gate:117/0, применимость analyze0 critical/
high/medium; отчёт `t113-ingress-before-code-2026-10-28.md`. Связи T112/T113
с #7698, T106 с #7696 и umbrella #7185 проверены; issues остаются открытыми.

Команда основного профиля:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/contract/test_activation_milestone_ingress.py \
  tests/contract/test_product_analytics_registration_handoff_contract.py \
  tests/unit/test_product_analytics_milestone_dedupe.py \
  tests/unit/test_product_analytics_conversion_campaign_labels.py \
  tests/unit/test_product_analytics_activation_funnel.py \
  tests/integration/test_product_activation_analytics_rollout.py \
  tests/unit/test_product_analytics_legal_basis_lifecycle.py \
  tests/contract/test_activation_milestone_ledger.py -q
```

- Первый прогон:2 FAIL/88 PASS — тестовые строки использовали неверный префикс
  withdrawal вместо установленного basis_withdrawal. Исправлены сами строки.
- Повтор:107 PASS/2 warnings,24.14с, runner28с.
- Отдельно после расширения try вокруг server-auth builder:22 PASS/2 warnings,
 10.65с, runner14с. Наборы пересекаются, числа не суммируются.
- Независимый review v1 нашёл R1/P1 (credentials на иной endpoint) и R2/P2
  (устаревший gate при ожидании lock). Оба исправлены до PR.
- Полный профиль исправлений: **110 PASS/2 warnings,24.58с, runner29с**.
  В том числе настоящее ожидание PostgreSQL `Lock` в двух очередностях отзыва:
  уровня2 и только рекламной цели. Отзыв уровня2 не оставляет решения;
  отдельный рекламный отзыв оставляет локальное решение без соответствующей очереди.
- После переноса accepted_at за lock: **12 PASS/2 warnings,5.49с, runner9с**,
  весь новый ingress файл, включая проверку времени относительно освобождения lock.
- Все временные контейнеры runner удалил. Warnings: загрузка pytest plugin и
  устаревающий Starlette/httpx. Ruff, governance, fragment validator и diff check PASS.

Успехи включают конкурентные соединения, оба HTTP-формата, настоящий server-auth,
неподтверждённые triggers, чужой псевдоним, отсутствие principal, отказ commit,
неизвестный/отозванный реестр. Provider dispatch/capture в тесте заменены
AssertionError: неожиданная сеть нарушила бы прогон. Только в тестовом процессе
подставлены операционные свидетельства; рабочего флага для обхода нет.

Журналы остаются в игнорируемом `.dev/growth/`, в Git только отчёт и хеши:

| Журнал | SHA-256 |
|---|---|
| t113-ingress-focused-20261028.log | 0e706c2b77197572011c2291f19a431ad887b7faf0aec0ad4cd1368226c38735 |
| t113-ingress-focused-v2-20261028.log | baac86947e2a0e4bda3639eadb83eb3d3c344559cdd9b4d086b909613f8e936b |
| t113-ingress-auth-final-20261028.log | 164df086a46f562e39acf31a3783807204bc95bad8e7ac32ac11cf14a84eea74 |
| t113-ingress-review-fixes-20261028.log | d1283d9fd6d06883254ea2466c132da9a7229885ca020192972f51b66267cdea |
| t113-ingress-lock-final-20261028.log | 7b5a271e0fe946f6c6cf2414cd61a84bdf5292c5e1b639effbcfe2ec5e17d7f8 |

## Converge текущего участка

Сверены FR-021/025/026/048/049/050, SC-006/007/011, контракт T113, порядок plan
и открытые T106/T110/T112/T113/T116/T118. Текущий участок частичный:

| Остаток | Уже назначен |
|---|---|
| Ограниченный maintenance dispatcher, транспортная неопределённость и provider readback | T113 |
| GRAF DB recovery verifier, сверка пропуска/удаления после restore | T110/T113 |
| Свежие основания непосредственно перед каждым внешним side effect | T106/T113 |
| Видимое открытие владельцем непустого нового готового результата | T112 |
| Рабочие backup/retention/inventory/restore/provider свидетельства | T109/T110/T116/T118 |

Нового непокрытого обязательного действия не найдено; дубли задач не добавлены,
`tasks.md` оставлен побайтно прежним. Это scoped convergence с известным
открытым остатком, не утверждение полного converged всей F273.

## Рабочий результат и границы

Публичный catalog прочитан 27.10.2026 в21:43:48UTC (28.10 местного времени):
enabled=false, validation_mode=disabled, provider_mode=disabled, verdict=blocked.
Штатного выпуска/выкладки текущего среза нет; аналитика/IP и провайдеры не включены.
Реальные source→activation→payment, трафик, 3 клиента и AC01–AC06 не приняты.
Основной план: `docs/growth/organic-growth-plan.md`.

До слияния нужны повторное независимое ревью и обязательные GitHub проверки
на точных SHA/base. Перед рабочим включением — следующий код, общий замороженный
кандидат, единственный release-full, dry-run, выпуск и отдельная приёмка.
Новых внешних публикаций/писем или изменений рабочих данных нет.
