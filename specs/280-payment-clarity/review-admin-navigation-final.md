# Независимый обзор исправления административной навигации

Дата: 2026-10-16. Роль: independent_4_payment, независимый reviewer и контролер слияния PR #7616. Область: дополнение T069 после discussion_r4290295731. Полоса проверки: существующий `high-risk-product`; текущий обзор разрешает подготовку коммита, но не заменяет новые GitHub проверки и выпуск.

## Итог

**SOURCE/BROWSER REVIEW PASS. Критических замечаний 0, высоких 0, исправимых средних 0.** Исходное замечание Codex подтверждено, минимальное исправление и содержательная регрессия проверены независимо. До коммита проверены рабочие байты поверх `c6dca30e522f3f1580a53cfdf2eeaf1b75683c84`, база PR `fb78b469aa7c22ad680424411025166870856b22`. Итоговый SHA коммита должен получить собственные точные head/base проверки.

Предыдущий общий CSS скрывал административную панель при ширине до 980 px. Единственная новая продуктовая правка добавляет `[data-cabinet-shell]` к этому hide-selector. Медиаграница, проверка NoJS, исключение `desktop-embedded`, непосредственный потомок и значение `display: none` сохранены. Проверка всего CSS подтвердила, что других отличий от указанного исходного коммита нет.

## Все производственные потребители общего CSS

- `cabinet/base.html` и `cabinet/components/sections.html`: настоящая `.app-shell` имеет `data-cabinet-shell` в самостоятельном и встроенном режимах. Новое ограничение сохраняет исходное исправление NoJS; встроенная оболочка остается исключенной.
- `admin/base.html`: загружает `cabinet.css`, затем `admin.css`; имеет `.app-shell.admin-app-shell[data-admin-shell]`, без `data-cabinet-shell` и `cabinet.js`. Новое правило больше не совпадает. Узкое административное правило `display: block` для оболочки и `display: flex` для панели снова действует.
- Форма в `api/summary_autosend.py`: загружает `cabinet.css`, но не создает `.app-shell`/`.sidebar`; новый селектор ее не затрагивает.

Других производственных конструкторов `.app-shell` или потребителей `cabinet.css` поиск по исходникам `apps` не обнаружил. Административные шаблоны, CSS, модель навигации, полномочия, кабинетный JavaScript, финансовые формы и обработчики этим исправлением не изменены.

## Проверка постоянной регрессии

Python harness отдельно рендерит настоящий `admin/base.html` штатными `render_template` и `admin_navigation`; административный HTML не подмешивается в словарь billing pages. Существующий CJS загружает оба настоящих CSS в порядке шаблона. Проверяет отсутствие искусственного `data-cabinet-shell`, признака готовности кабинета и `cabinet.js`, видимость панели и всех семи штатных ссылок, достижимость каждой через Tab/Option-Tab, контур фокуса, границы экрана и отсутствие перекрытия. Enter на ссылке пользователей дает ровно два синтетических GET, затем панель остается видимой.

Матрица: 320/360/980/1280 px, светлая/темная тема, JavaScript включен/выключен — 16 административных сочетаний на движок. Проверено программным сравнением: после удаления только добавленного административного сценария, его констант и вызова прежний CJS совпадает побайтово с исходником. Старые assertions, порядок остальных проверок и таймеры не ослаблены; прежние 24 сочетания cancellation на движок сохранены.

Прочитаны постоянные RED-журналы `.dev/admin-regression-red-chromium.log` и `.dev/admin-regression-red-webkit.log`: оба падают на `admin: 320px, light, JS=false: admin sidebar visible`, по одному failed и 19 deselected. Причина совпадает с просмотренными CSS и реальной административной оболочкой; ошибки зависимостей или авторизации за RED не выдаются.

Дополнительно reviewer самостоятельно выполнил причинный probe на реальном `admin/base.html`, семи синтетических ссылках, исходном CSS фиксированного коммита и той же единственной замене селектора в памяти. Chromium и WebKit: по 20 сочетаний old/scoped × 320/360/980/981/1280 × JS on/off. Старое правило дает скрытую панель и 0 доступных ссылок до 980 px; scoped дает семь видимых ссылок с клавиатурой, контуром фокуса и допустимой геометрией. На 981/1280 поведение сохранено. Этот probe дополняет постоянную матрицу проверкой соседней ширины 981 px.

