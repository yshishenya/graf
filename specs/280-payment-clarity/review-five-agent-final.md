# F280 T069/T070 — независимый итоговый обзор исходников

Дата: 2026-10-16. Роль: независимый final source reviewer после первоначальной проверки результата платежа. Рабочая копия `/Users/yshishenya/.codex/worktrees/billing-reaudit/crisp`; HEAD `6de02bc59d20bbab1cfa0487e942963509aa9d15` плюс перечисленные ниже незакоммиченные изменения. Полоса — существующий `high-risk-product`, обзор без изменения продукта.

**SOURCE REVIEW PASS. Применимых critical/high/исправимых medium замечаний: 0/0/0.** Самостоятельно проверены причины исправлений, минимальность, границы финансовых изменений и новые проверки. Свои результаты: 133 contract PASS, полный accessibility suite Chromium20 PASS и WebKit20 PASS; отдельно новая матрица24 PASS на каждый движок,48 суммарно. Наборы пересекаются и не складываются в число независимых сценариев.

Это допуск проверенных исходников и локальных проверок, а не подтверждение нового commit/PR CI, выпуска, production, финансовой F278, GRAF Dev или человеческого понимания. T070 полностью этим отчетом не закрывается.

## Независимость и область

Перед просмотром окончательной реализации прочитаны Phase29 в актуальных spec/plan/tasks/quickstart и `review-five-agent-requirements.md`. Отчет проверки требований использован для границ и критериев, не как доказательство работоспособности кода. После сообщения root о завершении product edits самостоятельно прочитаны полный product diff, измененные tests и соседние CSS/shell/template правила; повторены проверки на тех же байтах. Выводы исполнителей о PASS не заменяли собственный анализ и запуски. Исходные пять ролей — агенты, не пять людей; человеческие SC005/006 остаются отдельно.

Сам reviewer создал только этот отчет и собственные `.dev/04-final*`. Код, checklist, spec/plan/tasks/quickstart, GitHub, commits и releases не изменял; чужие изменения не откатывал. Использован навык `code-reviewer` для проверки текущего локального diff.

## Выводы по коду

| Область | Оценка и проверенные строки |
|---|---|
| Причина обрезания без JavaScript | PASS. В `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css:2517` одна колонка ограничена `minmax(0, 1fr)`, а `:2520` более точное правило скрывает sidebar именно в узкой standalone оболочке до готовности JS. Это исправляет саму сетку: позднее общее `.sidebar { display:flex }` в `:4394` ранее перекрывало менее точное мобильное правило `:2544`. Оставшаяся широкая sidebar участвовала в автоматическом размещении сетки вместе с явно расположенным main. Новая специфичность убирает ее из сетки, а minmax не дает колонке расширяться по минимальной ширине содержимого. |
| Минимальность и сохранение других режимов | PASS. Две новые строки находятся внутри существующего media max-width980, исключают `.desktop-embedded` и JS ready. Нет дополнительных overflow hidden/clip, нового JS, абстракций, зависимости или переноса правил всего приложения. Существующая навигация без JS в `components/sections.html:99` остается, как и ее горизонтальная прокрутка. Это общий дефект оболочки, поэтому исправление расположено в существующем общем CSS, не продублировано на платежных страницах. |
| Нейтральное действие хранения | PASS. В `cabinet/templates/cabinet/pages/billing_storage_content.html:34` заменен только literal «Проверить доплату» → «Проверить изменение». Он подходит выбору5 и15ГБ при текущих10ГБ. Существующий POST `/billing/storage/preview`, CSRF, eligibility/billing_enabled, receipt-contact и coupon guards, цена, сроки и отдельное подтверждение покупки сохранены побайтово. |
| Проверка увеличения/уменьшения | PASS. `tests/contract/test_billing_clarity.py:228` параметризует прежний случай двумя направлениями, сохраняя прежние запреты промокода до receipt contact. Дополнительно проверяются selected option, ровно одна форма preview POST, CSRF и отсутствие purchase/offer/recurring consent в предварительном выборе. Удаленные ожидания заменены более строгими, а не ослаблены. |
| Новая проверка обрезания и клавиатуры | PASS. `tests/browser/billing-accessibility.test.cjs:129` открывает настоящую полную `shell-subscription`, обслуживает реальные текущие CSS/JS, использует browser javaScriptEnabled false/true, Tab/Option-Tab и actual activeElement. Проверяет bounding rect после фокуса по обеим осям, центр элемента на переднем плане, существующий focus outline и геометрию каждой строки пояснений через Range; это не повтор прежнего недостаточного scrollWidth. |
| Матрица и неизменность прежнего набора | PASS. Циклы `:130–131`: 3 ширины320/360/1280 ×2 темы ×2 масштаба100/200% ×2 режимаJS =24 на движок,48 для двух движков. Внутри —8 первоначально проблемных сочетаний суммарно для двух движков. Diff browser-файла содержит только новую функцию и ее вызов; прежние assertions, матрицы, таймеры и copy/security/consent проверки не удалены и не ослаблены. Python browser harness не изменен: прежний subprocess timeout300 и генерация полной оболочки сохранены. |
| Native submit без ложного подтверждения БД | PASS с явной границей. В `billing-accessibility.test.cjs:141–146` POST перехватывается route и получает текст «Синтетическая отправка принята»; `:183–189` Enter должен отправить ровно один POST на прежний cancel URL с CSRF и expected_authority_version1. Это доказательство доступности HTML-формы/ее полей и перехода, не фактической отмены автопродления или транзакции в БД. |
| Финансовая поверхность | PASS по неизменности. `git diff --name-only 6de02bc59d20bbab1cfa0487e942963509aa9d15 -- apps/server/src` перечисляет только cabinet.css и storage template. Весь остальной runtime source, включая payment routes, recurring/cancel handlers, paid-through, receipt, provider, idempotency, auth/CSRF/tenant, API/DB и cabinet.js, неизменен. Новых денежных или сетевых путей нет. Проверки контрактов подтверждают прежние required unchecked offer и optional checked recurring; default/сохранение выбора этой правкой не меняются. |

