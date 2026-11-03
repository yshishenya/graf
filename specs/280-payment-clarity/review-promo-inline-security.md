# F280: независимое ревью безопасности и серверной логики промокода

Дата:2026-10-02. Рецензент: отдельный `promo_security`. Рабочая копия `release-f280/crisp`, ветка `codex/280-promo-inline`, исходный HEAD `c4277f48b84e854774a87d0a452f1511a4a5a4bd`. Lane: независимое read-only review активного high-risk-product среза F280. Использован `code-reviewer`. Изменен только этот отчет; код, тесты, требования, tasks, checklist, GitHub, коммиты и выпуск не менялись.

## Вердикт

**PASS по безопасности и серверной логике текущего среза.** Открытых critical0 / high0 / medium0. Первоначальное M1 устранено явным типом отказа и подтверждено итоговым HTTP GREEN; первоначальный finding и последовательность проверки сохранены ниже. Нового обхода auth/CSRF/финансовых ограничений, XSS или передачи секретов при просмотре кода не обнаружено. Этот scoped PASS не подтверждает незавершенную браузерную матрицу, выпуск или реальные платежи.

## M1 — первоначальный finding, устранен и проверен

Severity:medium. Требования: FR-024, SC-012, plan «Архитектура и границы»5.

Места: `apps/server/src/twobrain_rec_server/billing/purchases.py:213` и `:219`; вызывающий путь `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py:4062`, широкий обработчик `:4120–4158`; отображение `cabinet/templates/cabinet/pages/billing_checkout_content.html:42`.

Статически воспроизводимый путь: получить обычный валидный quote для personal workspace с отключенным/истекшим/исчерпанным `BillingAcceptanceBudget`, принять оферту и отправить native start. `reserve_acceptance_budget` правильно выбрасывает `PurchaseError("Оплата для этого аккаунта сейчас недоступна. Обратитесь в поддержку.")` до commit/provider dispatch. `PurchaseError` наследуется от `ValueError`; общий обработчик откатывает созданные operation/invoice/reservation и возвращает `result=unavailable`. GET страницы показывает «Оплата временно недоступна. Повторите попытку позже.» Новая причина и нужное действие обратиться в поддержку потеряны. При отключении/исчерпании лимита пользователь снова видит пригодную денежную форму и может повторять бесполезную попытку; запрет остается безопасным, но сообщение противоречит принятому различению недоступного кода и недоступной оплаты аккаунта.

Это **не доказанный обход бюджета**: порядок reserve → commit → provider сохранен, rollback выполняется. Finding касается конкретного действующего caller, поэтому изменения только текста исключения недостаточно. Unit проверки текста exception не покрывают результат native start.

Минимальное исправление: выделить эти два budget отказа явным типом или ограниченным машинным reason и сопоставить только этот тип/reason с публичным `account_unavailable` результатом/сообщением поддержки в initial handler. Сохранить существующие `PurchaseError` catches других покупок. Не сравнивать русский текст и не показывать произвольный `str(exc)` общего обработчика: YooKassa/HTTP/configuration/неизвестные `ValueError` должны сохранить прежние безопасные публичные сообщения. Не вводить новый платежный процесс или API ради сообщения. Требуемая регрессия: disabled/expired/exhausted account для ordinary checkout без promo и после удаления promo дает поддержку,0 новых invoice/operation/redemption/reservation и0 вызовов provider; обычные provider failures не становятся account ограничением.

## Подтвержденные свойства текущего кода

