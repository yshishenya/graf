# Проверки страницы «Платёж и чек» — F280

## Текущий результат после слияния PR7532 — 2026-10-04

**T055 завершена; T056 остаётся открытой до серверного выпуска.** Этот раздел задаёт текущий результат. Более ранние локальные записи ниже сохраняются как история с их исходными границами; их прежние слова «ещё требуются» не обозначают нынешнее состояние PR.

- PR [#7532](https://github.com/yshishenya/graf/pull/7532): окончательный head `deb639ca8613daebfc31473ecc9418cdcaa1362f`, checked base `872d5b2d066869a6f4693950991f6a5cf4aeec6d`; обычное squash-слияние `498c9a296446cfca98aebf668b12b2e6e5131889` от 2026-10-04T04:30:29Z.
- Common current validator после слияния — PASS: точные head/base/merge и действительные успешные source proofs вместе с последними обязательными gates совпадают. [governance-fast37176667299](https://github.com/yshishenya/graf/actions/runs/37176667299), [macos-pr37176667451](https://github.com/yshishenya/graf/actions/runs/37176667451), [pr-metadata37176666833](https://github.com/yshishenya/graf/actions/runs/37176666833) — PASS. Прежние неуспешные SHA не используются для допуска.
- Merged source/test manifest17/17MATCH: прежние16 файлов плюс исправленный direct-render unit context. Независимые requirements16checked/0unchecked, source и visual0CRITICAL/0HIGH/0исправимыхMEDIUM; узкое source дополнение сохраняет7 прежних unit assertions. См. `review-invoice-t060-{requirements,source,visual}.md` и `validation-invoice-t060.md`.
- Окончательные относящиеся к срезу результаты:202 contracts PASS,22 actualGET PASS,35 unit PASS, полный statusChromium56PASS242.62s и WebKit56PASS254.74s; одноразовые контейнеры удалены. Наборы пересекаются и не суммируются. Accessibility16×2 относится к неизменным template/CSS/JS/fixture bytes; C0/DEL исправление подтверждено финальными contract/GET проверками. Старые88 DB и T059 browser результаты сохраняют свои честные исторические границы.

T052–T055/T059/T060 имеют подтверждённую реализацию и проверки; отметки ведёт единственный канонический писатель F280. Следующие ворота относятся к T048/T056: новый frozen train/candidate, authoritative release-full/GO, CD dry-run/execute, live страницы, CalVer tag/Release и scoped tracker closeout. T011/T012, SC005/006, установленный GRAF Dev, финансовая F278 и umbrella не закрыты.

## Исторические локальные записи до текущего слияния

Дата: 2026-10-04. Полоса: high-risk-product / active Spec Kit slice. Срез T052–T056, FR046–052, SC016/017. Рабочая копия `billing-simple/crisp`, исходная база `3cf989cd93f4d3d4b72f83068664f802a11a5eac`. Это исторический отчёт локальной проверки рабочего изменения; актуальные PR/head/base/merge результаты приведены в текущем разделе выше, выпуск остаётся отдельным этапом.

## Границы и предварительные ворота

Канонические spec/plan/tasks/research/contracts/quickstart согласованы с единственным писателем F280, срез подписки принадлежит PR7506. Invoice сохраняет денежные обработчики, checkout, JavaScript, owner/tenant/session/receipt guards и предвыбранное согласие на автосписания. Изменение status ограничено классом одного dl. Ширина invoice и подписки720, checkout620. GRAF Dev занят другим срезом и не использовался.

Независимый checklist:14 checked /0 unchecked; отчёт `review-invoice-consistency-requirements.md`. Scoped analyze:0 CRITICAL/0 HIGH/0 исправимых MEDIUM, coverage9/9, tasks5/5; `analyze-invoice-consistency.md`. T052–T056 связаны с issues7514–7518. Requirements review и implementation review выполнялись разными проходами независимо от автора кода.

## Причинные проверки

| Набор | RED | GREEN | Значение |
| --- | --- | --- | --- |
| Реальный invoice GET на одноразовом PostgreSQL |7 failed/11 passed |23 passed/71 deselected,53.45s |Краткий и точный viewer-local срок, дата создания, неизвестный цикл, invalid/naive/reversed сроки. |
| Темы помощи и безопасность mailto |5 failed/7 passed |92 passed в полных `test_payment_history_support.py` и `test_billing_ui.py` |Разные намерения, сохранён прежний refund API, safe reference/адрес, encoded CRLF/query не вводят заголовки. |
| Chromium accessibility |1 failed,18.23s: отсутствовал compact paid period |16 passed,66.50s |Настоящая оболочка и синтетические invoice состояния. |
| WebKit accessibility |Причинный шаблонный RED выполнен Chromium |16 passed,87.95s |Та же полная матрица и JS-off. |
| S001 — переполнение даты при переводе зоны |Independent repro OverflowError |25 passed/71 deselected,45.65s после catch и двух boundary cases |9999 с Europe/Istanbul и0001 с отрицательной зоной дают GET200 и nullable срок; финансовые строки неизменны. |

Команды contract и accessibility из `apps/server`:

```sh
uv run --extra dev pytest tests/contract/test_payment_history_support.py tests/contract/test_billing_ui.py -q --tb=short --show-capture=no
BILLING_VISUAL_OUTPUT_DIR=/tmp/f280-invoice-chromium uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
GRAF_BROWSER=webkit BILLING_VISUAL_OUTPUT_DIR=/tmp/f280-invoice-webkit uv run --extra dev pytest tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no
```

DB tests сравнивают полные снимки финансовых таблиц до/после GET и запрещают provider calls. Покрыты историческая2025/будущая2027 покупка, Istanbul midnight, unknown cycle, invalid/naive/reversed/boundary periods, receipt allowlist/no URL, service-gap/recovery, previous payer/foreign workspace, несколько интервалов хранения, valid/invalid/missing support,0/25% скидка. Нет live платежей, писем, возвратов или изменений рабочего пространства.

Браузерная матрица320/360/390/768/1280, light/dark,100/200%, клавиатура/видимый фокус, native details, номер copy через настоящий обработчик с synthetic clipboard, две темы письма без внешнего открытия, service-gap вне раскрытий, receipt/no URL, длинные маскированные значения и storage intervals. Существующие subscription/checkout/consent/status assertions не удалены. JS-off проверяет ссылки и нативные раскрытия. PNG содержат только синтетические сведения; не доказывают live provider/DB состояние.

## Полная проверка и обнаруженные отказы

Полная quickstart выборка:348 passed,777.55s; digest `40f631bd29b62acd67d8df9a6d7d378b17dc47e5f94066c93fafb5947aeec9b8`, runner793s, одноразовый контейнер удалён. Она запущена до catchS001 и двух новых boundary параметров; её результат не называется post-fix full. Отдельная post-fix targeted25 проверка уже завершена. Из root:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_clarity.py tests/integration/test_billing_review_regressions.py tests/integration/test_billing_return.py tests/contract/test_payment_history_support.py tests/contract/test_billing_purchase_ui.py tests/contract/test_billing_safety_contract.py tests/unit/test_billing_copy_and_redaction.py -q --tb=short --show-capture=no
```

Из-за изменения dlclass повторена настоящая status browser матрица56 cases в каждом движке. Первый одновременный запуск с общей DB quickstart выборкой: Chromium53 passed/3 failed,627.01s; WebKit54 passed/2 failed,665.25s. Отказы: guards320/1280 в обоих; lifecycle320 толькоChromium. В WebKit guards и Chromium lifecycle таймаут первоначального page.goto; Chromium guards — ожидание обработки ответа или закрытие route context. Они возникали до проверок изменённого контекста, не были падениями financial/context assertions. Денежные/JS файлы и оба status harness идентичны базе. Assertions и пределы времени не изменены. Узкие и полные последовательные повторы завершены PASS; исходные отказы сохранены, точная причина нагрузки не объявляется доказанной.

Последовательный Chromium repeat `-k 'guards or lifecycle'`:4 passed/52 deselected,86.49s; WebKit repeat `-k guards`:2 passed/54 deselected,48.96s. Прежние assertions/таймауты, контейнеры удалены. Независимая read-only диагностика исходников/trace: `/tmp/f280-invoice-status-analysis.md`; исходные отказы сохранены. Узкий PASS не устанавливает причину первоначальных таймаутов.

Полный последовательный Chromium repeat:56 passed,323.91s, runner332s; WebKit repeat:56 passed,348.98s, runner355s. Оба digest `f61d5bb9ed1bb294054f821962c07ce747e94abbc7814825dcc25616e09f4d12`, оба контейнера удалены. Команда из root:

```sh
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=chromium apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -q --tb=short --show-capture=no
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=webkit apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -q --tb=short --show-capture=no
```

Логи этих отладочных запусков могут содержать временные synthetic HTTP session headers; сырые trace/headers не копируются в git или отчёты. Передаются только названия сценариев, этап, тип ошибки, totals и duration.

## Статические проверки и независимый обзор

Ruff для пяти изменённых Python файлов, Node syntax, `git diff --check`, `scripts/check_spec_kit_governance.py` и `scripts/validate-changelog-fragments.py` прошли. Повторный source/security reviewS001 и независимый visual/browser review записаны в собственные отчёты reviewer; его статус не заменяется авторским решением.

Повторный independent source/security и representative visual review PASS:0 CRITICAL/0 HIGH/0 исправимых MEDIUM; `review-invoice-consistency-source.md` и `review-invoice-consistency-visual.md`. AST billing route сравнение с базой подтверждает изменения только `_invoice_period_labels` и `billing_invoice_detail_page`; statusJS/оба status harness побайтово прежние. Digest девяти owned product/test файлов на финальном локальном срезе: `f0e0377fd4db859c1068bb3172ca210aa1f7193bee20939dea6e185cd4752886`. После переноса поверх новых root subscription bytes этот digest не следует объявлять общим digest новой ветки без пересчёта.

## Уточнение владельца: плотнее карточка

После первоначальных PASS пользователь прямо выбрал «Сделать карточку плотнее». Изменены только две invoice-scoped CSS декларации: gap карточки18→12px, padding24→16px20px, vertical padding строки10→8px. Ширина720, шрифты, native control targets, focus, данные/состояния и handlers сохранены; подписка/status этим селектором не затрагиваются. Не добавлены зеркальные padding-tests; повторён существующий содержательный browser набор. Fresh density Chromium16 passed52.71s, WebKit16 passed59.51s; предыдущие66.50/87.95s результаты остаются историческими. Captures `/tmp/f280-invoice-density-chromium` и `/tmp/f280-invoice-density-webkit`, включая closed состояния настоящей оболочки. Финальный source/visual refresh плотности тот же независимый reviewer записал отдельным append:0CRITICAL/0HIGH/0исправимыхMEDIUM,13 текущих fingerprints подтверждены. Канонический писатель F280 добавил narrow решение в root spec/plan; автор invoice эти документы не менял, их байты войдут после переноса на общий master. Окончательный digest девяти owned product/test файлов: `a452c1a0ad71f50c1df2cfe5be69ed5db472b502e71ee884603dbf036cd0ab7e`; CSS SHA256 `144b3649d73a02cf5b6634bc80c87b6e9162433aa561f2346a6739a9568e752d`. Предыдущий digest выше относится к состоянию до cosmetic правки. На момент этой локальной записи ворота среза PASS, exact PR/head/base и выпуск ещё требовались. Текущие PR/head/base/merge результаты записаны выше; выпуск ещё открыт.

На момент первоначального локального отчёта ещё не были получены exact PR/head/base required checks и merged source. Теперь они подтверждены текущим разделом выше. Frozen release-full, dry-run/execute, live acceptance, установленный GRAF Dev, финансовая F278 и человеческие SC005/006 не подтверждаются этой локальной историей. T056 остаётся открытой до доказанного общего серверного выпуска.
