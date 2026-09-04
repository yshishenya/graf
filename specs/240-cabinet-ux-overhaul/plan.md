# Implementation Plan: Полная переработка интерфейса кабинета GRAF

**Branch**: `240-cabinet-ux-overhaul` | **Date**: 2026-09-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Провести высокорисковую UX/UI/IA-полировку существующего server-rendered
кабинета GRAF. Сначала зафиксировать визуальную и интерактивную матрицу,
затем улучшить общие токены, оболочку, список встреч, detail, настройки,
авторизацию и состояния. Существующие маршруты, формы, HTMX hooks, data-hooks,
capture/privacy/deletion truth и нативный capture-контур остаются неизменными.
Работа выполняется в существующих HTML/CSS/JS-файлах без новой зависимости и
без отдельного дизайн-фреймворка.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.13 server-rendered Jinja templates, CSS and
vanilla JavaScript; SwiftUI/WebKit shell remains a compatibility surface.

**Primary Dependencies**: FastAPI/Jinja2, HTMX 2.0.10 already vendored in the
cabinet, existing native macOS shell; no new dependency.

**Storage**: N/A for this slice. No schema, persistence or server data model
changes.

**Testing**: Existing pytest unit/contract/integration tests, `node --check`
for JavaScript, focused DOM contract assertions and browser visual/a11y
evidence when the local harness is available.

**Risk / Validation Lane**: `high-risk-feature` — user-facing UX, responsive,
accessibility and reference-fidelity review; no product semantics change.

**Release Gate**: `no deploy` — this task ends at PR; production release needs
the separate approved release candidate gate.

**Target Platform**: Standalone browser and embedded macOS cabinet at
320/390/768/1024/1440 CSS px, light/dark theme, keyboard and screen reader.

**Project Type**: Monorepo; implementation is limited to
`apps/server/src/twobrain_rec_server/cabinet/` and its tests/evidence docs.

**Performance Goals**: CSS/JS remains static and dependency-free; no additional
network request or client-side rendering pass is introduced.

**Constraints**: Preserve all behavior and product gates, including visible
capture controls, local recording policies, deletion truth, privacy, auth,
no secret-bearing evidence, clean-room independent implementation and
reference-fidelity review.

**Scale/Scope**: All user-facing cabinet surfaces, with native code changed
only if a focused audit proves the embedded shell blocks the same UX contract.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] High-risk UX clarification is recorded in `spec.md`; reviewer-owned UX
  checklist remains unchecked until evidence is reviewed.
- [x] No recording, capture, privacy, deletion, auth, storage or AI semantics
  are redesigned; only presentation and proven dead UI candidates are in scope.
- [x] Observable Krisp patterns are used as clean-room reference; no private
  assets, code, data or protected credentials are copied. Deviations are logged.
- [x] Keyboard, focus, accessible names, reduced motion, contrast and responsive
  states are explicit evidence requirements.
- [x] Evidence is metadata-only and synthetic.

## Validation Plan

Use `quickstart.md`, focused cabinet contract/unit/integration tests, `node
--check`, `git diff --check`, browser visual/accessibility matrix and
`infra/scripts/ci-local.sh --fast` before PR. No deployment gate is run because
the user requested an interface PR, not a release. A full gate remains for the
exact release candidate only.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
apps/server/src/twobrain_rec_server/cabinet/
├── static/cabinet/cabinet.css
├── static/cabinet/cabinet.js
├── templates/cabinet/base.html
├── templates/cabinet/components/{sections,primitives,icons}.html
├── templates/cabinet/pages/*.html
└── templates/cabinet/auth/*.html

apps/server/tests/
├── contract/test_cabinet*_contract.py
├── contract/test_settings_ui_contract.py
├── contract/test_billing_ui.py
├── integration/test_cabinet_meeting_{list,detail}.py
└── integration/test_settings_ia_flow.py
```

**Structure Decision**: Reuse the existing server-rendered cabinet, shared CSS/JS
and test harness. No new frontend application, dependency, route or design
system layer is introduced.

## Complexity Tracking

> No constitution violations. Existing structure is sufficient.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
