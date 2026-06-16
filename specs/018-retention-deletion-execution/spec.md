# Feature Specification: Retention And Deletion Execution

**Feature Branch**: `018-retention-deletion-execution`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "Continue toward MVP after accepted meeting review, desktop cabinet embedding, and access/sharing/downloads by implementing server-side retention jobs, deletion workflows, deletion verification reports, local desktop purge coordination, backup expiry accounting, and external dependency deletion truth for 2brain Rec."

## Product Scope Boundary

This feature turns the deletion and retention truth surfaces reserved by
`016` and `017` into executable lifecycle behavior. It owns whole-meeting
deletion for MVP-created artifacts, retention eligibility, active server purge,
deletion verification reports, local desktop purge coordination, backup expiry
truth, metadata-only audit, and external dependency state for MediaScribe,
Langfuse, diagnostics, workflow payloads, exports, and post-egress limits.

The MVP deletion unit is the whole meeting. Partial deletion of only audio,
only transcript, only notes, or only one artifact class is out of scope unless
a later accepted spec supersedes this boundary. This feature must not promise
universal erasure beyond `2brain Rec` control. Product copy must use the
bounded deletion model: "Delete this meeting everywhere 2brain Rec controls."

This feature is server/web owned. The macOS app may receive local purge tasks
and report purge acknowledgements, but server lifecycle workflows own policy,
state, audit, reports, and user-visible deletion truth. Native desktop capture
controls, active recording, upload queue truth, and local diagnostic safety
remain native and must not be weakened by this feature.

## Clarifications

### Session 2026-06-16

- Q: What deletion unit is supported in the MVP? -> A: Whole meeting only.
- Q: What retention policy source is used before admin editing UI exists? -> A: Deployment/default policy snapshot.
- Q: What if MediaScribe deletion support is unavailable or unconfirmed? -> A: Report unknown/unsupported; never claim full purge.
- Q: What proves local desktop purge? -> A: Metadata acknowledgement or documented local-expiry reliance.
- Q: Does this feature add public links, external invitations, legal hold management, or partial artifact deletion? -> A: No; explicitly out of scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Delete A Whole Meeting With Truthful Scope (Priority: P1)

As a meeting owner, I want to delete a whole meeting with clear confirmation,
progress, and completion truth, so that meeting content is removed everywhere
`2brain Rec` controls without making false promises about downloaded or
external copies.

**Why this priority**: Deletion truth is a launch gate. After `017` enabled
sharing, downloads, and exports, users need a reliable way to remove a meeting
and understand what can and cannot be revoked.

**Independent Test**: Create a meeting with accepted MVP artifact classes,
request deletion as the owner, and verify the meeting enters `deleting`,
eligible server artifacts are purged or marked with explicit failure states,
normal review access is blocked, and a verification report explains covered
and uncovered classes.

**Acceptance Scenarios**:

1. **Given** a meeting owner opens a ready meeting, **When** they choose delete
   and confirm the bounded deletion copy, **Then** the meeting enters a
   `deleting` lifecycle state and normal transcript/audio/download/export
   access is blocked.
2. **Given** a deletion workflow completes active server purge, **When** the
   owner opens the deleted meeting destination, **Then** the surface shows a
   deletion report rather than the original content.
3. **Given** a meeting has prior downloads or exports, **When** deletion is
   requested, **Then** the confirmation and report state that already delivered
   files cannot be technically revoked by `2brain Rec`.
4. **Given** a non-owner or unauthorized actor attempts deletion, **When** the
   request is evaluated, **Then** deletion is denied without exposing private
   meeting content or artifact details.

---

### User Story 2 - Run Retention Jobs Without Surprises (Priority: P1)

As a workspace owner, I want retention policy to identify meetings or artifact
classes eligible for lifecycle action and move them through the same truthful
deletion states, so that storage does not grow forever and policy-driven
cleanup is auditable.

**Why this priority**: MVP launch cannot rely only on manual deletion. The PRD
requires retention and deletion workers, lifecycle accounting, and admin-visible
retention state.

**Independent Test**: Seed meetings across retained, expired, already deleting,
deleted, legal-hold-blocked, and processing states; run the retention scan; and
verify only eligible meetings or artifact classes receive lifecycle actions
with audit and report state.

**Acceptance Scenarios**:

