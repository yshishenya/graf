# Research: Retention And Deletion Execution

Feature: `018-retention-deletion-execution`
Date: 2026-06-16

## Decision 1: Add a dedicated lifecycle domain instead of extending egress audit

**Decision**: Add `twobrain_rec_server.deletion` plus dedicated deletion
tables for requests, artifact states, reports, local purge tasks, retention
policy snapshots, and lifecycle audit.

**Rationale**: Feature 017 egress audit records access/share/download/export
events. Deletion and retention need durable workflow state, report state, retry
state, dependency state, and post-deletion visibility after private meeting
content is purged. Overloading egress audit would mix policy evidence with
destructive lifecycle execution and make report reconstruction fragile.

**Alternatives considered**:

- Reuse `meeting_egress_audit_events`: rejected because it lacks artifact
  lifecycle, dependency, backup, local purge, and retry semantics.
- Use only `meetings.status`: rejected because whole-meeting status cannot
  represent per-artifact, dependency, backup, and local purge truth.

## Decision 2: Persist lifecycle columns on `meetings`

**Decision**: Add meeting-level lifecycle columns for `deletion_state`,
`deletion_requested_at`, `deleted_at`, `retention_delete_after`, and
`retention_policy_state`.

**Rationale**: Normal list/detail/share/download/export routes must block or
hide meetings quickly without reconstructing report tables for every query.
The report tables remain the source of detailed truth; the meeting columns are
the fast gate and user-facing lifecycle summary.

**Alternatives considered**:

- Derive all state from latest deletion request: rejected because list and
  egress paths would become harder to make fail-closed.

## Decision 3: Manual deletion and retention use the same workflow model

**Decision**: Manual owner/admin deletion and retention-triggered deletion
create the same deletion request and artifact state records, differing only in
request source, actor, and policy snapshot.

**Rationale**: Users and auditors need one deletion report shape regardless of
why deletion started. This keeps access blocking, retry behavior, report copy,
dependency truth, local purge tasks, and backup expiry accounting consistent.

**Alternatives considered**:

- Separate retention-only archival state: rejected for MVP because it would
  create two user-visible deletion truth models.

## Decision 4: Retention policy comes from a default/deployment snapshot

**Decision**: Use configured/default retention values and persist a
`RetentionPolicySnapshot` per evaluation/action. Admin editing UI remains out of
scope.

**Rationale**: The spec requires retention execution before admin editing
exists. Snapshotting policy values makes later review truthful and avoids
retroactive reinterpretation when defaults change.

**Alternatives considered**:

- Hard-code retention values without a snapshot: rejected because reports would
  not explain why an action happened.
- Build admin policy editing now: rejected as explicit out of scope.

## Decision 5: Access blocking starts at deletion request acceptance

**Decision**: As soon as deletion is accepted and audit/request state is
persisted, normal cabinet review, transcript, audio, share, download, and export
surfaces resolve to deleting/deleted lifecycle states or bounded not-found
states.

**Rationale**: Deletion must not allow content egress while purge is in
progress. Blocking at acceptance prevents races with downloads/exports and
stale share links.

**Alternatives considered**:

- Wait until active purge completes: rejected because content could still be
  viewed or exported after the user requested deletion.

## Decision 6: Local desktop purge is task/acknowledgement based

**Decision**: Server creates metadata-only local purge tasks for relevant
registered devices. Desktop clients poll or receive these tasks and respond with
metadata-only acknowledgement, failure, local expiry reliance, or unreachable
state.

**Rationale**: The server cannot prove local file removal while a device is
offline, and the desktop must not upload private local artifacts as proof.
Task/ack state gives truthful user-visible accounting and works for future
platform shells.

**Alternatives considered**:

- Server assumes local purge when upload finished: rejected as false deletion
  truth.
- Desktop uploads local file inventory as proof: rejected for privacy and local
  path leakage risk.

## Decision 7: External dependencies are truth states, not assumed deletion

**Decision**: MediaScribe, Langfuse, workflow/temp state, diagnostics, backups,
exports, and post-egress copies are represented as explicit report states. The
system never claims full external purge unless supported and confirmed.

**Rationale**: The constitution requires bounded deletion truth. Current
MediaScribe deletion support is not assumed, Langfuse is metadata-only by
default, and downloaded/exported files are outside later revocation.

**Alternatives considered**:

- Omit external dependencies from reports until integrations mature: rejected
  because omission would imply stronger deletion than the system can prove.

## Decision 8: Metadata-only audit fails closed before destructive action

**Decision**: Deletion request, lifecycle audit, and initial report state must
be persisted before any destructive purge runs. If required audit persistence
fails, the deletion request is rejected or marked failed before content changes.

**Rationale**: Audit must survive deletion without becoming hidden content
storage. Fail-closed ordering prevents unverifiable destructive actions.

**Alternatives considered**:

- Best-effort audit after purge: rejected because a failure would leave no
  trustworthy deletion proof.
