# Tasks: Надёжный GitHub CI для PR

## Phase 1: Workflow

- [X] T001 Добавить pinned installation `specify-cli` и `speckit-bootstrap` в `governance-fast.yml`.
- [X] T002 Проверить exact-SHA workflow на PR #6361 (governance-fast run #33635356354, SHA `b66ede945192cbf6308a004e55528bc7b67c1b09`).
- [X] T003 Проверить exact-SHA workflow на PR #6362 (governance-fast run #33637377154, SHA `23d8cddcbd985914b1b20cf225ceb999f7edc9b5`).

## Phase 2: Repository enforcement

- [X] T004 Включить GitHub Actions и проверить repository permissions.
- [X] T005 Добавить `governance-fast` в required status checks при нулевом approval для sole owner.
- [X] T006 Обновить операторскую документацию: GitHub check authoritative, local CI fallback.

## Phase 3: Closeout

- [X] T007 Выполнить focused governance tests и workflow validation.
- [X] T008 Добавить русский closure evidence в issue #6363 (final closure comment #5510595506).

## Dependencies

T001 -> T002,T003 -> T004,T005 -> T006,T007 -> T008

## Legacy Impact

`untouched`: локальный fallback сохранён, новые legacy пути не добавляются.
