# Implementation Plan: Понятная подсказка на таймлайне

**Branch**: `codex/161-graf-ux-regressions` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

## Summary

Заменить абстрактный текст hint на короткую action/result формулировку,
уточнить его wrapping/secondary styling и усилить contract tests. Existing
track accessible names already cover keyboard and screen-reader path.

## Technical Context

**Language/Version**: Python 3.13, vanilla JavaScript, CSS, Jinja2

**Primary Dependencies**: Existing cabinet renderer, CSS, static contract
tests; no new dependency

**Storage**: N/A; hint is server-rendered copy

**Testing**: Focused pytest contract/unit checks, static assertions and
`node --check`

**Risk / Validation Lane**: `high-risk-feature` — user-facing accessibility
and discoverability UX; no auth, capture, privacy, AI or data contract change

**Release Gate**: `no deploy` for this slice; final release gate is shared

**Target Platform**: Modern browser and embedded macOS WebView

**Project Type**: Server-rendered web cabinet

**Performance Goals**: No new event handler, network request or client state

**Constraints**: Russian copy, clean-room design, reduced-motion safe, narrow
viewport safe, same markup in web/embedded

**Scale/Scope**: One hint paragraph and existing track labels

## Constitution Check

- Capture-First MVP Integrity: PASS — no capture or audio route changed.
- Visible Consent and User Control: PASS — playback remains user-triggered.
- Privacy and secret discipline: PASS — copy contains no meeting data.
- UI/accessibility/clean-room: PASS — action/result copy and existing
  keyboard label are required; no competitor-specific copy is copied.
- Spec-driven delivery: PASS — spec, clarify, research, checklist, tasks,
  analyze, focused validation and review are present.

## Validation Plan

1. Run focused timeline rendering and accessibility contract tests.
2. Check exact hint count and action/result copy in synthetic playable render.
3. Run `node --check` and `git diff --check`.
4. Review narrow wrapping rules and verify no duplicate hint after partial
   render.
5. Defer combined fast CI to final UX closeout.

## Project Structure

```text
specs/162-timeline-click-hint/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/timeline-click-hint.md
├── checklists/requirements.md
├── checklists/ux.md
└── tasks.md

apps/server/src/twobrain_rec_server/cabinet/
├── rendering.py
└── static/cabinet/cabinet.css

apps/server/tests/contract/test_recording_workflow_accessibility.py
apps/server/tests/unit/test_cabinet_web_shell.py
```

**Structure Decision**: Keep copy in the existing renderer and presentation
rules in the existing stylesheet; no JS change is needed because track
keyboard semantics already exist.

## Complexity Tracking

No constitution violations. Ponytail ceiling: one copy change plus the
smallest wrapping rule and assertions; no tooltip library or first-use state.