- В `purchases.py` diff меняет четыре публичные строки, но сохраняет проверки workspace, UUID, наличия/включенности/срока campaign, бюджетного лимита и reserved/spent; блокировки и idempotency/reservation не переставлены. Недоступная campaign дает действие исправить/убрать код, dedicated workspace budget остается запретом для любой покупки.
- GET checkout заново выполняет `_billing_role == owner`; POST preview сохраняет `WebCSRFDependency`, principal/tenant scope, owner, rate limit, catalog, промокод и referral расчет. Оно не делает provider dispatch и не создает invoice/operation/redemption/reservation. Создаваемый GET quote — прежняя отдельная модель предложения, не платеж/резерв.
- Native start независимо проверяет workspace owner/member, receipt, quote/offer/catalog, промокод/сумму и current transaction. Галочка в browser memory/sessionStorage является только предпочтением: денежный route принимает фактический `recurring_consent` из формы и сохраняет snapshot. Изменения не создают согласие или финансовую authority из metadata/storage.
- `billingPreviewRequest` и `xhr.grafBillingPreview` связывают ответ с текущим запросом. `beforeSwap` требует200, активную прежнюю страницу/target, полный checkout main и совпадение user/workspace/session из response с исходным и текущим контекстом. Auth/owner HTML без этой оболочки, missing/mismatched meta и detached/stale ответы не вставляются как расчет.
- На ожидании снимается offer, блокируются inputs/buttons/cycle/start; native submit дополнительно блокируется в checking/recovery. Ошибка восстанавливает редактирование, но сохраняет disabled start до новой серверной формы.15с timeout задан текущему preview, автоматических денежных повторов нет.
- Memory renewal preference ограничена непустым composite key user/workspace/session, сбрасывается при несовпадении, используется до optional sessionStorage. Она сохраняет False в том же документе даже через promo error страницу без checkbox; offer из новой формы остается unchecked.
- Новый JS выводит status через `textContent`. Промокод/ошибка/quote идут через существующую autoescaped Jinja форму. Код/quote/consent не добавлены в history или storage; replaceState содержит только фиксированный path и allowlisted month/year. Подписанный300с draft, HttpOnly/path/samesite cookie,48 chars и10мин quote не изменены.
- Установленный HTMX2.0.10 source проверен: нормальный synchronous swap порождает afterSwap раньше afterRequest; clearing current request в afterSwap предотвращает ошибочное recovery при последующем afterRequest. Existing global afterSwap → initCabinet восстанавливает renewal после scoped listener. Native action/method остаются запасным путем без JS.
- В inspected cabinet/API templates нет `HX-Redirect`/`HX-Refresh`/`HX-Retarget`/`HX-Reselect` или `hx-swap-oob` логики, которая меняла бы ожидаемый checkout response. Заголовки/HTML стороннего сервера не являются новым источником финансовой истины.

## Источники и проверка

Прочитаны active pointer, guidance index/spec-kit-flow/product-gates, constitution relevant privacy/Spec Kit/UX sections, baseline/current billing status, F280 spec FR-024–030/SC-010–012, plan/quickstart/tasks, reviewer-owned checklist и production diffs с соседними callers. Прочитаны новые unit/browser test изменения. `promo-inline.md` остается16checked /0unchecked **requirements** gate; никаких implementation proof отметок в него не добавлено.

Самостоятельные read-only команды: `git diff` по3 production файлам и чтение неизменного `billing.py`; `node --check cabinet.js` PASS; `git diff --check` PASS. Прочитан отдельный worker лог `graf-f280-inline-copy-unit-green.log`:29PASS0.21с; это чужой unit run, не собственный HTTP/browser evidence. Рецензент не запускал одновременно принадлежащие worker PostgreSQL/browser runs, не делал live provider/read/write, реальных оплат или продления кампании.

Хеши проверенной версии SHA256:

| Файл | SHA256 |
| --- | --- |
| billing/purchases.py | `c6931b9d8471a92cbfba9873f3dcebb027a6e854a77c7a822ed00ce27ad9d93d` |
| cabinet/web_routes/billing.py | `60151eb2a2c5d46bff9314eb5e10fbfd0eedeb939029d6fa4fbd9eab53a4dd12` |
| cabinet/static/cabinet/cabinet.js | `42bcf011b4f9817119e98a853afc22ce565702a403331b8dd92cdb0c7a22cecc` |
| cabinet/pages/billing_checkout_content.html | `1530e68351fdc060b5d92c1bdbc82775ba91547ae8058932f71758fcad458256` |

## Ограничения

Browser worker продолжает Chromium/WebKit/JS-off/scope/timeout/error/storage/a11y матрицу; отсутствующее итоговое доказательство не заменено статическим просмотром. Нужны независимый браузерный/flow повтор, устранение M1, converge, exact-SHA checks, frozen release-full, CD/runtime/publication. User decision включить публичную оплату ранее дан и этим review не отменяется; это решение не означает завершение F278 финансовой/человеческой приемки. Реальная привязка, списание, чек, банк, возврат, удержание и конверсия не подтверждены этим отчетом.

## Повтор после исправления M1 — 2026-10-02

