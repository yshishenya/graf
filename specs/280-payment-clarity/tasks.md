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
