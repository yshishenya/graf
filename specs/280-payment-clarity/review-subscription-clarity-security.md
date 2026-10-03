# F280 US4 — независимая итоговая проверка финансовой безопасности

Дата: 2026-10-04, Europe/Istanbul. Проверка завершена по рабочим файлам ветки
`codex/280-subscription-clarity`; базовый коммит и текущий HEAD:
`a7553db61b2625e767b3afa147c7b61c097fe918`.

**Readiness: PASS в пределах финансовой безопасности US4.** Применимых
незакрытых замечаний: Critical 0, High 0, Medium 0, Low 0. Это заключение по
проверенному рабочему diff, а не разрешение выпуска или подтверждение реальной
банковской/периодической оплаты. Требования выпуска остаются открытыми.

Проверяющий не автор реализации. Проверка — read-only investigation активного
Spec Kit среза `high-risk-product`; единственное изменение в репозитории со
стороны проверяющего — этот отчёт. Код, тесты, спецификация, план, задачи,
чеклисты, GitHub, git, выпуск и внешнее состояние не изменялись.

## Источники и границы

Прочитаны фактические FR-039–045 и приёмка US4 в `spec.md:327`, раздел US4
`plan.md:237`, контракт `contracts/payment-journey.md:122`, текущие задачи и
проверки US4 в `quickstart.md:233`. Использованы `AGENTS.md`, индекс guidance,
`spec-kit-flow.md`, применимые правила `product-gates.md` и
`release-and-validation.md`, конституция (§II/VI/VII), продуктовая база и
текущий статус продукта. Старые записи статуса продукта не принимаются за
доказательство выпуска этого diff. Применён навык `code-reviewer`.

Проверены diff относительно указанной базы, фактические обработчики и их
зависимости, шаблон, CSS, изменённые контрактные/браузерные/интеграционные тесты,
существующие отрицательные проверки финансовых ограничений и настоящие журналы
синтетических запусков. Утверждения автора сами по себе доказательством не были.

В runtime изменены только:

