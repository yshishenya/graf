# Validation and convergence — 2026-09-11

## Scope and source
High-risk product area (auth/sessions/UX), full Spec Kit. Base origin/master: `ad71f2ce4db68d846d7c333213961c5f5f7d5e89`. Локальная незакоммиченная реализация; это не exact-SHA PR/CI или release evidence.

## Requirements gate
Clarify завершён, analyze: CRITICAL 0 / HIGH 0 / MEDIUM 0. Независимый reviewer session_flow: requirements 2/2, security 3/3, UX 3/3 PASS. Issue canon: 288 issues checked, PASS; задачи связаны с #6926–#6929, umbrella #6925.

## Implementation and checks
- История и счётчик удалены из шаблона. Действующий фильтр, сортировка, данные и авторизация сохранены. Неизвестные действующие клиенты видимы, одинаковые названия не объединяются.
- Scope виден у заголовка; счётчик относится к другим действующим входам. Подписи, подтверждение, ошибка и повторный вход согласованы.
- До правки шаблона новые проверки давали 4 expected failures на истории/старых действиях; после изменения проходят.
- `uv run --extra dev pytest tests/contract/test_account_routes.py tests/unit/test_settings_view_models.py -q`: 75 passed.
- `bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/unit/test_auth_session_clients.py`: 17 passed, временный контейнер удалён.
- `bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_account_lifecycle.py -k session`: 7 passed / 12 deselected, временный контейнер удалён.
- После усиления проверки текста подтверждения и исчезновения завершённого входа: тот же runner с `-k session_confirmation`: 2 passed / 17 deselected. Обычная и embedded ветви подтверждены, повторное завершение безопасно; текущий доступ сохраняется.
- Итого 99 уникальных focused tests; последние 2 — повторная проверка изменённых утверждений, не дополнительные уникальные тесты.
- Ruff для четырёх изменённых Python-файлов (rendering, settings routes, contract, integration): PASS.
- `git diff --check`: PASS. `validate-changelog-fragments.py`: PASS.
- Первый запуск auth_session_clients напрямую дал 10 setup errors без TWOBRAIN_DATABASE_URL; исправлен способ запуска через штатный изолированный PostgreSQL runner, последующий полный файл PASS.

## Browser evidence
Синтетические страницы собраны реальным render_settings_page с реальными CSS/JS, без частных данных. Playwright Chromium:
- Web/embedded × light/dark × 390/1280 px: 8/8 PASS, без горизонтального переполнения, native details открываются/закрываются Enter.
- JavaScript disabled: active, current-only, unavailable и confirmation при 390 px: 4/4 PASS. Нет ложного bulk при нуле других, ошибку не выдают за пустоту, форма confirm=1 и отмена имеют корректные цели.
- Скриншоты локально: `output/playwright/f6794-desktop-dark.png`, `f6794-mobile-light.png`, `f6794-confirmation-mobile.png`. Desktop dark и mobile light просмотрены визуально.
- Формы/отзыв проверены настоящим integration test через HTTP TestClient и PostgreSQL. Синтетическая статическая браузерная страница не выдаётся за backend e2e или установленный GRAF Dev.

## Converge
FR-001–009, SC-001–004, US1/US2 покрыты реализацией и перечисленными проверками. Нереализованных требований в локальном изменении не найдено, новые задачи не нужны. AuthSession/history в хранилище не удаляются. Последний mandatory acceptance остаётся в T004: exact-SHA governance-fast и review после одобрения коммита.

## Remaining gates
`python3 scripts/check_spec_kit_governance.py`: BLOCKED по environment drift — локальный specify v1.0.4/ref cb610277fdea781fcfa83d20522c2db37c94068d, lock требует v1.0.1/ref 9118ed15a0ba65053469a94c560ea5d233f75884. Lock byte-identical с HEAD; global tools и governance не менялись. Отдельная проверка repository invariants без runtime doctor: PASS, не заменяет полный gate.
Implementation ready; tracker pending. Коммит, PR, governance-fast exact SHA, merge, release-full и deploy не выполнены. Issues остаются OPEN до положенного evidence; текущий пользовательский запрос не является разрешением на коммит после проверки или выпуск. GRAF Dev не пересобирался/не запускался.

## T005 — утверждённый компактный интерфейс, 2026-09-11
Risk/validation lane: high-risk auth/UX, полный Spec Kit. Требования и новые checklists независимо проверены session_flow: PASS, все замечания закрыты. Повторный code review шаблона/CSS/JS/тестов: PASS, findings отсутствуют.

