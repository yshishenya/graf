# Research: Desktop Upload Queue And Resilient Upload Behavior

## Decision: Use File-Backed Durable Queue State

Persist queue items as JSON under the app support area and rewrite atomically
after each state transition. Queue identity is derived from local recording
`directoryId` and `sessionId`, with server IDs recorded only after the server
confirms them.

**Rationale**: The macOS MVP already stores local recording artifacts under app
support, and this feature does not need a database. File-backed JSON is easy to
audit, survives restart, and keeps recovery available even when upload cannot
start.

**Alternatives considered**:

- SQLite/Core Data: deferred because queue volume is small and no relational
  query surface is needed yet.
- In-memory queue: rejected because restart survival is a P1 requirement.
- Server-only state: rejected because offline startup and local retention truth
  must remain visible before any server call succeeds.

## Decision: Use Only Server-Mediated `012` Ingest API

The desktop client creates/uses backend meetings and upload sessions through
`POST /api/v1/meetings`, `POST /api/v1/meetings/{meeting_id}/upload-sessions`,
`PUT /api/v1/upload-sessions/{session_id}/tracks/{track_role}/parts/{part_number}`,
`GET /api/v1/upload-sessions/{session_id}/missing-ranges`, and
`POST /api/v1/upload-sessions/{session_id}/finalize`.

**Rationale**: The constitution forbids desktop MediaScribe credentials and
hidden external egress. The `012` contract already defines server-mediated
upload, accepted bytes, missing ranges, idempotency, and desktop truth labels.

**Alternatives considered**:

- Direct MinIO/object-store upload: rejected for this slice because it would
  require signed URL/token handling on desktop.
- Direct MediaScribe upload: constitution violation.
- Local-only queue with no client: rejected because this feature must move
  accepted local artifacts toward owner-controlled ingest.

## Decision: Map Local Track Roles Explicitly

Local recording `local_mic` maps to backend `microphone`, local
`remote_speaker`/system-audio incoming maps to backend `system`, and
`manifest.json` maps to backend `manifest`.

**Rationale**: Local manifests use product-facing dual-track roles, while the
backend ingest contract uses transport roles. Explicit mapping prevents
`remote_speaker` from leaking into API paths that only accept `system`.

**Alternatives considered**:

- Rename local roles: rejected because existing recording contracts and tests
  rely on `local_mic` and `remote_speaker`.
- Let backend infer roles from filenames: rejected because it weakens
  idempotency and missing-range reconciliation.

## Decision: Retry Until Local Retention Deadline, Then Manual-Only

Transient network/server availability failures use bounded exponential retry.
The automatic retry window ends at the local buffer retention deadline; after
that the queue item becomes manual-only/blocked and keeps local artifacts until
explicit policy terminalization.

**Rationale**: The local buffer policy already captures owner expectations for
how long local artifacts remain available. Reusing it avoids an unbounded
background worker and keeps retention/deletion truth consistent.

**Alternatives considered**:

- Infinite automatic retry: rejected because it hides stale failures and can
  create resource pressure.
- Immediate terminal failure after one error: rejected because transient
  network failures are expected.
- Purge on retry expiry: rejected because upload truth is unknown and the spec
  requires explicit terminal decision.

## Decision: Compact Native Queue UI Inside Existing Capture Controls

Expose the newest/active queue item and aggregate pending count in the existing
`CaptureControlView`, with status, progress, reason, and one relevant action.

**Rationale**: Apple Human Interface Guidelines emphasize feedback and progress
for lengthy operations; NN/g's usability heuristics emphasize visibility of
system status and recovery from errors. A compact queue surface keeps the
desktop workflow simple and avoids a product-wide redesign.

**Primary sources**:

- Apple Human Interface Guidelines: <https://developer.apple.com/design/human-interface-guidelines>
- Apple Progress Indicators: <https://developer.apple.com/design/human-interface-guidelines/progress-indicators>
- Apple Feedback: <https://developer.apple.com/design/human-interface-guidelines/feedback>
- NN/g Visibility of System Status: <https://www.nngroup.com/articles/visibility-system-status/>
- NN/g Error-Message Guidelines: <https://www.nngroup.com/articles/error-message-guidelines/>

**Alternatives considered**:

- Separate upload manager window: deferred until queue volume and admin
  workflows justify it.
- Status only in diagnostics logs: rejected because users need visible truth and
  recovery controls.
- Marketing-style redesign: rejected because this is an operational native
  desktop control surface.
