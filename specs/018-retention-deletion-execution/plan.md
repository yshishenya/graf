# Implementation Plan: Retention And Deletion Execution

**Branch**: `018-retention-deletion-execution` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/018-retention-deletion-execution/spec.md`

## Summary

Turn the planned deletion and retention affordances from the meeting cabinet
into executable server-owned lifecycle behavior. The slice adds whole-meeting
deletion requests, retention eligibility scans, active server purge accounting,
metadata-only deletion verification reports, local desktop purge tasks, backup
expiry truth, and external dependency deletion state for MediaScribe, Langfuse,
workflow/temp state, exports, diagnostics, and post-egress limits. Browser and
desktop clients consume the same server/web lifecycle routes; the macOS app only
acknowledges local purge tasks and does not own policy or deletion truth.

## Technical Context

**Language/Version**: Python >=3.13 for server/API/web code; HTML/CSS/vanilla
JavaScript served by FastAPI for cabinet routes; Swift 5 macOS client changes
only for local purge task polling/acknowledgement stubs when needed.

**Primary Dependencies**: Existing FastAPI, Pydantic v2, SQLAlchemy 2 async,
Alembic, existing auth/session/device/tenant dependencies, existing cabinet
access/egress services from feature 017, existing ingest/processing/import
models, existing redaction helpers, existing macOS upload/cabinet clients, and
existing local CI/evidence scanners.

**Storage**: Existing Postgres identity, meeting, ingest, processing,
transcript, diarization, access/share/egress tables plus new lifecycle tables
and meeting lifecycle columns. Existing MinIO/object storage remains
server-only. Desktop local buffers remain local; the server stores only
metadata-only purge task/acknowledgement state.

**Testing**: `uv run --extra dev pytest -q` for server tests; focused contract,
unit, integration, and web-state tests for deletion request/report APIs,
retention jobs, active purge accounting, lifecycle blocking, dependency truth,
local purge tasks, audit fail-closed behavior, no-secret/no-content responses,
and compact cabinet UI states. Swift tests are required only for local purge
client changes. `./infra/scripts/ci-local.sh` remains the final local gate.

**Target Platform**: Rec server/browser cabinet and desktop-embeddable web
routes consumed by macOS. Future Windows/Linux shells consume the same server
contracts for purge task acknowledgement.

**Project Type**: FastAPI backend web service with server-owned product web
surface and a native macOS desktop app as policy client for local purge tasks.

**Performance Goals**: Manual deletion request accepted in under 1 second
locally for seeded MVP meetings. Retention scan evaluates 100 seeded meetings
in under 5 seconds locally. Deletion report renders in under 1 second. Active
server purge reaches complete or explicit failure state within the MVP target of
24 hours; tests may use accelerated clocks and fixtures.

**Constraints**: Whole-meeting deletion only. No public links, external
recipient invitations, partial artifact deletion, legal hold management, admin
policy editor, or universal erasure claims. No direct MediaScribe/object-store
credentials, storage keys, signed URLs, bearer tokens, provider payloads, private
meeting content, or live local paths in API responses, logs, audit metadata,
reports, specs, screenshots, or evidence. Audit and request records must be
persisted before destructive action; failure to write required audit fails
closed.

**Scale/Scope**: MVP owner/admin deletion and retention lifecycle for one
workspace, accepted meeting artifacts from 014-017, local desktop purge task
coordination for registered devices, dependency truth for MediaScribe/Langfuse/
Temporal/MinIO/Postgres/diagnostics/exports/backups, and responsive browser plus
embedded desktop UI states.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Feature does not change macOS recording start/stop, system audio, microphone capture, routing, or upload queue truth. |
| Visible consent and user control | PASS | Deletion and retention cannot start recording or hide the native capture indicator; manual stop remains native. |
| Data boundary and secret discipline | PASS | Server owns lifecycle state, object/dependency accounting, and reports; contracts forbid credentials, signed URLs, storage keys, local paths, and private content in audit/evidence. |
| Deletion truth and lifecycle accounting | PASS | This feature directly implements bounded deletion truth, backup expiry, local purge, dependency, and post-egress accounting. |
| Spec-driven delivery with gates | PASS | Spec and clarification are committed; plan creates research, data model, contracts, quickstart and requires checklist/tasks/analyze before implementation. |
| Product/platform constraints | PASS | Lifecycle policy and UI are browser/server-owned and desktop consumes purge tasks only, preserving multi-platform reuse. |

## Project Structure

### Documentation (this feature)

```text
specs/018-retention-deletion-execution/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── retention-deletion.openapi.yaml
│   ├── deletion-lifecycle-contract.md
│   └── local-purge-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── api/
│   │   ├── cabinet.py              # add deletion/report/lifecycle/local purge routes
│   │   └── schemas.py              # lifecycle, report, retention, purge schemas
│   ├── cabinet/
│   │   ├── access.py               # deleted/deleting access decisions
│   │   ├── egress.py               # block egress for deleting/deleted meetings
│   │   ├── queries.py              # hide deleted rows from normal list by default
│   │   ├── view_models.py          # lifecycle/report/governance state mapping
│   │   └── web.py                  # deletion confirmation/report UI states
│   ├── db/
│   │   ├── models/deletion.py      # lifecycle/report/local purge/audit models
│   │   ├── models/meeting.py       # meeting lifecycle columns
│   │   ├── models/__init__.py      # export deletion models
│   │   └── migrations/versions/0007_retention_deletion_execution.py
│   ├── deletion/
│   │   ├── audit.py                # metadata-only lifecycle audit fail-closed helpers
│   │   ├── policy.py               # retention policy snapshots and safety checks
│   │   ├── service.py              # manual deletion workflow orchestration
│   │   ├── retention.py            # retention eligibility scan and action creation
│   │   ├── report.py               # verification report composition
│   │   └── local_purge.py          # desktop purge task creation/ack handling
│   └── main.py                     # existing router registration remains server-owned
└── tests/
    ├── contract/
    │   ├── test_retention_deletion_contract.py
    │   └── test_deletion_no_secret_leakage.py
    ├── integration/
    │   ├── test_meeting_deletion_workflow.py
    │   ├── test_retention_policy_execution.py
    │   ├── test_deletion_lifecycle_blocks_access.py
    │   ├── test_local_purge_coordination.py
    │   └── test_cabinet_web_deletion_states.py
    └── unit/
        ├── test_deletion_report_view_models.py
        ├── test_deletion_audit_metadata.py
        ├── test_retention_policy_snapshot.py
        └── test_dependency_deletion_states.py

