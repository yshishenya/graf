# Implementation Plan: Access, Sharing, And Downloads

**Branch**: `017-access-sharing-downloads` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/017-access-sharing-downloads/spec.md`

## Summary

Extend the accepted meeting review cabinet with browser-owned access,
login-required sharing, policy-gated downloads, safe export packages, and
metadata-only egress/audit evidence. The slice closes the MVP gap where feature
016 exposes review surfaces only by workspace convention and leaves
share/export/download controls as planned affordances. Desktop shells may embed
or open these routes, but the server remains the only policy and artifact-egress
owner.

## Technical Context

**Language/Version**: Python >=3.13 for server/API/web code; HTML/CSS/vanilla
JavaScript served by FastAPI for cabinet and embedded desktop routes. No
capture-critical Swift/macOS changes are planned in this slice.

**Primary Dependencies**: Existing FastAPI, Pydantic v2, SQLAlchemy 2 async,
Alembic, existing auth/session/device/tenant dependencies, existing
meeting/processing/import models, existing redaction helpers, and existing
server-owned cabinet module from feature 016.

**Storage**: Existing Postgres identity, meeting, processing, transcript,
diarization, ingest artifact, and audit tables plus new access/share/egress
metadata tables. Existing MinIO/object storage remains server-only; no signed
dependency URLs or object keys are returned to browser or desktop clients.

**Testing**: `uv run --extra dev pytest -q` for server tests; focused contract,
integration, and unit tests for access policy, share grants/revokes, direct
artifact egress denial, audit fail-closed behavior, web UI states, and
content/secret leakage. Ruff and canonical local CI remain required before
closing the slice.

**Target Platform**: Browser web cabinet served by the Rec server and desktop
embedded routes consumed by the macOS shell. Future Windows/Linux shells can
consume the same browser-owned policy routes.

**Project Type**: FastAPI backend web service with server-owned product web
surface and desktop-embeddable review routes.

**Performance Goals**: Access checks for list/detail/share/download/export
complete in under 1 second locally for seeded MVP-size data. Share grant or
revoke state is visible after one page refresh or retry. A small transcript plus
summary export package is authorized and prepared within 5 seconds locally from
seeded fixture data.

**Constraints**: No public links by default; no desktop-owned share/download
policy; no direct MediaScribe/object-store credentials; no raw storage keys,
signed URLs, bearer tokens, filesystem paths, or private transcript/audio in
logs, problem responses, specs, screenshots, or tracked evidence. Downloads and
exports must fail closed if the required metadata-only audit record cannot be
written before egress.

**Scale/Scope**: MVP owner/reviewer flow for one active workspace with
owner/team/shared access, specific-user login-required grants, share revoke,
artifact availability states, per-artifact download policy, combined package
export, audit trail evidence, and responsive desktop-width/mobile-width browser
UI. Public links, external-recipient accounts, retention execution, deletion
execution, legal hold, desktop purge, billing, admin policy editor, and
cross-workspace sharing remain later slices.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Feature extends processed meeting review data only and does not change macOS capture, system audio, microphone, routing, or local recording truth. |
| Visible consent and user control | PASS | No recording start/stop behavior is added; embedded routes cannot hide native active capture indicator or one-action Stop. |
| Data boundary and secret discipline | PASS | Server owns egress and contracts forbid dependency credentials, signed URLs, storage keys, raw paths, and private content in diagnostics/evidence. |
| Deletion truth and lifecycle accounting | PASS | Download/export copy states the post-egress boundary and does not promise universal erasure outside 2brain Rec control. |
| Spec-driven delivery with gates | PASS | Spec/clarify are committed; plan creates research, data model, contracts, quickstart and requires checklist/tasks/analyze before implementation. |
| Product/platform constraints | PASS | Browser/server owns sharing/access/download/export/audit; desktop remains a consumer of browser-owned routes and native capture shell. |

## Project Structure

### Documentation (this feature)

```text
specs/017-access-sharing-downloads/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── access-sharing-downloads.openapi.yaml
│   ├── artifact-egress-contract.md
│   └── meeting-access-ui-state-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── api/
│   │   ├── cabinet.py              # extend list/detail and add access/share/egress routes
│   │   └── schemas.py              # access, share, download, export schemas
│   ├── cabinet/
│   │   ├── access.py               # effective access and share policy decisions
│   │   ├── egress.py               # authorize-and-audit download/export service
│   │   ├── queries.py              # viewer-scoped list/detail reads
│   │   ├── view_models.py          # governance and artifact state mapping
│   │   └── web.py                  # share/download/export UI states
│   ├── db/
│   │   ├── models/meeting_access.py
│   │   └── migrations/versions/    # access/share/egress migration
│   └── main.py                     # existing router registration remains server-owned
└── tests/
    ├── contract/
    │   ├── test_access_sharing_downloads_contract.py
    │   └── test_access_sharing_no_secret_egress.py
    ├── integration/
    │   ├── test_meeting_access_policy.py
    │   ├── test_meeting_share_links.py
    │   ├── test_artifact_egress_policy.py
    │   └── test_cabinet_web_access_states.py
    └── unit/
        ├── test_meeting_access_decisions.py
        ├── test_artifact_egress_view_models.py
        └── test_artifact_egress_audit.py
