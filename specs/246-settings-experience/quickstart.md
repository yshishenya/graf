# Проверки F246

## Среда и границы

База: `107e7e692b896863f70ba632a101469d6f80e29a`, ветка `codex/246-settings-experience`.
Выбран `high-risk-product`: полный Spec Kit и профильные проверки. Все данные синтетические;
БД тестов — отдельные автоматически удаляемые контейнеры PostgreSQL. Общие dev/prod,
аккаунты, настройки записи и подписки пользователя не изменялись.

## Воспроизводимая проверка браузера

Из `apps/server` запустить:

```sh
PYTHONPATH=src:. .venv/bin/python -m uvicorn tests.fixtures.settings_visual_ui_harness:app --host 127.0.0.1 --port 8765 --no-access-log
```

Из корня репозитория, используя уже установленный Playwright:

```sh
NODE_PATH=/path/to/existing/node_modules node specs/246-settings-experience/visual-check.cjs
```

`SETTINGS_PREVIEW_URL` позволяет выбрать другой локальный порт. Новых зависимостей проекту
не добавлено. Проверка завершается ненулевым кодом при ошибке; результаты и синтетические
снимки записываются в `/tmp/graf-f246-*`. Preview использует настоящие шаблоны и CSS/JS,
не обращается к БД/провайдерам. POST перехватывается или обслуживается тестовой заглушкой.

## Сервер

Из корня:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
 tests/contract/test_settings_ui_contract.py \
 tests/contract/test_calendar_settings_contract.py \
 tests/integration/test_calendar_settings_flow.py \
 tests/integration/test_settings_ia_flow.py \
 tests/contract/test_account_routes.py \
 tests/contract/test_provider_link_settings_contract.py \
 tests/contract/test_billing_ui.py \
 tests/contract/test_billing_accessibility.py \
 tests/unit/test_settings_view_models.py \
 tests/unit/test_cabinet_web_shell.py \
 tests/unit/test_cabinet_template_components.py \
 tests/unit/test_cabinet_template_sections.py \
 tests/unit/test_settings_outcomes.py -q -o addopts=''
