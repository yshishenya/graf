# Implementation Plan: Адаптивное стартовое состояние боковой панели

**Branch**: `codex/161-graf-ux-regressions` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/165-sidebar-responsive-default/spec.md`

## Summary

Исправить общий `initCabinetRail`: при отсутствии явного
`is-rail-pinned` выбирать initial state через существующий responsive
contract. Standalone browser раскрыт от 981 px, embedded shell — от 1121 px;
ручное состояние после инициализации не переопределяется.

## Technical Context

**Language/Version**: Python 3.13, vanilla JavaScript, CSS, Jinja2

**Primary Dependencies**: Existing cabinet shell, `window.matchMedia`, pytest;
no new dependency

**Storage**: N/A; rail state is ephemeral presentation state

**Testing**: Focused pytest unit/contract tests, a small Node VM regression
harness for initial-state boundaries, `node --check`, synthetic browser and
embedded visual review

**Risk / Validation Lane**: `high-risk-feature` — shared responsive navigation,
keyboard/ARIA behavior and embedded parity are user-facing UX gates; no
capture, auth, data or release behavior changes

**Release Gate**: `no deploy` for this slice; production deploy is owned by the
later release train and requires its separate approval

**Target Platform**: Modern browser and embedded macOS WebView cabinet

**Project Type**: Server-rendered web cabinet shared by web and embedded shell

**Performance Goals**: One media-query read during shell initialization; no
resize listener, polling, layout loop or added request

**Constraints**: Reuse current `is-rail-pinned` state path and CSS breakpoints;
preserve focus, ARIA, icon/label parity, partial-update idempotency and no
cross-session persistence

**Scale/Scope**: One shared shell initializer, two static assets, existing
unit/contract tests and one visual boundary matrix

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-First MVP Integrity: PASS — no recording, audio route, permission or
  playback behavior changes.
- Visible Consent and User Control: PASS — no capture control is hidden or
  altered; only navigation presentation state changes.
- Plaintext observability and privacy: PASS — no meeting data, storage,
  network, telemetry or secret path is introduced.
- UI/accessibility/clean-room: PASS — existing toggle, focus, ARIA and original
  GRAF shell remain the contract; responsive states are explicit and
  measurable.
- Spec-driven delivery: PASS — clarification found no critical gaps; plan,
  checklists, tasks, analyze and focused evidence are required.

## Validation Plan

1. Run the focused unit/contract selection for shell markup, CSS breakpoints and
   rail initialization.
2. Run the Node VM harness for browser/embedded widths 1280, 981, 980, 1121,
   1120 and 720 px, plus explicit pinned state and resize preservation.
3. Run `node --check` and `git diff --check`.
4. Review the synthetic shell visually in the in-app browser at wide and narrow
   sizes and in the embedded macOS shell with Computer Use; record only
   metadata, not user meeting content.
5. Run `infra/scripts/ci-local.sh --fast` once for the completed shared UX
   slice. No `--full`, deploy or macOS release command is required here because
   this is not the release candidate.

## Project Structure

### Documentation (this feature)

```text
specs/165-sidebar-responsive-default/
├── spec.md
├── clarify.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/sidebar-responsive-default.md
├── checklists/requirements.md
├── checklists/ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/
├── static/cabinet/cabinet.js
└── static/cabinet/cabinet.css

apps/server/tests/
├── unit/test_cabinet_web_shell.py
└── contract/test_cabinet_static_assets_contract.py

CHANGELOG.md
```

**Structure Decision**: Reuse the shared server-rendered cabinet shell and its
existing JavaScript initializer. The implementation is a single state-selection
guard plus a regression harness; CSS breakpoints remain the source of truth and
no router, storage or component layer is added.

## Complexity Tracking

No constitution violations. Ponytail ceiling: read one responsive media query
at initialization and reuse the existing toggle/state path; do not add
persistence or a resize observer unless a later requirement explicitly changes.
