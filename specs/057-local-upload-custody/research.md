# Research: Local Upload Custody

Date: 2026-06-26

## Decision: Reuse `desktop-upload-queue.v2` As The Custody Ledger

**Rationale**: Feature `042` already provides durable local identity, media
revision identity, server truth, accepted ranges, retry records, and retention
decision fields in `DesktopUploadQueueItem`. Replacing it would increase data
loss risk and create a migration problem for existing local recordings.

**Alternatives considered**:

- New custody database: rejected because the current JSON ledger already holds
  the necessary durable state and a second store creates split-brain risk.
- Server-only queue: rejected because offline, auth-expired, and server-unknown
  recordings must remain locally accountable before the server can represent
  them.
- Native second meeting list: rejected because it competes with the
  server-owned WebView meeting list.

## Decision: Add A Product Custody Projection Instead Of Showing Queue Internals

**Rationale**: Existing implementation states such as `retrying`,
`manual_only`, `server_validation`, and `syncConflictState` are useful for code
but harmful as normal user tasks. A projection can map these to user-safe
custody states, responsible owner, retry class, allowed action, display
priority, and safe copy.

**Alternatives considered**:

- Rename existing enums only: rejected because implementation retry state and
  user-facing action policy are different concepts.
- Keep current UploadQueueStatusView controls: rejected because retry/stop retry
  makes the user responsible for transport mechanics.

## Decision: Automatic Retry Is Product-Owned

**Rationale**: Network, temporary server dependency, upload session expiry, and
unknown transient conditions are not user work. The runner should retry while
retention allows and surface only conditions the meeting owner, admin, support,
or lifecycle policy can change.

**Alternatives considered**:

- Manual retry button for every failure: rejected because it produces a fake
  task and hides product responsibility.
- Hide all local status: rejected because users still need to know whether a
  recording is saved and whether action is required.

## Decision: `404 recording_not_found` Means Server-Unknown Local Custody

**Rationale**: The current desktop client already treats sync-state 404 as
`nil` reconciliation and can create/reuse server identity later. Product
custody must make this behavior explicit: 404 is not terminal loss and must not
authorize fake server rows.

**Alternatives considered**:

- Treat 404 as upload failure: rejected because valid offline/local recordings
  would look lost before registration.
- Insert a native row into the WebView list: rejected because it breaks the
  server-owned list authority.

## Decision: 057 And 058 Communicate Through Stable Fields, Not Shared UI Files

**Rationale**: The server web interface is undergoing a full refactor in
feature `058`. Feature `057` should expose stable API/read-model custody fields
and fallback rules, while `058` owns how those fields are rendered.

**Alternatives considered**:

- Implement cabinet status chips in `057`: rejected because it creates direct
  conflict with the `058` refactor.
- Delay all server fields to `058`: rejected because desktop custody needs
  stable machine-readable owner/action/problem codes independent of cabinet UI.

## Decision: Purge Acknowledgement Requires Local Verification

**Rationale**: Current `acknowledgePendingLocalPurgeTasks()` can acknowledge a
task after listing it. Feature `057` needs stronger lifecycle truth: ack only
after local artifacts are actually removed, tombstoned, or cryptographically
rendered unrecoverable. Failed or unverifiable purge must report safe failure.

**Alternatives considered**:

- Trust server purge requests as complete: rejected because deletion truth would
  overclaim local desktop state.
- Require raw proof payloads: rejected because support/diagnostics must remain
  metadata-only.

## Decision: Expand Custody Runner Triggers

**Rationale**: Current app processing is triggered on app appearance and desktop
auth session change. Feature `057` also needs app activation, network recovery,
wake from sleep, and scheduled retry triggers so the user does not need to open
the meeting WebView or press retry.

**Alternatives considered**:

- Poll constantly: rejected because it is noisy and unnecessary.
- Depend on WebView route load: rejected because local custody is native app
  responsibility and must work when the WebView is closed or on another route.

## Decision: Malformed Queue State Is Blocked Custody Truth

**Rationale**: A malformed or partially written queue file may be the only
remaining pointer to local recordings. It must be quarantined with safe
metadata and surfaced as blocked custody truth, not silently reset to an empty
queue.

**Alternatives considered**:

- Delete and recreate malformed queue: rejected because it can destroy custody
  evidence.
- Show raw JSON/path error to the user: rejected because it leaks technical
  details and private local paths.
