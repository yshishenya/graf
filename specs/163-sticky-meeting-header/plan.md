# Implementation Plan: Закреплённый верхний блок встречи

**Branch**: `codex/161-graf-ux-regressions` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

## Summary

Обернуть topline и tabs meeting detail в один sticky header, перенести
background/shadow на wrapper, убрать независимый sticky режим у tabs и
обновить scroll-margin для responsive header.

## Technical Context

**Language/Version**: Python 3.13, vanilla JavaScript, CSS, Jinja2

**Primary Dependencies**: Existing meeting detail template and cabinet.css;
no new dependency

**Storage**: N/A; presentation-only

**Testing**: Focused pytest unit/contract tests, static CSS/template contract,
node syntax check

**Risk / Validation Lane**: `high-risk-feature` — shared meeting UX,
accessibility and scroll interaction; no AI/auth/capture semantics

**Release Gate**: `no deploy` for this slice; shared final release gate later

**Target Platform**: Modern browser and embedded macOS WebView

**Project Type**: Server-rendered web cabinet

**Performance Goals**: CSS-only layout change; no extra request, storage or
  per-scroll handler

**Constraints**: Preserve existing tab ARIA/keyboard contract, actions,
  transcript/outcome anchors, responsive shell and clean-room UI

**Scale/Scope**: One meeting detail page template and shared CSS

## Constitution Check

- Capture-First MVP Integrity: PASS — no recording controls or routes change.
- Visible Consent and User Control: PASS — actions remain visible and usable.
- Privacy and secret discipline: PASS — no data is added to the header.
- UI/accessibility/clean-room: PASS — one semantic block, focus-visible and
  target visibility are required; no competitor copying.
- Spec-driven delivery: PASS — full artifacts and focused validation included.

## Validation Plan

1. Render synthetic detail page and assert one wrapper, one tablist and both
   panels.
2. Run static CSS contract for wrapper position/background/scroll margin and
   absence of independent tabs sticky rule.
3. Run focused unit/accessibility tests and node syntax check.
4. Review wide, narrow and embedded layout using synthetic render; record any
   unavailable visual environment honestly.
5. Run combined fast gate only at final UX closeout.

## Project Structure

```text
specs/163-sticky-meeting-header/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/sticky-meeting-header.md
├── checklists/requirements.md
├── checklists/ux.md
└── tasks.md

apps/server/src/twobrain_rec_server/cabinet/
├── templates/cabinet/pages/meeting_detail_content.html
└── static/cabinet/cabinet.css

apps/server/tests/
├── unit/test_cabinet_web_shell.py
└── contract/test_recording_workflow_accessibility.py
```

**Structure Decision**: Use existing template hierarchy and native CSS sticky;
do not add JavaScript scroll management.

## Complexity Tracking

No constitution violations. Ponytail ceiling: replace one sticky rule with
one wrapper rule; no new abstraction or scroll listener.
