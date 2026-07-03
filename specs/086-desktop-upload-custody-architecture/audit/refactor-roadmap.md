# Refactor Roadmap: Desktop Upload Custody Architecture

086 does not implement these batches. Each batch is a future small PR or a
separate Spec Kit slice with its own validation.

## Batch Order

### RB-086-01: Queue Persistence And Package Discovery Map

- **Classification**: `split soon`
- **Goal**: Separate queue document load/save/quarantine and package discovery
  responsibilities from upload orchestration without changing queue state.
- **Included paths**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
  - related upload queue tests under `apps/macos/Shared/Tests/`
- **Excluded paths**: server ingest behavior, local purge acknowledgement,
  support incident behavior, capture writer behavior.
- **Expected diff shape**: extraction-only, behavior-preserving.
- **Validation**: `swift test --package-path apps/macos` plus focused queue
  persistence/package discovery tests.
- **Stop condition**: Stop if queue document compatibility, deterministic item
  identity, upload eligibility, or malformed queue quarantine behavior changes.

### RB-086-02: Upload Transport And DTO Boundary

- **Classification**: `split soon`
- **Goal**: Split HTTP request/DTO helpers from upload orchestration while
  preserving idempotency, missing-range retry, and finalize behavior.
- **Included paths**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
  - server ingest contract tests if DTO shape or endpoint calls move.
- **Excluded paths**: server route behavior, schema changes, processing
  submission behavior.
- **Expected diff shape**: extraction-only unless a separate contract slice is
  approved.
- **Validation**: upload client tests, server ingest contract tests,
  `infra/scripts/ci-local.sh` if server tests or contracts change.
- **Stop condition**: Stop if idempotency keys, missing range behavior, upload
  part numbering, status mapping, or finalize semantics change.

### RB-086-03: Custody Projection And User Copy Split

- **Classification**: `split soon`
- **Goal**: Separate custody state derivation from user-facing copy and support
  safe reports.
- **Included paths**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
  - `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` only if
    call-site wiring is required.
- **Excluded paths**: upload retry behavior, server ingest contracts, deletion
  behavior.
- **Expected diff shape**: extraction-only with tests pinning copy keys and
  projection outputs.
- **Validation**: custody projection tests, support incident fixture tests,
  accessibility/copy tests already present for support action surfaces.
- **Stop condition**: Stop if custody state, owner, copy key, normal action,
  support report availability, or metadata safety output changes.

### RB-086-04: Local Purge Acknowledgement Boundary

- **Classification**: `risky / needs spec`
- **Goal**: Make local purge acknowledgement easier to review without changing
  deletion truth.
- **Included paths**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
  - `apps/server/src/twobrain_rec_server/deletion/local_purge.py`
  - `apps/server/src/twobrain_rec_server/api/cabinet.py`
- **Excluded paths**: deletion product copy changes and server purge behavior
  unless a deletion/retention slice owns them.
- **Expected diff shape**: separate Spec Kit slice before code if server and
  desktop both change.
- **Validation**: desktop local purge tests, server deletion/local purge tests,
  no-private-path evidence scan.
- **Stop condition**: Stop if local purge can be acknowledged without verified
  local deletion truth or if deletion report wording changes incidentally.

### RB-086-05: Support Incident Payload Boundary

- **Classification**: `split soon`
- **Goal**: Separate metadata-only support report construction from custody
  projection copy while preserving redaction and safe schema.
- **Included paths**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
  - `apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift`
  - `apps/server/src/twobrain_rec_server/support/`
  - `apps/server/src/twobrain_rec_server/api/support_incidents.py`
- **Excluded paths**: GitHub issue operational behavior unless tests cover it;
  raw diagnostics; support token handling.
- **Expected diff shape**: extraction-only for desktop; server change only if a
  contract fix is explicitly required.
- **Validation**: support incident fixture tests, server support redaction
  tests, no-secret scan.
- **Stop condition**: Stop if safe schema version, allowed fields, idempotency,
  rate limiting, or copy fallback behavior changes.

### RB-086-06: Delete-Proof Sweep

- **Classification**: `risky / needs spec`
- **Goal**: Search for removable upload-custody code only after the maps above
  are stable.
- **Included paths**: upload/custody/support/local purge paths from this slice.
- **Excluded paths**: broad repo cleanup.
- **Expected diff shape**: deletion-only PR after proof.
- **Validation**: caller search, runtime/entrypoint search, Codable/persistence
  compatibility review, focused tests, rollback plan.
- **Stop condition**: Stop if evidence depends only on static reference count
  or if any product gate depends on the candidate.

## Plain-Language Closeout

1. Healthy: the product already has a server-mediated upload boundary,
   explicit local purge, metadata-only support intent, and useful tests.
2. Pain: queue, client, custody projection, support, and local purge concerns
   are packed together around the product's custody promise.
3. Safe deletion: none approved yet.
4. Separate PRs: queue persistence, upload transport, custody projection,
   support payloads, and local purge need separate batches.
5. Checks: Swift tests, focused upload/custody/local purge/support tests,
   server ingest/deletion/support checks, no-secret scans, and local CI when
   server code changes.