## Собственные проверки причинности

Браузерный RED получен без изменения рабочей копии: `.dev/04-final-causal-baseline.cjs` содержит точную текущую `checkCancellationReflow` и обслуживает CSS из `git show 6de02bc59d20bbab1cfa0487e942963509aa9d15:apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`; остальные текущие assets и HTML fixture сохранены. Для воспроизведения использован fixture собственного полного pytest запуска.

```sh
node .dev/04-final-causal-baseline.cjs .dev/04-final-chromium-tmp/test_billing_keyboard_focus_an0/billing-pages.json
GRAF_BROWSER=webkit node .dev/04-final-causal-baseline.cjs .dev/04-final-webkit-tmp/test_billing_keyboard_focus_an0/billing-pages.json
```

Оба baseline процесса завершились ожидаемым exit1 на первом сочетании320/light/200%/JSfalse: Chromium left−39.625/right359.359375; WebKit left−29.625/right350.484375. При viewport320 кнопка выходит за обе границы. Ожидаемые RED записаны в `.dev/04-final-causal-{chromium,webkit}-red.log`; они не являются отказом текущего исправленного кода.

С тем же checker и текущим CSS:

```sh
node .dev/04-final-causal-current.cjs .dev/04-final-chromium-tmp/test_billing_keyboard_focus_an0/billing-pages.json
GRAF_BROWSER=webkit node .dev/04-final-causal-current.cjs .dev/04-final-webkit-tmp/test_billing_keyboard_focus_an0/billing-pages.json
```

Оба exit0, каждый сообщает24 выполненных full-shell keyboard/native-submit сочетания. Журналы `.dev/04-final-reflow-{chromium,webkit}.log`. Это собственный причинный RED→GREEN, а не пересказ результата исполнителя.

Подпись: существующая новая параметризованная contract-функция вызвана для selected_package_count0/2. Подмена только текста результата render прежним literal дает два ожидаемых AssertionError; настоящее текущее render дает два GREEN. Продуктовый шаблон не изменялся. Журнал `.dev/04-final-label-causal.log`. Это проверка формулировки/контракта, не расчет денег или сохранение данных.

## Собственные полные запуски

Из корня рабочей копии, существующий `.venv`, без установки зависимостей, БД и приложения:

```sh
apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_clarity.py apps/server/tests/contract/test_billing_purchase_ui.py apps/server/tests/contract/test_billing_ui.py -q --tb=short --show-capture=no
apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no --basetemp="$PWD/.dev/04-final-chromium-tmp"
GRAF_BROWSER=webkit apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no --basetemp="$PWD/.dev/04-final-webkit-tmp"
apps/server/.venv/bin/python -m ruff check apps/server/tests/contract/test_billing_clarity.py
node --check apps/server/tests/browser/billing-accessibility.test.cjs
git diff --check
```

| Проверка | Собственный результат |
|---|---|
| Три contract-файла полностью | exit0,133 passed,0 failed/skipped,0.40s; `.dev/04-final-contracts.log` |
| Accessibility полный Chromium | exit0,20 passed,0 failed/skipped,57.53s; `.dev/04-final-chromium.log` |
| Accessibility полный WebKit | exit0,20 passed,0 failed/skipped,74.47s; `.dev/04-final-webkit.log` |
| Ruff измененного Python test | exit0,All checks passed |
| Node синтаксис и git diff whitespace | exit0 |

