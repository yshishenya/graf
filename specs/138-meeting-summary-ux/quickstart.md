# Quickstart: meeting-summary-ux

Команды выполняются из `/Users/yshishenya/.codex/worktrees/632e/crisp`.

## Focused checks

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_outcomes.py -q
```

Проверить только изменённый UI contract:

```sh
cd apps/server
uv run --extra dev pytest \
  tests/unit/test_cabinet_web_shell.py -k 'outcome or detail_shell' -q
```

## Browser runtime

```sh
GRAF_NODE_MODULES=/Users/yshishenya/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
  /Users/yshishenya/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  specs/138-meeting-summary-ux/evidence/summary-runtime-check.cjs
```

Runtime fixture MUST быть synthetic и metadata-only. Проверить desktop 1440×900
и mobile 390×844: order, owner/due, source controls, URL hash, collapsed
secondary sections, no horizontal overflow, fixed player spacing и отсутствие
английских category labels.

## Repository gate

```sh
git diff --check
infra/scripts/ci-local.sh --fast
```

Full lane/release/deploy не запускается автоматически: для него требуется
отдельный release request и approval. Production data mutation не входит в
feature.

## Последнее evidence

- 2026-08-04: focused disposable PostgreSQL lane — `77 passed`.
- 2026-08-04: synthetic browser runtime — 4 сценария (`web-stored` desktop/mobile,
  `embedded-stored` mobile, `embedded-blocked` mobile), `failures: []`;
  horizontal overflow `0`, player spacing безопасен, secondary disclosure
  collapsed, private content отсутствует.
- 2026-08-04: `infra/scripts/ci-local.sh --fast` — `862 passed`, lint и Python
  compile passed; Swift validation штатно skipped fast lane.
- 2026-08-04: после reference review UI упрощён: secondary sections закрыты по
  умолчанию, inline summary export CTA удалена, existing meeting menu сохранён.
- Известное ограничение: поиск по расшифровке, история ручных правок и внешние
  task integrations остаются отдельным P2 slice; эта фича использует только
  существующие source seek и export primitives.
