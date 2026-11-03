# Независимый обзор исправления переноса в Linux

Дата: 2026-10-16. Reviewer: `independent_4_payment`. Область: существующие T069/#7613 и T070/#7614, полоса `high-risk-product`. Проверены окончательные рабочие байты поверх `c9f938851942c6f5c931ae57e5dfd9043d664769`. Reviewer изменил только этот новый отчет и собственные журналы в `.dev`; код, тесты, задачи, контрольные списки, GitHub, коммиты и выпуск не менял. Оператор слияния и выпуска — root.

## Решение

**SOURCE / macOS BROWSER REVIEW PASS; Linux gate OPEN.** Критических, высоких и исправимых средних замечаний к проверенным исходникам нет. Можно подготовить согласованный коммит и новые точные PR-проверки. Локальные успешные результаты не разрешают считать Linux исправленным: обязательна новая успешная Ubuntu-проверка на исправленном SHA с прежними ограничениями. Этот отчет сам по себе не закрывает T069/T070 и не разрешает выпуск.

## Независимо проверенный исходный отказ

Reviewer самостоятельно прочитал журнал `governance-fast` [38846102759](https://github.com/yshishenya/graf/actions/runs/38846102759), сохранив его в `.dev/04-linux-original-ci-failure.log`. Журнал содержит requested/head SHA `c9f938851942c6f5c931ae57e5dfd9043d664769`, base `69f493dba540f13b780e7ecb2cc34680d776fdb2` и реальную ошибку:

```text
cancel: 320px, light, 200%, JS=false: focused cancellation fits viewport
left=58, right=322.203125, top=410.5625, bottom=489.9375,
outline=solid, outlineWidth=2, exposed=true
1 failed, 52 passed
```

Допустимая правая граница осталась `width + 1 = 321`. До отказа все 16 административных сочетаний прошли. Штатный workflow использует `ubuntu-latest`. Прежний macOS PASS этого нарушения не обнаружил и не заменяет Ubuntu GREEN.

Прочитанный `.dev/linux-reflow-sizing-probe.log` — только причинная диагностика исполнителя на macOS с разными шрифтами: базовая автоматическая колонка карточки имеет ширину `125.031px`, при ограничении — `102px`; правая граница кнопки меняется с `308.0625` на `262`. Это не Linux-запуск. `.dev/linux-reflow-label-red-chromium.log` завершился кодом 130 после успешной cancellation-подматрицы; он прерван и не является ни причинным RED, ни полным PASS. Доказательство Linux RED — указанный реальный CI.

## Область и причинность изменения

В продуктовом коде ровно два добавления к `cabinet.css`:

- `.billing-checkout-card` получает `grid-template-columns: minmax(0, 1fr)`. Явная одна колонка сохраняет существующий вертикальный порядок, но позволяет ей сжиматься по доступной ширине вместо автоматического минимального размера содержимого формы.
- `.billing-subscription-page .button` получает `overflow-wrap: anywhere`. Существующее `.settings-page .button` уже задает `white-space: normal`; новое правило позволяет перенести длинное слово подписи, когда оно шире доступного места внутри кнопки. Шрифт, размер текста и подпись не заменены.

Проверены все четыре производственных потребителя `.billing-checkout-card`: подписка, оплата тарифа, покупка изменения хранения/периода и сведения платежа. Они уже представляют одну вертикальную карточку; зависимых правил нескольких колонок или ручного размещения ее непосредственных детей в шаблонах нет. Вложенные таблицы условий, формы и переключатель периода сохраняют собственные правила. Полные браузерные наборы включают эти поверхности.

Проверены потребители общего `cabinet.css`: кабинетная оболочка с `data-cabinet-shell`, административная `.app-shell.admin-app-shell[data-admin-shell]` и отдельная форма `api/summary_autosend.py` без `.app-shell`/`.sidebar`. Новые правила не меняют административную оболочку; прежнее ограничение скрытия панели через `[data-cabinet-shell]` сохранено. Правила JS/NoJS и встроенной оболочки не изменены.

Программно сравнены исходники с указанным исходным SHA: после удаления только двух новых CSS-деклараций весь CSS совпадает побайтово. Нет новых обрезаний, `overflow: hidden`, подмен шрифта, изменений размеров или отступов, которые маскировали бы проблему. Во всем `apps/server` изменены только CSS и браузерный тест; шаблоны, JavaScript, API, обработчики POST, CSRF, версии полномочий, цены и согласия побайтово сохранены. Отдельно просмотрены исходные согласия: оферта обязательна и изначально не отмечена; необязательное разрешение автосписаний отмечено по умолчанию; возобновление требует отдельного обязательного неотмеченного согласия.

## Постоянная проверка без ослабления прежних условий

К существующей `checkCancellationReflow` добавлено 10 строк: `Range` получает фактические строки подписи кнопки и проверяет их в пределах самой кнопки и экрана с той же погрешностью 1 px. Таким образом, сжатая рамка с выступающим текстом больше не может пройти только по размеру кнопки.

После удаления только этого блока CJS побайтово совпал с исходным SHA. Прежние проверки, погрешности, таймеры, порядок остальных сценариев и матрицы не менялись. Сохранены 24 сочетания отмены на движок: 320/360/1280 px, две темы, 100/200%, JS on/off; клавиатурный фокус, видимость и отсутствие перекрытия, строки последствий, ровно один перехваченный нативный POST, CSRF и `expected_authority_version`. Сохранены все 16 административных сочетаний на движок, семь ссылок, клавиатура и синтетическая навигация.

## Собственные повторы окончательных байтов

Все повторы ниже выполнены reviewer на macOS без установки зависимостей. Каждый завершился с exit 0, без пропусков и ошибок. В pytest два существовавших предупреждения: imported fixture assertion rewriting и Starlette/httpx deprecation.

| Набор | Результат | Журнал |
|---|---|---|
| Shell/admin unit, billing clarity/purchase/ui, usability, copy convention | 338 passed, 1.17 s | `.dev/04-linux-final-contracts.log` |
| Полный `test_billing_accessibility.py`, Chromium | 20 passed, 64.69 s | `.dev/04-linux-final-chromium.log` |
| Тот же полный набор, WebKit | 20 passed, 85.71 s | `.dev/04-linux-final-webkit.log` |
| `node --check` измененного CJS и `git diff --check` | PASS | вывод собственных команд |

Встроенные 24 cancellation и 16 admin сочетаний входят в один browser pytest на движок и не прибавляются к 20 как отдельные pytest-тесты. Повторы автора и reviewer не суммируются в уникальное покрытие.

Команды из корня рабочей копии:

```sh
PYTHONDONTWRITEBYTECODE=1 apps/server/.venv/bin/python -m pytest -p no:cacheprovider apps/server/tests/unit/test_cabinet_web_shell.py apps/server/tests/unit/test_admin_overview_view_models.py apps/server/tests/unit/test_admin_audit_view_models.py apps/server/tests/contract/test_billing_clarity.py apps/server/tests/contract/test_billing_purchase_ui.py apps/server/tests/contract/test_billing_ui.py apps/server/tests/integration/test_billing_usability.py apps/server/tests/contract/test_copy_convention_contract.py -q --tb=short --show-capture=no
PYTHONDONTWRITEBYTECODE=1 apps/server/.venv/bin/python -m pytest -p no:cacheprovider apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no --basetemp=.dev/04-linux-final-chromium-tmp
GRAF_BROWSER=webkit PYTHONDONTWRITEBYTECODE=1 apps/server/.venv/bin/python -m pytest -p no:cacheprovider apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no --basetemp=.dev/04-linux-final-webkit-tmp
```

Контрольные суммы до и после собственных повторов совпали:

| Файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` | `f4ba435b5461e65a189c5fd85276031b22a9f64dabfad5cbe99101c375f477da` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `78a69c2e07363f1a4dab12e9f140be4f3bb4b8102c628e51aad5aee6c3750de4` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `e027b49d7a6a81a8937baaad5edba54495fd20b2d1feb5761cb0a5cd5f491989` |

## Условия дальнейшего закрытия

Требуются согласованный коммит, новый точный head/base, успешный штатный Ubuntu CI с прежней геометрией и матрицей, остальные обязательные PR-проверки и обычное слияние. При отсутствии нового Linux GREEN общий статус остается HOLD независимо от macOS PASS. Владелец выпуска затем выполняет новый frozen release-full и release/live gates; опубликованный ранее выпуск не доказывает эти новые байты.

Синтетическая маршрутизация не проверяет реальную серверную авторизацию административных страниц, сохранение POST в БД, реальные платежи, банк, возвраты, будущее автосписание, отправку писем или установленный GRAF Dev. Человеческая приемка T012/SC-005/006 и отдельные незакрытые задачи этим отчетом не подтверждены.
