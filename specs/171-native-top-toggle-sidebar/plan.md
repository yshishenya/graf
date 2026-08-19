# Implementation Plan: Единый верхний toggle и аккуратный rail

**Branch**: `codex/168-cabinet-layout-polish` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/171-native-top-toggle-sidebar/spec.md`

## Summary

Исправить два связанных состояния общей навигационной оболочки. Native inspector
получит один fixed top-trailing slot с резервом места для контента в collapsed и
expanded состояниях. Shared cabinet rail перестанет закрываться от клика вне
sidebar, будет использовать рабочий wide default для embedded surface, а
compact-режим уберёт пустой workspace-header slot и сохранит доступные имена
nav-ссылок.

Решение повторно использует текущие `InspectorDisclosureButton`,
`setRailPinned`, `initCabinetRail`, `railReady` и существующие CSS-переменные.
Новые state-хранилища, router, зависимости и native/web coordinator не нужны.

## Technical Context

**Language/Version**: Swift 5.9+ / SwiftUI; Python 3.13; vanilla JavaScript;
CSS; Jinja2

**Primary Dependencies**: Existing macOS shell, server-rendered cabinet,
`window.matchMedia`, XCTest, pytest and Node VM harness; no new dependency

**Storage**: N/A; rail and inspector presentation state remain ephemeral

**Testing**: Focused XCTest/source contracts, focused pytest/Node static
contracts, `node --check`, in-app Browser visual review and Computer Use visual
review

**Risk / Validation Lane**: `high-risk-feature` — shared navigation and native
shell geometry are user-facing, accessibility-sensitive and embedded-aware;
capture, auth, data and permissions remain out of scope

**Release Gate**: `no deploy` for this slice; later release train owns deploy
and public macOS packaging approval

**Target Platform**: Modern browser, embedded macOS WebView and macOS SwiftUI
shell

**Project Type**: Server-rendered web cabinet plus desktop app shell

**Performance Goals**: One responsive media-query read per shell initialization;
no resize listener, polling, layout loop or extra request

**Constraints**: Preserve existing 52px/308px native widths, 44px native target,
focus/ARIA labels, capture and settings actions, `is-rail-pinned` precedence,
HTMX idempotency, no horizontal overflow and no cross-session persistence

**Scale/Scope**: One SwiftUI view, one shared rail initializer, one Jinja macro,
one CSS compact layout block, focused tests and one web/native visual matrix

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-First MVP Integrity: PASS — no recording, audio routing, stop path or
  capture status behavior changes.
- Visible Consent and User Control: PASS — native capture controls remain
  visible and reachable; only the inspector disclosure slot moves.
- Privacy and secret discipline: PASS — no meeting content, storage, network,
  telemetry or credentials are added.
- UI/accessibility/clean-room: PASS — stable placement, 44px target, labels,
  focus, accessible nav names and original GRAF composition are explicit.
- Auth, tenant and deletion boundaries: PASS — no route, form, session, RLS or
  deletion behavior changes.
- Public macOS distribution: PASS — no signing, entitlement, updater or
  packaging artifact changes.
- Spec-driven delivery: PASS — spec, clarify, plan/research, contracts,
  checklist, tasks, analyze, implementation review and focused evidence are
  required.

## Validation Plan

1. Run the existing and new focused server contracts for rail initialization,
   accessible markup, compact geometry and no auto-collapse; run `node --check`
   and `git diff --check`.
2. Run focused macOS XCTest/source contracts for top slot, one control per mode,
   reserved content space, 44px target and unchanged capture semantics.
3. Use the in-app Browser at a wide default viewport and a temporary 900px
   viewport. Check initial state, toggle twice, content click, nav click,
   keyboard focus, tooltip and horizontal overflow; reset viewport afterwards.
4. Rebuild/launch the installed `GRAF Dev` app and use Computer Use to check
   native collapsed/expanded top slot, title/settings/capture separation, two
   clicks without pointer movement, and left rail wide default after Reload.
5. Perform correctness, accessibility, clean-room and Ponytail review; add one
   focused regression check for every actionable finding.
6. Run `infra/scripts/ci-local.sh --fast` once after both stories and record the
   exact SHA and metadata-only evidence in `quickstart.md`/`analysis.md`.

No full CI, production deploy, notarization or release command is required for
this isolated layout regression slice.

## Project Structure

### Documentation (this feature)

```text
specs/171-native-top-toggle-sidebar/
├── spec.md
├── clarify.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── native-top-toggle.md
│   └── cabinet-rail.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
├── quickstart.md
├── analysis.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html
apps/server/tests/unit/test_cabinet_web_shell.py
apps/server/tests/contract/test_cabinet_static_assets_contract.py
CHANGELOG.md
```

**Structure Decision**: Keep the existing shared shell paths as the single
owner. SwiftUI owns native geometry; the server-rendered macro owns web markup;
the existing JS initializer owns rail state; CSS owns compact/expanded layout.
No cross-surface state abstraction is introduced.

## Complexity Tracking

No constitution violations. Ponytail ceiling: reuse the existing button/helper,
state class and test harness; delete the two auto-collapse listener paths and
one compact empty slot instead of adding persistence or a new controller.
