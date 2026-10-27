# Ограниченная доставка T113/T106 — 28.10.2026

Режим: существующий high-risk Spec Kit F273, частичный T113/FR-025 и
T106/FR-048/049. Основа реализации — head PR #7775
`2968b175d13b1d4132178c12ae54e6010731afd2`; он принят обычным squash merge
`fc8fc32f1f48bb677ee3618e8dd9df6384a94164` после трёх обязательных проверок
точных head/base. Это не выпуск, включение или закрытие F273.

## Реализовано

Существующий maintenance worker подбирает не больше20 строк за проход,
делает паузу60с и использует штатные PostHog/Yandex wrappers. Нового сервиса,
брокера, зависимости или пользовательского флага нет. Короткий общий
транзакционный advisory lock сериализует claims одного получателя между
процессами; committed dispatching удерживает слот. Сеть выполняется после
commit и закрытия SQL-сессии, один запрос получателю одновременно.

Нативный асинхронный HTTP с запретом redirects ограничен5с; существующие
синхронные wrappers работают вне основного цикла, через штатный injectable
transport. Перед фактическим транспортом проверяются точные maintenance
login/context/RLS, существование той же строки/provider/attempt и свежие
основания/получатель/отдельная рекламная цель. Неподтверждённая доступность
основания оставляет pending; действительный отзыв отменяет намерение.

HTTP2xx даёт только submitted, без confirmed. После входа в транспорт timeout,
network error и недоказанный non2xx дают ambiguous, без автоматического
повтора. Только доказанный технический сбой до сети допускает pre_send_retry
того же event_id. Неизвестный commit не разрешает транспорт. Отмена ожидания
дожидается ограниченного реального запроса и оставляет dispatching для
карантина; забытый dispatching становится ambiguous, без пересылки.
PostHog получает детерминированный UUID в envelope, Yandex — тот же PurchaseId.
Исходное решение и счёт не меняются, not_requested не заполняется задним числом.

В begin_account_close_finalization ожидающие pending/pre_send_retry/dispatching
обоих получателей отменяются атомарно с закрытием доступа, до асинхронного
удаления содержимого. Другие аккаунты и уже submitted/ambiguous/confirmed
не переписываются. Fresh attempt lookup блокирует отменённое; поздний finish
не воскрешает запись. Уже начавшуюся передачу нельзя объявить отозванной.
Расширения прав RLS и миграции для этого изменения не требуется.

## Проверки и исправления

Before-code reviewer:117 checked/0 unchecked, действующий analyze без
critical/high; `t113-delivery-before-code-2026-10-28.md`.

- V1:58 PASS; первоначальный профиль.
- V2:76 PASS/2 FAIL; wrappers перехватывали PermissionError как OSError,
  теряя доказанную причину отказа. Теперь она сохраняется до вызова wrapper.
- V3:78 PASS после исправления.
- Независимый review дополнительно нашёл: unknown advertising basis ошибочно
  становился окончательным отзывом; provider resolver также использует
  legal_basis_withdrawn для ошибок файла; закрытие аккаунта оставляло окно
  до purge. Исправлены причины, включая атомарную отмену до fanout.
- V4:85 PASS/2 FAIL в новых тестах: попытка изменить immutable payload была
  правильно остановлена SQL-trigger; сбор logger через caplog не соответствовал
  настройке общего test harness. Тесты исправлены через detached corrupt
  snapshot и mock logger, защиты не ослаблены.
- **V5:98 PASS/2 warnings,42.60с; runner46с.** Наборы перекрываются,
  результаты не суммируются. Warnings: pytest plugin rewrite и прежний
  Starlette/httpx deprecation. Временные контейнеры удалены runner.
- Ruff, git diff --check, governance и changelog-fragments PASS.

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/contract/test_activation_milestone_delivery.py \
  tests/contract/test_activation_milestone_ledger.py \
  tests/contract/test_activation_milestone_ingress.py \
  tests/unit/test_maintenance_worker.py tests/unit/test_account_closure.py \
  tests/unit/test_product_analytics_posthog_provider.py \
  tests/unit/test_product_analytics_yandex_offline_provider.py -q
```

Collection98; digest `c8b2829b4449ad9b8005c320ac69cdd83bd040edcb8fd17c4de05982cc80345a`.
Игнорируемый журнал `t113-delivery-focused-v5-20261028.log`:
SHA-256 `38a9937774bbed6919c2ba3694bafdada83d583fc01cbd3ea61def154772a981`.

Покрыты20+3 строки, разные процессы/строки/один provider slot, отсутствие
SQL-lock во время ожидания HTTP, действительный5с timeout и доступность
цикла другим задачам, commit faults до/после claim и после remote accept,
отмена ожидания, stale quarantine, unsafe snapshot, recovery_unverified,
две независимые доставки, secret failure с безопасным retry, свежие
withdrawn/unknown после приготовления запроса. Настоящие app/superuser/
BYPASSRLS/bogus context отклонены; настоящий maintenance login разрешён.
Отдельно под настоящей maintenance ролью проверен begin-close commit без
fanout/purge: оба intents cancelled, другой аккаунт pending, повтор begin
безопасен, поздний finish false, транспорт не вызван.

Только тестовый процесс подставляет операционные receipts; рабочего обхода
нет. Внешние providers, приватные записи, Dev app, рабочие данные не менялись.

## Converge и остатки

Сверены7 требований FR-021/025/026/048/049/050 и SC-006, delivery states,
порядок plan, ограничения20/1/5/60, независимость продукта, защита данных,
хранение/отзыв/удаление. Открытые обязательства уже имеют владельцев:

| Остаток | Задача |
|---|---|
| Точное readback подтверждение, без признания2xx за confirmed | T113 |
| GRAF DB recovery verifier, полный ledger и пропуск после точки копии | T110/T113 |
| Видимый готовый результат владельца, браузерная и desktop ветви | T112 |
| Остальные side-effect writers после отзыва основания | T106 |
| Рабочие backup/restore/retention/inventory/readiness receipts | T109/T110/T116/T118 |

Нового непокрытого исполнимого обязательства нет, дубли задач не добавлены.
`tasks.md` оставлен прежним: это scoped partial convergence, не полное
converged F273. Независимый implementation review записывается отдельно в
`t113-delivery-implementation-review-2026-10-28.md`.

Свежий публичный catalog в22:13:28UTC27.10 (28.10 местного времени):
enabled=false, validation_mode=disabled, provider_mode=disabled,
rollout_verdict=blocked. Неизменённый activation_recovery_unverified
безусловно запрещает новый writer. Для этого участка ещё нужны собственный
PR, точные GitHub проверки, merge и штатный общий выпуск; для включения —
реальные операционные свидетельства. Трафик, продажи, AC01–AC06 не приняты.
