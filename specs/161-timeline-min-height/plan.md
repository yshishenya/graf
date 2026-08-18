# Implementation Plan: Минимальная высота таймлайна спикеров

**Branch**: `codex/161-graf-ux-regressions` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

## Summary

Поднять общий минимум панели дорожек спикеров с `96px` до `120px` во всех
слоях, чтобы три двухстрочные дорожки были видны сразу. Существующий resize
останется bounded по `scrollHeight` и viewport.

## Technical Context

**Language/Version**: Python 3.13, vanilla JavaScript, CSS, Jinja2

**Primary Dependencies**: Existing FastAPI cabinet rendering, server-rendered
Jinja markup, `cabinet.js`, `cabinet.css`; no new dependency

**Storage**: N/A; no persistence

**Testing**: Focused pytest unit/contract checks and existing Node resize harness

**Risk / Validation Lane**: `high-risk-feature` — shared meeting UX and
accessibility surface; no capture, audio routing, auth, storage or AI semantics
change

**Release Gate**: `no deploy` for this slice; production release is handled at
the final release candidate gate

**Target Platform**: Modern browser and embedded macOS WebView cabinet

**Project Type**: Server-rendered web cabinet

**Performance Goals**: No additional event handlers, requests or layout state;
  resize remains idempotent after partial updates

**Constraints**: Preserve existing audio playback, keyboard resize, viewport
  ceiling, reduced-motion behavior and synthetic-only evidence

**Scale/Scope**: One shared speaker timeline component and its focused tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-First MVP Integrity: PASS — only layout height changes; recording and
  playback routes remain unchanged.
- Visible Consent and User Control: PASS — no recording control is hidden.
- Privacy and secret discipline: PASS — synthetic fixtures only; no data model
  or evidence change.
- UI/accessibility/clean-room: PASS — existing keyboard separator and ARIA
  values remain required; no competitor-specific copying.
- Spec-driven delivery: PASS — this slice includes spec, clarification audit,
  research, checklist, tasks, analyze, focused validation and review.

## Validation Plan

1. Run the focused speaker timeline unit and static contract tests.
2. Run the existing Node resize harness for fitting, overflowing and
   viewport-limited synthetic cases.
3. Run `node --check` for `cabinet.js`.
4. Review the diff for one minimum-height constant and no persistent state.
5. Run `infra/scripts/ci-local.sh --fast` once after the final UX slice, not
   after every small change.

## Project Structure

```text
specs/161-timeline-min-height/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/timeline-min-height.md
├── checklists/requirements.md
├── checklists/ux.md
└── tasks.md

apps/server/src/twobrain_rec_server/cabinet/
├── rendering.py
├── static/cabinet/cabinet.css
└── static/cabinet/cabinet.js

apps/server/tests/
├── unit/test_cabinet_web_shell.py
└── contract/test_cabinet_static_assets_contract.py
```

**Structure Decision**: Reuse the existing server-rendered timeline contract;
the minimum is a shared presentation constant, not a new component or model.

## Complexity Tracking

No constitution violations. Ponytail ceiling: keep one existing default value
in sync across the current three surfaces; do not add a settings object or
persistent preference for a fixed layout requirement.
