# Implementation Plan: Боковая навигация настроек

**Branch**: `codex/135-settings-sidebar` | **Date**: 2026-07-27 | **Spec**: [spec.md](spec.md)

**Selected lane**: high-risk product area / UX. The change is user-facing,
shared by browser and embedded macOS surfaces, and touches accessibility and
navigation contracts. It does not change production deployment in this slice.

## Summary

Replace the current horizontal settings navigation with one shared, grouped
vertical rail inside the settings workspace. The rail exposes the five
actionable settings categories exactly once; `/settings` remains a compact
overview entry point without duplicating the rail. Browser/embedded route
parity, category content, scope semantics, forms and CSRF checks remain intact.
At narrow widths the same links become a stacked menu above the content.

## Technical Context

**Language/Version**: Python 3.11 server rendering, HTML, CSS, existing Jinja templates

**Primary Dependencies**: FastAPI, Jinja2, existing GRAF cabinet design tokens

**Storage**: N/A; no persistence or schema changes

**Testing**: pytest contract/integration/unit suites; `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: high-risk-feature; user-facing UX and accessibility change shared by browser and embedded settings

**Release Gate**: no deploy; a later approved release must first pass `infra/scripts/cd-remote.sh --dry-run`

**Target Platform**: modern browsers and the macOS embedded desktop webview

**Project Type**: server-rendered web surface inside a desktop product

**Performance Goals**: no extra request or client-side router; no layout shift beyond the existing page load

**Constraints**: preserve explicit routes, auth, CSRF, safe presentation fields, native capture boundary and 320px reachability

**Scale/Scope**: one shared navigation macro, one view-model presentation field, settings CSS and focused tests

## Constitution Check

*Gate before Phase 0 research: PASS.*

- UX/accessibility work follows the full Spec Kit flow with clarify, checklist,
  analyze, focused validation and repository CI.
- The existing route definitions remain the source of truth; no catch-all
  redirects, new permissions, persistence or mutation endpoints are introduced.
- Recording remains a native macOS handoff. The web surface does not gain a
  capture toggle or audio-routing behavior.
- Account and provider navigation continues to expose safe presentation fields
  only; no credentials, subjects, device secrets or private meeting content are
  added.
- Krisp is used only as a structural reference. GRAF tokens, copy, brand
  distance and existing product gates remain authoritative.

*Re-check after Phase 1 design: PASS.* The selected design reuses the existing
macro and CSS tokens, adds only presentation-only group metadata, and uses CSS
grid plus a responsive media query. No new dependency, client router or backend
contract is needed.

## Validation Plan

1. Run the feature quickstart: render browser and embedded overview/category
   pages, assert five grouped links, active state, canonical hrefs and safe-copy
   invariants; render the calendar and provider-link surfaces as well.
2. Run focused pytest files covering settings UI, settings IA flow, calendar,
   provider-link and cabinet shell contracts.
3. Run `git diff --check` and inspect the template/CSS diff for route and
   accessibility regressions.
4. Run the repository gate `infra/scripts/ci-local.sh` before PR/closeout because
   this changes a shared user-facing surface.
5. Production deploy is out of scope here. If a later release gate is approved,
   run `infra/scripts/cd-remote.sh --dry-run` before any execute step.

The in-app browser audit of the currently deployed production URL timed out
during navigation, so source/render tests and local validation are authoritative
until a reachable local or deployed environment is available for screenshot QA.

## Project Structure

### Documentation

```text
specs/135-settings-sidebar/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/settings-ui-sidebar.md
├── checklists/requirements.md
├── checklists/ux.md
└── tasks.md
```

### Runtime and tests

```text
apps/server/src/twobrain_rec_server/cabinet/
├── view_models.py
├── static/cabinet/cabinet.css
└── templates/cabinet/components/settings_navigation.html

apps/server/tests/
├── contract/test_settings_ui_contract.py
├── contract/test_calendar_settings_contract.py
├── contract/test_provider_link_settings_contract.py
├── integration/test_settings_ia_flow.py
└── unit/test_cabinet_web_shell.py
```

**Structure Decision**: Keep the existing server-rendered cabinet architecture.
The settings navigation remains a reusable Jinja macro; route generation stays
in `settings_category_navigation`; shared layout belongs in `cabinet.css`;
contracts remain close to the existing settings and shell tests.

## Complexity Tracking

No constitution violations. No new abstraction or dependency is required.