- `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`;
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html`;
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

Нет изменений финансовых модулей, моделей, миграций, API, JavaScript приложения,
провайдера, цен или штатных финансовых наборов состояний. CSS добавляет только
три правила для ширины и отступов страницы подписки (`cabinet.css:5417`).

## Проверенные финансовые и защитные свойства

| Свойство | Фактическое доказательство |
|---|---|
| Денежные обработчики сохранены | Сравнение синтаксического дерева и исходного текста всех функций `billing.py` с базой: изменена только `billing_subscription_page`; остальные 84 функции совпадают, включая тела, параметры и финансовые проверки. `cancel_billing_subscription:3197`, `resume_billing_subscription:3270`, `start_billing_checkout:3752`, `continue_billing_checkout:2324`, `preview_early_renewal:4703`, `_billing_owner_subscription:3161`, `_resume_renewal_snapshot:5318` неизменны. |
| Новый поиск ограничен пространством пользователя | В `billing.py:2820` используется JOIN по `operation_id` и условие `BillingInvoice.workspace_id == tenant_scope.workspace_id`. Удалён только фильтр вида операции; условие пространства сохранено. Скомпилированный реальный SQL проверен изолированным вызовом без БД. Штатная RLS для финансовых таблиц в `0044_user_account_billing.py:52` сохраняет ограничение `workspace_id = rec_current_workspace_id()`. |
| Отсутствие subscription не обходит авторизацию | `_billing_role:1197` проверяет активное членство, личное пространство и его неизменяемого владельца; `_can_manage_billing:1225` требует owner, а при наличии подписки — совпадения billing owner. Эти функции и зависимости Principal/WebTenant не изменены. Проверка в `billing_subscription_page:2764` выполняется до нового чтения invoices. Изолированно подтверждены owner без подписки и отказ member, отсутствующему участнику, неверному неизменяемому владельцу и корпоративному владельцу; при отказе `execute` не вызывается. |
| Ожидающие платежи всех видов видны также без подписки | Новый блок начинается с `if db is not None` (`billing.py:2820`), поэтому не зависит от существования subscription. В запросе нет ограничения kind: `initial_checkout`, `storage_upgrade`, `renewal`, `early_renewal` читаются одним способом. Настоящий окончательный PostgreSQL журнал подтверждает оба варианта наличия подписки для этих видов и состояний provider pending/key expired. |
| Истечение ключа расширяет только чтение страницы | `CHECKOUT_BLOCKING_STATES | {"provider_key_expired"}` вычисляется локально в `billing.py:2826`; исходный `frozenset` в `billing/operations.py:23` не меняется. Общие денежные проверки и `blocks_new_checkout` неизменны. |
| Прежняя политика initial checkout сохранена | `INITIAL_CHECKOUT_OBSERVATION_EXPIRED == "observation_expired"` (`billing/operations.py:40`) не добавлен в запрос и не добавлен в финансовый блокирующий набор. Два окончательных PostgreSQL сценария с/без subscription подтверждают доступность GET оформления и отсутствие ссылки проверки этого старого наблюдения. Готовая страница может связать прежний не денежный resume quote. Состояния `succeeded`, `canceled`, `failed` также не входят в новый запрос; прежние terminal/retry ограничения обработчиков остаются прежними. |
| Подготовленное продление остаётся отдельным | В `billing.py:2831` только renewal + scheduled + `provider_id is None` даёт prepared amount и не устанавливает pending invoice. Отправленное scheduled или иной kind попадает в pending. Шаблон показывает prepared пояснение только без настоящего pending (`billing_subscription_content.html:29`); существующая досрочная проверка и прямая отмена доступны при прежних условиях. Контрактный тест `test_subscription_prepared_renewal_keeps_early_preview_and_direct_cancel` сохранён и прошёл. |
| Pending имеет приоритет над новым оформлением | Шаблон вычисляет `payment_unresolved` по URL, сумме либо resolution (`:16`), а не по одной сумме. Ветка pending (`:23`) предшествует `renewal_notice` (`:26`): даже notice `receipt_contact_required` с checkout href не предлагает конкурирующую оплату. Manual GET (`:40`, `:45`), resume (`:54`) и early-preview (`:60`) требуют `not payment_unresolved`. Изолированные проверки настоящего шаблона подтверждают это без суммы, в том числе без subscription и при каждой из четырёх неопределённых resolution. |
| Лишний quote при неопределённом результате не создаётся | В `billing.py:2845` требуется `pending_invoice is None`, затем исключаются `pending`, `unknown`, `unknown_pending`, `provider_key_expired`, `receipt_contact_required` (`:2846`). Это защита уже существовавшего GET создания quote, без изменения денежного POST. Окончательные 18 PostgreSQL сценариев подтверждают отсутствие даже quote при найденном pending invoice; изолированные вызовы подтверждают отсутствие quote/commit при каждой из четырёх resolution без invoice. Положительный ready вызов по-прежнему связывает один quote. Прежние правила подготовки snapshot сохранены. |
| Отмена доступна непосредственно и в прежних пределах | Форма cancel (`billing_subscription_content.html:49`) по-прежнему требует subscription + recurring_allowed + paid_through. Она не зависит от active, pending, карты или выключателя checkout и находится вне details. `csrf_token` и `expected_authority_version` сохранены. Это прежняя область допустимости отмены, включая истёкший срок с отправленным платежом; нельзя толковать её как безусловное разрешение чужому пользователю. POST проверяет сессию, owner/tenant, блокировку строки и authority version как раньше. Он отменяет только ещё не отправленные renewals и не объявляет возврат либо отмену отправленного платежа. |
| Согласие на восстановление остаётся явным | Resume находится на одном уровне native details (`:55`), сумма/точная попытка/карта показаны перед формой. Скрытые CSRF/version/quote и required checkbox `resume_consent` без checked сохранены (`:57`). POST повторно проверяет auth session, личного owner, доступность checkout, версию, верифицированную карту и связанный неизменяемый quote/snapshot. Истечение, другой owner/workspace/purpose, изменившаяся цена и уже использованный quote не становятся допустимыми из-за раскрытия формы. |
| Эффективный тариф и время правдивы | `billing.py:2768` использует неизменённый `effective_plan_code` из `billing/entitlements.py:53`; active означает действительный personal, trial использует trial cutoff, истёкший personal становится free. Короткие даты используют существующий `local_datetime` (`billing.py:2883`), полные — `_billing_datetime_label` с локальным временем/UTC offset. Точный оплаченный и пробный срок доступны в одном native details (`template:68`, `:70`, `:71`). Тест перехода 23:30 UTC → следующий день 02:30 UTC+03 проверяет paid и trial. |

Существующие actor/owner/tenant/session/CSRF/version/quote/consent/catalog-price/
offer/idempotency/provider проверки не удалены и не ослаблены. Ссылка
«Продлить подписку» остаётся GET с текущим month/year и сама не включает
продление. История и помощь остаются доступны. Поля, согласия и денежные
проверки досрочного preview/confirm сохранены; ошибка preview раскрывает
прежнюю форму.

Чтение страницы при неопределённом результате не создаёт operation, invoice,
entitlement grant и не меняет их статусы; провайдер не вызывается. Возможность
создать существующий не денежный resume quote в готовом состоянии сохраняется.
Это не обещание, что GET вообще никогда не делает commit: прежняя ветка
связывания quote делает commit, когда условия её допускают.

## Фактические результаты проверок

Журналы находятся вне git. Ниже приведены только их имена, без абсолютных или
частных путей. Прохождение не выводилось из имени файла `green`.

| Журнал | Что фактически зафиксировано | Граница доказательства |
|---|---|---|
| `graf-f280-subscription-focused-green.log` | **95 passed**, 2 warnings, 0.79 s | Завершённый предоставленный focused запуск. Проверен фактический итог; журнал не записывает точный source fingerprint или полный список node IDs. |
| `graf-f280-subscription-route-final-green.log` | **18 passed**, 125 deselected, 2 warnings, 63.06 s; `postgres_test_result=pass`; одноразовый контейнер удалён | Финальный предоставленный запуск для invoice всех четырёх видов, с/без subscription, provider_pending/provider_key_expired и двух legacy observation_expired случаев. Проверяет новую защиту quote по найденному invoice. |
| `graf-f280-subscription-postgres-green.log` | **229 passed, 8 failed**, 2 warnings, 526.21 s; phase status fail; контейнер удалён | Предоставленный общий запуск до последней защиты quote. Все восемь отказов — варианты has_subscription=True × четыре kind × два pending state. Снимки менялись с `[3, 3, 2, 0]` на `[3, 3, 2, 1]`: лишний quote; operation/invoice/grant counts и состояния прежние. Этот журнал нельзя называть полным PASS текущего кода. Последующий финальный запуск 18 случаев проверяет исправление этих восьми сценариев. |
| `graf-f280-subscription-review-negative-controls.log` | **54 passed**, 2 warnings, 2.95 s | Независимый запуск текущих `test_billing_security.py`, `test_billing_safety_contract.py`, `test_subscription_controls.py`, `test_billing_trust_boundaries.py`, `test_billing_entitlements.py`; синтетические проверки без настоящей оплаты. |
| `graf-f280-subscription-review-isolation.log` | **10 synthetic probes passed** | Независимые вызовы реального GET с заглушками: SQL workspace/state/kind scope; owner без подписки; четыре отказа до чтения; четыре resolution без invoice; quote/commit только в положительном ready случае. Нет БД/сети. Это структурная и динамическая проверка маршрута, не новый PostgreSQL RLS запуск. |
| `graf-f280-subscription-review-pending-priority.log` | **6 real-template synthetic probes passed** | Настоящий шаблон при pending без суммы перекрывает checkout URL внутри receipt notice, manual GET, early и resume. Включены invoice, отсутствие subscription и четыре resolution. Нет POST/БД/сети. |
| `graf-f280-subscription-review-resolution-final.log` | Собраны **4** текущих resolution случая; Docker Engine unavailable; контейнер не запускался | Дополнительный PostgreSQL запуск не состоялся. Ни pass, ни failure самих четырёх тестов не заявляются. Их guard проверен выше заглушками; исполнение на PostgreSQL остаётся дополнительным неподтверждённым доказательством. |

Существующие отрицательные тесты не удалены: diff UI/браузерных/интеграционных
файлов добавляет сценарии; в accessibility fixture изменён перечень страниц и
timeout, без удаления прежних ограничений. Прочитаны настоящие проверки:

- `test_billing_security.py:44`: обязательный CSRF всех mutation routes;
  `:79` — другой persisted actor не доходит до provider;
  `:101` — общий personal-owner gate.
- `test_subscription_controls.py:13`, `:26`: stale authority version и resume
  после cutoff запрещены. Они прошли в независимом наборе 54 тестов.
- `test_billing_entitlements.py:314`: точное True в неизменяемом согласии,
  другая billing authority и другой owner не дают сохранение карты/продления.
  Эти отрицательные варианты прошли в том же запуске.
- `test_billing_purchase_quotes.py:18`: другой owner/workspace/purpose,
  истечение, изменение денежного snapshot и application version отклоняются;
  `test_billing_purchase_journey.py:510`, `:627`: неопределённую оплату нельзя
  отправить снова, истёкший quote/изменившийся каталог не доходит до провайдера.
- `test_billing_return.py:452`, `:514`: отмена истёкшей подписки с pending
  требует прежний CSRF/version/owner и сохраняет отправленный платёж;
  `test_billing_review_regressions.py:707`: закрытая область checkout либо
  исчерпанные попытки не разрешают resume старым quote.
- `test_billing_rls.py:189`: настоящая роль приложения не видит и не изменяет
  финансовые строки другого пространства или без контекста. Этот тест
  прочитан; новый запуск настоящего RLS в рамках данного обзора не заявляется.

Предоставленные журналы без полного списка node IDs не позволяют приписывать
прохождение каждому отдельно прочитанному интеграционному тесту. Их сохранность
и неизменность соответствующих обработчиков проверены непосредственно.

## Отпечатки проверенного состояния

SHA-256 полного `git diff` только source/tests относительно базы:
`8c549c0d2e2427e93ecda6976730d0e1d41748fbc7363d80bad5e692d93c132c`.
Отпечатки относятся к рабочим файлам, а не к новому коммиту; после изменения
проверенной реализации это заключение следует пересмотреть.

| Файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `b199d977373883be3a94c5d395387c219beed1eebbdd3931921188bfdcced666` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `3fa4aa82bbe3362e3f3688a44c19fda0467656cf72eed11b3f1f868dd33c2d13` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` | `77ee7e8297b2c9c4696e115f1d7729b70380079eb26bf0a23df897718f5f2247` |
| `apps/server/tests/integration/test_billing_review_regressions.py` | `1e0833ca58e0a6cc4597601f751bc469861d62657e5c222e5bead8f4cb875b2f` |
| `apps/server/tests/contract/test_billing_ui.py` | `14b17920fbae54d05f14d4ce1b8d9a76b9e608941f65c29ee9e701978845b723` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `559a0c7590593015ac3e75e2b4784e0b66601d6df9e29aa2fdd248b408e9dfef` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `4a76c35e0d838a4255778c01ac322f104cf3688cd3037bca8620cb81e0220a85` |
| `spec.md` | `948c14f89d63059de5e91499c01b882b74a27167fdb6344515b93c090fd14a11` |
| `plan.md` | `c2ca366c4373fe26e087eabf3c74a7010fdc60ce9427bd6900d98dd6d589723f` |
| `contracts/payment-journey.md` | `60c7adefaec2720de6fe7e5b2855c78c3ff5cbcded0de158a5aae251d43ec800` |

