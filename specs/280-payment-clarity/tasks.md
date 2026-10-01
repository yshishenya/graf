# Tasks: F280 — понятная оплата

**Lane**: high-risk-product · **Branch**: codex/280-payment-clarity · **Umbrella**: #7366
Источник реализации — этот файл. Requirement review → analyze → issue sync → code. Все изменения основываются на текущем контракте F278; финансовая приемка не наследуется.

## Phase 1 — Исследование и допуск

- [X] T001 Зафиксировать аудит всех страниц и прочитанные источники в `specs/280-payment-clarity/research.md`, `audit.md`, `ux-audit.md` (FR-001/014).
- [X] T002 Получить независимый PASS `specs/280-payment-clarity/checklists/ux-payment.md`, провести analyze и синхронизацию задач; сохранить результат в `specs/280-payment-clarity/review-requirements.md` (FR-015, gates).

## Phase 2 — US1: выбор и оформление

- [X] T003 [US1] Зафиксировать исходный checkout, добавить проверки существенных условий/скидок в `apps/server/tests/contract/test_billing_clarity.py`; использовать реальные fixture/CSS (FR-003/004/005/011, SC-002).
- [X] T004 [US1] Упростить `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_plans_content.html` и `billing_checkout_content.html`: один главный путь, полный итог, ясные непредвыбранные согласия, детали по запросу (FR-002–005/013).

## Phase 3 — US2: место и досрочная оплата

- [X] T005 [US2] Упростить `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_storage_content.html`, `billing_purchase_content.html` и существующий storage JS в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`; общий объем вместо подсчета пакетов, все существенные future условия видны (FR-006/007).
- [X] T006 [P] [US2] Добавить отрицательные и положительные route tests в `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`, затем разрешить четыре точных purchase POST в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift` (FR-008).

## Phase 4 — US3: результат и восстановление

- [X] T007 [US3] Проверить regression сценарии в `apps/server/tests/integration/test_billing_clarity.py`, исправить invoice/status recovery, годовой cycle, receipt readiness и reason/state projection в `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` и соответствующих invoice/status templates; восстановить узкий GET-only `next` через settings/email/merge существующего account flow, добавить проверки в `apps/server/tests/integration/test_billing_return.py` (FR-009/011, Contract Состояния).

## Phase 5 — US4: управление и удержание