В каждом pytest запуске два прежних предупреждения: повторный импорт pytest fixture module и устаревающее использование httpx в Starlette test client. Ни один тест из-за них не пропущен. DB-набор повторно не запускался: runtime money source не менялся; этот отчет не выдает предыдущие595 DB PASS за новое исполнение на новом серверном исходнике.

## Точные проверенные байты

Контрольные суммы сняты до собственных запусков и после них повторно подтверждены5/5 OK через `shasum -a 256 -c .dev/04-final-hashes.txt`.

| Файл | SHA-256 |
|---|---|
| cabinet/static/cabinet/cabinet.css | `454a94e62017fcbbc3f57aa1ae82586182d91728d4fcf5c9b593f9a126e5dcd0` |
| cabinet/templates/cabinet/pages/billing_storage_content.html | `159054815ba9669fcb66e0eac45d127ba302612dbc030bc0f569071043d6b79d` |
| tests/browser/billing-accessibility.test.cjs | `1e2222840a2fb401cbb1816372bb61d8d980a07a4e727cb023aec797dac9ceee` |
| tests/contract/test_billing_clarity.py | `2fd93105aa881b168585e05bbaaa958933b0e40bee16dc3c8d977ba120ef366f` |
| tests/contract/test_billing_accessibility.py, неизменный harness | `35fa2de41619c80db1b1fbb068fde9808d2204da5fe072647c4160c5b08a1c04` |

Для первых двух путей префикс `apps/server/src/twobrain_rec_server/`, для тестов — `apps/server/`. Полный diff сохранен в `.dev/04-final-server.diff`. Эта таблица квалифицирует dirty bytes; любой последующий содержательный diff требует сверки применимости.

## Границы заключения

Новых actionable дефектов не найдено; дополнительная архитектура или код не нужны. Оба независимых browser запуска и собственный causal check достаточны для этого узкого CSS/copy среза. CSS zoom2 воспроизводит найденное поведение; эти проверки не являются полной WCAG или приемкой каждого системного способа масштабирования. Визуальная ручная приемка, установленный macOS, реальные банковские платежи, серверное сохранение cancel из синтетического браузерного POST, новый exact-SHA CI/merge/frozen release/deploy/live и человеческие SC005/006 остаются UNVERIFIED этим отчетом. Новая сборка приложения и реальные письма/подписки/оплаты не выполнялись.

## Дополнение: совместные исходники после PR7612, 2026-10-16

**Предыдущие разделы и hashes исторические:** они относятся к прежней базе6de02bc и не выдаются за текущие доказательства. Это отдельный повтор на HEAD `2340d6d2ff4ca2a7f8fb9bde7ae77f20b22ed57b` (merged PR7612) плюс объединенный diff T069. **COMBINED SOURCE REVIEW PASS, применимых незакрытых critical/high/исправимых medium0/0/0.** Найденное несовпадение selector исправлено по разрешению root и проверено собственными полными прогонами.

После сигнала стабильности root самостоятельно просмотрены diff к новой базе, соседние изменения хранения/новых чеков, текущие обработчики и проверки. Независимость исходного прохода сохранена; PASS исполнителей не использован вместо собственной проверки. Новая база меняет money/receipt source по сравнению с предыдущим обзором, поэтому прежнее утверждение о неизменности денег применимо только к прошлому срезу.

### Сохранность обеих реализаций

- CSS текущей версии после удаления ровно двух строк нашего переноса **побайтово совпадает с новой базой**. Все38 строк новых storage styles PR7612 сохранены. Нет нового clipping/overflow обхода; причина/область двух строк T069 прежняя.
- Storage template после замены только нового literal обратно на прежний **побайтово совпадает с новой базой**. Сохранены addon-price/total-price, `data-billing-primary`, будущий объем, отмена отложенного выбора, раскрытие оплаченных периодов и receipt-contact/preview guards.
- `receipts.py`, `renewal_charge.py`, `cabinet/web_routes/billing.py`, `cabinet.js` и `billing_usage_content.html` **побайтово совпадают с PR7612**; собственный проверяющий скрипт сравнил bytes с `git show 2340d6d...:<path>`, результат `.dev/04-final-combined-preservation.log`.
- Соседний shared verified contact helper фильтрует конкретного пользователя, active/verified и существующий email. Планировщик выбирает текущий подтвержденный контакт для нового invoice, с прежним fallback на прошлый succeeded invoice при его отсутствии; dispatch читает неизменяемый `invoice.receipt_contact_snapshot`. Наш merge этот путь не меняет. Собственный полный `test_renewal_charge.py` ниже проверяет текущий контакт/fallback и остальное планирование без рабочей БД или провайдера.
- Общий browser diff к новой базе сохраняет ее storage/usage/NoJS случаи и добавляет прежние67 строк reflow. Найдено одно несовпадение объединения: новый upstream `packages-timeline-year` NoJS case на строке721 искал «Проверить доплату» при новом названии кнопки. По прямому поручению root изменен **только этот literal** на «Проверить изменение»; остальные assertions/матрица/таймеры неизменны. Это единственное изменение исходника самим reviewer в данном повторе. Оно отражено в `.dev/04-final-combined-server.diff` и итоговых hashes.
- В объединенном clarity test сохранен upstream `addon_label` и добавлены оба направления с прежними усиленными guards. `test_billing_accessibility.py` полностью сохранен из новой базы, включая fixtures `packages-timeline-year`, usage и новые полные оболочки.

