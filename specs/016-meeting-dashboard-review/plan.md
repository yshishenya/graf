# Implementation Plan: Meeting Dashboard Review

**Branch**: `016-meeting-dashboard-review` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/016-meeting-dashboard-review/spec.md`

## Summary

Implement the first authorized post-processing product surface for `2brain Rec`:
a browser web cabinet and desktop-embeddable meeting review surface for
processed, processing, degraded, failed, and unavailable meetings. The slice
adds content-safe meeting list/detail contracts, server-owned cabinet routes,
truthful notes/transcript/speaker/provenance states, list search/filter/sort
controls, and gated future governance entry points. It does not add live
recording controls, public sharing, downloads, retention jobs, deletion
execution, billing, team admin, or new MediaScribe egress.

## Technical Context

**Language/Version**: Python >=3.13 for server/API/web code; HTML/CSS/vanilla
JavaScript served by FastAPI for the first cabinet shell; Swift macOS app stays
untouched except for future embedding contracts.

**Primary Dependencies**: Existing FastAPI, Pydantic v2, SQLAlchemy 2 async,
Alembic, structlog/redaction helpers, existing auth/session/device dependencies,
existing processing/import models. No new frontend build system is introduced
in 016.

**Storage**: Existing Postgres tables for meetings, upload/session artifacts,
processing workflows/jobs/results, transcript segments, diarization segments,
dependency state, and RLS-protected tenant identity. No new content-bearing
storage is required for 016.

**Testing**: `uv run --extra dev pytest -q` for server unit/contract/integration
tests; focused cabinet API/web tests; Ruff; content/secret leakage scans for
problem responses, logs, evidence, and tracked screenshots.

**Target Platform**: Browser web cabinet served by the Rec server and allowed
desktop embedded routes for macOS now and future Windows/Linux shells. Desktop
native capture shell remains platform-owned.

**Project Type**: FastAPI backend web service with server-owned product web
surface plus future desktop embedding contract.

**Performance Goals**: Meeting list and detail API responses complete in under
1 second locally for seeded MVP-size data. A user can navigate from cabinet
list to a ready meeting detail within 30 seconds without operator tooling.
Frontend interactions avoid layout shifts and keep table/detail controls
scannable at 1440x900 and compact desktop widths.

**Constraints**: No public link creation, no audio/transcript/summary download,
no deletion execution, no live capture start/stop, no direct object-store or
MediaScribe credentials in UI/API/logs, no raw transcript text in diagnostics or
tracked evidence, no server-rendered ownership of active capture truth, and no
Krisp brand/copy/icon copying.

**Scale/Scope**: MVP owner/reviewer flow for authorized meetings in one active
workspace, with list/search/filter/sort, ready detail, processing/detail
states, transcript/speaker review, provenance, and disabled/gated governance
slots. Full Action Items center, Contacts management, AI assistant execution,
templates generation, settings policy editing, access/sharing/downloads, and
retention/deletion remain later slices.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Feature consumes uploaded/processed meeting records only and does not alter macOS capture, system audio, microphone, or local package truth. |
| Visible consent and user control | PASS | No new recording trigger; embedded routes cannot hide native active recording indicator or Stop. |
| Data boundary and secret discipline | PASS | UI/API contracts forbid MediaScribe/object-store credentials, signed URLs, raw audio, live paths, and transcript content in logs/diagnostics/evidence. |
| Deletion truth and lifecycle accounting | PASS | Deletion is a gated future entry point using truthful "2brain Rec controls" wording; no deletion execution is introduced. |
| Spec-driven delivery with gates | PASS | Spec, clarify review, plan, checklists, tasks, analyze, issue sync, implementation, validation, and evidence are required. |
| Product/platform constraints | PASS | Server/web owns post-meeting UI; native desktop retains capture-critical trust shell per ADR 001 and 030 route contracts. |

## Project Structure

### Documentation (this feature)

```text
specs/016-meeting-dashboard-review/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── meeting-dashboard.openapi.yaml
│   ├── embedded-meeting-route-contract.md
│   └── meeting-review-ui-state-contract.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   ├── ux.md
│   └── infra.md
├── research/
│   ├── reference-audit.md
│   ├── desktop-screenshot-checklist.md
│   └── notes/
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── api/
│   │   ├── cabinet.py              # new content-safe cabinet JSON API
│   │   └── schemas.py              # cabinet response schemas
│   ├── cabinet/
│   │   ├── __init__.py
│   │   ├── queries.py              # meeting list/detail DB reads
│   │   ├── view_models.py          # UI-safe state mapping
│   │   └── web.py                  # HTML/CSS/JS cabinet routes
│   ├── main.py                     # include cabinet API/web routers
│   └── observability/
│       └── redaction.py            # reused for evidence/log safety
└── tests/
    ├── contract/
    │   ├── test_cabinet_contract.py
    │   └── test_cabinet_no_secret_content_egress.py
    ├── integration/
    │   ├── test_cabinet_meeting_list.py
    │   └── test_cabinet_meeting_detail.py
    └── unit/
        ├── test_cabinet_view_models.py
        └── test_cabinet_web_shell.py