```

## macOS

```sh
swift test --package-path apps/macos --filter 'MeetingDetectionPolicyTests|AppControlAccessibilityTests|CaptureControlTests|DesktopCabinetRoutePolicyTests|DesktopCabinetWorkspaceTests|MeetingDetectionCountdownTests|MeetingDetectionRecordingLifecycleTests'
swift build --package-path apps/macos
```

## Результаты 2026-09-06

| Проверка | Результат |
|---|---|
| 13 профильных Python suites, изолированная PostgreSQL | 348 passed, 86.96 s |
| Финальные settings contracts + outcomes после исправлений CSS | 56 passed |
| Swift: правила, миграция, countdown, capture, маршруты, доступность оболочки | 173 passed; повтор после системного alert — 173 passed |
| Swift build | PASS; существующие предупреждения `@preconcurrency` в EmbeddedCabinetWebView |
| Геометрия 9 страниц × 2 оболочки × 2 темы × 5 ширин | 180/180 PASS; разница полей ≤2px, горизонтального переполнения нет |
| Формы профиля | pristine → dirty → reset → saving; повторная отправка блокируется |
| Ошибка / повторный вход / недоступность | PASS; корректные классы и видимый текст, reauth POST+CSRF |
| Tab/Shift-Tab, видимый фокус, forced colors | PASS для формы профиля; это не полная сертификация доступности |
| Масштаб 200% | PASS на аккаунте через CSS zoom 2 при viewport 1440px |
| JavaScript выключен, browser и embedded | Поле редактируется, submit доступен, POST содержит CSRF; запрос перехвачен, реальные данные не меняются |
| Открытые подсказки Email/calendar/manual upload | PASS; дополнительно независимый reviewer проверил 20 hover/focus состояний на 320/390px |
| Computer Use | Установленный Krisp 3.15.6; GRAF synthetic browser: редактирование имени и отмена через настоящий интерфейс |
| Нативный render | Реальный NSHostingController, окно 820×600, 10 синтетических приложений, длинное имя, mixed rules; снимок просмотрен |
| Независимый correctness/Ponytail review | Все 3 P2 исправлены и перепроверены; открытых замечаний к коду нет, лишних абстракций нет |
| Ruff, JavaScript syntax, diff whitespace | PASS |
| Frozen bootstrap doctor | PASS |
| `GRAF_CI_ALLOW_DIRTY=1 infra/scripts/ci-local.sh --fast` | PASS, 187 s: 1424 server + 80 changed tests + 66 CI contracts и остальные fast стадии |

Fast запускался до последних локальных исправлений alert/tooltip и добавления сохраняемого
preview. После них повторены профильные Swift/Python/browser/линтер проверки.
Fast evidence имеет `status=ambiguous`, поскольку дерево не закоммичено. Это диагностический
результат, не exact-SHA доказательство для merge/release. Full CI и публикация не выполнялись.

## Ручная проверка macOS после обновления master

Блокировка Mac больше не мешает: через Computer Use открыта пересобранная тестовая
программа с настоящим `MeetingDetectionSettingsView`, 10 синтетическими приложениями и
заведомо недоступным хранилищем. Список прокручен вниз; попытка изменить Winter Room
вызывает системное предупреждение с фокусом на `alert`. Escape закрывает предупреждение,
прежнее `Спрашивать` остаётся выбранным; прокрутка сохраняется.

В ходе проверки исправлены одинаковые доступные названия трёх кнопок: теперь группа
имеет имя приложения и текущее значение, а каждая кнопка — собственное название правила.
AX tree окончательной сборки подтверждает `Winter Room: Всегда / Спрашивать / Никогда`
и selected trait только у выбранного правила. Звуковой прогон VoiceOver не выполнялся;
не заявляется полная сертификация доступности. Реальные настройки пользователя не менялись.

## Convergence и закрытие

Проверены FR-001–009, SC-001–004, три пользовательских сценария и пять решений plan;
проверены применимые ограничения capture/consent, локального хранения правил, auth/CSRF,
правдивого удаления и независимой реализации. Невыполненных работ по реализации не найдено;
новые convergence tasks не требуются. T005 остаётся открытой только до звукового прогона VoiceOver; ручная проверка ошибки и AX завершена.
GitHub issues остаются открытыми до завершения соответствующих проверок и PR evidence.
Commit, PR/merge, установленное приложение и deploy требуют отдельного этапа.

## Повторная проверка после синхронизации с master — 2026-09-06

- Текущая база: `6ff8db3ee18dc7faf52fd8a31c8bade97c5ca548`, +17 upstream коммитов.
  HEAD совпал с удалённым master при заключительной проверке `git ls-remote`.
- Локальные изменения сохранены перед fast-forward и восстановлены. Резервный stash:
  `24384233a2dcdb41e0fd34a557ff626fce33757d`; не удалён. Коммит реализации не создавался.
- Единственный конфликт CSS разрешён в пользу текущего Popover из master. Удалены старые
  локальные поправки tooltip; обе стороны проверки подтверждают актуальное поведение.
- Удалены поздние width/max-width 900px, перекрывавшие общую колонку: обычные страницы
  остаются 780px, оплата — 880px. Новый текст/aria-describedby русского интерфейса сохранён.
- Расширенный набор 17 серверных suites: **466 passed**, 96.50 s.
- Браузерный сценарий обновлён под Popover: **180/180** геометрии, формы, состояния,
  клавиатура, 200%, forced colors, no-JS, открытие и Escape подсказок — PASS.
- Независимый reviewer: **36** проверок Popover (3 поверхности, 2 оболочки, 2 ширины,
  hover/focus/click), границы экрана и Escape — PASS; совместимость форм/защит — PASS.
- macOS с WebKit regression tests: **185 passed**; после исправления AX labels повтор —
  **185 passed** (8.62 s). Проверка через Computer Use выполнена на окончательной сборке.
- Диагностический `GRAF_CI_ALLOW_DIRTY=1 infra/scripts/ci-local.sh --fast`: **PASS**, 215 s;
  внутри **801 Swift**, **1426 server unit**, **80 changed server**, **66 CI contracts**.
  После этого цикла окончательная доступность кнопок дополнительно проверена 185 Swift tests.
- Evidence: `.dev/ci-evidence/ci-fast-6ff8db3ee18d-373e5e8b736f.json`, status=ambiguous
  из-за незакоммиченного дерева. Это не full CI и не merge/release attestation.
- Ruff, JS syntax, diff whitespace и отсутствие unmerged paths: PASS.
- Финальная визуальная проверка выявила растяжение поля часового пояса из-за нового
  пояснения языка в master. В общей сетке полей добавлено `align-items: start`; проверка
  теперь измеряет одинаковые Y/высоту соседних select. Повторно **180/180** browser checks
  и **57** settings/theme contracts — PASS. Эта последняя CSS-поправка выполнена после fast.
- Независимый reviewer подтвердил финальную структуру доступности нативных кнопок:
  отдельные имена действий, selected trait, группа с текущим значением; новых замечаний нет.

## Звуковая приёмка владельцем — 2026-09-07

На отдельной GRAF Release QA владелец проверил нативные настройки автозаписи:
названия приложений и действий, выбранное правило, навигацию VoiceOver и возврат
без мыши. Подтверждение: «проверил. Все нормально». T005 завершена. Это результат
ручной проверки человеком, а не прослушивание агентом. Нативный состав соответствует
`ae593ee63d64a70809c5b254299a1f7dba1bd979`.
Evidence: https://github.com/yshishenya/graf/pull/6762#issuecomment-5565072923.
