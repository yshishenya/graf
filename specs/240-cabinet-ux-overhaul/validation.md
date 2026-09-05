# Validation record: feature 240

## Корректирующий проход 2026-09-06

Lane: `high-risk-product`, gate: `no deploy`. Данные и изображения синтетические.
Производственное изменение этого прохода ограничено `cabinet.css`; JS,
шаблоны и backend не менялись. Предыдущий theme PASS отозван; блоки ниже
этого раздела — исторические результаты, не доказательство новых исправлений.

### Итоговые проверки

Полная повторяемая команда: [quickstart.md](quickstart.md), раздел проверок
контрактов и сценариев. Последний прогон через изолированную PostgreSQL:

```text
369 passed, 2 warnings in 216.82s (0:03:36)
postgres_test_phase=focused status=pass duration_seconds=221
postgres_test_result=pass mode=focused
postgres_test_cleanup=isolated_container_removed
```

Набор включает list/detail/settings integration, playback/share/billing
contracts, общую разметку, доступность и новые 34 проверки темы/стенда.
Предупреждения: уже импортированная pytest fixture и устаревающая связка
Starlette TestClient/httpx. Новых зависимостей не добавлялось.

- Ruff для трёх изменённых Python-файлов: PASS.
- `node --check` для неизменённого `cabinet.js`: PASS.
- `git diff --check`: PASS.
- `python3 scripts/check_spec_kit_governance.py`: PASS.
- Отрицательный контроль через `assert_theme_palette_contract(css)` на
  `git show 8eb1bb8078140d51ae910197a613ce0999a98ed9:.../cabinet.css`:
  PASS — исходные правила отклонены, обнаружены две корневые палитры.

Промежуточные падения не скрыты: первый запуск без БД дал 249 passed и 6
fixture errors; прогон с PostgreSQL — 316 passed и 2 старых literal-assertions
для удалённых CSS-дублей. Их заменили актуальными семантическими контрактами,
не вернули мёртвые правила. Новый тест обнаружил hover-контраст 4,04:1;
цвет исправлен до 4,84:1. Промежуточный расширенный прогон дал 366 passed,
окончательный после всех доработок — 369 passed.

### Браузер, ревью и границы

Свежие измерения, снимки и ограничения: [light-theme-qa.md](light-theme-qa.md).
В частности: шесть комбинаций темы, реальные поля/окна, список с записями,
спикеры, удаление с отменой, вход/код, ошибка получателя и фактические
320/390/768/1024/1440 CSS px. Успешные backend-операции не имитировались.

Независимое correctness/Ponytail review выявило и повторно проверило исправления
контраста checked-controls и hover-кнопок, границ сегментов и active+hover/pressed.
Последнее замечание закрыто. Reviewer-owned UX checklist — 15/15 по качеству
требований; это не визуальный PASS всей реализации. Новый тест и стенд
подготовлены отдельным субагентом, не автором производственного CSS.

Сопоставление FR-009a/b/c/d, SC-007/008 с корректирующими T036–T040 подтверждает
CSS и тестовые исправления. Полная исходная F240-матрица, настоящий WKWebView,
успешные share/export операции, точная мышиная hover-матрица и оставшиеся
геометрические проблемы не объявляются пройденными. Полная convergence F240
не заявляется. Старые T001–T035 не заменяют эти проверки.

### PR gate

