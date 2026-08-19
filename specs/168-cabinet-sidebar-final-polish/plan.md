# Implementation Plan: Финальная геометрия боковой панели кабинета

**Branch**: `codex/168-cabinet-layout-polish` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

## Summary

Сделать rail width и playback inline start одной CSS truth: compact state —
64px, expanded state — 176px. Оставить существующий responsive initializer,
top toggle и focus/tooltip contract.

## Technical Context

**Language/Version**: CSS, vanilla JavaScript, pytest and Node

**Primary Dependencies**: Existing server-rendered cabinet shell; no new dependency

**Storage**: N/A

**Testing**: Focused static/Node rail tests, `node --check`, synthetic Browser
and embedded visual review

**Risk / Validation Lane**: `high-risk-feature` — shared responsive navigation,
accessibility and fixed playback geometry

**Release Gate**: `no deploy`; later release candidate only

**Target Platform**: Modern browser and embedded macOS WebView

**Project Type**: Server-rendered web cabinet

**Performance Goals**: CSS-only geometry correction; no new listener or request

**Constraints**: Reuse `--app-rail-width`, `--app-sidebar-width`, existing
  `is-rail-pinned` class and Feature 165 initialization

**Scale/Scope**: Shared cabinet stylesheet and focused contract assertions

## Constitution Check

- Capture/audio: PASS — only layout offsets change.
- Consent/privacy: PASS — no data, storage or telemetry.
- UI/accessibility/clean-room: PASS — existing original shell and accessible
  toggle remain the contract.
- Spec-driven delivery: PASS — clarify, checklist, tasks, analyze and visual
  evidence are included.

## Validation Plan

1. Run rail static assertions and existing responsive Node VM harness.
2. Run `node --check` and `git diff --check`.
3. Check expanded/collapsed browser and embedded synthetic layouts, including
   bottom playback alignment and tooltip/focus.
4. Run the combined fast repository lane once after all four slices.

## Project Structure

```text
specs/168-cabinet-sidebar-final-polish/
├── spec.md
├── clarify.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/sidebar-final-polish.md
├── checklists/requirements.md
├── checklists/ux.md
├── quickstart.md
└── tasks.md

apps/server/src/twobrain_rec_server/cabinet/static/cabinet/
└── cabinet.css

apps/server/tests/contract/
└── test_cabinet_static_assets_contract.py
```

**Structure Decision**: Fix the late shared CSS layer; do not add a layout
component or state manager.

## Complexity Tracking

No constitution violations. Ponytail ceiling: two state selectors and existing
tokens are enough; no JS geometry observer.