- Contract + view-model: 83 passed (`uv run --extra dev pytest tests/contract/test_account_routes.py tests/unit/test_settings_view_models.py -q`). Включены 8 новых комбинаций одиночной/массовой/исчезнувшей цели/пустого массового подтверждения × web/embedded.
- PostgreSQL integration: 7 passed, 12 deselected (`bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_account_lifecycle.py -k session`). Проверены CSRF, доступ до confirm, реальное завершение, повторное завершение, текущий вход, актуальный результат. Изолированный контейнер удалён штатно.
- Ruff изменённых Python файлов, `node --check cabinet.js`, `git diff --check`, `validate-changelog-fragments.py`: PASS.
- Playwright Chromium, реальный render_settings_page с синтетическими данными: 8 сочетаний web/embedded × light/dark ×390/1280 PASS. Строки на широком экране 69–70 px, в узком embedded с переносом 84 px; кнопки 44 px. Горизонтального переполнения нет, native details раскрывается Enter.
- 8 состояний подтверждения web/embedded × single/bulk/missing/empty_bulk: фокус на отмене, Escape и нажатие отмены убирают только панель и возвращают фокус к правильной кнопке либо заголовку — PASS.
- Без JS: 14 состояний web/embedded × active/alone/unavailable/confirmation/bulk/missing/empty_bulk — PASS. Подтверждение содержит POST + CSRF + confirm=1, отмена ведёт к существующему якорю; native details работает. Масштаб CSS 200% при 1280 px и длинное имя при 390 px — без переполнения в обеих формах кабинета.
- Скриншоты `output/playwright/f6794-compact-{web,embedded}-{light,dark}-{390,1280}.png`, `f6794-compact-confirmation-mobile.png`, `f6794-compact-embedded-zoom200.png`; desktop/mobile/confirmation/zoom просмотрены визуально.
- Браузерные результаты: `output/playwright/f6794-compact-browser-results.txt` и `f6794-compact-extra-results.txt`. Попытка дополнительного browser route-макета полного отзыва завершилась timeout на искусственном redirect и не использована как evidence. Реальный серверный путь подтверждён HTTP TestClient + PostgreSQL; браузер проверяет реальную разметку и клиентские действия, не backend e2e.

### Повторный converge
FR-010–011 покрыты T005, FR-001–009 сохранены. Единый список/счётчик, native disclosure, соседнее подтверждение, безопасная отмена и fallback реализованы. Нового незапланированного кода или непокрытой функциональности не найдено. T004 остаётся открытой до exact-SHA governance-fast; дублирующих задач converge не добавляет.

### Остаток общей проверки
Повторный `check_spec_kit_governance.py` блокирован тем же несовпадением установленного specify 1.0.4 и закреплённого 1.0.1. Repository invariants с run_doctor=False PASS; это не полный gate. Коммит/PR/CI/deploy и проверка установленного GRAF Dev не выполнялись. Все соответствующие issues OPEN; локальная реализация не объявляется выпущенной.

## Подготовка PR и релиза по запросу пользователя
После предъявленных результатов пользователь запросил подготовку PR и релиза; это разрешает фиксацию и отправку проверенного изменения. Перед коммитом выполнен fetch `origin/master`: base HEAD и master совпадают (`ad71f2ce4db68d846d7c333213961c5f5f7d5e89`), конфликтов или новых изменений базы нет.

Блокер локального runtime doctor разрешён без изменения global tools: в игнорируемом `.dev/f6794-tools/` установлены specify-cli 1.0.1 из закреплённого ref и bootstrap 0.9.9 с SHA-256 из GitHub workflow. Полный `check_spec_kit_governance.py` с этим PATH: PASS (bootstrap integrity + GRAF invariants). Прежние записи о блокере описывают предыдущий запуск.

Ponytail review: существующие модели доступа, icons, native details/forms и стандартный DOM; новых зависимостей или лишних абстракций нет, net: 0 lines to remove. Фокус и защита отмены сохранены. `release-preparation.md` содержит русские заметки, границы, порядок выпуска и откат. CD dry-run: PASS как план команд, candidate ещё не supplied; production не затронут.


## GitHub PR evidence
PR: https://github.com/yshishenya/graf/pull/6942
PR SHA реализации: `0a54cf79a6e6a4418f42ac6212d26e7795208c5a`.
- governance-fast: PASS https://github.com/yshishenya/graf/actions/runs/34609124722
- pr-metadata: PASS https://github.com/yshishenya/graf/actions/runs/34609124829

T004 закрыта в tasks.md по локальным проверкам, независимому review и GitHub gate. Последующее изменение только документации и синтетических снимков проходит новый GitHub gate на финальном SHA; итоговая ссылка находится в PR, чтобы не создавать рекурсивные evidence-коммиты. Перед merge обязательно проверить именно текущий SHA.

Снимки для рецензента сохранены в `reference/` и снабжены описанием происхождения. PR и задачи связаны; ни task-backed issues, ни umbrella не закрываются этим evidence до предусмотренного closeout. Изменение готовится к выпуску, но не опубликовано.
