# Implementation Plan: Аккуратная нижняя панель воспроизведения

**Branch**: `codex/205-playback-panel-layout` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

## Summary

Перенести playback из viewport-fixed слоя в отдельную нижнюю строку уже существующего cabinet shell. Sidebar занимает обе строки, meeting content прокручивается только в верхней content-cell, а playback автоматически следует за текущей шириной content-column. Удалить ставшие ненужными CSS/JavaScript компенсации высоты и горизонтальной координаты.

## Technical Context

**Language/Version**: Jinja HTML, CSS Grid, vanilla JavaScript, Python 3.13 tests

**Primary Dependencies**: существующий server-rendered cabinet shell; новых зависимостей нет

**Storage**: N/A

**Testing**: pytest static/render contracts, существующий Node syntax/runtime harness, реальная browser geometry review

**Risk / Validation Lane**: `significant-feature` — меняется общий layout-контракт meeting detail в web и desktop-embedded поверхностях, без high-risk product domain

**Release Gate**: focused validation + `infra/scripts/ci-local.sh --fast`; production release следует отдельному release/deploy gate после validated commit approval

**Target Platform**: современные браузеры и macOS WKWebView desktop-embedded cabinet

**Project Type**: server-rendered web cabinet внутри web и desktop shell

**Performance Goals**: ноль layout polling и resize-observer работы для размещения панели; resize остаётся нативным grid reflow

**Constraints**: панель постоянно видима; один scrollbar у content-area; без изменения playback/audio semantics, DOM control order и API

**Scale/Scope**: один shared shell, meeting detail template, CSS/JS contracts и затронутые responsive states

## Constitution Check

### Before research

- PASS — Capture, consent, audio routing, privacy, storage, deletion и AI boundaries не меняются.
- PASS — Значимый shared UX оформлен отдельным Spec Kit slice с testable contract.
- PASS — Сохраняются видимые playback controls, keyboard resize и reduced-motion.
- PASS — Ponytail: переиспользуется существующий CSS Grid; новых wrappers, abstractions и dependencies нет.

### After design

- PASS — [layout contract](contracts/playback-layout.md) ограничен presentation boundary и не меняет данные или playback state.
- PASS — [quickstart](quickstart.md) покрывает web/embedded, rail/expanded, narrow/short и unavailable states.
- PASS — data model отсутствует, потому что данные и state contracts не меняются.

## Validation Plan

1. Сначала изменить static/render contract так, чтобы он требовал отдельную grid-row и запрещал `position: fixed`, `--playback-inline-start` и JS clearance observer.
2. Реализовать минимальный template/CSS/JS diff и запустить focused cabinet tests.
3. Проверить Node syntax/runtime harness и реальную computed geometry в web и desktop-embedded вариантах.
4. Проверить fail-closed recovery: при потере доступа sibling playback остановлен и удалён до безопасного recovery main; no-JS и accessibility contracts сохранены.
5. Запустить `git diff --check` и `infra/scripts/ci-local.sh --fast` как repository gate значимого UX.
6. До production выполнить release guidance: validated commit approval, PR/merge, exact-SHA dry-run, release и smoke.

## Project Structure

### Documentation

```text
specs/205-playback-panel-layout/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/playback-layout.md
├── checklists/{requirements,ux}.md
└── tasks.md
```

### Source Code

```text
apps/server/src/twobrain_rec_server/cabinet/
├── templates/cabinet/pages/meeting_detail_content.html
└── static/cabinet/{cabinet.css,cabinet.js}

apps/server/tests/
├── contract/test_cabinet_static_assets_contract.py
└── unit/test_cabinet_web_shell.py
```

**Structure Decision**: Playback становится прямым sibling content-main внутри существующего `.app-shell`; shell grid является единственным источником геометрии sidebar/content/playback.

## Complexity Tracking

Нарушений нет. Изменение удаляет две компенсационные переменные и один `ResizeObserver`, не добавляя новой абстракции.