Root добавил `AcceptanceBudgetUnavailable(PurchaseError)` и использует его только в двух прежних budget guards. Initial handler после прежнего rollback сопоставляет только этот тип с `account_unavailable` до восстановления unresolved operation. Эта причина возникает до commit/provider dispatch; условия самого budget fence не изменены. Шаблон выводит фиксированный текст поддержки, без русского string matching и без публичного `str(exc)` широкого обработчика. Другие `PurchaseError` и YooKassa/HTTP/configuration/неизвестные `ValueError` сохраняют прежние branches. Наследование сохраняет совместимость других purchase callers. Открытие coupon details перед afterSwap focus не меняет финансовую authority.

**Статическое замечание M1 устранено; финальное доказательство HTTP GREEN ожидается.** Прочитан RED `graf-f280-inline-account-red-tests-final.log`:6FAIL26.65с, runner33с, isolated cleanup PASS. Все6 failure — прежнее «Оплата временно недоступна. Повторите попытку позже.» Прочитаны новые `test_account_restriction_remains_actionable_without_promo_and_rolls_back_money`: disabled/expired/exhausted × ordinary/promo-removed, fixed support alert без предложения убрать промокод; all financial5 models absent, budget fields unchanged. Imported `owner` fixture из `test_billing_discount_presentation.py` заменяет `YooKassaClient` на `pytest.fail`, так что отсутствие обращения к провайдеру проверено выполнением теста, а не только подсчетом DB строк. Прочитан root unit GREEN `graf-f280-inline-copy-type-green-root.log`:29PASS0.05с.

Provider-denial regression `test_billing_review_regressions.py::test_rejected_creation_releases_reservations_but_unknown_result_keeps_them` включает initial/storage,400/401/recurring403/500/timeout/setup/secret_io, один provider POST/setup и прежние authoritative status ветви. Точный окончательный batch итог пока ожидается.

Свежие production SHA256 после исправления:

| Файл | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/purchases.py` | `d03b4743c9ef29d12025e149b130260d3b2fd335a6eb4557cd063bccc9cfc66c` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `ba7db4c90ec19f85e114a276e3983619cf8e6321e45f1e992ab831532c5b75b8` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `c6e1485081d7ca460ce5483ed539e10d536b4d27f7c1da4825d4228b7008b5d1` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html` | `4b17d26ee11577eeb30a6d7788d4a8eafabfa1649a4dcef2613d34ebd10db3b0` |

## Повтор после browser RED недоступного storage

Проверено дополнительное узкое исправление `initCabinetRail`: getItem/setItem перехватывают только отказ optional browser storage; используется прежний responsive default или текущий ручной выбор панели. До исправления unguarded getItem мог прервать `initCabinet()` до renewal initializer и регистрации общего afterSwap listener. Это объясняет потерю False при storage blocked и не устраняется одним catch внутри billing initializer. Новый catch не подавляет другие ошибки и не добавляет storage/permission/payment authority. Финансовые routes со времени устранения M1 не менялись. Итоговая браузерная матрица перезапускается worker после узкого GREEN; старый run с F не засчитывается.

Текущий `cabinet.js` SHA256: `ea894567e3a61b17917b5668297db539cb930d2277cb911c4a4bdc8ec1022a15`.

## Окончательный повтор M1: HTTP GREEN

Прочитан полный итог worker `graf-f280-inline-http-domain2-tests-final.log`:205PASS395.14с, runner403с, collection205/digest `aab51288926c504ea7fcf68781a2839132d4533cb1a52c78e493883b48be4cc2`, focused status/result PASS, isolated_container_removed. Текущие6 account сценариев входят в этот набор и их assertions/fixture проверены отдельно чтением. Это завершает требуемое GREEN доказательство M1: ordinary и promo-removed × disabled/expired/exhausted, правильное support сообщение, финансовый rollback и немутировавший бюджет, provider-fail fixture. Unit29PASS также прочитан отдельно. **M1 CLOSED, применимых открытых critical/high/medium findings0.**

Browser RED storage-blocked сохранен отдельно; узкий rail get/set catch просмотрен и source syntax PASS. Финальная Chromium/WebKit/JS-off/a11y матрица остается отдельным обязательным доказательством browser reviewer и root, текущий security PASS ее не заменяет.237 money регрессий еще идут; provider диагностический итог проверяется root отдельно. Код в ходе этого повторного review не менялся, кроме уже перечисленных исправлений root; рецензент изменил только свой отчет.

Provider browser diagnostic FAIL прочитан: assertion `proof["submit_redirects"] == 2`, actual1 на recurring320. Та же причина6 parameter failures в старом Chromium batch. Это конкретное несовпадение счетчика переходов после превращения preview в XHR; само по себе оно не доказывает потерю provider safety. Browser worker/root должны согласовать ожидаемые native/XHR counters и пройти повтор; этот FAIL не представлен как PASS.

