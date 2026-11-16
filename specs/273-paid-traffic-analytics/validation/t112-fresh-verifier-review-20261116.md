# T112 — независимое ревью свежего доступа и выбранного результата

Дата: 16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Основа: `41fdf6c11475819993a3584aa869496034a391e2`.
Полоса: существующая `high-risk-product`, изолированный шаг F273/T112.

## Решение

**PASS изолированного шага свежего серверного доступа и повторного чтения
результата; P1=0, P2=0.** Блокирующих замечаний к рассмотренному изменению
не найдено. Это не завершение T112/T113, не разрешение рабочего сбора,
не принятие T0 и не подтверждение трафика или продаж.

Независимо прочитаны изменения двух файлов приложения, оба файла тестов,
связанные чистые проверки сессии, регистрация устройства и применимые
PostgreSQL RLS policies. Повторно проверены точные SHA-256 изменённых
источников. Прежние требования и ограничения взяты из уже принятого
`t112-fresh-verifier-preflight-20261116.md`; оснований менять его решение
124 отмечено / 0 не отмечено нет. Эти отметки относятся к качеству требований.
Проверяющий не менял списки, требования, задачи, код, Git/GitHub или runtime,
не запускал тесты и не проводил внешних действий.

## Проверенный порядок и границы транзакции

1. Общий владелец `_account_transaction` получает внутренний period context,
   проверяет его тип, дату и guard. Настоящий `_result_period_context` по-прежнему
   возвращает `None`, поэтому тестовые подстановки не включают рабочий путь.
2. После штатного `auth_bootstrap` перечитывается active UserIdentity с точным
   user/organization и `merged_into_user_id IS NULL`, удерживается `FOR SHARE`.
3. Для `require_period` точная AuthSession перечитывается с
   `populate_existing=True` под `FOR UPDATE`. Проверены principal, workspace,
   membership в principal, configured customer workspace, active status и expiry.
4. Точные WorkspaceMembership и Workspace перечитываются под `FOR SHARE`.
   Проверены активное участие, organization, а для personal — текущий владелец
   и роль owner. Владелец встречи не заменяет эту проверку членства.
5. До чтения устройств и содержимого применяется штатный request context с
   organization/workspace/user/session/device. Связи и устройства читаются
   заново, упорядочены по ID, удерживаются `FOR SHARE`; используется чистая
   `session_device_access`. Результат обязан совпасть с device principal.
6. `load_fresh_result_view_bindings` получает Meeting `FOR UPDATE`, проверяет
   точное владение и deletion state/timestamps, затем вызывает общий
   `get_cabinet_meeting_review(storage=None)` и `load_result_view_bindings`.
   Выбор summary/source передаётся в тот же общий reader.
7. Пара событий и единственный commit остаются у общего владельца. Новый helper
   не делает commit/rollback, не выдаёт readiness, не запускает auth renewal,
   workflow, export, storage probe или внешний транспорт.

AuthSession `FOR UPDATE` защищает также отсутствие device bindings: INSERT
новой связи с FK к этой session конфликтует с parent lock. Shared locks лишь
найденных связей такой защиты не обеспечили бы. Существующий допустимый API
bootstrap без device и без связей сохранён; он не открывает аналитическую
пару без остальных условий.

Порядок аналитики не доказывает глобальное отсутствие взаимных ожиданий всех
старых writers. Прежние account-merge/reconciliation пути могут брать locks
иначе. Сохранены закрытый отказ без retry, `lock_timeout=250ms`,
`statement_timeout=500ms`, внутренний бюджет 1.5s и внешний 2s. Приёмка полного
бюджета HTTP/body/pool/commit/cleanup остаётся следующим отдельным шагом.

## Свежесть, proof и срок сессии

Свежий reader запускается после Meeting lock. Прежний список или сохранённый
объект review не используется как доказательство текущего текста: callback
тестов сохраняет только meeting ID и proof, заново получает bindings и
выполняет настоящую `verify_result_view_proof` с HMAC. Сам
`load_fresh_result_view_bindings` HMAC не проверяет; это обязанность доверенного
callback будущего HTTP-пути. Текущий callback не передаётся клиентом.

Общие source/result/outcome/slot проверки и защита Meeting сохраняются по
предыдущему writer-fences review. В текущем профиле причинно проверены
предшествующие изменения deletion/epoch/source/version/текста. Проверки всех
конкурентных публикаций revision/result/summary slot и всех селекторов HTTP
не подменяются этими пятью случаями.

Блокировка строки сессии не останавливает часы. Новая композиция guard
выполнена **до yield внутри владельца**: прежний T113 recheck вызывается первым,
затем заново проверяется expiry свежей заблокированной session. Один
дополненный context используется обеими вставками через `before_insert`
и проверкой непосредственно перед commit. Предупреждение preflight о замене
лишь локального context потребителя устранено. Тесты истечения перед второй
вставкой и перед commit проверяют полный rollback новой пары.