```

**Structure Decision**: Extend the existing FastAPI server with a `cabinet`
module. Keep product UI server-owned, content-safe, and embeddable without
introducing a separate frontend build stack. The macOS app is not changed in
016; desktop embedding is validated through route contracts and web route
behavior.

## Phase 0 Research

Research output is captured in [research.md](./research.md).

Resolved decisions:

- Use a server-owned FastAPI web cabinet plus content-safe JSON endpoints rather
  than a new SPA build stack for 016.
- Use authenticated/RLS-guarded database reads from existing meeting,
  processing, transcript, and diarization tables; do not add duplicate review
  storage.
- Use explicit ready/processing/degraded/failed/unavailable view states rather
  than rendering fake notes or transcript placeholders.
- Reserve Action Items, Contacts, Templates, Assistant, Share, Export,
  Download, Retention, and Delete locations while keeping execution disabled or
  out of scope.
- Save raw authenticated reference screenshots outside git; tracked artifacts
  remain metadata-only and sanitized.

## Phase 1 Design

Design artifacts created by this plan:

- [data-model.md](./data-model.md): meeting list/review view models, transcript
  segment state, speaker state, governance actions, and embedded route state.
- [contracts/meeting-dashboard.openapi.yaml](./contracts/meeting-dashboard.openapi.yaml):
  content-safe list/detail API contracts.
- [contracts/embedded-meeting-route-contract.md](./contracts/embedded-meeting-route-contract.md):
  browser and desktop route ownership, fallback, and native-boundary rules.
- [contracts/meeting-review-ui-state-contract.md](./contracts/meeting-review-ui-state-contract.md):
  UI states, disabled actions, accessibility/localization, and evidence rules.
- [quickstart.md](./quickstart.md): validation scenarios for list, ready detail,
  processing/degraded states, RLS denial, web shell, embedded route safety, and
  reference/evidence leakage.

## Post-Design Constitution Check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Design adds review routes only; native capture controls remain outside the web cabinet and outside 016. |
| Visible consent and user control | PASS | Embedded route contract requires native capture indicator and Stop to remain visible and authoritative. |
| Data boundary and secret discipline | PASS | API/UI contracts expose transcript only in authorized detail payloads and keep logs, diagnostics, problem responses, screenshots, and evidence content-safe. |
| Deletion truth and lifecycle accounting | PASS | Governance contract keeps deletion as disabled/planned and uses truthful lifecycle copy; no execution path is added. |
| Spec-driven delivery with gates | PASS | Plan creates research, data model, contracts, quickstart, and requires checklist/tasks/analyze before implementation. |
| Product/platform constraints | PASS | Web-owned product surface aligns with ADR 001 and 030 embedded route contract; broad admin/billing/team routes remain browser-only/future. |

## Complexity Tracking

No constitution violations or complexity exceptions are required.