Окончательные проверенные source SHA256:

| Файл | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/purchases.py` | `d03b4743c9ef29d12025e149b130260d3b2fd335a6eb4557cd063bccc9cfc66c` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `ba7db4c90ec19f85e114a276e3983619cf8e6321e45f1e992ab831532c5b75b8` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `ea894567e3a61b17917b5668297db539cb930d2277cb911c4a4bdc8ec1022a15` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html` | `4b17d26ee11577eeb30a6d7788d4a8eafabfa1649a4dcef2613d34ebd10db3b0` |
| `apps/server/tests/integration/test_billing_promo_refresh.py` | `c01cfd362355ea4a68c55a03e19db33fb7cd6dffe14e5f32e0d96833d43d5cf7` |

## Нормализация evidence и отдельный account GREEN

Абсолютные пути рабочей станции удалены; ниже локальные артефакты идентифицируются именем и SHA256. Прочитан отдельный `graf-f280-inline-account-green-tests-final.log`:6PASS36.23с /101deselected, runner46с, focused status/result PASS, isolated_container_removed. Актуальные6 tests дополнительно устанавливают явный sentinel на `_create_initial_checkout_payment`: любое обращение записывается и вызывает `AssertionError`; после refusal ожидается пустой `provider_calls`. Это усиливает проверку0provider calls, не опираясь только на fixture-конструктор или DB счетчики. Проверены актуальные hashes production и этого testfile; `cabinet.js` соответствует `ea894567e3a61b17917b5668297db539cb930d2277cb911c4a4bdc8ec1022a15`. Финальный статический security/backend PASS сохраняется, открытых findings0; браузерный допуск остается отдельным.

| Локальный артефакт | SHA256 |
| --- | --- |
| `graf-f280-inline-account-red-tests-final.log` | `7196b2bab249beb05dfaebe044cdc0b9e0052475bfd81d880207b4e86cc771df` |
| `graf-f280-inline-copy-type-green-root.log` | `f2c16949610cb6b233d8e02694e190f68088d504f7a808786bd2f6d48a824ef2` |
| `graf-f280-inline-copy-unit-green.log` | `30d477907a56c05ddae513149dd75c47ac63d20750247273a65516f87b5d4f89` |
| `graf-f280-inline-http-domain2-tests-final.log` | `825efdd6b160f37464c2d30921fc8d93202b88963d32c450af6b61d4c877f0f3` |
| `graf-f280-inline-account-green-tests-final.log` | `30cd81cb6a80326c5d168479bb2af34d29eefa295a6b3a5729198454adaa4e47` |

## Сценарий сверки production: отдельное статическое read-only review

Прочитан подготовленный root локальный артефакт `graf-f280-inline-runtime-readonly.py`, SHA256 `b99c142f05c5565578cd237b9b2728f1fdf188623a225591e26f631139699071`. На сервере этот рецензент его **не запускал**. AST прочитан без исполнения:3 subprocess call sites — только `check_output` для `docker ps`, `docker inspect`, `docker exec ... cat`. Команд записи/изменения контейнеров, базы, оплаты или провайдера нет. Twelve allowlisted sourcefiles сверены непосредственно с относительными `apps/server/src/...`:12/12 expected SHA256 совпали с текущими файлами, включая новый `cabinet.js`.

Полный inspect/env читается в память, но наружу выводится ограниченная JSON проекция: source SHA, flags boolean, running/health, source hashes и equality verdict. Env/tokens/secret values/secret paths/содержимое sourcefiles не выводятся. Вычисление SHA256 производится в памяти. При отсутствующей тройке служб assert останавливает вывод; mismatched code отражается false и должен проверяться root, а не считаться успешным runtime verdict автоматически. По статическому коду mutations0/secrets-in-output0. Это допуск безопасного чтения, **не** доказательство36 runtime matches, актуального public/health или завершения выпуска; такие факты появятся только после разрешенного запуска root и отдельной проверки результата.

## M2: освобождение ожидания после удаленной формы — независимый повтор

Изменение root после RED независимого browser/flow обзора: к каждому текущему XHR добавлен прямой одноразовый `loadend` callback на существующий `finishBillingPreview(state, true)`. Event от удаленной формы не обязан дойти до body; поэтому очистка не должна полагаться только на всплывание HTMX события. Проверено текущее `cabinet.js:1894–1895` и соседние lifecycle guards.

