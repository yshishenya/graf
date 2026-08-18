# Implementation Plan: Понятный toggle боковой панели

**Branch**: `codex/161-graf-ux-regressions` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

## Summary

Добавить к существующей shared toggle короткий non-interactive tooltip,
управляемый тем же action label, который уже обновляет `aria-label`, `title`,
`aria-expanded` и icon. Сохранить один control и существующий guarded JS path.

## Technical Context

**Language/Version**: Python 3.13, vanilla JavaScript, CSS, Jinja2

**Primary Dependencies**: Existing sections template, cabinet.js and cabinet.css; no new dependency

**Storage**: N/A; ephemeral presentation state

**Testing**: Focused pytest unit/contract tests, node syntax check, synthetic browser/embedded visual review

**Risk / Validation Lane**: `high-risk-feature` — shared navigation affordance and accessibility

**Release Gate**: `no deploy`; include in later release train only

**Target Platform**: Modern browser and embedded macOS WebView

**Performance Goals**: CSS-only tooltip; no network request, observer or scroll handler

**Constraints**: Preserve Feature 159 route/state mechanics and Feature 165 ownership of responsive default state

## Constitution Check

- Capture-First MVP Integrity: PASS — no capture, recording or permission path changes.
- Auth and tenant boundaries: PASS — no routes, sessions, CSRF or profile data changes.
- UI/accessibility/clean-room: PASS — tooltip is keyboard-visible, non-interactive and original GRAF copy.
- Spec-driven delivery: PASS — specification, clarify result, research, contracts, checklists, tasks and analysis included.

## Validation Plan

1. Add template/CSS/JS contract assertions for one control, matching state text and tooltip marker.
2. Run focused shell/static tests and `node --check`.
3. Render browser/embedded synthetic shell in wide and narrow viewports; inspect hover/focus and dark/light states.
4. Run `git diff --check` and `infra/scripts/ci-local.sh --fast` once at closeout.

## Project Structure

```text
specs/164-sidebar-toggle-tooltip/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/sidebar-toggle-tooltip.md
├── checklists/requirements.md
├── checklists/ux.md
├── tasks.md
└── quickstart.md

apps/server/src/twobrain_rec_server/cabinet/
├── templates/cabinet/components/sections.html
├── static/cabinet/cabinet.js
└── static/cabinet/cabinet.css

apps/server/tests/
├── unit/test_cabinet_web_shell.py
└── contract/test_cabinet_static_assets_contract.py
```

## Complexity Tracking

Ponytail ceiling: reuse the existing button state and add one CSS affordance;
no tooltip component, persistent state, library or duplicate event path.