Обычный `ingest_authenticated`, работающий без `require_period`, не получает
новые требования session/device этого шага. Старые client
`trigger_unverified`, runtime absence и legal/recovery blockers сохранены.
В рассмотренном diff нет включения HTTP, выдачи или обновления proof.

## PostgreSQL RLS: что подтверждено

Прочитаны действующие политики `0005_rls_hardening`,
`0027_workspace_account_onboarding`, `0028_active_workspace_membership_read`,
`0076_account_linking_rls`, `0077_provider_unlink_cross_workspace`,
`0102_summary_sharing` и `0106_activation_milestones` в применимой части.

- `auth_bootstrap` разрешает чтение и блокировку identity/session, точного
  membership и workspace; operation policy identity предусматривает UPDATE
  USING также для строковой блокировки без изменения профиля.
- `registered_devices` в обычном пути требует request context. Его применение
  до чтения devices/bindings необходимо и в рассматриваемом коде выполнено.
- Политика bindings проверяет session и device parents текущего user/workspace;
  device parent также ограничен RLS. Переход `auth_bootstrap → request` является
  применением штатного контекста, а не maintenance обходом.
- Положительный тест действительно выполняет admission после `SET LOCAL ROLE`
  в роль `NOLOGIN NOSUPERUSER NOBYPASSRLS` и проверяет current_user/атрибуты роли.
  Это полезное доказательство исполнения обычных RLS predicates. Штатный
  maintenance helper не даёт этой роли обход в данном request-контексте.

Предел: этот тест не использует отдельный production login и не доказывает
фактические grants рабочей роли, отрицательную межтенантную изоляцию либо все
варианты отсутствующих/чужих parents. Некорректная связь с чужим устройством
может быть скрыта RLS, поэтому формулировка «все связи» означает все доступные
по штатной модели user/workspace, а не обход RLS для аудита повреждённых строк.
Поддерживаемый путь регистрации блокирует session, проверяет принадлежность
устройства и не создаёт такую чужую связь; конкретного допустимого writer,
обходящего этот инвариант, в рассмотренных источниках не найдено. Это не
самостоятельное доказательство очистки произвольной повреждённой БД и не
основание выдавать текущий positive test за полную RLS-приёмку T112.

## Итоговые проверки и их предел

Проверяющий самостоятельно прочитал завершённый журнал:
`/private/tmp/graf-t112-access-final-20261116.log`.
В нём: **190 passed, 1 warning, 125.96s**, runner status/result pass,
cleanup isolated container removed. SHA-256:
`c910894b7061ef69771e7ed95cba35ddb6834309bdb1183a6e4dc8962010dde2`.

Терминальный `session42619 EXIT0` и collection digest подтверждены основным
агентом в `t112-fresh-access-20261116.md`; только после появления этого
подтверждения итоговый профиль принят в настоящем отчёте. Проверяющий сам
терминальную сессию и тесты не запускал. Ruff, diff, agent-context и fragments
заявлены основным агентом; независимо повторно не выполнялись.

Новые тесты покрывают persisted revoke/expiry/membership/device/account,
свежую замену source/body, время между вставками/commit, занятые шесть locks,
parent FK phantom и три analytics-first конфликтующих writer. Прежние
account-pair/ingress/ledger/delivery и source/projection тесты дают регрессию.
Они не доказывают все поддерживаемые production writers или реальный
browser/native показ. Тест текста исправлен после выявления ошибки fixture:
раньше менялся не выбранный текст, теперь оба текстовых источника. Прежний
44 PASS / 1 FAIL не выдаётся за продуктовую ошибку или окончательный результат.

До полного T112/T113 остаются HTTP issuance/renewal/CSRF и selectors,
проверка фактического показа, большой проекции и общего ограниченного бюджета,
runtime readiness/restore/local_only, T0, exact-SHA CI/merge/release и рабочая
приёмка. Внешние события, визиты, регистрации и оплаты здесь не создавались.
T112/T113 и продуктовая цель не закрываются.

## Точные источники

Пути относительно `apps/server/`.

| Путь | SHA-256 |
| --- | --- |
| `src/twobrain_rec_server/product_analytics/ingest.py` | `b718fd0c23c08c1b51cfe2062254c1433b026f4bc68c1f37a2b79b2c5f31095a` |
| `src/twobrain_rec_server/cabinet/result_visibility.py` | `b59aa36240282748ed88696e1cfee04710302364ce9df9f2b5fc3315fdedb5e7` |
| `tests/contract/test_result_view_admission.py` | `543c94a4d67b03c66da39b659947aac9b1aefaf42dfb88e2e100fe212755cf27` |
| `tests/contract/test_result_view_access.py` | `297252d3f8a4c53156b608393396e8319c8a92293e09bd8ef8c9f2a0ee5228b9` |