При успешном synchronous outerHTML swap прежний afterSwap уже сбрасывает текущий request; последующий loadend видит несовпадение состояния и ничего не меняет. При удалении страницы callback очищает только свой текущий request до `isConnected` проверки, не восстанавливает прежние controls/quote в новую страницу и разрешает ей новый preview. При позднем loadend от старого request guard `billingPreviewRequest !== state` не дает снять busy/recovery нового request. Не меняются beforeSwap scope/target/200 проверки,15с timeout, offer reset, start blocking или финансовый route. Новый callback не создает provider вызов или consent authority. **Статическое M2 закрыто, применимых открытых security/backend findings0.**

Прочитан отдельный RED `graf-f280-inline-detached-retry-red-tests-final.log`: inline-guards320 failed конкретно на `inline-detached-fresh-retry` с TimeoutError, bridge errors0. Прочитаны текущие boundary5 GREEN: Chromium4PASS63.51с, runner68с; WebKit4PASS65.04с, runner70с; оба collection4/digest `746bc63dfa0200b821c3930e2d755db014da2b883545bad3cf54f6ef101d57a2`,24deselected, focused result PASS и isolated_container_removed. Cases: timeout/guards ×320/1280. Проверен testsource: после detached late response ожидается XHR loadend, прежний quote не подменяется, новый preview вызывается без навигации документа; общие assertions/SQL teardown сохраняют отсутствие extra financial/provider действий. Эти4+4 scoped cases не представлены как полная28+28 матрица; ее итог — отдельный browser gate.

Прочитан завершенный `graf-f280-inline-money-regression-tests-final.log`:237PASS446.56с, runner461с, focused PASS, cleanup изолированной базы PASS. Это финансовая регрессия server routes; она не превращает synthetic проверки в реальные платежи/чек/банк/возврат или человеческую приемку. `node --check cabinet.js` и `git diff --check` прошли на текущем source.

### Актуальные хеши после M2

| Репозиторный файл | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/billing/purchases.py` | `d03b4743c9ef29d12025e149b130260d3b2fd335a6eb4557cd063bccc9cfc66c` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `ba7db4c90ec19f85e114a276e3983619cf8e6321e45f1e992ab831532c5b75b8` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html` | `4b17d26ee11577eeb30a6d7788d4a8eafabfa1649a4dcef2613d34ebd10db3b0` |
| `apps/server/tests/integration/test_billing_promo_refresh.py` | `c01cfd362355ea4a68c55a03e19db33fb7cd6dffe14e5f32e0d96833d43d5cf7` |
| `apps/server/tests/browser/billing-promo-refresh.test.cjs` | `e180e2c4fe54748e9ed20cf70849d2883b470af3ac4a5f65f50a054298ee82e5` |
| `apps/server/tests/contract/test_billing_promo_refresh_browser.py` | `5ab899f007db8023b7d51906484cb04b79e757138ce20c0e572a7a8dcf22442b` |

| Локальный артефакт | SHA256 |
| --- | --- |
| `graf-f280-inline-chromium-boundary5-tests-final.log` | `e976f9c8e513476b0144d512d1abffe41712d9b4158f4598f48a23bab2000619` |
| `graf-f280-inline-webkit-boundary5-tests-final.log` | `4aaf0821b5e4fc744555482dd899900bcbb33cdf5bed6a28225ee05776e30707` |
| `graf-f280-inline-detached-retry-red-tests-final.log` | `4cbb4bc4042dff43abe7fbe6f1068a5464f98b542fd201086268755f7610054e` |
| `graf-f280-inline-money-regression-tests-final.log` | `043e16009712ae384fa8696abd3825f1a30263ea131ae0e58cb61b45e1246ae1` |
| `graf-f280-inline-runtime-readonly.py` | `213e4139a44c24d423fd2e2cd0886b7d1e22a4aab61ba11440c355cd2c2ba35f` |

Root обновил подготовленный runtime verifier на текущий JS `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34`. Сценарий перечитан без исполнения, AST проверен повторно:12/12 expected source hashes совпали, те же3 read command sites, output projection и границы mutations0/secrets-in-output0 сохраняются. Актуальная версия идентифицирована SHA256 в таблице выше; прежний digest относится к прошлому статическому обзору. На production этот рецензент сценарий не запускал;36 runtime matches/public/health остаются фактом будущего разрешенного запуска root.