1. **Given** a meeting has reached its configured retention date and is not
   blocked, **When** the retention job evaluates it, **Then** a deletion or
   retention action is created with a metadata-only audit trail.
2. **Given** a meeting is processing, already deleting, already deleted, or
   blocked by policy, **When** retention runs, **Then** the job skips or blocks
   it with a clear reason and no duplicate destructive action.
3. **Given** retention configuration is absent or unsafe, **When** the job
   starts, **Then** it fails closed and records a non-content-bearing operator
   reason.

---

### User Story 3 - Coordinate Local Desktop Purge (Priority: P1)

As a user who records on a desktop device, I want server deletion to request
local purge of any remaining local buffers and show whether each device has
acknowledged it, so that server purge does not falsely imply local cleanup.

**Why this priority**: The constitution requires deletion reports to distinguish
server purge from local desktop purge. The desktop can be offline, unreachable,
or holding local buffers after upload.

**Independent Test**: Create deletion reports for meetings with registered
devices in acknowledged, pending, unreachable, and expired-local-buffer states;
verify user-visible report state distinguishes server completion from local
purge acknowledgement.

**Acceptance Scenarios**:

1. **Given** a meeting may still have local desktop buffers, **When** server
   deletion starts, **Then** local purge tasks are created for relevant devices.
2. **Given** a desktop device acknowledges purge, **When** the report refreshes,
   **Then** local purge status moves to acknowledged for that device.
3. **Given** a desktop device remains unreachable, **When** server purge
   completes, **Then** the report stays truthful by showing local purge
   unverified or pending until acknowledgement or local expiry.

---

### User Story 4 - Report External Dependency And Backup Limits (Priority: P1)

As a security owner, I want each deletion report to show backup expiry and
external dependency state, so that compliance review can distinguish verified
purge from pending expiry, unsupported dependency deletion, and post-egress
limits.

**Why this priority**: `2brain Rec` depends on MediaScribe, Langfuse,
diagnostics, exports, workflow payloads, and backups. Launch trust depends on
not overstating what deletion has proven.

**Independent Test**: Delete meetings with dependency states including not
submitted, delete requested, delete confirmed, unsupported, unknown, metadata
only, content-bearing trace disabled, backup pending expiry, and backup
expiry complete; verify the report uses the correct bounded wording.

**Acceptance Scenarios**:

1. **Given** MediaScribe deletion is unsupported or unconfirmed, **When** a
   deletion report is generated, **Then** the report uses `unknown` or
   `delete_not_supported` dependency truth and does not claim full end-to-end
   purge.
2. **Given** backups retain copies until a documented expiry window, **When**
   active purge completes, **Then** the report shows pending backup expiry
   instead of complete deletion where backup expiry is still pending.
3. **Given** Langfuse traces are metadata-only, **When** the report lists
   Langfuse state, **Then** it distinguishes metadata-only traces from any
   future content-bearing traces that would require deletion participation.
4. **Given** diagnostics, exports, or external egress events exist, **When**
   the report is generated, **Then** it lists covered purge, retained audit
   evidence, and post-egress limits without exposing private content.

---

### User Story 5 - Preserve Audit And Review History Safely (Priority: P2)

As an administrator, I want deletion and retention actions to preserve safe
audit evidence without preserving private meeting content, so that security
review can prove what happened without recreating the deleted meeting.

**Why this priority**: Auditability must survive deletion, but audit logs must
not become hidden content storage.

**Independent Test**: Execute manual deletion, retention-triggered deletion,
denied deletion, retryable failure, terminal failure, and local purge
acknowledgement flows; verify activity and admin-visible reports show
metadata-only lifecycle events and no deleted content payloads.

**Acceptance Scenarios**:

1. **Given** a deletion request is accepted, denied, retried, completed, or
   failed, **When** audit is inspected, **Then** a metadata-only lifecycle event
   records actor, meeting identity, action, state, and reason.
2. **Given** a deleted meeting had transcript, notes, diarization, audio,
   exports, and processing results, **When** audit events are inspected,
   **Then** no private meeting text, audio payload, object key, signed URL,
   credential, or provider payload is present.
3. **Given** a deletion action fails, **When** the owner or admin opens the
   report, **Then** retryable and terminal failures are distinguishable with
   safe next-action guidance.

