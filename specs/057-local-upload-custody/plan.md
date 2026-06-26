# Implementation Plan: Local Upload Custody

**Branch**: `codex/057-local-upload-custody` | **Date**: 2026-06-26 |
**Spec**: `specs/057-local-upload-custody/spec.md`

**Input**: Feature specification from
`specs/057-local-upload-custody/spec.md`

## Summary

Turn the existing desktop upload queue into a product custody flow: local
recordings are preserved, retried automatically, reconciled with server truth,
and exposed through calm native status plus stable API/read-model contracts.
This plan builds on feature `042` (`desktop-upload-queue.v2`,
`DesktopUploadQueueService`, `DesktopUploadClient`, and server sync-state)
instead of adding a second queue or a separate local meeting list.

The implementation boundary is explicit: feature `057` may change native
custody logic and stable API/read-model contracts, but it must not edit server
cabinet presentation files owned by feature `058` (`cabinet/web.py`, templates,
CSS/static, or meeting-list/detail markup).

## Technical Context

**Language/Version**: Swift 6 / macOS 14+ desktop app; Python 3.13 FastAPI
server; server-rendered cabinet remains Python/HTML but is out of 057
presentation scope.

**Primary Dependencies**: Swift Foundation, SwiftUI, WebKit embedding,
CryptoKit, existing local recording models, FastAPI, Pydantic, SQLAlchemy async,
existing ingest/sync/deletion contracts.

**Storage**: macOS Application Support recording packages plus
`desktop-upload-queue.v2` JSON; Postgres for server meetings, media revisions,
upload sessions, processing/deletion/local purge lifecycle state; MinIO remains
server-mediated only.

**Testing**: `swift test --package-path apps/macos --disable-swift-testing`;
`cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q`; final local
gate `infra/scripts/ci-local.sh`.

**Target Platform**: macOS MVP desktop app plus existing Linux/Docker server
runtime. No Windows or new capture path in this slice.

**Project Type**: Native desktop app plus FastAPI backend contracts. Server web
cabinet presentation is a dependent consumer for feature `058`, not an
implementation target here.

**Performance Goals**:

- App launch/activation/auth/network recovery must inspect custody state without
  blocking the main UI thread.
- Automatic retry scheduling must preserve accepted server ranges and avoid full
  re-upload when server truth is available.
- Summary status must answer "saved?", "will send?", and "do I need action?"
  within 10 seconds for a first-time user in validation.
- No duplicate server meeting, upload session, or processing job may be created
  by relaunch, reconnect, or re-authentication.

**Constraints**:

- No direct desktop upload to MediaScribe, object storage, or third-party STT.
- No raw audio, transcript text, credentials, bearer tokens, signed URLs,
  cookies, private local paths, or private meeting content in diagnostics,
  logs, specs, screenshots, or evidence.
- Normal UI must not expose "Retry", "Stop retry", manual verification, or
  queue-operation controls for conditions the meeting owner cannot fix.
- `057` write scope must exclude server cabinet presentation files and route
  markup owned by `058`.
- Local purge acknowledgement requires verified local deletion, tombstone, or
  cryptographic unrecoverability before ack.

**Scale/Scope**: Existing MVP owner/workspace path; multiple pending local
recordings; large recordings split into bounded parts; offline/restart/auth
expiry/server outage/policy/deletion/corruption states; one server-owned meeting
row per server-known recording.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Plan Response |
|------|--------|---------------|
| Capture-first MVP integrity | PASS | Uses accepted local recording packages and does not alter live capture, routing, driver behavior, Record, Pause, Resume, or Stop. |
| Visible consent and user control | PASS | Active capture remains native and visible; this slice only changes post-stop custody/upload behavior. |
| Data boundary and secret discipline | PASS | Desktop talks only to 2brain Rec APIs; server-owned dependencies and credentials remain server-side. |
| Deletion truth and lifecycle accounting | PASS | Plan requires purge-before-ack, retention warnings, terminal undelivered evidence, and no recovery promises after terminal purge. |
| Spec-driven delivery with testable gates | PASS | Spec and clarify are complete; plan creates research, data model, contracts, and quickstart before tasks/analyze/implementation. |
| Product/platform constraints | PASS | macOS-native custody UI; Docker/FastAPI backend contracts only; no virtual-driver or MediaScribe direct egress. |
| Metadata-only evidence | PASS | Contracts and quickstart forbid content-bearing diagnostics/evidence. |
| UI trust/accessibility gates | PASS | Native status must be compact, Russian-ready, keyboard reachable, VoiceOver-readable, and non-color-only. |

Post-design re-check: PASS. The design artifacts keep `057` within native
custody plus API/read-model contracts and leave server cabinet presentation to
`058`.

## Project Structure

### Documentation (this feature)