```

**Structure Decision**: Extend the existing FastAPI `cabinet` module created by
feature 016. Add access and egress services beside current query/view-model/web
code so list/detail, share, download, export, and desktop embedded routes all
use the same server-side policy decisions. Do not introduce a separate frontend
build system or any desktop-owned policy execution.

## Phase 0 Research

Research output is captured in [research.md](./research.md).

Resolved decisions:

- Use server-side effective-access decisions for every list/detail/share/
  download/export route rather than UI-only hiding.
- Use explicit login-required share grants for authenticated users and team
  visibility; keep public links disabled by default.
- Use server-mediated artifact egress, never browser-visible signed dependency
  URLs or object keys.
- Require audit-before-egress and fail closed on share/revoke/download/export
  audit write failures.
- Extend 016 cabinet UI affordances cleanly instead of copying Krisp copy,
  assets, layout, or private data.

## Phase 1 Design

Design artifacts created by this plan:

- [data-model.md](./data-model.md): access state, share grants, artifact policy,
  egress events, export packages, and lifecycle relationships.
- [contracts/access-sharing-downloads.openapi.yaml](./contracts/access-sharing-downloads.openapi.yaml):
  API contract for access state, login-required sharing, download policy, and
  export package operations.
- [contracts/artifact-egress-contract.md](./contracts/artifact-egress-contract.md):
  server-mediated egress, audit, denial, and no-secret rules.
- [contracts/meeting-access-ui-state-contract.md](./contracts/meeting-access-ui-state-contract.md):
  list/detail/share/download/export UI states for browser and embedded routes.
- [quickstart.md](./quickstart.md): validation scenarios for permitted, denied,
  revoked, missing-artifact, policy-disabled, audit-failure, and responsive UI
  states.

## Post-Design Constitution Check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Design consumes processed artifacts and never changes native recording or upload truth. |
| Visible consent and user control | PASS | No route starts capture; desktop embedding contract keeps native capture indicator and Stop outside this feature. |
| Data boundary and secret discipline | PASS | Contracts require server-mediated egress, no dependency URLs/keys, metadata-only audits, and content-safe evidence. |
| Deletion truth and lifecycle accounting | PASS | Data model tracks post-egress events and UI copy states that exported files cannot be revoked by later 2brain Rec deletion. |
| Spec-driven delivery with gates | PASS | Checklists, tasks, analyze, issue sync, implementation, CI, and screenshot evidence remain required after planning. |
| Product/platform constraints | PASS | Browser-owned policy routes can be embedded by desktop shells without making desktop responsible for access or egress. |

## Complexity Tracking

No constitution violations or complexity exceptions are required.