### Edge Cases

- A user requests deletion while processing is running or queued.
- A user requests deletion while a download/export action is in progress.
- A meeting has no retained audio but does have transcript, notes, audit, and
  dependency state.
- A meeting was uploaded from a desktop device that has not checked in since
  deletion started.
- A desktop device acknowledges purge after the server workflow completed.
- A deletion workflow is retried after a partial failure.
- A retention job sees a meeting that is already deleting or deleted.
- Backup expiry is longer than active storage purge completion.
- External dependency deletion is unavailable, unsupported, or unconfirmed.
- Audit persistence fails before a destructive action.
- A restore rehearsal encounters a deleted meeting.
- A meeting is shared or downloaded before deletion and then opened through an
  old share link after deletion starts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support owner/admin-initiated whole-meeting
  deletion for MVP-created meeting artifacts.
- **FR-002**: The system MUST require explicit confirmation copy that states
  the bounded deletion scope and avoids universal erasure promises.
- **FR-003**: The system MUST block normal meeting review, transcript, audio,
  share, download, and export access once a meeting enters deleting or deleted
  lifecycle state.
- **FR-004**: The system MUST expose deletion lifecycle states including
  requested, deleting, active purge complete, pending backup expiry, complete,
  retryable failed, terminal failed, policy blocked, post-egress limit, and
  local purge unverified.
- **FR-005**: The system MUST record a deletion request before any destructive
  action runs and MUST fail closed when required metadata-only audit cannot be
  written.
- **FR-006**: The system MUST purge or lifecycle-mark eligible active server
  artifacts created by the MVP, including retained audio objects, transcript
  rows, diarization rows, notes/summary/action-item rows, export packages,
  processing temp state, retry queues, and search/index entries that exist in
  accepted slices.
- **FR-007**: The system MUST preserve metadata-only deletion reports and audit
  events needed to prove lifecycle outcome after private content is purged.
- **FR-008**: The system MUST produce a deletion verification report listing
  each artifact class, current state, completion time when known, failure reason
  when known, and whether the class is controlled, externally limited, or not
  applicable.
- **FR-009**: The system MUST represent backup deletion truth as pending expiry,
  expiry complete, crypto-erased, unsupported, unknown, or not applicable based
  on deployment policy evidence.
- **FR-010**: The system MUST create local desktop purge tasks for registered
  devices that may hold local meeting buffers or local package artifacts.
- **FR-011**: The system MUST accept metadata-only desktop purge
  acknowledgements and update the deletion report without requiring desktop
  upload of private meeting content.
- **FR-012**: The system MUST distinguish server purge complete from local
  purge acknowledged, local purge pending, local purge unreachable, and local
  buffer expiry relied upon.
- **FR-013**: The system MUST support retention eligibility scanning for
  meetings and artifact classes based on configured retention deadlines and
  lifecycle state.
- **FR-014**: Retention jobs MUST skip or block meetings that are processing,
  already deleting, already deleted, policy blocked, or unsafe to mutate, and
  MUST record the reason.
- **FR-015**: The system MUST represent MediaScribe dependency deletion state
  using not submitted, submitted delete supported, delete requested, delete
  confirmed, retention window pending, delete not supported, or unknown.
- **FR-016**: The system MUST represent Langfuse state as metadata-only,
  content-bearing deletion required, delete requested, delete confirmed,
  disabled, not applicable, or unknown.
- **FR-017**: The system MUST represent downloads, exports, external
  integrations, and post-egress recipients as post-egress limits that cannot be
  technically revoked by `2brain Rec`.
- **FR-018**: Deleted or deleting meetings MUST be hidden from normal meeting
  lists by default while remaining available through authorized deletion report
  and audit views.
- **FR-019**: Share links and direct artifact destinations MUST resolve to
  deleted/deleting states once deletion starts and MUST NOT expose original
  meeting content.
- **FR-020**: The system MUST provide owner/admin-visible retry state and safe
  retry guidance for retryable deletion failures.
- **FR-021**: The system MUST keep deletion, retention, purge, dependency, and
  report evidence out of logs, diagnostics, screenshots, and validation
  artifacts when it would include private meeting content, object-storage keys,
  signed dependency URLs, credentials, bearer tokens, provider payloads, or live
  local filesystem paths.
