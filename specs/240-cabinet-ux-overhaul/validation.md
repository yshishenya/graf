# Validation record: feature 240

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
