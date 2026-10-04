# Независимый SOURCE обзор T061 — точное раскрытие помощи в contract test

2026-10-04. Reviewer `/root/sdd_supplement`; ownership только этот внеgit отчет. Другие участники работают одновременно; repo/code/canonical/checklist/Git/GitHub не изменялись reviewer. Suites/браузеры/full не повторялись. Выбрана узкая test-only проверка существующего F280 после requirements PASS16/0; денежных/product требований T061 не добавляет.

**SOURCE PASS: CRITICAL0 / HIGH0 / исправимых MEDIUM0.** Это заключение о точном изменении теста, не PASS старого release-full или будущего CI/CD.

## Точная область и неизменность

Текущий HEAD лично прочитан: `deb639ca8613daebfc31473ecc9418cdcaa1362f`. `git diff --name-only deb639` содержит ровно `apps/server/tests/contract/test_billing_clarity.py`; dirty state также содержит только этот файл. Полный diff состоит из замены двух литералов в одном существующем html.replace и переноса строки для читабельности.

Прежний target `<details class="billing-coupon">` отсутствует в invoice. Новый target точно `<details class="settings-disclosure"><summary>Помощь и возврат</summary>`, replacement добавляет `open` только к этому details. Target включает текст summary, поэтому не открывает соседние «Сведения о платеже». Template/source/fixture менять не требуется.

AST comparison полного файла относительно deb639: после восстановления только двух replace literals AST целиком совпадает. Следовательно, Page parser, imports, контексты всех fixtures, decorators/параметры, остальные функции и assertions неизменны. Отдельно сопоставлены **5 assert AST nodes** целевого теста: сумма/summary видны до раскрытия; результат возврата скрыт; после раскрытия четыре прежние фразы; переход к subscription; отсутствие form именно в этой fixture без can_refresh_receipt. Assertions не ослаблены, legitimate guarded receipt form продукта не запрещена новым общим правилом.

Reviewer выполнил только чистое rendering существующих literal kwargs (не test suite) и HTMLParser чтение open attrs: новый target совпадает **ровно1раз**, результирующий HTML содержит2details, `open` только у «Помощь и возврат», «Сведения о платеже» остается закрытым. Устаревший target не помогает открытию; native product disclosure не изменен. Чистый рендер не выполнял денежных/провайдерских/почтовых действий.

## Прочитанные доказательства

Лично прочитаны requirements `review-invoice-t061-requirements.md`:existing checklist16/0 покрывает FR049/052 и узкое исправление opening simulation; новый requirements waiver отсутствует. Read-only causal `временное локальное доказательство оператора` и JSON `временное локальное доказательство оператора` подтверждают oldselector0/currentdetails2, сохранение четырех raw пояснений и closed-state. Предложение causal report раскрыть оба класса не применяется: окончательный T061 target уже ограничен semantic help.

Терминальные логи лично прочитаны:

- `временное локальное доказательство оператора`: **1failed/20deselected0.12s**, именно прежний AssertionError отсутствующей видимой фразы после неработающей замены.
- `временное локальное доказательство оператора`: **1passed/20deselected0.07s**, тот же целевой тест с неизменными assertions.
- `временное локальное доказательство оператора`: **21passed0.09s**, весь измененный contract файл.

Reviewer отдельно выполнил только `ruff check` указанного файла и `git diff --check`: оба PASS. Не повторял focused/full tests, браузеры или release-full. Две предупреждающие записи terminal logs не являются failures.

## Отпечатки и применимость прежней реализации

`временное локальное доказательство оператора` перечитан в окончательном формате old/new SHA. Current file SHA-256 `8314a40b2b40f19ca2ffac278c359add1d5206d4a999d2c3ac4a4de7ca423d92`; прежний `570b7b24db080dffa8ef79d28f8bdc0a6b68b6e662cd64fe9453b710a5054341`.

Предыдущий `временное локальное доказательство оператора` проверен лично вычислением каждого hash: **17/17MATCH**. Все ранее проверенные product/helper/templates/CSS/JS/routes/finance guards и T060 tests побайтно неизменны. Этот узкий дополнительный файл не входит в прежний17manifest, его собственный fingerprint выше. Поэтому SOURCE T060 применимость сохраняется; T061 добавляет узкий test-only source review, не переносит прежний CI на новый commit.

## Границы выпуска

Первоначальный full37178472845 shard1 остается **FAIL**. Его run/job результат описан в независимом causal report, не выдавается за новую live API проверку этим reviewer. Исторический frozen11d2 и старый full не становятся успешными из-за local GREEN.

Новый test-only commit/normalPR требует собственных exactSHA/base gates; новый frozen candidate, успешный authoritative release-full, dry-run/execute и live/CD отдельно. Никакие денежные handlers/согласия/цены/roles/flags/query/API/DB не изменены этой поправкой; реальная оплата/почта/возвраты, installed GRAF Dev и человеческая приемка не выполнялись и не закрыты. Reviewer не изменял Git/GitHub/commit/release/deploy.

После записи reviewer перечитал diff, terminal logs и fingerprints: открытых findings **0/0/0**, prior17MATCH плюс собственный T061 testMATCH. Любые последующие bytes этого файла требуют refresh заключения.