- **FR-022**: The system MUST include retention/deletion activity in the
  meeting activity trail and admin lifecycle/audit surfaces as metadata-only
  events.
- **FR-023**: The feature MUST NOT implement public-link policy, external
  recipient invitation policy, billing, legal hold release, partial artifact
  deletion, admin retention-policy editing UI, or content-bearing Langfuse trace
  deletion beyond explicit state accounting.
- **FR-024**: The UI MUST remain clean-room relative to Krisp references and use
  `2brain Rec` product language, accepted V8 IA, and existing cabinet patterns
  without copying Krisp assets, private screenshots, or proprietary copy.

### Key Entities *(include if feature involves data)*

- **Deletion Request**: A user or retention-initiated lifecycle request for a
  whole meeting, including requester, reason, policy source, lifecycle state,
  and confirmation boundary.
- **Deletion Workflow**: Durable lifecycle execution for active purge,
  dependency state, retry/failure state, and report generation.
- **Deletion Artifact State**: Per-artifact-class status covering active server
  data, local desktop buffers, exports, diagnostics, workflow state, backups,
  and external dependencies.
- **Deletion Verification Report**: Metadata-only report explaining covered
  classes, outstanding failures, local purge state, backup expiry state, and
  dependency limits.
- **Retention Policy Snapshot**: Policy values used when evaluating a meeting
  for retention action, preserved so later review understands why an action was
  or was not taken.
- **Local Purge Task**: Server-issued task for a registered desktop device to
  purge local buffers or local package artifacts for a deleted meeting.
- **Local Purge Acknowledgement**: Metadata-only device response recording
  purge completion, failure, unreachable state, or local expiry reliance.
- **External Dependency State**: MediaScribe, Langfuse, diagnostics, workflow,
  backup, export, integration, and post-egress deletion/accounting status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Validation demonstrates whole-meeting deletion for a ready meeting
  with audio, transcript, diarization, notes, processing result, export package,
  and audit state without exposing private content in evidence.
- **SC-002**: 100% of accepted deletion requests create a metadata-only deletion
  request and audit event before destructive actions run.
- **SC-003**: Deleted or deleting meetings are no longer available through
  normal list/detail/share/download/export surfaces in validation.
- **SC-004**: Deletion reports list active server artifacts, local desktop purge
  state, backup expiry state, MediaScribe state, Langfuse state, workflow/temp
  state, diagnostics state, exports, and post-egress limits.
- **SC-005**: Retention validation covers eligible, not-yet-eligible,
  processing, already deleting, already deleted, unsafe-config, and blocked
  meetings.
- **SC-006**: Local purge validation covers acknowledged, pending,
  unreachable, failure, and local-expiry-relied-upon device states.
- **SC-007**: Failure validation distinguishes retryable failure, terminal
  failure, audit-write failure, external dependency unknown, and backup expiry
  pending.
- **SC-008**: Product copy and reports contain zero universal erasure claims
  such as "delete forever everywhere" or "remove all copies."
- **SC-009**: Evidence and diagnostics scans find no private meeting content,
  object-storage keys, signed dependency URLs, credentials, bearer tokens,
  provider payloads, or live local filesystem paths.
- **SC-010**: Active server purge for eligible artifacts reaches complete or
  explicit failure state within the MVP target of 24 hours; automated tests may
  use accelerated clocks or fixtures to prove the state transitions.

## Assumptions

- Existing auth, workspace membership, meeting access, egress audit, RLS,
  processing, transcript, and cabinet foundations from `013`, `015`, `016`,
  `017`, `031`, and `032` remain available.
- MVP deletion is whole-meeting deletion only.
- Legal hold is represented only as a blocking state if existing data requires
  it; legal hold management and release workflows are out of scope.
- Backup expiry can be represented from deployment policy evidence; immediate
  physical removal from all backup media is not required unless the deployment
  supports and documents crypto-erasure.
- MediaScribe deletion capability is not assumed. Unknown or unsupported
  dependency states must be represented truthfully.
- Langfuse is metadata-only by default for current accepted slices; future
  content-bearing traces require additional deletion participation.
- Desktop local purge coordination is metadata-only and must not upload local
  private artifacts as proof.
- Retention policy editing UI is out of scope; the feature may use existing or
  default policy values and must preserve a policy snapshot for audit.
