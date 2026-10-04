# Сверка реализации «Платёж и чек» — F280

Дата:2026-10-04. `$speckit-converge`, scoped продолжение FR046–052/SC016–017/T052–056 после реализации. Намерение взято из действующих spec/plan/tasks; конституция задаёт ограничения. Прочитаны active paths через `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`. Существующий скрипт не поддерживает skill-параметр `--require-spec`; наличие spec проверено явно. Общие канонические документы принадлежат единственному писателю F280.

## Инвентаризация

| Требование | Текущая реализация и доказательство |
| --- | --- |
| FR046 |Назначение/сумма/статус/короткий срок/объём/чек видны в карточке, история перед ней; status action единственный primary. Invoice720 и order-summary согласованы с подпиской. Browser и независимый visual review. |
| FR047 |Invoice-only `_invoice_period_labels` проверяет parsing/aware/order/local conversion. Short date и exact zone, несколько интервалов, unknown cycle и invalid nullable. Historical/future/midnight/boundary real GET tests. Дата подписана «Дата создания платежа». |
| FR048 |Native details с номером/созданием/точным сроком/ненулевой скидкой/масками/интервалами. Настоящий copy handler; noJS номер остаётся текстом. Service-gap открыт. Previous-payer/foreign guards и read-only snapshots. |
| FR049 |Два узких mailto builder с общими проверками safe address/reference; static темы/тело. Старый refund API сохранён. Никакой отправки/возврата, правдивая copy; invalid/missing support без raw fallback. Contract/security tests. |
| FR050 |Existing owner/receipt state/HTTPS allowlist; noURL без ложного действия. Реальные GET и synthetic browser noURL. |
| FR051 |Status меняет только dlclass. JS/формы/атрибуты/пределы/финансовые переходы сохранены; полный status browser gate выполнен T055:56PASS в каждом движке, первые отказы сохранены отдельно. |
| FR052 |Native controls, existing tokens/focus, темы/320/200%/JS-off browser matrix. Independent requirements/source/visual0CRITICAL/0HIGH/0исправимыхMEDIUM. Новых assets/fonts/dependencies нет. |
| SC016 |Все invoice acceptance scenarios сопоставлены с реальными GET/browser проверками; snapshots полных финансовых строк и no-provider guard. Invoice presentation достигнута, T055 допуска ещё требует текущего exact-SHA CI. |
| SC017 |Invoice responsive/source review достигнуты; общий release допуска не завершён до merged source/current frozenFull/CD/live и root subscriptionT057. T056 остаётся открытой. |

Проверены9 requirement/success items, пять задач invoice и шесть решений плана: существующий Jinja/stdlib стек, narrow read-model, native disclosures, width720/order-summary, сохранение money/consent/tenant boundaries и единый release train. Применимые принципы конституцииII/III/VI/VII: текущие разрешения/правдивые статусы, отсутствие новых чувствительных данных, Spec Kit/current validation, независимый код/происхождение активов и доступность. Capture/AI/deletion/macOS distribution не изменяются; серверный выпуск не заменяет установленную или финансовую приёмку.

## Результат

Новых отсутствующих, противоречащих или непрошенных функций в коде invoice не найдено; исправление S001 уже входит в T053 и независимо принято. Новых задач к canonical tasks.md не добавлено; файл сохранён без изменений. Это **converged для buildable invoice scope**, а не завершение всей F280/продакшена.

Оставшиеся обязательства уже имеют задачи: T055 — exact PR/head/base checks и допуска; T056 — общий серверный выпуск/live/отчёт/трекер. Их нельзя заменить узкими invoice PASS или закрыть новой дублирующей задачей. Другой писатель ведёт T057/подписку; её актуальная готовность обязательна для общего train. Исходные отказы browser сохраняются в validation report, причины не списываются на flaky без проверки.

Прямое уточнение владельца «Сделать карточку плотнее» удовлетворяется двумя invoice-only CSS правилами в пределах FR046/T054; canonical narrownotes добавляет root. После правки свежие Chromium16/WebKit16 PASS и independent source/visual0/0/0, всё существенное и размер controls сохранены. Новый слой, задача, зависимость или денежное правило не требуются.

После завершения локальных ворот — разрешённый пользователем коммит, перенос только invoice commit на fresh master после подписки, текущие GitHub gates. Затем release оператор замораживает общий новый кандидат; одно авторитетное release-full, CD dry-run/execute/live. Hooks after_converge отсутствуют в `.specify/extensions.yml`; дополнительных действий hook не запускалось.

## Финальная совместимость T059

Три causal отказа объединенного набора устранены минимальной правкой текста и содержательного теста. Действующая F278 receipt-only форма сохранена; refund/money forms остаются запрещены. Требования14/0, contracts186PASS, focusedinvoice+receiptDB74PASS до copy-only правок, окончательные Chromium16PASS/WebKit16PASS при прежних assertions/timeouts. Первый WebKit timeout сохранен; не подменен успешным повтором. Подписка меняет один знак и три соответствующих точных browser selectors, handlers/guards не изменены. Команды/границы: validation-invoice-t059.md. Доказательства code/source/visual относятся к текущим frozen bytes; actual rebase equivalence и exact PR/base CI еще проверяются отдельно. T055 и T056 не объявлены выполненными этим локальным append.

## T060 — общая безопасность помощи

Требования16checked/0unchecked, independent source и visual0critical/0high/0исправимыхmedium. Общая нормализация и encoded mailto исправляют все действующие presentation callers; строгий account-merge display-name guard сохранен. Reviewer finding raw/decoded C0/DEL закрыт causalRED4FAIL9PASS→GREEN202PASS и realGET22PASS с неизменными финансовыми снимками. Изолированный88PASS invoice/F278/support до финального guard имеет точную историческую границу. Accessibility16PASSChromium/16PASSWebKit применим к неизменным templates/CSS/CJS/fixtures; последняя helper ветка проверена contracts/GET. Browser outer300с не меняет individual assertions/limits. Дополнительная полная status56matrix PASS обоими движками: Chromium242.62s/WebKit254.74s, каждый cleanupPASS. Exact newSHA/base CI и выпуск должны быть подтверждены до соответствующего закрытия. T055/T056/T060 здесь не отмечаются выполненными вместо единственного canonical писателя. Команды/результаты:validation-invoice-t060.md; отчеты:review-invoice-t060-{requirements,source,visual}.md.

T060 GitHub обнаружил две несовместимости подготовки evidence/testcontext: requirementsreport EOF (только newline исправлен reviewerowner,16/0 неизменно) и существующий emptyhistory unit без validated mailto. Исправлено только unitrendercontext, causalRED1FAIL1PASS→fullunit35PASS. Все16production/testbytes прежнего manifest сохранены; добавленный unit расширяет manifest до17. Никакие assertions/guards не ослаблены. NewSHA/base CI остаётся обязательным; исторические failure не скрываются.