| Журнал | SHA-256 |
|---|---|
| `graf-f280-subscription-focused-green.log` | `e71f131c6a702cd5df6dfe97ae25b0332ab30e0515f22fcb75eedd7aecaad9d9` |
| `graf-f280-subscription-route-final-green.log` | `fdbd06de28cefea8d7f07fcda5b659979c171dad5af4e4b9352755b619995855` |
| `graf-f280-subscription-postgres-green.log` | `a6480faea916b43c4ecea490d7d7faf24e99825cf397b77d9748cca8acdf476c` |
| `graf-f280-subscription-review-negative-controls.log` | `b160cfb1beec4b8629b7da47145d85581a88039d97f43f953e7fce709c098143` |
| `graf-f280-subscription-review-isolation.log` | `160eb450d015db2a29f196b556ee97146f85e026717683c9d2501e44f8ef6a45` |
| `graf-f280-subscription-review-pending-priority.log` | `effef7f9510bd623d2314ea2267e777aa74a97a411d15acdcb9d33150bd5f5bd` |
| `graf-f280-subscription-review-resolution-final.log` | `af5190720e49c65d2313368d37d2c369f99ed0e405c2ea5597e6750076bb459e` |

## Оставшиеся требования и предел заключения

Применимых исправлений финансового кода по итогам обзора нет. Новый PostgreSQL
запуск четырёх resolution без invoice не выполнен из-за среды; общий журнал
237 случаев остаётся красным историческим запуском, с устранённой причиной
восемью последующими окончательными сценариями, а не полным текущим PASS.
Это ограничения доказательств, не скрытые результаты тестов.

Текущий рабочий diff ещё требует остальных независимых обзоров/convergence,
обязательных `governance-fast`, `macos-pr`, `pr-metadata` на точном PR SHA и
проверенной базе, затем `release-full` на замороженном кандидате и штатных
требований GO/CD/публикации/runtime evidence. Их выполнение этот отчёт не
подтверждает и не заменяет.

Безопасные синтетические проверки не подтверждают реальное банковское
зачисление, настоящее автосписание, работу сохранённой карты в банке,
финансовую/юридическую приёмку F278, SC-005/006 или T011/T012. Реальные
платежи, списания, возвраты, grants, производственные изменения и обращения
к настоящему платёжному провайдеру проверяющим не выполнялись.
