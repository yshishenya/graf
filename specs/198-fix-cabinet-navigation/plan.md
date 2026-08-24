# Implementation Plan: Надёжная навигация кабинета

**Branch**: `198-fix-cabinet-navigation` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/198-fix-cabinet-navigation/spec.md`

## Summary

Общая macOS-панель кабинета должна выбирать не просто первый элемент WebKit
history, а ближайший безопасный элемент, отличный от текущего URL, в обоих
направлениях. Исправление затрагивает один общий
`EmbeddedCabinetNavigationController`: back/forward state вычисляется тем же
правилом, а переход выполняется к выбранному `WKBackForwardListItem`, поэтому
дубликаты пропускаются. «Домой», «Обновить», loading state и accessibility
контракт остаются общими и проверяются отдельно.

## Technical Context

**Language/Version**: Swift 6, macOS 14+

**Primary Dependencies**: SwiftUI, AppKit, WebKit, existing
`DesktopCabinetRoutePolicy`, XCTest

**Storage**: N/A; only in-memory WebKit history and existing safe/unsafe URL
ledgers are used.

**Testing**: Focused SwiftPM XCTest, macOS package build, installed-GRAF
Computer Use smoke, repository fast lane

**Risk / Validation Lane**: `high-risk-feature` within a new Spec Kit slice;
this is a shared user-facing navigation and accessibility surface with session
boundary/security filtering, even though no server or data contract changes.

**Release Gate**: `no deploy`; no production release, notarization, Sparkle,
or appcast work is requested.

**Target Platform**: Native GRAF macOS desktop app, embedded same-origin
cabinet WebKit surface

**Project Type**: desktop-app

**Performance Goals**: Navigation state remains synchronous and bounded by the
existing WebKit history lists; no network call, polling, or capture callback
work is added.

**Constraints**: Preserve safe route policy, auth/session fences, fallback to
the meetings list, manual capture controls, accessibility labels/identifiers,
existing shortcuts, and no new dependency.

**Scale/Scope**: One shared controller and one shared titlebar control strip;
manual smoke covers meetings, overview, recording, summaries, calendars,
workspace, account, notifications, and billing.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-First MVP Integrity: **PASS** — no capture source, permission,
  lifecycle, audio callback, or recording artifact code changes.
- Visible Consent And User Control: **PASS** — the persistent recording HUD,
  manual Record/Stop, and native control surface remain unchanged.
- Privacy And Truthfulness: **PASS** — unsafe/auth/external history entries
  remain blocked; no new data egress, secret, transcript, or raw audio is added.
- Deletion Truth And Lifecycle Accounting: **PASS** — no meeting lifecycle,
  deletion, or retained-observability behavior changes.
- Clean-room UX/accessibility: **PASS** — existing four-button strip and
  identifiers remain; state and loading labels become truthful across routes.
- Spec-driven delivery: **PASS** — new spec, clarification pass, plan,
  requirements checklist, tasks, analyze, focused tests, and fast lane are
  required before closeout.
- Ponytail ceiling: **PASS** — reuse the existing controller, route policy,
  history ledgers, native WebKit list, and current buttons; no abstraction or
  dependency is introduced beyond the smallest shared selection helper.

## Validation Plan

1. Run the focused `DesktopCabinetWorkspaceTests` suite, including duplicate
   history selection, back/forward safety, fallback, loading, and stable
   accessibility identifier assertions.
2. Run the feature quickstart against the installed GRAF app: calendar path,
   settings-to-billing path, back then forward, Home, Reload, loading state,
   and all nine cabinet sections: meetings, settings, recording, summaries,
   calendar, workspace, account, notifications, and billing.
3. Run `swift build --package-path apps/macos` and
   `swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests`.
4. Run `infra/scripts/ci-local.sh --fast` before PR/closeout because the
   change affects a shared user-facing macOS path.
5. Do not run deploy, release preparation, notarization, Sparkle, or appcast
   checks; the spec explicitly excludes production publication.

## Project Structure

### Documentation (this feature)

```text
specs/198-fix-cabinet-navigation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── cabinet-navigation.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift
apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift
CHANGELOG.md
```

**Structure Decision**: Keep all behavior in the existing shared navigation
controller. The titlebar view remains a thin projection of published state;
route/security policy remains the source of truth for allowable history.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | N/A | Existing controller and native WebKit history are sufficient. |
