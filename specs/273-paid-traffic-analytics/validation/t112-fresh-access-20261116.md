# T112 — свежий доступ и выбранный результат

Дата:16.11.2026. Основа:41fdf6c11475819993a3584aa869496034a391e2.
Полоса:существующий high-risk-product F273/T112/T113. Рабочий сбор закрыт.
Это продолжение серверной реализации, не завершение T112 или измерения.

## Реализованный путь

Общий владелец account-транзакции до verifier проверяет active identity,
organization и отсутствие merge; получает AuthSession FOR UPDATE, точные
WorkspaceMembership/Workspace FOR SHARE, все bindings/devices FOR SHARE.
Сессия перечитывается с populate_existing; проверяются user/workspace,
active/expiry, customer workspace, personal owner rule и active membership.
Полный набор связей проверяет прежняя чистая session_device_access.
Допустимый bootstrap без device/links сохранён; session parent защищает также
появление новой binding, а не только существующие строки.

Перед частными device/source чтениями выставляется штатный request tenant
context. Это не обход RLS; отдельная положительная проверка использует
синтетическую роль NOSUPERUSER/NOBYPASSRLS с табличными правами. Она не
доказывает фактические grants рабочей роли.

Проверка expiry добавлена к прежнему T113 guard **внутри владельца транзакции**,
поэтому обе вставки и pre-commit используют один дополненный context.
Его подмена через dataclasses.replace происходит до yield владельца, а не
только у потребителя. При истечении срока новая пара откатывается полностью.

load_fresh_result_view_bindings получает прежний Meeting FOR UPDATE,
проверяет точного владельца и deletion timestamps/state, затем заново вызывает
тот же get_cabinet_meeting_review(storage=None) с разрешённым выбором и
load_result_view_bindings. Helpers с внутренним commit, запись DeletionFence,
полные auth dependencies или сеть не вызываются. Блокировки удерживает общий
admission до своего commit. Ни дата, ни возвращённый binding не открывают T113.

Положительный callback DB-тестов теперь использует этот свежий review и
настоящую HMAC-проверку сохранённого proof. Синтетический период подставляется
только внутренним тестовым context; настоящий _result_period_context
по-прежнему yield None. activation_recovery_unverified и client
trigger_unverified сохранены. HTTP/выдача/обновление proof не подключены.

## Проверки

RED: ранее отозванная AuthSession не мешала внутреннему приёму — assert not True,
1 failed/1 прежний warning/EXIT1. Это действительная проверка нового условия,
не ошибка fixture. Журнал:/private/tmp/graf-t112-access-red-20261116.log.
Первый промежуточный профиль27PASS. Следующий профиль44PASS/1FAIL выявил
неверный тест: менялся только diarization text, который не являлся выбранным
текстом transcript. Тест исправлен на изменение обоих сохранённых текстов;
это не выдаётся за ошибку продукта. Последний профиль описывается ниже.

Новые причинные случаи:

- persisted revoked/replaced/expired session, closed account, inactive/удалённое
  membership, missing/blocked/лишняя binding, revoked/quarantined/unapproved
  device и неправильный personal owner отказывают до частного verifier;
- mutation-first deletion/epoch/source/version/показанный text отвергают старый
  proof при новом review; сохранённая render fixture больше не заменяет его;
- истечение во время пары перед второй вставкой или commit откатывает всё;
- занятые session/workspace/membership/binding/device/Meeting locks отказывают
  за менее1s в тесте при250ms lock_timeout;
- analytics-first: независимые session revoke, новая binding и Meeting deletion
  действительно получают PostgreSQL55P03 при50ms, затем успешно выполняются
  после commit аналитики. Следующий старый показ уже отказывает;
- допустимый empty-binding bootstrap защищён от конкурентной вставки parent
  lock; после завершения вставка succeeds, аналитических строк нет;
