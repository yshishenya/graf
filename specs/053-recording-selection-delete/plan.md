# Implementation Plan: Recording Selection And Delete

**Branch**: `053-delete-ux-simplification` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/053-recording-selection-delete/spec.md`

## Summary

This follow-up keeps the existing selection and deletion lifecycle but removes the confusing report hand-off from the owner flow. The smallest safe implementation is to return a concise status fragment, redirect non-JavaScript form submits back to the list, and remove accepted rows from the browser list immediately. The lifecycle service, audit rows, and separate diagnostic report remain unchanged.

## Technical Context

**Language/Version**: Python >=3.13 for server-rendered cabinet and tests; plain browser JavaScript embedded in the existing cabinet HTML shell.

**Primary Dependencies**: Existing FastAPI/SQLAlchemy cabinet web routes, existing deletion lifecycle service, existing server-rendered cabinet JavaScript, and existing pytest server test suite. No new dependency.

**Storage**: Existing Postgres meeting/deletion lifecycle tables. No new schema.

**Testing**: Focused pytest for web/API feedback, list-shell JavaScript, and existing deletion workflow, plus metadata-safe runtime/browser proof when available.

**Target Platform**: Production web cabinet and macOS embedded WebKit cabinet at `/meetings` and `/desktop/meetings`.

**Project Type**: Server-rendered web cabinet inside the hybrid 2brain Rec server/desktop product.

**Performance Goals**: Selection feedback should appear in under one second for the current list limit. Delete submission uses existing deletion lifecycle behavior.

**Constraints**: All new visible strings must be Russian. Deletion copy must remain bounded to `2brain Rec` controlled systems. Evidence must stay metadata-only. Desktop clients still do not receive secrets, signed URLs, object keys, raw audio, or transcript text through list evidence.

**Scale/Scope**: Current owner meeting list limit is at most 100 rows. Batch delete uses the existing single-meeting deletion request once per selected meeting; no new batch API or lifecycle schema is introduced. The normal owner flow does not expose the detailed deletion report.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. This slice does not change capture, recording, routing, or local artifact creation.
- **Visible consent and user control**: PASS. Native capture controls remain untouched; this work is post-meeting cabinet cleanup.
- **Data boundary and secret discipline**: PASS. The list UI and tests must remain metadata-only and reuse server-owned deletion endpoints.
- **Deletion truth and lifecycle accounting**: PASS. The feature explicitly reuses existing deletion lifecycle accounting and bounded copy.
- **Spec-driven delivery**: PASS. Spec, checklist, plan, tasks, analyze, and implementation are produced for feature 053.
- **Product URL governance**: PASS. Public URL and deployment host are unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/053-recording-selection-delete/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cabinet-selection-delete-contract.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── cabinet/web_routes/deletion.py
├── cabinet/deletion_rendering.py
├── cabinet/rendering.py
├── cabinet/static/cabinet/cabinet.js
├── cabinet/templates/cabinet/fragments/deletion_feedback.html
├── api/cabinet.py
└── deletion/service.py

apps/server/tests/
├── unit/test_cabinet_web_shell.py
└── integration/test_meeting_deletion_workflow.py
```

**Structure Decision**: Keep the implementation in the existing cabinet web route, rendering, template, and browser-script modules. Reuse `api/cabinet.py` and `deletion/service.py` without changing the public API response or lifecycle/report contract. Only the user-facing web feedback and list state change.

## Phase 0: Research

See [research.md](./research.md).

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md), [contracts/cabinet-selection-delete-contract.md](./contracts/cabinet-selection-delete-contract.md), and [quickstart.md](./quickstart.md).

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. No capture path changes.
- **Visible consent and user control**: PASS. Post-meeting delete UI does not affect active capture visibility or stop controls.
- **Data boundary and secret discipline**: PASS. UI calls the existing server-owned delete endpoint with bounded confirmation text only.
- **Deletion truth and lifecycle accounting**: PASS. The contract requires bounded Russian copy and existing lifecycle accounting.
- **Deletion UX boundary**: PASS. The detailed report remains a diagnostic surface, while the owner flow returns to the list with concise progress copy and never promises universal erasure.
- **Spec-driven delivery**: PASS. Tasks and analyze must be clean before code edits.

## Complexity Tracking

No constitution violations or extra architecture layers are introduced.
