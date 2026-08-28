# Quickstart: Проверка playback layout

## Focused contracts

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/unit/test_cabinet_web_shell.py \
  -k 'playback or speaker_timeline or rail_ready_state_geometry or profile_menu'
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
```

Expected: `13 passed`; contract требует grid-row placement и не допускает fixed/clearance compensation.

## Runtime geometry matrix

```sh
GRAF_NODE_MODULES=/path/to/node_modules node \
  specs/205-playback-panel-layout/evidence/playback-layout-runtime-check.cjs

GRAF_BROWSER=webkit GRAF_NODE_MODULES=/path/to/node_modules node \
  specs/205-playback-panel-layout/evidence/playback-layout-runtime-check.cjs
```

Если `playwright` уже доступен обычному Node resolution, переменную
`GRAF_NODE_MODULES` можно не задавать.

Verifier рендерит synthetic meeting через production renderer и проверяет:

1. Standalone web: широкий и узкий viewport.
2. Desktop embedded: collapsed и expanded rail, включая ширину до 1120px.
3. Playback: available, preparing/unavailable и увеличенная speaker timeline.
4. Standalone web без playback и no-JS narrow layout.
5. Открытое profile menu и правое подменю поверх playback в Chromium и WebKit.

Для каждого состояния сравниваются DOM rectangles по [layout contract](contracts/playback-layout.md): границы main и playback совпадают, `main.bottom == playback.top`, scrollbar не заходит в playback и content достигает конца прокрутки.

## Repository gate

```sh
git diff --check
infra/scripts/ci-local.sh --fast
```

## Release gate

После validated commit approval: PR/merge, clean master exact SHA, `infra/scripts/cd-remote.sh --dry-run`, CalVer release и production smoke по `docs/agent-guidance/release-and-validation.md`.

## Evidence

- TDD red phase: 5 ожидаемых падений подтвердили старый viewport-fixed контракт.
- Focused contracts: `13 passed, 135 deselected`; `node --check` — PASS.
- Полные затронутые static/render suites: `148 passed`.
- Затронутые DB integration tests в disposable Postgres: `29 passed`, контейнер удалён.
- Runtime matrix: 11 состояний web/desktop-embedded, wide/narrow, rail
  expanded/collapsed, preparing/unavailable, увеличенный timeline, страница без
  playback и no-JS narrow; overlap, gap, left/right delta и horizontal overflow
  — `0 px`, прокрутка до последнего элемента доступна.
- Visual review: `web-wide`, `web-narrow`, `embedded-wide` и
  `embedded-narrow` — PASS.
- Review remediation: затронутые non-DB contracts — `203 passed`; DB contracts
  через disposable Postgres — `9 passed`, контейнер удалён; access-loss runtime
  останавливает, очищает и удаляет playback до safe recovery main.
- После синхронизации с `origin/master` (`ee8210e0`) focused и runtime matrix
  повторены без расхождений; новый base содержал release metadata, а не cabinet
  layout.
- Repository gate: `git diff --check` — PASS;
  `infra/scripts/ci-local.sh --fast` — `1235 passed`, lint/compile — PASS,
  disposable Postgres удалён.
- Production regression T006: до исправления runtime contract фиксировал
  `menuTopLayer=false`; после исправления Chromium и WebKit matrix прошли по 12
  состояний без ошибок. Для expanded sidebar и длинного email подтверждены
  `menuTopLayer=true`, `menuTriggerGap=8px`, видимый правый край и подменю внутри
  viewport; playback не дублируется. Затронутые static/render suites —
  `148 passed`; повторный fast gate — `1235 passed`, lint/compile — PASS.
- После переноса diff на актуальный `origin/master` (`84e7cd75`) затронутые
  suites, обе browser matrix и fast gate повторены с тем же PASS-результатом.
- Полный CI не запускался по явному ограничению пользователя; это не PASS
  полного CI.