apps/macos/RecApp/
├── Sources/Upload/DesktopUploadClient.swift          # add purge task API calls if needed
├── Sources/Upload/DesktopUploadQueueService.swift    # coordinate local purge ack if needed
└── Tests/RecAppTests/DesktopLocalPurgeTests.swift     # Swift tests only if client changes
```

**Structure Decision**: Extend the existing FastAPI `cabinet` and add a focused
server `deletion` domain package. Deletion policy, lifecycle state, reports,
retention jobs, dependency truth, and access blocking stay server-owned. The
desktop app receives and acknowledges local purge tasks through the same API
contract but does not compute policy or prove purge with private content.

## Phase 0 Research

Research output is captured in [research.md](./research.md).

Resolved decisions:

- Use new lifecycle tables and explicit meeting lifecycle columns rather than
  overloading processing status or egress audit rows.
- Use a metadata-only deletion report as the durable post-deletion surface.
- Block normal review/share/download/export through access decisions and route
  guards as soon as deletion starts.
- Use a deployment/default retention policy snapshot until admin policy editing
  is implemented in a later slice.
- Represent MediaScribe and Langfuse as dependency truth states; do not assume
  external deletion capability.
- Represent local desktop cleanup with purge tasks and acknowledgements; never
  require local private content as proof.

## Phase 1 Design

Design artifacts created by this plan:

- [data-model.md](./data-model.md): deletion request, workflow state,
  artifact/dependency state, verification report, retention policy snapshot,
  local purge task, and audit entities.
- [contracts/retention-deletion.openapi.yaml](./contracts/retention-deletion.openapi.yaml):
  API contract for deletion request/report/lifecycle, retention scan, and
  desktop local purge task acknowledgement.
- [contracts/deletion-lifecycle-contract.md](./contracts/deletion-lifecycle-contract.md):
  lifecycle state machine, access blocking, active purge, dependency, backup,
  report, retry, and no-secret rules.
- [contracts/local-purge-contract.md](./contracts/local-purge-contract.md):
  desktop purge task scope, acknowledgement semantics, offline/unreachable
  states, and privacy constraints.
- [quickstart.md](./quickstart.md): validation scenarios for manual deletion,
  retention, local purge, dependency truth, access blocking, UI states, evidence
  scans, and full local CI.

## Post-Design Constitution Check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Design consumes meeting/artifact metadata and does not alter native capture, route repair, or upload queue semantics. |
| Visible consent and user control | PASS | No route starts recording; deleted/deleting UI states cannot hide native capture indicator or Stop in the macOS shell. |
| Data boundary and secret discipline | PASS | Contracts and data model require metadata-only audit/report state and forbid private content, object keys, dependency payloads, credentials, signed URLs, and local paths. |
| Deletion truth and lifecycle accounting | PASS | Report model separates server purge, backup expiry, local purge, dependency support, and post-egress limits without universal erasure claims. |
| Spec-driven delivery with gates | PASS | Checklists, tasks, analyze, GitHub issue sync, implementation, CI, and screenshot/evidence review remain required after planning. |
| Product/platform constraints | PASS | Server/browser policy routes are reusable across platforms; macOS-specific work is limited to local purge acknowledgement. |

## Complexity Tracking

No constitution violations or complexity exceptions are required.
