# Сверка реализации «Платёж и чек» — F280

## Текущий результат после слияния PR7532 — 2026-10-04

**T055 завершена; T056 остаётся открытой до серверного выпуска.** Этот раздел задаёт текущий результат. Более ранние локальные записи ниже сохраняются как история с их исходными границами; их прежние слова «ещё требуются» не обозначают нынешнее состояние PR.

- PR [#7532](https://github.com/yshishenya/graf/pull/7532): окончательный head `deb639ca8613daebfc31473ecc9418cdcaa1362f`, checked base `872d5b2d066869a6f4693950991f6a5cf4aeec6d`; обычное squash-слияние `498c9a296446cfca98aebf668b12b2e6e5131889` от 2026-10-04T04:30:29Z.
- Common current validator после слияния — PASS: точные head/base/merge и действительные успешные source proofs вместе с последними обязательными gates совпадают. [governance-fast37176667299](https://github.com/yshishenya/graf/actions/runs/37176667299), [macos-pr37176667451](https://github.com/yshishenya/graf/actions/runs/37176667451), [pr-metadata37176666833](https://github.com/yshishenya/graf/actions/runs/37176666833) — PASS. Прежние неуспешные SHA не используются для допуска.
- Merged source/test manifest17/17MATCH: прежние16 файлов плюс исправленный direct-render unit context. Независимые requirements16checked/0unchecked, source и visual0CRITICAL/0HIGH/0исправимыхMEDIUM; узкое source дополнение сохраняет7 прежних unit assertions. См. `review-invoice-t060-{requirements,source,visual}.md` и `validation-invoice-t060.md`.
- Окончательные относящиеся к срезу результаты:202 contracts PASS,22 actualGET PASS,35 unit PASS, полный statusChromium56PASS242.62s и WebKit56PASS254.74s; одноразовые контейнеры удалены. Наборы пересекаются и не суммируются. Accessibility16×2 относится к неизменным template/CSS/JS/fixture bytes; C0/DEL исправление подтверждено финальными contract/GET проверками. Старые88 DB и T059 browser результаты сохраняют свои честные исторические границы.

T052–T055/T059/T060 имеют подтверждённую реализацию и проверки; отметки ведёт единственный канонический писатель F280. Следующие ворота относятся к T048/T056: новый frozen train/candidate, authoritative release-full/GO, CD dry-run/execute, live страницы, CalVer tag/Release и scoped tracker closeout. T011/T012, SC005/006, установленный GRAF Dev, финансовая F278 и umbrella не закрыты.

## Исторические локальные записи до текущего слияния

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
| SC016 |Все invoice acceptance scenarios сопоставлены с реальными GET/browser проверками; snapshots полных финансовых строк и no-provider guard. Invoice presentation достигнута; на момент первоначальной локальной сверки T055 ещё требовала exact-SHA CI. Текущие CI/merge результаты подтверждены выше. |
| SC017 |Invoice responsive/source review достигнуты; общий release допуска не завершён до merged source/current frozenFull/CD/live и root subscriptionT057. T056 остаётся открытой. |

Проверены9 requirement/success items, пять задач invoice и шесть решений плана: существующий Jinja/stdlib стек, narrow read-model, native disclosures, width720/order-summary, сохранение money/consent/tenant boundaries и единый release train. Применимые принципы конституцииII/III/VI/VII: текущие разрешения/правдивые статусы, отсутствие новых чувствительных данных, Spec Kit/current validation, независимый код/происхождение активов и доступность. Capture/AI/deletion/macOS distribution не изменяются; серверный выпуск не заменяет установленную или финансовую приёмку.

## Результат

Новых отсутствующих, противоречащих или непрошенных функций в коде invoice не найдено; исправление S001 уже входит в T053 и независимо принято. Новых задач к canonical tasks.md не добавлено; файл сохранён без изменений. Это **converged для buildable invoice scope**, а не завершение всей F280/продакшена.

На момент первоначальной локальной сверки оставались T055 — exact PR/head/base checks и допуска, T056 — общий серверный выпуск/live/отчёт/трекер. T055 теперь завершена по текущему разделу выше; T056 остаётся открытой. Их нельзя заменить узкими invoice PASS или закрыть новой дублирующей задачей. Другой писатель ведёт T057/подписку; её актуальная готовность обязательна для общего train. Исходные отказы browser сохраняются в validation report, причины не списываются на flaky без проверки.

Прямое уточнение владельца «Сделать карточку плотнее» удовлетворяется двумя invoice-only CSS правилами в пределах FR046/T054; canonical narrownotes добавляет root. После правки свежие Chromium16/WebKit16 PASS и independent source/visual0/0/0, всё существенное и размер controls сохранены. Новый слой, задача, зависимость или денежное правило не требуются.

Исторический план перехода после локальных ворот: разрешённый пользователем коммит, перенос invoice commit на fresh master после подписки, текущие GitHub gates. Эти source/PR этапы теперь подтверждены текущим разделом выше. Затем release оператор замораживает общий новый кандидат; одно авторитетное release-full, CD dry-run/execute/live. Hooks after_converge отсутствуют в `.specify/extensions.yml`; дополнительных действий hook не запускалось.

## Финальная совместимость T059

Три causal отказа объединенного набора устранены минимальной правкой текста и содержательного теста. Действующая F278 receipt-only форма сохранена; refund/money forms остаются запрещены. Требования14/0, contracts186PASS, focusedinvoice+receiptDB74PASS до copy-only правок, окончательные Chromium16PASS/WebKit16PASS при прежних assertions/timeouts. Первый WebKit timeout сохранен; не подменен успешным повтором. Подписка меняет один знак и три соответствующих точных browser selectors, handlers/guards не изменены. Команды/границы: validation-invoice-t059.md. Доказательства code/source/visual относятся к текущим frozen bytes; actual rebase equivalence и exact PR/base CI еще проверяются отдельно. Этот исторический локальный append не объявлял T055/T056 выполненными; текущий результат T055 записан выше, T056 остаётся открытой.

## T060 — общая безопасность помощи

Требования16checked/0unchecked, independent source и visual0critical/0high/0исправимыхmedium. Общая нормализация и encoded mailto исправляют все действующие presentation callers; строгий account-merge display-name guard сохранен. Reviewer finding raw/decoded C0/DEL закрыт causalRED4FAIL9PASS→GREEN202PASS и realGET22PASS с неизменными финансовыми снимками. Изолированный88PASS invoice/F278/support до финального guard имеет точную историческую границу. Accessibility16PASSChromium/16PASSWebKit применим к неизменным templates/CSS/CJS/fixtures; последняя helper ветка проверена contracts/GET. Browser outer300с не меняет individual assertions/limits. Дополнительная полная status56matrix PASS обоими движками: Chromium242.62s/WebKit254.74s, каждый cleanupPASS. На момент этого локального append exact newSHA/base CI и выпуск ещё требовали отдельного подтверждения. Текущие CI/merge записаны выше; выпуск остаётся отдельным этапом. Этот исторический локальный append не выставлял T055/T056/T060 вместо единственного canonical писателя. Текущие T055/T060 подтверждены разделом после слияния выше; T056 остаётся открытой. Команды/результаты:validation-invoice-t060.md; отчеты:review-invoice-t060-{requirements,source,visual}.md.

T060 GitHub обнаружил две несовместимости подготовки evidence/testcontext: requirementsreport EOF (только newline исправлен reviewerowner,16/0 неизменно) и существующий emptyhistory unit без validated mailto. Исправлено только unitrendercontext, causalRED1FAIL1PASS→fullunit35PASS. Все16production/testbytes прежнего manifest сохранены; добавленный unit расширяет manifest до17. Никакие assertions/guards не ослаблены. На момент этого локального test-only исправления новый SHA/base CI ещё требовался. Его текущий PASS подтверждён выше; исторические failure не скрываются.

## Scoped converge после реализации T061

Единственный обнаруженный полный CI разрыв — прежнее моделирование открытия помощи — исправлен в existing contract selector; FR049/052/SC017 и existing checklist покрывают результат. Содержательные assertions и все17ранее проверенных файлов неизменны. Requirements16/0, source0/0/0, причинныйRED1→GREEN1, fulltouched21PASS и18hashMATCH подтверждены. Buildable gaps0; T061/T048/T056 требуют нового exactSHA/base PR и frozen release-full/GO/CD/live/publication. Старый frozen/fullFAIL сохранен, release не объявлен. Дополнительных task дубликатов нет.

## Актуальное подтверждение выпуска 2026-10-04

Исторические ожидания CI/выпуска выше сохранены по времени наблюдения. Текущий серверный source `e50c4a729cdb2cd4d1d9a59c27637410bcd8b908`: обычные PR7506/7532/7536/7538 и обязательные exactSHA/base checks PASS; source18/18 MATCH; authoritative [Full37180461213](https://github.com/yshishenya/graf/actions/runs/37180461213) SUCCESS, новый frozen candidate/GO, штатный CD dry-run/execute PASS, runtime12/12 product files и три service SHA MATCH, флаги публичной оплаты/наблюдения/всех пространств true. Обе живые страницы проверены только GET, public artifacts3/3 unchanged, stable tag/Release v2026.10.04.5 и publication attestation на том же источнике подтверждены. [Итог выпуска](release-subscription-clarity-closeout.md) и [подробный отчет](../../docs/deployments/2brain-rec/release-v2026.10.04.5.md) содержат независимые обзоры и пределы. Предыдущие failed кандидаты и неустановленная причина macOS timing failure не удалены; диагностический PASS не подменяет authoritative Full. Финансовая, человеческая, установленная приемка и SC005/006/F278 остаются открытыми. Новых реализуемых пробелов этого среза нет.
