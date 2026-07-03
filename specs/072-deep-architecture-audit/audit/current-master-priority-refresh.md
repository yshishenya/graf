# Current Master Priority Refresh

**Date**: 2026-07-03
**Inspected commit**: `c4dc54c4`
**Worktree**: `/private/tmp/crisp-085-global-architecture-scan`
**Branch**: `codex/085-global-architecture-scan`
**Lane**: Significant architecture / high-risk read-only audit.

This refresh updates the 072 roadmap after the cabinet follow-up PRs merged.
It does not approve product/runtime code changes, dependency removals, file
deletions, or production deploy.

## Why This Refresh Exists

The next architecture work should not keep shaving small cabinet helpers just
because earlier PRs proved that pattern. Ponytail applies here as a shape
constraint: delete or simplify only where the real runtime flow proves value;
do not add more files merely to make the tree look tidy.

The broad scan shows that `cabinet/rendering.py` is no longer the main product
architecture pain after recent cabinet splits. Continuing route/rendering
micro-splits now has diminishing returns. The next high-value work should move
up to product flows that combine custody, deletion/local purge, support,
export, or capture lifecycle responsibility.

## Evidence Snapshot

Commands used in the clean worktree:

- `git ls-files` inventory, not raw filesystem `find`.
- Python AST import/fan-in scan for `apps/server/src/twobrain_rec_server/`.
- Swift/function landmark scan for macOS upload, app composition, diagnostics,
  and shared model files.
- Runtime-flow review against `specs/072-deep-architecture-audit/audit/runtime-flows.md`.

Current hotspot sizes:

| Surface | Current evidence |
|---------|------------------|
| Server package | 170 Python files / 35,993 lines under `apps/server/src/twobrain_rec_server/` |
| Server cabinet | 5,426 lines in `cabinet/` plus 2,372 lines in `cabinet/web_routes/` |
| macOS app services | 66 Swift files / 20,917 lines under `apps/macos/RecApp/Sources/` |
| macOS upload | 4,717 lines under `apps/macos/RecApp/Sources/Upload/` |
| Shared Swift models | 6,593 lines under `apps/macos/Shared/Sources/Models/` |
| macOS scripts | 24 shell scripts / 3,696 lines |
| Infra scripts | 9 shell scripts / 820 lines |

Selected file evidence:

| Path | Lines | Current read |
|------|-------|--------------|
| `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` | 1,657 | Queue persistence, retry, reconciliation, upload orchestration, local purge acknowledgement, support incident state, artifact summaries. |
| `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift` | 1,550 | Custody truth, local purge state, support report safety, user-facing custody explanation. |
| `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift` | 1,112 | HTTP ingest client, upload sessions, reconciliation, local purge task API, support incident API, DTOs. |
| `apps/macos/RecApp/App/TwoBrainRecApp.swift` | 2,160 | App lifecycle, permission prompts, capture controls, upload queue refresh, support reporting, local audio diagnostics, window behavior. |
| `apps/server/src/twobrain_rec_server/cabinet/view_models.py` | 1,970 | Cabinet presentation truth across calendar, review, processing, transcript, notes, playback, provenance. |
| `apps/server/src/twobrain_rec_server/cabinet/egress.py` | 1,070 | Egress policy, audit events, download, playback, export package, artifact state. |
| `apps/server/src/twobrain_rec_server/cabinet/rendering.py` | 579 | Still shared, but no longer the biggest cabinet problem. |
| `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift` | 1,162 | Multiple diagnostic evidence families and redaction-sensitive support data. |
| `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift` | 2,370 | Shared capture contract models. |
| `apps/macos/Shared/Sources/Models/AudioModels.swift` | 2,295 | Shared audio contract models. |

Python fan-in/fan-out highlights:

- `cabinet/egress.py`: 1,070 lines, fan-in from API, admin, cabinet queries,
  and access code; fan-out to database/domain/cabinet dependencies.
- `api/schemas.py`: 943 lines, 28-module fan-in, therefore a contract surface,
  not a casual split target.
- `domain/statuses.py`: 439 lines, 42-module fan-in, therefore a shared status
  vocabulary, not delete-now evidence.
- `api/auth.py`, `auth/dependencies.py`, and `auth/callbacks.py` remain
  sensitive auth/session/device surfaces.

## Priority Shift

### P0: Stop Cabinet Rendering Micro-Splits

Do not continue splitting cabinet rendering helpers just because the previous
server PRs were safe. The cabinet work already reduced the most obvious route
and rendering concentration. Future cabinet work should be boundary-level:
egress policy/export/playback/audit, or presentation view-model families.

Allowed next cabinet PR shape:

- split `cabinet/egress.py` by audit, policy/state, playback, download, and
  export only if tests prove no authorization or output change;
- or split `cabinet/view_models.py` by presentation family only after egress is
  stable.

Disallowed next cabinet PR shape:

- another tiny helper extraction that does not reduce review risk;
- any auth/session/deletion behavior change hidden inside a "cleanup" PR;
- deletion by static ref-count alone.

### P1: Desktop Upload Custody Architecture

This is the highest-value next architecture slice if the goal is to improve the
product, not just make files smaller.

Runtime flow covered:

`capture -> local package -> desktop queue -> upload/ingest -> server custody -> processing -> cabinet/review -> deletion/local purge -> support`

