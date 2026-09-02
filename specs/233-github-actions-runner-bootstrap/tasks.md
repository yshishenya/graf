# Tasks: Надёжный GitHub CI для PR

## Phase 1: Workflow

- [X] T001 Добавить pinned installation `specify-cli` и `speckit-bootstrap` в `governance-fast.yml`.
- [ ] T002 Проверить exact-SHA workflow на PR #6361.
- [ ] T003 Проверить exact-SHA workflow на PR #6362.

## Phase 2: Repository enforcement

- [X] T004 Включить GitHub Actions и проверить repository permissions.
- [X] T005 Добавить `governance-fast` в required status checks при нулевом approval для sole owner.
- [X] T006 Обновить операторскую документацию: GitHub check authoritative, local CI fallback.

## Phase 3: Closeout

- [X] T007 Выполнить focused governance tests и workflow validation.
- [ ] T008 Добавить русский closure evidence в issue #6363.

## Dependencies

T001 -> T002,T003 -> T004,T005 -> T006,T007 -> T008

## Legacy Impact

`untouched`: локальный fallback сохранён, новые legacy пути не добавляются.