### Собственные повторные команды

```sh
apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_clarity.py apps/server/tests/contract/test_billing_purchase_ui.py apps/server/tests/contract/test_billing_ui.py apps/server/tests/unit/test_renewal_charge.py -q --tb=short --show-capture=no
apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no --basetemp="$PWD/.dev/04-final-combined-chromium-tmp"
GRAF_BROWSER=webkit apps/server/.venv/bin/python -m pytest apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no --basetemp="$PWD/.dev/04-final-combined-webkit-tmp"
apps/server/.venv/bin/python -m ruff check apps/server/tests/contract/test_billing_clarity.py
node --check apps/server/tests/browser/billing-accessibility.test.cjs
git diff --check
git diff --cached --check
```

Contracts+renewal: **exit0,252 passed,0 failed/skipped,1.19s**, `.dev/04-final-combined-contracts.log`. Полный combined accessibility: **Chromium exit0,20 passed,62.22s**, **WebKit exit0,20 passed,79.72s**, оба0 failed/skipped; `.dev/04-final-combined-chromium.log` и `.dev/04-final-combined-webkit.log`. В обоих выполнена новая функция24 reflow сочетаний вместе с сохраненными upstream storage/usage/NoJS и всей прежней матрицей; итого48 reflow сочетаний, не48 pytest tests. Native submit остается синтетическим, прежние timers/assertions сохранены. Каждый pytest запуск имеет два прежних предупреждения, не пропуски. Ruff/Node/оба whitespace checks exit0. Пакеты не устанавливались, рабочая БД/провайдер/GRAF Dev/реальные платежи не использовались.

### Текущие fingerprints совместной версии

| Файл, префиксы как в предыдущей таблице | SHA-256 |
|---|---|
| cabinet/static/cabinet/cabinet.css | `ae1b04768110b363c5b8720448dbf554b89b093874e0a5f10d3864069dad3da5` |
| cabinet/templates/cabinet/pages/billing_storage_content.html | `b9646c2199446194383d36cddfbb54cd3475286472a9fc25aee024f7d3d219a7` |
| tests/browser/billing-accessibility.test.cjs | `ae3cef66dbe4dce4cbe0a0fe4fac9f101b9f8817207012fbd78cd67af4f3fe69` |
| tests/contract/test_billing_clarity.py | `eb2c40a22a502f097875c3dd611dc14cab8c6bfbb515ef062b09228c6d550eec` |
| tests/contract/test_billing_accessibility.py | `c5db39c970ea71e1fc408212d4455515d548f71094f42ce09a988c708d219519` |
| billing/receipts.py | `71196cf85a24e0bb9d16181a75089fe8969d5acc51b2f4186173039a8f743d9c` |
| billing/renewal_charge.py | `1e11a885bea77456d97deded3afeb4a9d3138c47801f38620967d2fed1c4de16` |
| cabinet/web_routes/billing.py | `95c4eea46fcdc581c02a155933f39da9c8459e3df504080a0bb588ab685b68dd` |
| cabinet/static/cabinet/cabinet.js | `ab3ab44f37d6ac4bf479503f5015f444edd8ef779f39c8fbb7e3251b89cb15cd` |

Полные пути в `.dev/04-final-combined-hashes.txt`; первые, последние и billing пути имеют префикс `apps/server/src/twobrain_rec_server/`, tests — `apps/server/`. Предыдущие hashes для других байтов не переиспользованы.

После всех повторов выполнен `shasum -a 256 -c .dev/04-final-combined-hashes.txt`: **9/9 OK**. Обе реализации сохранены; текущие исходники допускаются к следующим воротам. Новый commit/exact-SHA CI, merge, frozen release/full, deploy/live и отдельные финансовая/человеческая/установленная приемки этим дополнением не подтверждаются.
