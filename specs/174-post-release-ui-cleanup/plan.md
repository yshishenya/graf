# Implementation Plan: Пострелизная очистка интерфейса

**Branch**: `codex/174-post-release-ui-cleanup` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/174-post-release-ui-cleanup/spec.md`

## Summary

Устранить реальную узкую embedded-регрессию и удалить остатки уже завершённых
миграций без нового поведения. Один финальный sidebar state layer владеет
compact/expanded geometry; старые breakpoint-блоки оставляют только отличающиеся
свойства. Settings templates становятся одноколоночными напрямую без
неиспользуемого inner-navigation macro. Native inspector теряет только
неиспользуемый `GeometryReader`, а дублирующие source tests сокращаются до одного
смыслового layout/accessibility contract. Живую computed geometry проверяет
маленькая Browser-матрица; статические tests сохраняют только устойчивые
семантические границы и точную защиту от повторного `display:none`.

## Technical Context

**Language/Version**: Server-rendered Jinja/HTML, CSS, vanilla JavaScript,
Python 3.13/3.14 tests; Swift 6 / SwiftUI macOS shell

**Primary Dependencies**: Existing cabinet shell and tokens, pytest, XCTest,
SwiftUI/WebKit, in-app Browser and current GRAF Dev tools; no new dependency

**Storage**: N/A — presentation and test-contract cleanup only

**Testing**: Focused pytest contracts/integration, existing Node JavaScript
harnesses, `node --check`, focused Swift tests/build, computed Browser matrix,
GRAF Dev visual interaction, `git diff --check`, one closeout fast lane

**Risk / Validation Lane**: `significant-feature` — shared responsive navigation,
settings IA, accessibility and native/web composition change across modules;
no auth, data, capture, billing, permissions or deployment behavior changes

**Release Gate**: `no deploy`; this slice prepares a later release and does not
authorize production or public macOS publication

**Target Platform**: Modern web browser, embedded macOS WKWebView and native macOS SwiftUI shell

**Project Type**: Server-rendered web cabinet embedded in a native desktop app

**Performance Goals**: No new request, listener, state, layout loop or runtime dependency; sidebar interactions remain immediate

**Constraints**: Preserve 64px/176px sidebar widths, 40×40 compact controls,
accepted breakpoints/default state, same-slot toggle, profile menu, routes,
HTMX fragments, accessibility and no horizontal overflow

**Scale/Scope**: One CSS state owner, 21 content templates plus two fragments,
one removable macro, one dead tooltip attribute, one SwiftUI wrapper and two focused test surfaces

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

- Capture-First MVP Integrity: PASS — no capture, audio, recording or permission path.
- Visible Consent and User Control: PASS — recording controls and indicator semantics are unchanged.
- Plaintext observability/secret discipline: PASS — no data, logs, network, transcript, credential or evidence content.
- Deletion truth: PASS — no persisted artifact or deletion copy.
- Public macOS distribution: PASS — no signing, package, updater, appcast or release operation.
- Spec-driven delivery: PASS — Feature 174 owns specify, clarify, plan, UX checklist, tasks, analyze, implementation, review and evidence.
- UI/accessibility/brand distance: PASS — accepted GRAF geometry is preserved; computed visibility, keyboard access and clean-room review are explicit gates.

Post-design re-check: PASS. The design deletes legacy owners and dependencies,
does not broaden trust boundaries, and retains all applicable gates.

## Validation Plan

1. Before edits, preserve the reproduced failure: embedded 720px profile has a zero-size rendered box because an older breakpoint sets `display:none`.
2. Run focused server tests for sidebar, settings, templates, shell and HTMX boundaries after each independent code slice; run existing Node harnesses and `node --check` only when JavaScript changes.
3. Use the in-app Browser to query rendered/computed sidebar geometry at 640/720/980/981/1120/1121/1280 for web and embedded states. Require 40×40 compact targets, 64/176 rail widths, visible profile and zero overflow.
4. Run focused Swift inspector/accessibility tests and a macOS build after removing the wrapper; inspect GRAF Dev expanded/collapsed states and same-coordinate double toggle.
5. Perform correctness, frontend/UX/accessibility and Ponytail review. Resolve every actionable finding and run `infra/scripts/ci-local.sh --fast` once at closeout. Full CI, deploy and notarization remain release-train work.

## Project Structure

### Documentation (this feature)

```text
specs/174-post-release-ui-cleanup/
├── spec.md
├── clarify.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── interface-cleanup.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
├── quickstart.md
├── analysis.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/
├── static/cabinet/cabinet.css
├── static/cabinet/cabinet.js
└── templates/cabinet/
    ├── components/sections.html
    ├── components/settings_navigation.html
    ├── fragments/calendar_settings.html
    ├── fragments/provider_link_settings.html
    └── pages/*_content.html

apps/server/tests/
├── contract/test_cabinet_static_assets_contract.py
├── contract/test_settings_ui_contract.py
├── integration/test_settings_ia_flow.py
└── unit/test_cabinet_web_shell.py

apps/macos/
├── RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
└── Shared/Tests/
    ├── AppControlAccessibilityTests.swift
    └── DesktopMeetingShellWebViewBoundaryTests.swift

specs/173-settings-single-column/
CHANGELOG.md
```

**Structure Decision**: Keep behavior in existing owners and delete superseded surfaces. No helper, component, dependency or parallel navigation/state system is introduced. Settings route/view-model parameters may remain where the outer sidebar consumes them; only dead inner rendering is removed.

## Complexity Tracking

No constitution violations. Ponytail ceiling: delete the stale declarations,
macro calls, dead attribute and unused wrapper; add only the smallest exact regression checks needed to prove rendered visibility and preserved semantics.