## Собственные повторные проверки итоговых байтов

| Набор | Результат | Журнал |
|---|---|---|
| Полные shell/admin unit, billing clarity/purchase/ui, usability и copy convention | 338 passed, 0 failed, 0 skipped; 1.52 s | `.dev/04-admin-final-contracts.log` |
| Полный `test_billing_accessibility.py`, Chromium | 20 passed, 0 failed, 0 skipped; 64.87 s | `.dev/04-admin-final-chromium.log` |
| Тот же полный набор, WebKit | 20 passed, 0 failed, 0 skipped; 84.77 s | `.dev/04-admin-final-webkit.log` |
| Ruff измененного Python, `node --check` CJS, `git diff --check` | PASS | вывод независимых команд |

В каждом pytest запуске два прежних предупреждения: imported-fixture assertion rewriting и Starlette/httpx deprecation. Ошибок и пропусков нет. Встроенные 16 административных и 24 cancellation сочетания входят в один browser pytest на движок; их нельзя прибавлять к 20 как отдельные pytest-тесты. Повторы исполнителя и reviewer также не суммируются в уникальное покрытие.

Команды reviewer из корня существующей рабочей копии, без установки зависимостей:

```sh
PYTHONDONTWRITEBYTECODE=1 apps/server/.venv/bin/python -m pytest -p no:cacheprovider apps/server/tests/unit/test_cabinet_web_shell.py apps/server/tests/unit/test_admin_overview_view_models.py apps/server/tests/unit/test_admin_audit_view_models.py apps/server/tests/contract/test_billing_clarity.py apps/server/tests/contract/test_billing_purchase_ui.py apps/server/tests/contract/test_billing_ui.py apps/server/tests/integration/test_billing_usability.py apps/server/tests/contract/test_copy_convention_contract.py -q --tb=short --show-capture=no
PYTHONDONTWRITEBYTECODE=1 apps/server/.venv/bin/python -m pytest -p no:cacheprovider apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no --basetemp=.dev/04-admin-final-chromium-tmp
GRAF_BROWSER=webkit PYTHONDONTWRITEBYTECODE=1 apps/server/.venv/bin/python -m pytest -p no:cacheprovider apps/server/tests/contract/test_billing_accessibility.py -q --tb=short --show-capture=no --basetemp=.dev/04-admin-final-webkit-tmp
```

## Контрольные суммы SHA-256

Сверены до и после собственных повторов; совпали с сообщенными исполнителем:

| Файл | SHA-256 |
|---|---|
| `cabinet/static/cabinet/cabinet.css` | `c93c799c35ef57aac56bc032c9c00655d85ce0f59fc9521d68742195ff46094c` |
| `tests/browser/billing-accessibility.test.cjs` | `1a4301f54a13aa45150ba910229d6c0c528fbc88a0910ac6f00963c0cbf08183` |
| `tests/contract/test_billing_accessibility.py` | `e027b49d7a6a81a8937baaad5edba54495fd20b2d1feb5761cb0a5cd5f491989` |

Пути таблицы относятся к `apps/server/src/twobrain_rec_server/` для CSS и `apps/server/` для тестов.

## Границы и оставшиеся ворота

Реальные шаблон, стили, браузерная доступность и нативная навигация проверены на синтетических данных. Маршрутизация GET на тот же HTML не доказывает серверную авторизацию или содержание `/admin/users`; кабинетный перехваченный POST не доказывает сохранение в БД. Нет утверждений о полной WCAG-приемке, понимании людей, установленном GRAF Dev, реальных платежах или доставке писем.

После подготовленного исполнителем коммита необходимы новый точный SHA/base, полный `validate-pr-checks.py`, ответ на замечание Codex с текущими доказательствами, решение обсуждения и обычное match-head squash merge без обходов. T069/#7613 и T070/#7614 не закрыты этим отчетом; требования release/live остаются у назначенных владельцев. Опубликованный v2026.10.16.2 на `fb78b469aa7c22ad680424411025166870856b22` не содержит это исправление. Reviewer изменил только данный отчет и собственные синтетические материалы/журналы в `.dev`, не менял код, тесты, другие документы, GitHub, коммиты или выпуск.