Why it matters:

- It owns the handoff from local recording truth to server custody.
- It touches deletion/local purge acknowledgement, which is product-trust
  sensitive.
- It touches support incident reporting and metadata-only evidence.
- It combines queue scheduling, HTTP client behavior, custody projection, local
  artifact deletion, retry logic, and UI-facing summaries.

Classification:

- `split soon`, but high-risk enough to start with a separate Spec Kit slice
  before code changes.

Recommended slice:

- `086-desktop-upload-custody-architecture`

First read-only outputs for that slice:

- queue/client/custody/local-purge/support responsibility map;
- desktop-to-server contract matrix;
- fixture and XCTest coverage inventory;
- proposed small PR sequence with stop conditions.

Minimum checks before any upload-custody refactor batch:

- `swift test --package-path apps/macos`;
- focused upload queue tests;
- local purge acknowledgement tests;
- support incident payload/redaction checks;
- server ingest contract checks if API payload or route call sites move;
- no raw audio, transcript, signed URL, token, or private path evidence in
  committed artifacts.

### P2: Cabinet Egress Boundary

If we want a lower-risk server-only PR before the desktop slice, this is the
best next target.

Runtime flow covered:

`cabinet/review -> download/playback/export -> audit -> deletion post-egress limits`

Why it matters:

- `cabinet/egress.py` mixes policy, audit, download, playback, and export.
- It is called by user cabinet API, admin API, admin web, cabinet queries, and
  cabinet access code.
- It is a trust boundary, so splitting it can improve reviewability only if
  tests pin behavior.

Classification:

- `split soon`, server-only, medium-high risk.

Suggested PR sequence:

1. Extract egress audit recording/safe metadata.
2. Extract artifact state and policy resolution.
3. Extract playback byte-range and playback artifact loading.
4. Extract export package assembly.

Minimum checks:

- cabinet API/web tests;
- admin file/export tests;
- playback byte-range tests;
- export/download authorization tests;
- deletion post-egress wording/state checks;
- `infra/scripts/ci-local.sh`.

### P3: Cabinet View Models

This is real size pain, but it should come after egress because much of the
risk is presentation coupling to policy/export/playback state.

Suggested boundaries:

- calendar settings and connection view models;
- meeting list/review shell view models;
- transcript/speaker/notes view models;
- playback/provenance/status view models.

Minimum checks:

- cabinet template rendering tests;
- route response snapshot or semantic assertions;
- no auth/session/deletion behavior changes;
- `infra/scripts/ci-local.sh`.

### P4: Desktop App Composition

`TwoBrainRecApp.swift` is a broad app-composition hotspot, but it owns sensitive
startup and capture visibility behavior. Treat it as a separate macOS slice,
not a casual cleanup.

Suggested boundaries:

- app lifecycle delegate and window behavior;
- permission onboarding and calendar prompts;
- manual recording command handlers;
- upload queue refresh/support reporting;
- local audio diagnostics.

Minimum checks:

- `swift test --package-path apps/macos`;
- app launch smoke;
- capture visible-state review;
- manual start/stop/pause/resume behavior proof;
- no change to capture startup order without a capture spec.

### P5: Diagnostics And Shared Models

Diagnostics and shared model segmentation are useful only after higher-value
flows above are stable.

Diagnostics checks:

- redaction tests;
- support payload tests;
- no-secret/evidence scan.

Shared model checks:

- Swift tests;
- contract validation tool;
- serialization fixture compatibility.

## Delete-Now Result

Current result remains:

`delete now`: 0

The broad scan did not find a safe deletion candidate with enough caller and
runtime evidence. Low-reference functions observed in server code were mostly:

- FastAPI route handlers reached by decorators;
- private helper functions used inside large modules;
- runtime policy helpers;
- contract/status types with high fan-in;
- script or deploy entrypoints.

Therefore deletion is not approved from this refresh. A future deletion batch
must be its own proof task, not a side effect of refactoring.

Deletion proof required before any `delete now` PR:

- static caller search;
- runtime or entrypoint search;
- package/Docker/script/test manifest search;
- focused tests for the owning boundary;
- rollback plan;
- evidence that no product gate depends on the artifact.

## Plain-Language Answer

1. Architecture is already normal where boundaries are explicit: native capture
   owns active recording, server owns MediaScribe/processing, cabinet owns
   post-meeting review, deploy is scripted, and deletion language is treated as
   a product-trust boundary.
2. The real pain is not "we need more layers." The pain is custody and trust
   reviewability: desktop upload/local purge/support, cabinet egress, cabinet
   view models, app lifecycle, diagnostics, and shared contract models.
3. Nothing can be safely deleted right now from the evidence collected. Deletion
   needs a separate proof pass.
4. Separate PRs should start with either desktop upload custody architecture or,
   if we want a smaller server-side step first, cabinet egress boundary.
5. Every batch needs focused boundary tests before merge. Full production deploy
   remains out of scope unless a later release/deploy request asks for it.

## Recommended Next Move

Choose one path:

- Product-value first: open `086-desktop-upload-custody-architecture` as a
  high-risk Spec Kit slice, read-only first.
- Lower-risk server first: open `086-cabinet-egress-boundary` for a
  behavior-preserving egress split with cabinet/admin tests.

Do not continue cabinet rendering micro-splits unless they are part of one of
the boundary-level plans above.