- [X] T008 [US4] Упростить оставшиеся billing overview/subscription/payment-method/history/usage/discounts и referrals_content.html templates в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/`, исправить помощь, renewal blockers и обещания действий; отмена доступна без препятствий (FR-002/009/010/013); проверить и зафиксировать решение по referral_landing, public pricing/offer, primitives quota notices и billing notification links.

## Phase 6 — Общая приемка

- [X] T009 Пройти `apps/server/tests/browser/billing-accessibility.test.cjs`, дополнить нужными сценариями/320px, проверить synthetic screenshots и подсчет слов; результаты в `specs/280-payment-clarity/validation.md` (FR-012, SC-001–004).
- [X] T010 Получить три независимых заключения по актуальному diff, исправить замечания и пройти converge; записать `specs/280-payment-clarity/review-final.md`, owned fragment `changes/unreleased/F280.yaml` (FR-015).
- [ ] T011 После отдельного одобрения коммита получить точные PR SHA checks и установленный GRAF Dev через harness; evidence в `specs/280-payment-clarity/validation.md` (FR-008/012, release boundary).
- [ ] T012 Провести пять человеческих прохождений и последующее измерение конверсии/удержания по `specs/280-payment-clarity/validation.md` без новой публичной платежной аналитики; SC-005/006 не заменять агентами (FR-016).

## Dependencies and parallelism

T001 → T002 → T003 → T004; T005 после T004 для единых условий. T006 независим от server после T002. T007 и T008 координируют один billing.py и templates: отдельное владение файлами, без конфликтующих правок. T009 после T004–008; T010 после T009; T011 после локального допуска и согласования; T012 human gates/данные после доступного кандидата. Незавершенные T011/T012 не мешают честно предъявить проверенный diff, но запрещают полное закрытие фичи.

## Independent validation

US1 — month/year/promo/consents; US2 — 5–500 ГБ, downgrade/timeline/early, четыре POST; US3 — history recovery/unknown/refused/receipt/cycle; US4 — cancel/resume/current status/help. MVP — US1 вместе с сохранением финансовых защит; весь запрос включает US1–US4.

## GitHub links

| Task | Issue |
| --- | --- |
| T001 | [#7368](https://github.com/yshishenya/graf/issues/7368) |
| T002 | [#7369](https://github.com/yshishenya/graf/issues/7369) |
| T003 | [#7370](https://github.com/yshishenya/graf/issues/7370) |
| T004 | [#7371](https://github.com/yshishenya/graf/issues/7371) |
| T005 | [#7372](https://github.com/yshishenya/graf/issues/7372) |
| T006 | [#7373](https://github.com/yshishenya/graf/issues/7373) |
| T007 | [#7374](https://github.com/yshishenya/graf/issues/7374) |
| T008 | [#7375](https://github.com/yshishenya/graf/issues/7375) |
| T009 | [#7376](https://github.com/yshishenya/graf/issues/7376) |
| T010 | [#7377](https://github.com/yshishenya/graf/issues/7377) |
| T011 | [#7378](https://github.com/yshishenya/graf/issues/7378) |
| T012 | [#7379](https://github.com/yshishenya/graf/issues/7379) |

## Состояние после локальной реализации, 2026-09-30

**Исторический результат до коммита: implementation ready; tracker pending**. T001–T010 выполнены в локальной рабочей копии и проверены; это не означает приемку соответствующих GitHub issues. На тот момент T011/T012 оставались открытыми, коммита, PR, точных SHA checks, установленной проверки GRAF Dev и человеческих прохождений не было. Финансовая приемка F278 не наследуется.

Три окончательных независимых PASS, закрытые замечания, границы и результат convergence: [review-final.md](review-final.md). Проверки и сценарий для людей: [validation.md](validation.md). Кандидат: 41 файл, SHA-256 `328d7805ff57d15de4fdd19b6d3fb92d08a66fbf4a6b59ffaead4362eaced187`.

Во время `$speckit-converge` новых реализуемых пробелов не найдено, задачи оставались byte-for-byte неизменными (SHA-256 `fee102547cb13156ade179d6534e542cdcb4414d78ce764e3723ac5b29c7d4e6`). Отметки выше выставлены отдельным завершением этапа implement после convergence. Дубли T011/T012 не создавались. Legacy Impact: `untouched`; новых устаревших путей нет.

## Состояние PR и Dev после проверки

PR [#7380](https://github.com/yshishenya/graf/pull/7380) проверен на исходном SHA `5457ae61b498d41ff356a41b33130cc97cb3aee1`: все три обязательные проверки GitHub прошли, общий валидатор подтвердил точный SHA и основу. Единственный GRAF Dev установлен тем же SHA через harness; smoke и доступные вручную экраны оплаты прошли. В Dev checkout выключен, поэтому живое оформление и полный ручной путь/доступность еще не подтверждены: **T011 остается открытой**. T012 — 0/5 людей и нет сопоставимых данных о конверсии/удержании. Подробности и ссылки: [validation.md](validation.md). Документальный коммит, включающий эту запись, проверяется отдельно по своему SHA.

Состояние внешнего трекера фиксируется отдельно в [tracker-closeout.md](tracker-closeout.md); до проверки merge/приемки issues не закрываются.

## Доработка по полной выпускной проверке

- [X] T013 [US3] Согласовать `apps/server/tests/contract/test_payment_history_support.py` и `apps/server/tests/integration/test_account_lifecycle.py` с упрощённым интерфейсом, сохранив проверки безопасных писем, чека, номера платежа, запрета автоматического возврата и истечения trial; пройти focused tests, независимый обзор и обязательные PR checks. Причина — три устаревших ожидания в `release-full` 36744581806; это не снимает T011/T012 либо финансовые условия F278. (Issue #7383)

T013: [#7383](https://github.com/yshishenya/graf/issues/7383).


## Phase 7: Convergence — дополнительная проверка промокода

Проверка после выпуска нашла два MEDIUM несоответствия в представлении скидок. Расчёт/применение промокода прошёл 10 HTTP/DB сценариев и 10 unit/preview проверок; эти результаты не исключают ошибок отображения.

- [X] T014 [US4] Показывать в истории скидок период фактического сохранённого счёта, сохраняя его после изменения универсальной кампании; при отсутствии надёжного периода не показывать выдуманный «Месяц». Источник: FR-003/009/011/013, plan: исправить недостоверные состояния (contradicts, MEDIUM). Владение: `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`; регрессия в `apps/server/tests/integration/test_billing_discount_presentation.py`. (Issue #7388)
- [X] T015 [US1] Убрать непроверенный общий список «Действующих предложений» с раздела скидок, сохранив ввод известного промокода, серверную проверку цены и историю; ограниченные кампании не представлять как доступные конкретному плательщику. Источник: FR-003/004/011/013, plan: один понятный шаг без лишнего текста (contradicts, MEDIUM). Владение: `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_discounts_content.html`; регрессия и цепочка применить/месяц/год/удалить в `apps/server/tests/integration/test_billing_discount_presentation.py`. (Issue #7389)

T014/T015 выполняются после независимого review `checklists/promo-presentation.md`, analyze и issue sync. Финансовые обработчики, цены, campaign eligibility, cookie TTL/path и правила списания не меняются; матрица реальных денег и T011/T012 остаются открытыми. Полный выпуск нового кода проходит отдельный frozen candidate, обязательные SHA checks и release/deploy gate.

Завершение implement T014/T015: исходники и локальные регрессии проверены, три актуальных независимых PASS записаны в [review-promo-final.md](review-promo-final.md), команды и ограничения — [validation-promo.md](validation-promo.md). Дополнительный охват FR-012: `apps/server/tests/contract/test_billing_accessibility.py` и `apps/server/tests/browser/billing-accessibility.test.cjs`. Статусы новых GitHub issues до production остаются открытыми; T011/T012 не меняются. Эти отметки не подменяют отдельные SHA/release/deploy условия.


## Phase 8 — US1: промокод после обновления, 2026-10-01

Ветка среза: `codex/280-payment-promo-refresh`, lane `high-risk-product`. Независимый requirements PASS до генерации: [review-promo-refresh-requirements.md](review-promo-refresh-requirements.md), checklist 9/0. T016–T019 завершены по актуальным доказательствам, серверный выпуск v2026.10.01.1 опубликован. Исторические T014/T015 не включали этот жизненный цикл. T011/T012 не заменяются.

**Goal**: После применения, двух обновлений и возврата пользователь сохраняет code и month/year до исходного expiry300с; ошибочный ввод до MAX48 остаётся для исправления, а каждая цена рассчитывается заново и согласия пусты.
**Independent Test**: Синтетическая HTTP/DB и реальная DOM цепочка Chromium/WebKit из дополнения quickstart, без провайдера; legacy/corrupt/expired/foreign draft отвергается, preview не создаёт финансовых записей.

- [X] T016 [US1] Воспроизвести потерю выбора до изменения исходников и добавить отрицательные/положительные регрессии в `apps/server/tests/integration/test_billing_promo_refresh.py`: Apply→303→два GET/reload, месяц/год/возврат без query, malformed/non-ASCII/control ввод «не более 48 символов», error/correction/remove, срок «300 секунд от явного применения/замены» и граница `now < expiry`, отсутствие продления GET/сменой cycle/start error, bind user/workspace/session, missing session/key, copy/rename/tamper и legacy cookie, свежие условия акции, пустые согласия и отсутствие invoice/operation/reservation/provider вызовов. Зафиксировать fail-before результат в `specs/280-payment-clarity/validation-promo-refresh.md` (FR-017/018, SC-007). (Issue #7402)
- [X] T017 [US1] Исправить жизненный цикл в существующем `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`: небольшой purpose/version helper по существующему stdlib HMAC/base64/expiry образцу, bounded code/cycle/expiry и проверенная связь user/workspace/session; прежние TTL300/HttpOnly/SameSite/Secure/path `/billing/checkout`; GET не очищает и не продлевает выбор, query cycle приоритетен, без query берётся saved cycle; Apply сохраняет также malformed до MAX48, empty/remove и авторитетная созданная/восстановленная операция очищают только выбор; start errors не продлевают срок. Все callers `_checkout_result_redirect`, checkout GET и discounts apply/remove использовать согласованно; old unsigned fallback отсутствует, денежные guards/quote свежесть/согласия сохраняются. При необходимости поправить только безопасное отображение/очевидное действие в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html` (FR-005/007/011/017/018, SC-007; после T016). (Issue #7402)
- [X] T018 [US1] Добавить настоящий браузерный submit→303→два reload→back/return с изолированной синтетической сессией/локальным сервером в `apps/server/tests/browser/billing-promo-refresh.test.cjs` и `apps/server/tests/contract/test_billing_promo_refresh_browser.py`; выполнить Chromium/WebKit, HTTP/DB и security регрессии из quickstart, сохранить точные команды/границы в `specs/280-payment-clarity/validation-promo-refresh.md`, получить три независимых заключения в `specs/280-payment-clarity/review-promo-refresh-final.md`, устранить применимые замечания и пройти convergence. Native handoff принимается как обычная новая browser session без наследования draft; installed GRAF Dev остаётся T011 (FR-012/015/017/018, SC-004/007; после T017). (Issue #7402)
- [X] T019 После T016–T018, requirements/analyze/issue sync и convergence пройти новые exact-SHA `governance-fast`, `macos-pr`, `pr-metadata` и общий PR валидатор, отдельный frozen `release-full`, CD dry-run/execute с разрешением владельца, runtime metadata smoke и опубликованный серверный выпуск; записать evidence в `specs/280-payment-clarity/validation-promo-refresh.md`, заполнить принадлежащий F280 новый `changes/unreleased/F280.yaml`, сверить эти задачи с GitHub issues через валидатор закрытия. Нынешний frozen кандидат не менять, публичная оплата сохраняется по решению владельца, macOS публичные artifacts не перевыпускать; T011/T012 и реальная финансовая F278 не закрываются из этого evidence (lane `high-risk-product` + `release-deploy`, FR-011/015/016/017/018). (Issue #7402)

**Dependencies**: полный requirements PASS → T016 fail-before → T017 → T018 validation/reviews/converge → T019 выпуск/сверка. Analyze и GitHub issue sync обязательны до T016/T017 реализации. Новые задачи без `[P]`, поскольку используют общие routes/helpers и зависят от предыдущего результата; документацию и независимые read-only reviews можно выполнять параллельно без совместного изменения этих файлов. Минимальный полный результат этого дополнения — US1 T016–T018 плюс T019 для уже запрошенного выпуска.

**Владение**: новый `apps/server/tests/integration/test_billing_promo_refresh.py` — агент HTTP/DB проверки; `apps/server/tests/browser/billing-promo-refresh.test.cjs` и `apps/server/tests/contract/test_billing_promo_refresh_browser.py` — агент browser-проверки, назначенный основным агентом. Код billing — отдельно назначенный владелец. Все учитывают чужие изменения, не откатывают их.

**Issue sync**: T016–T019 принадлежат одной задаче [#7402](https://github.com/yshishenya/graf/issues/7402), созданной после analyze и проверки отсутствия дубля по project canon. Canon ensure/validate пройдены; внешнюю синхронизацию выполнил основной агент. Закрытие после evidence T019, без закрытия T011/T012/F278. Редактор документов не создавал GitHub state, commits или deployments.

Уточнение T017/T018 после визуального обзора: основной агент владеет узкой правкой `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, устраняющей подтвержденное растяжение согласий WebKit320; агент браузерной проверки добавляет проверку фактических размеров в уже принадлежащий сценарий. Изменение относится к FR-012 и существующей приемке T018.

Фактический выпуск T014/T015: v2026.09.30.2 / df3a91a01fc8e741a7ebe355ad098353c290770c, независимый runtime/file/publicPKG proof и live issue-closeout PASS. #7388/#7389 закрыты с подробными комментариями; остальные открытые обязательства не менялись.

Завершение T016–T018: fail-before 3 FAIL; окончательные HTTP/SQL и защитные проверки 84 PASS, настоящий DOM Chromium/WebKit по 16 POST→303 и PASS, доступность 16/16 PASS. Три независимых заключения — [review-promo-refresh-final.md](review-promo-refresh-final.md). Сверка реализации с FR-017/018, SC-007 и планом не выявила новых пробелов кода; существующие T011/T012/T019 не дублируются. Выпуск остается отдельным этапом.

Повторное открытие T017/T018 по review PR #7403: сохранять годовой период подписчика при применении со страницы скидок без cycle; устаревшая вкладка не стирает более новый подписанный выбор; ошибочный код редактируется/очищается до подтверждения почты без разрешения оплаты. Эти случаи относятся к FR-005/008/011/017/018 и Edge Cases двух вкладок. Прежние финальные обзоры относятся к коммиту 8a01a9bc145648e9e2ff1ce478377bec7426baad и не закрывают найденные замечания. Новые регрессии и окончательные независимые обзоры обязательны до T019.

Окончательное завершение повторных T017/T018: три применимых P2 и LOW expiry объяснения исправлены;109PASS текущегоcf91d565… (56refresh+53UI), DOM2PASS на движок verified/unverified36POST303, accessibility16/16PASS. Независимые currentflow/browser/security и closing reviews — review-promo-refresh-final.md. Controlled HTTP clock не меняет подписанный срок;109 и прежние199 не складываются. Converge после всей реализации не выявил новых задач кода; существующий выпускT019 и внешниеT011/T012/F278 сохраняются.

Повторное открытие T017/T018 по дополнительным P2 PR7403 (4150171395/4150171399): исторический status GET не очищает текущий draft; прямые HTTP409 offer_changed/quote_changed после старого start отображают действующий подписанный B и его период, не возрождают истёкший A, сохраняют причину/срок и пустые согласия. Это уточнение FR005/011/017/018, новой задачи/фичи не требуется. До регрессий и новых независимых обзоров прежние PASS являются историческими для изменяемого исходника. T019 остаётся открытым.

Окончательное завершение дополнительных T017/T018: 228 PASS (79 HTTP/БД сценариев refresh), независимые flow/security/browser PASS по billing.py 2c571a3e… и шаблону 8351694f…; Chromium 1 PASS / 16,48 с и WebKit 1 PASS / 45,60 с последовательно, по 4 настоящих отказных POST409. Новых конкретных замечаний и задач реализации 0. Исторические неполные/неуспешные запуски отделены; T019 открыт до нового точного PR SHA, release-full и production.

T017/T018 повторно открыты после governance-fast36792155653: прямой409 без saved draft терял допустимый year. Уточнение FR017 сохраняет допустимый период отправленной формы только при отсутствии действующего B; старый промокод не восстанавливает. Постоянная пара регрессий и свежая независимая сверка обязательны; прежние2c571a/228 относятся к истории после новой runtime-правки.


Окончательное завершение T017/T018 после двух последнихP2: runtime9b7c4b41,307PASS171,16с; оба direct409year безdraft и unavailable×10, emptyFormNone очистка исправлена в общем helper без ослабления assertions. Независимые flow/security/реальныйbrowser PASS: Chromium1PASS28,16с, WebKit1PASS173,67с, по12unavailablePOST303 и4direct409. Checklist9/0 независим. Converge: новых задач кода0, внешниеT011/T012/F278 и выпускT019 не дублируются.

T017/T018 повторно открыты по query-selected cycle P2: signeddraft period должен сохранять явный validGET выбор с исходным сроком; новое воспроизведение/независимые обзоры обязательны. Прежний9b7c/307 и DOM относятся к истории после новой правки.

Завершение querycycle T017/T018: runtimefec78d91,313PASS179,05с; Chromium6PASS40,12с и WebKit6PASS131,96с на текущемsource, оба направления/три причины/две ширины/две вкладки/исходныйexpiry. Три независимых ограниченных PASS, конкретных оставшихся замечаний0. Converge: новых задач0; T019 и внешниеT011/T012/F278 не дублируются.


Повторное открытие T018 по выпускному `release-full` 36798151219: единственный отказ `tests/contract/test_billing_clarity.py::test_checkout_missing_receipt_contact_provides_recovery_without_money_form` содержит устаревший запрет редактирования промокода до подтверждения почты. Это противоречит уже принятому FR-005/008/011/017/018 и plan.md:99/105. Минимальная коррекция принадлежит `apps/server/tests/contract/test_billing_clarity.py`: разрешён только preview-редактор, но `/billing/checkout/start`, денежные согласия и кнопка оплаты по-прежнему отсутствуют. Runtime, цены, сроки, guard и текущие 313/DOM доказательства не меняются. Неуспешный frozen кандидат `rc-20261001T005011Z-b1f956559a15` оставлен без выпуска и не переписывается. До исправления обязательны независимый requirements gate, analyze и синхронизация #7402; затем focused clarity/UI/refresh, независимый повтор и новый exact-SHA PR/release.

Окончательное завершение повторного T018:329PASS179.06с/runner183cleanupPASS; три независимых scopedPASS flow/security/browser текущего testhash6b088ff18…/неизменныхruntimehashes, новых findings0. Ошибочный assert скрытойApply устранён без изменения UI; stale receipt-фраза договора синхронизирована. Analyze/issue sync/convergence завершены; T019 остаётся открытым до нового exact-SHA выпуска, старый FullFAIL не переиспользуется.

Завершение T019: v2026.10.01.1 опубликован на `002c15d34975edff3b8029a0dc496952188ad165`; новый Full 36800518268 PASS, train/decision GO, CD dry-run/execute PASS и publication attestation. Три службы: exact SHA/source hashes/public checkout TRUE; deployed helpers PASS, публичный PKG прежний по скачанным байтам. Проверяемая запись — evidence/promo-refresh-release.json; отчёт — release-promo-refresh-closeout.md. Документы закрытия создаются после frozen release без изменения кандидата. T011/T012/F278 и umbrella #7366 остаются открытыми; issue #7402 закрывается только после live closeout validator.


## Phase 9 — US1: необязательное автопродление, 2026-10-01

Ветка `codex/280-payment-optional-renewal`, lane `high-risk-product`. Предыдущие завершённые T001–T019 описывают исторические версии и их доказательства; здесь новый договор FR-019/020 заменяет прежние ожидания пустых обеих галочек. Отметки других задач/чеклистов и F278 не наследуются.

**Goal**: Новая форма предлагает продление по умолчанию, снятие разрешает оплату одного периода и не сбрасывается соседними действиями. Оферта по-прежнему непринята и обязательна.
**Independent Test**: Month/year × оба режима, promo/reload/cycle/ошибки/две вкладки; подтверждённый fake-provider результат False→один период/no new card/no recurring, False recovery с прежним ключом; late cancel/owner/duplicate сохраняют ограничения.

- [X] T020 [US1] Зафиксировать RED-регрессии и минимально реализовать FR-019/020 в `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`, `billing/entitlements.py`, `cabinet/templates/cabinet/pages/billing_checkout_content.html` и существующем `cabinet/static/cabinet/cabinet.js` при необходимости: optional default checked, required unchecked offer, сохранение выбранного False в sessionStorage по существующим meta user/workspace/session без изменения API/cookie, actual bool snapshots и save_payment_method, no new card/no renewal при False; сохранить quote/authority/owner/CSRF/idempotency/paid remainder. Проверки в `apps/server/tests/unit/test_initial_checkout_recovery.py`, `test_billing_entitlements.py`, `test_billing_money_path_e2e.py` и scoped integration/contract наборах; fail-before и GREEN в `specs/280-payment-clarity/validation-optional-renewal.md`. До изменений — reviewer-owned requirements PASS `checklists/optional-renewal.md`, analyze и issue sync (FR-003/007/010/011/019/020, SC-008). (Issue #7408)
- [X] T021 [US1] После T020 выполнить настоящие Chromium/WebKit сценарии выбора/промокода/двух reload/cycle/ошибок/старых вкладок и JS-off в существующих `apps/server/tests/browser/billing-promo-refresh.test.cjs`, `apps/server/tests/contract/test_billing_promo_refresh_browser.py` и accessibility fixture (новый файл только при доказанной невозможности простого расширения), актуализировать существующие expectations только изменённого договора; провести три независимых flow/security/browser review, исправить применимые замечания и convergence. Точные команды/хеши/границы в `specs/280-payment-clarity/validation-optional-renewal.md`, обзоры в `review-optional-renewal-final.md` (FR-012/015/019/020, SC-004/008). (Issue #7408)
- [X] T022 После T020/T021 пройти новые exact-SHA `governance-fast`, `macos-pr`, `pr-metadata`, общий PR validator, frozen `release-full`, CD dry-run/execute по ранее данному разрешению владельца, runtime SHA и опубликованный серверный выпуск; owned `changes/unreleased/F280.yaml`, evidence в `specs/280-payment-clarity/validation-optional-renewal.md`, GitHub closeout только после live validator. Не менять старый кандидат и публичные подписанные macOS байты; T011/T012/реальная финансовая F278 остаются открытыми (FR-011/015/019/020, lane `release-deploy`). (Issue #7408)

Dependencies: requirements review → analyze → issue sync → T020 → T021/converge → T022. Задачи без [P] из-за общего договора и последовательной приёмки; root назначает непересекающееся владение backend/UI/tests. Новый issue покрывает T020–T022 по canon, создаётся после проверки дублей; umbrella #7366 остаётся открытой. Окончательная генерация T020–T022 выполнена после независимого requirements PASS 2026-10-01: optional-renewal10/0, reviewer-owned43/0, все checklist51/0; отчёт review-optional-renewal-requirements.md. Только после текущего analyze и issue sync допускается implementation.

Завершение T020/T021: backend RED8/GREEN49; общий HTTP465PASS/2 устаревших ожидания исправлены полным return82PASS; contract69PASS, accessibility16/16, final verified Chromium1PASS82.45с/WebKit1PASS173.89с. Три независимых current flow/security/browser PASS и requirements51/0; конкретных незакрытых замечаний0. Доказательства validation-optional-renewal.md/review-optional-renewal-final.md. Это исторический срез локальной приёмки до выпуска T022; окончательное состояние выпуска указано ниже. F278/T011/T012 сохраняются открытыми.

Завершение T022: v2026.10.01.2 опубликован на `e9d34cf349a6bc2248a9d4e206138fd77dee9c56`; новый Full36913925182 PASS, train/decision GO, CD dry-run/execute PASS и publication attestation. Три службы exact SHA/source hashes, публичная оплата TRUE, API/processing healthy, maintenance running. Установленный helper/template synthetic PASS без БД/реальных provider calls; public health200/200 и прежний публичный PKG подтверждены свежим скачиванием. Документы release-optional-renewal-closeout.md/evidence/optional-renewal-release.json фиксируются отдельно после frozen release. T020–T022 завершены; T011/T012/F278/#7366 остаются открытыми. #7408 закрывается после live validator и подробного комментария.

## Продолжение F280: отказ создания платежа (2026-10-01)

**Goal**: Достоверный отказ создания имеет понятный статус и существующий путь ручной разовой оплаты; неизвестный исход остаётся защищённым. **Independent Test**: exact recurring403/True, old generic403, соседние ответы/False, provider-bound/unknown/настоящая отмена и browser retry → manual False → явный start.

- [X] T023 [US3] После independent requirements PASS `checklists/provider-rejection.md`, текущего analyze и issue sync зафиксировать RED и минимально реализовать FR-021–023/SC-009 в `apps/server/src/twobrain_rec_server/billing/yookassa.py`, `cabinet/web_routes/billing.py`, `cabinet/templates/cabinet/pages/billing_operation_status_content.html`: strict403/type/error/code/forbidden/exact known recurring denial → фиксированный безопасный reason; авторитетный schema2/canceled/no-provider/safe provider_rejected HTTP → «Не удалось начать оплату», старый403 без specific reason только generic; подсказка ручного False только known403 + saved True. Не менять финансовые переходы, defaultTrue, consents, dispatch, promo/budget release, idempotency или добавлять POST. Расширить `apps/server/tests/contract/test_yookassa_adapter.py`, `tests/unit/test_initial_checkout_recovery.py`, `tests/integration/test_billing_review_regressions.py`; существующие return/UI/observation regression обязательны. Точные RED/GREEN, отсутствие raw response/description/ids и границы в `specs/280-payment-clarity/validation-provider-rejection.md`. (Issue #7414)
- [X] T024 [US3] После T023 выполнить настоящий Chromium/WebKit 320/1280: отказ → existing retry/cycle → True/оферта unchecked → ручной False → новое явное принятие оферты/start/save_payment_method False, без автоматического POST/снятия галочки; расширить только `apps/server/tests/contract/test_billing_promo_refresh_browser.py` и `tests/browser/billing-promo-refresh.test.cjs` по существующей harness. Проверить старый403 и unknown без ложной recurring подсказки/новой оплаты, keyboard/JS-off и прежние promo/quote/cycle boundaries. Три независимых current flow/security/browser review, исправление применимых замечаний и converge в `specs/280-payment-clarity/review-provider-rejection-final.md`, `converge-provider-rejection.md`, `validation-provider-rejection.md` (FR-012/015/021–023, SC-009). (Issue #7414)
- [ ] T025 После T023/T024 пройти новые exact-SHA `governance-fast`, `macos-pr`, `pr-metadata`, общий PR validator, frozen `release-full`, CD dry-run/execute по прежнему разрешению, runtime SHA и публикацию серверного выпуска. Создать owned `changes/unreleased/F280.yaml`, metadata-only evidence и `specs/280-payment-clarity/release-provider-rejection-closeout.md`; закрывать issue только после подробного русского комментария/live validator. Не переиспользовать прежний Full/DOM для изменённого кода, не менять публичные подписанные macOS байты; подключение recurring у ЮKassa, T011/T012/F278 и umbrella7366 остаются отдельными (FR-011/015/021–023, lane `release-deploy`). (Issue #7414)

Dependencies: independent requirements PASS → окончательная генерация T023–T025 → read-only analyze → canon ensure/deduplicated issue sync/canon validate → T023 → T024/converge → T025. Reviewer provider_rejection_requirements перечитал новые10/0, reviewer-owned53/0, все61/0; основания `review-provider-rejection-requirements.md`. Это только готовность требований. Задачи без [P] из-за последовательной приёмки; внутри T023 root владеет тремя production-файлами, tests worker — adapter/recovery/review_regressions, внутри T024 browser worker — двумя существующими harness файлами. Документы/changelog — отдельное владение; чужие изменения не перезаписываются. Один deduplicated issue покрывает T023–T025, прошлый #7408 не переоткрывается для нового scope.

Допуск реализации 2026-10-01: requirements61/0, окончательные T023–T025, analyze CRITICAL/HIGH0 и canon issue7414 PASS. T023/T024 завершены2026-10-02: RED20/GREEN45, общий450PASS315.82с, Chromium8PASS/WebKit8PASS, accessibility16/16, security38PASS; три независимых current flow/security/browser PASS, source hashes совпадают. Прежние FAIL и исправления ожиданий тестов сохранены в validation-provider-rejection.md и review-provider-rejection-test-repair.md. Source-converged, новых missing tasks0. T025 требует нового exact-SHA PR/Full/CD/runtime/publication, а F278/T011/T012/#7366 остаются открытыми.