```text
specs/057-local-upload-custody/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── desktop-custody-contract.md
│   └── 057-to-058-handoff-contract.md
├── checklists/
│   └── requirements.md
├── validation/
│   └── README.md              # Created by tasks; metadata-only evidence notes
└── tasks.md                 # Created later by $speckit-tasks
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/App/
│   └── TwoBrainRecApp.swift
├── RecApp/Sources/Capture/
│   └── CaptureControlView.swift
├── RecApp/Sources/Upload/
│   ├── DesktopUploadClient.swift
│   └── DesktopUploadQueueService.swift
├── Shared/Sources/Models/
│   └── AudioModels.swift
└── Shared/Tests/
    ├── DesktopUploadQueueTests.swift
    ├── DesktopUploadClientTests.swift
    └── DesktopLocalPurgeTests.swift

apps/server/
├── src/twobrain_rec_server/api/
│   ├── ingest.py
│   ├── cabinet.py              # API endpoints only, not cabinet presentation
│   └── schemas.py
├── src/twobrain_rec_server/domain/
│   └── statuses.py
├── src/twobrain_rec_server/ingest/
│   ├── desktop_sync.py
│   └── meetings.py
├── src/twobrain_rec_server/cabinet/
│   ├── queries.py              # only if structured read-model fields are needed
│   └── view_models.py           # only if structured read-model fields are needed
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

infra/
└── scripts/ci-local.sh
```

**Structure Decision**: Use the existing macOS/server split from `042`.
Implementation tasks must reject writes to `apps/server/src/twobrain_rec_server/cabinet/web.py`,
server cabinet templates, server cabinet CSS/static, or meeting-list/detail
HTML markup.

## Phase 0 Research Decisions

Research output is captured in `research.md`. Key decisions:

1. Reuse `desktop-upload-queue.v2` and add a custody projection/action policy;
   do not introduce a second native list or queue engine.
2. Treat `UploadItemState`, `UploadRetryMode`, `UploadFailureCategory`, and
   `DesktopSyncConflictState` as implementation inputs, not as normal user copy.
3. Remove normal-user retry/stop-retry controls from the primary UI; automatic
   transport retry remains product-owned.
4. Preserve `404 recording_not_found` as server-unknown local custody truth.
5. Add stable owner/action/retry-class/problem-code fields through API/read-model
   contracts and hand them to `058` without editing server cabinet presentation.
6. Verify local purge before acknowledgement; current blind ack behavior is not
   enough for 057.
7. Add custody triggers for app activation, network recovery, wake, and scheduled
   retry in addition to current launch/auth triggers.

## Phase 1 Design Decisions

Design artifacts:

- `data-model.md`: custody item, custody projection, owner/action policy,
  server truth, incident, purge verification, and malformed ledger quarantine.
- `contracts/desktop-custody-contract.md`: desktop queue-to-custody mapping,
  automatic retry behavior, user action policy, trigger points, purge ack, and
  forbidden content.
- `contracts/057-to-058-handoff-contract.md`: stable read-model/API fields,
  enum values, fallback behavior, and presentation ownership for feature `058`.
- `quickstart.md`: focused and full validation scenarios.

## Implementation Approach

1. **Custody projection over existing queue**
   - Add or refine a product-facing custody projection from
     `DesktopUploadQueueItem`.
   - Keep durable item identity, `localMediaRevisionId`, server ids, accepted
     range truth, retry records, and retention decisions.
   - Quarantine malformed queue documents metadata-safely instead of dropping or
     overwriting them.

2. **Native UI and action policy**
   - Replace normal-user retry/stop-retry controls with owner-aware actions:
     sign in, choose workspace, grant permission, open known review, open
     diagnostics, copy safe report, or explicitly delete local copy.
   - Keep the main workspace as the WebView meeting list. Show aggregate custody
     in the shell/right control surface and secondary details outside the
     server-owned list.
   - Ensure accessibility labels describe custody state without color-only
     meaning.

3. **Automatic custody runner**
   - Run custody processing on launch, app activation, auth/session changes,
     network recovery, wake from sleep, and scheduled retry time.
   - Resume after WebView sign-in without manual retry.
   - Keep processing independent of the meeting WebView route being open.

4. **Server reconciliation and stable contracts**
   - Keep server registration and sync through existing ingest APIs.
   - Normalize problem codes and conflict owner/action fields for auth, access,
     policy/quota, stale device, deletion, dependency, payload, and conflict
     classes.
   - Treat `404 recording_not_found` as local custody, not terminal loss.
   - Add structured fields only in API/read-model layers needed by desktop and
     `058` handoff.

5. **Purge and terminal outcomes**
   - List local purge tasks as today, but acknowledge only after verified local
     deletion, tombstone, or cryptographic unrecoverability.
   - Record safe failures when verification cannot prove purge.
   - Keep terminal undelivered outcomes metadata-only and explicit.

6. **Validation**
   - Add/update macOS unit tests for custody projection, action policy, purge
     verification, malformed queue quarantine, background triggers, and no retry
     buttons in normal UI.
   - Add/update server contract/integration tests for sync-state problem codes,
     owner/action fields, 404 behavior, local purge ack semantics, and handoff
     field fixtures.
   - Run focused tests, then `infra/scripts/ci-local.sh` before implementation
     closeout.

## Complexity Tracking

No constitution violation or additional complexity exception is required. The
feature deliberately reuses the existing queue, server ingest, reconciliation,
and local purge contracts.