Пользователь явно подтвердил коммит, push и ревью. Исправления отправлены в
существующий PR #6560 коммитом `03a6974e11c003e538150b310cda5ec617ff7638`.
Свежий `governance-fast` на этом SHA:
[33995479492 — PASS](https://github.com/yshishenya/graf/actions/runs/33995479492).
Повторная локальная проверка перед коммитом: `106 passed`, 2 прежних
предупреждения; Ruff и Spec Kit governance — PASS.

[Повторное агентское ревью](https://github.com/yshishenya/graf/pull/6560#pullrequestreview-5123225841)
привязано к тому же SHA: блокирующих замечаний к корректирующему diff нет.
Это не независимое человеческое approval и не приёмка полной F240-матрицы.
Issue #6561 остаётся открыт, связь с PR — `Refs #6561`.

Первый run `33995456385` получил старое описание при push до обновления PR,
не прошёл проверку SHA и был отменён новым запуском. Защита не обходилась:
новый run проверил обновлённое описание и успешно завершил все обязательные
шаги. Старые runs от 2026-09-04 не использованы как подтверждение исправлений.

Эта запись добавлена отдельным документационным коммитом после успешной
проверки кода. Любой новый HEAD требует своего `governance-fast`: финальные
SHA и результат фиксируются в описании, Checks и итоговом комментарии PR,
без рекурсивного изменения документа ради собственного SHA.
Локальный fast CI заново не запускался: по текущей repository guidance он
ручной диагностический fallback. Полный CI, merge, release и deploy не
запускались. Итоговые focused-проверки не являются разрешением на merge.

## Исторические результаты 2026-09-04

Дата: 2026-09-04. Режим: `high-risk-product`, release gate: `no deploy`.

## Scoped cabinet checks

Команда запускалась из `apps/server`:

```sh
uv run --extra dev pytest -q \
  tests/contract/test_cabinet_frontend_foundation_contract.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_cabinet_shell_response_contract.py \
  tests/contract/test_settings_ui_contract.py \
  tests/contract/test_billing_ui.py \
  tests/contract/test_recording_share_ui_contract.py \
  tests/contract/test_billing_accessibility.py \
  tests/contract/test_recording_workflow_accessibility.py \
  tests/unit/test_cabinet_template_sections.py \
  tests/unit/test_cabinet_template_components.py \
  tests/unit/test_cabinet_web_shell.py
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
git diff --check
```

Результат: `279 passed`, 2 предупреждения сторонних библиотек; `node --check`
и `git diff --check` — PASS.

Дополнительный новый contract file:

```text
tests/contract/test_graf_ux_ui_contract.py
```

проверяет основные маршруты, landmarks, HTMX hooks, detail tabs/dialog/recovery,
no-JS fallback и standalone one-column shell.

Отдельный quickstart-набор с PostgreSQL через
`bash apps/server/scripts/run_local_postgres_tests.sh --focused`:

```text
207 passed, 2 warnings in 180.44s
postgres_test_result=pass mode=focused
postgres_test_cleanup=isolated_container_removed
```

Он включал list/detail/settings integration tests и подтвердил сохранение
запросов, маршрутов, состояний и embedded/standalone parity. Прямой запуск
этого набора без `TWOBRAIN_DATABASE_URL` ожидаемо не стартует; это
окруженческое требование, а не ошибка тестируемого кода.

## Browser smoke

Использован `tests.fixtures.calendar_visual_ui_harness` с production Jinja
templates и локальным static asset. Проверены:

- standalone `/meetings` в dark/light;
- standalone `/settings/integrations/calendar` в dark;
- embedded `/desktop/meetings` в dark;
- 320, 390, 768, 1024 и 1440 CSS px;
- filter disclosure, upload dialog, profile popover, keyboard Tab focus;
- отсутствие document-level horizontal overflow.

Проверяемые метрики после правки:

```text
320: scrollWidth=320, main=320, nav=flex, sidebar=none
390: scrollWidth=390, main=390, nav=flex, sidebar=none
768: scrollWidth=768, main=768, nav=flex, sidebar=none
1024: scrollWidth=1024, main=784, nav=none, sidebar=flex
1440: scrollWidth=1440, main=1200, nav=none, sidebar=flex
```

Обновление фильтра открыло существующий `details`, загрузка открыла существующий
native dialog и сфокусировала control выбора файла, закрытие вернуло управление
в toolbar, профильный popover открылся и сохранил фокус на trigger.

## Local fast diagnostic

```sh
GRAF_CI_ALLOW_DIRTY=1 infra/scripts/ci-local.sh --fast
```

Результат: `ci_local_result=pass mode=fast`; receipt имеет статус
`ambiguous/dirty_worktree_opt_in` по правилам самого скрипта. Состав receipt:

- governance tests: `224 passed`;
- server fast suite: `1362 passed`;
- changed server tests: `9 passed`;
- server lint, Python compile, shell syntax, CI contracts: PASS;
- production compose config, deployment evidence scan, whitespace and active CI
  documentation consistency: PASS;
- PostgreSQL fixture поднят в изолированном контейнере и удалён после проверки.

Это локальное диагностическое evidence, не замена GitHub `governance-fast` на
точном SHA PR. Полный CI и релизный gate не запускались: задача заканчивается
на PR, без production deploy.

Последний запуск на чистом коммите `883ac834f1f6cfb6c959c951e1b6835e51b6ab26`:
`ci-fast-883ac834f1f6-974e7d5dcc22`. Результат pipeline — `pass`, receipt —
`passed`; authoritative PR gate всё равно должен быть запущен GitHub на
финальном SHA после push.

## Ponytail review

Изменения остаются dependency-free и используют существующий server-rendered
шаблон, CSS и контрактные тесты. Новых абстракций, обработчиков JavaScript,
дублирующих функциональных путей или безопасного к удалению усложнения не
найдено: `Lean already. Ship.`

## Blockers and limitations

Первый ручной запуск playback contract без окружения дал ошибки fixture из-за
отсутствия `TWOBRAIN_DATABASE_URL`. Тот же PostgreSQL-backed fast lane затем
прошёл внутри рекомендованного изолированного контейнера. Свежий DB-backed
browser walkthrough detail/auth/billing/shared не заявляется; contract, unit и
static audit для этих поверхностей прошли.