- ограниченная тестовая роль сохраняет RLS и успешно проводит пару, без
  maintenance/admin обхода в самом admission.

Регрессии:account-pair, source/projection, прежние ingress/ledger/delivery и
unit funnel/campaign labels. Provider transport запрещён прежней fixture;
рабочие пользователи, содержимое, почта и внешние события не использовались.

Итоговый профиль:**190 passed,1 прежний fixture warning,0 skips,125.96s,EXIT0**;
runner130s. Журнал:/private/tmp/graf-t112-access-final-20261116.log,
SHA-256 `c910894b7061ef69771e7ed95cba35ddb6834309bdb1183a6e4dc8962010dde2`.
Collection190/digest
`8d1957b51fd17f7af82cf159c7f4b3e63838d3fbb1895c2df50146efae1dfcd4`.
Terminal session42619 EXIT0 наблюдался; runner удалил свой isolated container.
Перед тестами165270504KiB свободно, выше80ГБ; backup и архивы не трогались.
Получено [независимое ревью](t112-fresh-verifier-review-20261116.md):
**PASS изолированного шага свежего доступа и повторного чтения результата,
P1=0/P2=0**. Четыре кодовых хеша и окончательный журнал совпали; отчёт прочитан
основным агентом полностью. Границы HTTP/T113 и ограниченной роли сохранены.
Ruff, git diff --check, agent-context и changelog-fragments PASS.
Новый test path добавлен только в игнорируемое ownership .specify/feature.json.

## Требования и предел

Независимый [preflight](t112-fresh-verifier-preflight-20261116.md):124/0,
P1=0/P2=0. Прежние12 requirements/analyze/checklist входов совпали с503805cb;
четыре базовые суммы совпали с T112 design-draft. Применимые ограничения
восстановлены по оригиналам:договор result-visibility, server preflight и
проект, spec Session16.11/FR-021/025, plan T112/T113, tasks, quickstart T112,
research T112, data-model transient proof, конституция II/III/IV/VI/VII,
PRD §23, текущий статус093/094 и product gates. Отметки не изменялись.

Это не приёмка всего fresh verifier: выбранные summary/source query,
публикация новой ревизии/result/слота и все конкурентные source writers
ещё требуют полного HTTP/issuance/renewal профиля. Не приняты общий bounded
body/pool/commit/cleanup и большие проекции, browser/native end-to-end,
runtime T113/restore/local_only/T0, exact-SHA GitHub/merge/выпуск и реальные
визиты/регистрации/оплаты. Требования, задачи и вопросы не закрываются.
Контент/вёрстка, nginx/DNS/Compose, почта/очереди и backup не менялись.

Следующий HTTP шаг должен учитывать порядок зависимостей: штатный
require_web_csrf при form content-type без заголовка сам вызывает request.form
до обработчика. Для proof-only JSON пути нужен ранний отказ чужому media type
до этого form-read, сохраняя сам WebCSRFDependency и его правила. Иначе предел
потокового чтения внутри route не ограничивает более ранний разбор формы.
get_web_owner_tenant_scope отдельно требует device для HTTP; сохранённая
совместимость чистого session bootstrap не является обходом этой зависимости.

## Точный проверенный код

| Путь | SHA-256 |
| --- | --- |
| product_analytics/ingest.py | b718fd0c23c08c1b51cfe2062254c1433b026f4bc68c1f37a2b79b2c5f31095a |
| cabinet/result_visibility.py | b59aa36240282748ed88696e1cfee04710302364ce9df9f2b5fc3315fdedb5e7 |
| tests/contract/test_result_view_admission.py | 543c94a4d67b03c66da39b659947aac9b1aefaf42dfb88e2e100fe212755cf27 |
| tests/contract/test_result_view_access.py | 297252d3f8a4c53156b608393396e8319c8a92293e09bd8ef8c9f2a0ee5228b9 |

Первые два пути относительно server package, остальные относительно apps/server.
