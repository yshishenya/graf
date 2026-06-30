# Implementation Plan: Universal Cabinet Sidebar

**Branch**: `069-universal-sidebar` | **Date**: 2026-06-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/069-universal-sidebar/spec.md`

## Summary

Create one server-owned cabinet shell/sidebar contract for all authenticated user cabinet full pages. The shell must render the same primary navigation in standalone browser and desktop embedded surfaces, preserve the existing embedded compact rail behavior, and keep fragments content-only so dynamic updates never duplicate the shell.

## Technical Context

**Language/Version**: Python 3.12 server code, Jinja templates, JavaScript/CSS shipped from the server, Swift macOS only for native shell boundary tests already in place

**Primary Dependencies**: FastAPI/Starlette response layer, Jinja2 templates, htmx for partial updates, existing cabinet static CSS/JS

**Storage**: N/A; this feature changes layout/navigation contracts only

**Testing**: `uv run --extra dev pytest` for server unit/contract/integration checks; `swift test --package-path apps/macos --disable-swift-testing` only if native shell boundary files are touched further

**Risk / Validation Lane**: significant-feature / architecture. The change touches shared user-facing cabinet layout, desktop embedded UX, accessibility, and fragment contracts.

**Release Gate**: no deploy during implementation. Run feature quickstart and `infra/scripts/ci-local.sh` before closeout/PR. Production deploy requires a separate release gate.

**Target Platform**: Browser cabinet and macOS desktop embedded WebView cabinet

**Project Type**: Web service with server-rendered authenticated cabinet UI plus native desktop host

**Performance Goals**: Full cabinet pages keep one shell and one content region; partial updates avoid replacing shell markup. No new client bundle or extra network round trip for sidebar rendering.

**Constraints**: No native desktop product sidebar; no new frontend framework; admin/auth surfaces stay out of scope; disabled future destinations remain non-focusable; active destination and keyboard focus remain visually distinct.

**Scale/Scope**: Covered user cabinet full pages: meetings list, meeting detail, deletion report, settings, calendar settings, and desktop embedded equivalents. Existing fragments remain content-only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-first MVP integrity: Pass. Product navigation remains in web cabinet; native macOS capture controls and stop path are not replaced.
- Visible consent and user control: Pass. Native recording controls remain separate from cabinet navigation; embedded layout must not hide stop/local safety controls owned by native chrome.
- Data boundary and secret discipline: Pass. No new storage, egress, credentials, or diagnostics content.
- Deletion truth and lifecycle accounting: Pass. Deletion report full page must adopt shell without changing deletion copy or lifecycle claims.
- Spec-driven delivery with testable gates: Pass. Significant architecture lane selected; clarify completed; plan, checklist, tasks, analyze, issue sync, and implement remain required.
- UX and brand distance: Pass with validation. The shared sidebar must preserve existing GRAF/2brain Rec visual language and avoid copied third-party patterns.

Post-design re-check: Pass. The selected design consolidates existing server-owned cabinet layout instead of adding a second navigation system or new dependency.

## Validation Plan

- Development checks:
  - Focused template/navigation tests for shared sidebar contract.
  - Existing cabinet shell tests for standalone and desktop embedded routes.
  - Existing fragment tests to prove content-only updates do not include shell/sidebar.
- Quickstart checks:
  - `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_template_sections.py tests/unit/test_cabinet_navigation_model.py tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_contract.py tests/contract/test_calendar_settings_contract.py tests/integration/test_cabinet_meeting_list.py tests/integration/test_cabinet_meeting_detail.py tests/integration/test_cabinet_hx_fragments.py`
  - `infra/scripts/ci-local.sh` before closeout/PR.
- Deploy gate: none for implementation. Use `infra/scripts/cd-remote.sh --dry-run` only in a later release/deploy slice.

## Project Structure

### Documentation (this feature)

```text
specs/069-universal-sidebar/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── sidebar-shell-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/
├── rendering.py
├── view_models.py
├── templates/cabinet/
│   ├── components/sections.html
│   └── pages/
│       ├── meetings.html
│       ├── desktop_meetings.html
│       └── calendar_settings.html
└── static/cabinet/
    ├── cabinet.css
    └── cabinet.js

apps/server/tests/
├── unit/
│   ├── test_cabinet_template_sections.py
│   ├── test_cabinet_navigation_model.py
│   └── test_cabinet_web_shell.py
├── contract/
│   ├── test_cabinet_contract.py
│   └── test_calendar_settings_contract.py
└── integration/
    ├── test_cabinet_meeting_list.py
    ├── test_cabinet_meeting_detail.py
    └── test_cabinet_hx_fragments.py

apps/macos/
├── RecApp/App/TwoBrainRecApp.swift
├── RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
└── Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift
```

**Structure Decision**: Keep the architecture in the existing server-rendered cabinet layer. Add/extend a shared cabinet shell/sidebar template contract and route all full cabinet pages through it. Do not introduce a new frontend package, admin merge, or native desktop navigation layer.

## Complexity Tracking

No constitution violations or complexity exceptions.
