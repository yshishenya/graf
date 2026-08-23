# Implementation Plan: Upload Status, Processing Visibility, And Upload Date

**Branch**: `191-upload-status-ux` | **Date**: 2026-08-23 | **Spec**: [spec.md](./spec.md)

## Summary

Expose the existing server receipt timestamp as `uploaded_at`, use it only as the date fallback for manual uploads, and redesign the main upload/processing experience. Consolidate the existing cabinet CSS into one canonical token and primitive layer for violet interaction color, typography, geometry, helper text, Settings navigation, and repeated controls. Reuse HTMX, XHR progress, current Jinja primitives, and the single existing stylesheet.

## Technical Context

**Language/Version**: Python 3.13, browser JavaScript, CSS

**Primary Dependencies**: Existing Pydantic schemas, Jinja rendering, HTMX, native XHR, existing cabinet CSS

**Storage**: Existing PostgreSQL `meetings.created_at`; no migration

**Testing**: Focused pytest unit/integration/contract tests, local rendered browser QA

**Risk / Validation Lane**: high-risk-feature; user-facing degraded/upload states and a shared backend projection are affected

**Release Gate**: no deploy; local validation only, production approval remains separate

**Target Platform**: Browser cabinet and embedded desktop cabinet

**Project Type**: Server-rendered web cabinet with embedded macOS surface

**Performance Goals**: No additional polling or network request; list refresh behavior remains unchanged

**Constraints**: Preserve server-mediated upload, metadata-only evidence, accessibility, keyboard focus, reduced motion, and forced colors

**Scale/Scope**: Whole server-rendered cabinet style audit; implementation prioritizes the meeting list, upload activity, upload dialog, Settings navigation/overview, and shared controls.

## Constitution Check

- **UX and reference use**: PASS WITH RECORDED PRODUCT DECISION. KRISP may be used as a direct UX/UI reference for effective patterns; implementation keeps GRAF violet tokens, assets, and Russian copy. The parallel constitution rewrite is outside this branch.
- **Upload and server boundary**: PASS. No endpoint, credential, object-storage, or MediaScribe boundary changes.
- **Accessibility**: PASS. Existing live regions, progressbar semantics, focus handling, reduced-motion, and forced-colors behavior remain required.
- **Deletion/storage truth**: PASS. The date is metadata only and does not change retention or deletion behavior.

## Validation Plan

1. Add focused tests for `uploaded_at`, manual-upload date fallback, and legacy «Без даты» behavior.
2. Add/adjust static contract assertions for violet product accents, shared checkbox/radio styling, compact progress composition, canonical Settings rules, and visible action discoverability.
3. Run focused pytest targets for view models, cabinet list, web shell, and static assets.
4. Run `infra/scripts/ci-local.sh --fast` if the environment supports the repository gate.
5. Run the local cabinet flow in the in-app Browser; inspect main, upload dialog, upload/processing evidence, Settings overview/detail, desktop/375px reflow, DOM state, interaction, and console health.

## Validation record

- Focused unit, static-contract, and web-shell tests: `216 passed`.
- Isolated PostgreSQL integration lane for the cabinet list: `29 passed`.
- `infra/scripts/ci-local.sh --fast`: `1168 passed`, lint and Python compile
  passed.
- In-app Browser on the local server: manual-upload meeting row rendered
  `Обрабатывается` and `Загружено 23 авг, 01:23`; 375px viewport had no
  horizontal overflow; upload dialog rendered with violet dropzone and primary
  action; browser error/warning log was empty.
- The native file chooser was unavailable to the in-app Browser harness, so the
  live transfer card itself was validated through the existing JavaScript
  contract harness and focused tests rather than an actual file transfer.

## Project Structure

```text
apps/server/src/twobrain_rec_server/api/schemas.py
apps/server/src/twobrain_rec_server/cabinet/view_models.py
apps/server/src/twobrain_rec_server/cabinet/rendering.py
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
apps/server/tests/unit/test_cabinet_view_models.py
apps/server/tests/integration/test_cabinet_meeting_list.py
apps/server/tests/unit/test_cabinet_web_shell.py
apps/server/tests/contract/test_cabinet_static_assets_contract.py
```

**Structure Decision**: Keep one `cabinet.css` and the existing Jinja primitives. Add only semantic tokens and consolidate duplicate shared rules; do not add a frontend framework, dependency, migration, CSS-in-JS layer, or parallel component system.

## Complexity Tracking

No constitution violations.
