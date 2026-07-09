# Feature Specification: Streaming Egress Audit Semantics

**Feature Branch**: `101-streaming-egress-audit-semantics`
**Created**: 2026-07-09
**Status**: Draft
**Input**: User description: "During review of the 090 upload/playback/security fixes, we found that streaming playback/download routes record `download_completed` and `playback_completed` before the HTTP stream is actually consumed. Do not patch this casually; capture a separate feature to make egress audit and deletion post-egress semantics truthful."

## Product Context

GRAF records audit events for meeting-content egress such as downloads, exports, shares and playback. These events feed several user- and admin-facing truths:

- admin audit journal;
- meeting deletion report;
- post-egress warnings that say copies already delivered outside GRAF control cannot be universally erased;
- support and security review of who accessed what class of meeting content;
- product copy around "Delete this meeting everywhere GRAF controls."

The current 090 security work changed audio playback/download to stream a stored `meeting-review.m4a` artifact instead of loading the full object into memory. That closes the memory/DoS risk, but it exposes a semantics issue: existing egress events named `download_completed` and `playback_completed` are emitted before the response stream is returned to ASGI. For non-streamed tiny bodies this was already a coarse server-side success marker. For streaming audio, the event name can be misread as "client definitely received the complete file", while the server has only proven "GRAF authorized the egress and prepared the stream."

This is not a direct data leak. It is safer to be conservative for deletion: once GRAF has allowed an egress response to begin, the product should treat a possible external copy as outside GRAF control. But the audit vocabulary should be precise so admins, deletion reports, and future compliance work do not overclaim byte-level delivery evidence.

## Current-State Correction

The current 090 patch should not try to solve this by merely moving the audit write after `StreamingResponse` construction or by deleting post-egress evidence.

Why a casual patch is risky:

- if audit is written only after streaming completes, bytes may leave before the audit write fails;
- request-scoped DB sessions may be closed before a post-stream background write runs;
- deleting `download_completed` from deletion reports would under-report possible external copies;
- renaming event types affects admin audit, deletion report, tests, and any future analytics/reporting consumers;
- playback has different product semantics from download/export: playback may be partial/ranged and still egress controlled content.

The correct future work is to define and implement an explicit egress lifecycle vocabulary that preserves fail-closed audit and deletion safety while avoiding overclaiming full delivery.

## Product Principles For 101

- **Deletion truth over perfect byte accounting**: if GRAF allowed content to leave its control, deletion reports must remain conservative.
- **No silent overclaim**: event names and copy must not imply complete client receipt unless the system has evidence for it.
- **Fail-closed authorization audit**: egress authorization/preparation must be recorded before bytes can leave where feasible.
- **Streaming-aware lifecycle**: range playback, interrupted streams, full downloads and package exports are different events.
- **Metadata-only audit**: audit must never include raw audio, transcript text, signed URLs, storage keys, tokens or private meeting content.
- **Compatibility-conscious migration**: existing audit/deletion readers must migrate without losing post-egress warnings.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin sees truthful egress audit (Priority: P1)

As a workspace admin, I want audit history to distinguish prepared, attempted and completed egress, so I can understand access without assuming proof the server does not have.

**Why this priority**: Audit is used for security review and deletion explanations. Vague "completed" events make support and compliance language too confident.

**Independent Test**: Trigger streamed playback/download and inspect admin audit. It shows a server-prepared or stream-attempted event before streaming, and a completed event only if the implementation has reliable completion evidence.

**Acceptance Scenarios**:

1. **Given** an authorized user starts playback, **When** the server prepares a range response, **Then** audit records a metadata-only egress-prepared/attempted event.
2. **Given** the client requests a byte range, **When** the stream is prepared, **Then** audit records range metadata such as requested byte count without raw headers or storage keys.
3. **Given** the stream is interrupted before completion, **When** audit is reviewed, **Then** it does not claim full delivery.
4. **Given** a non-streamed export package is created and downloaded, **When** completion semantics are available, **Then** audit distinguishes package creation/readiness from actual response egress.

---

### User Story 2 - Deletion report stays conservative and precise (Priority: P1)

As a privacy-conscious user, I want deletion reports to say when a copy may have left GRAF control, without claiming GRAF can know or erase every outside copy.

**Why this priority**: Deletion language is a product trust boundary. Under-reporting possible egress is unsafe; overclaiming exact delivery is also unsafe.

**Independent Test**: Create egress events for prepared stream, completed stream where supported, export package, share and share-open. Then request deletion and verify the report includes post-egress limits with safe reasons that match the actual event types.

**Acceptance Scenarios**:

1. **Given** streamed playback was prepared, **When** deletion report is generated, **Then** the report includes a post-egress limitation because content may have left GRAF control.
2. **Given** a stream was only prepared but not completed, **When** report copy is shown, **Then** it says possible external copy or prepared egress, not confirmed full download.
3. **Given** a full non-streamed export was downloaded, **When** the report is generated, **Then** it can identify the export/download event without exposing package contents.
4. **Given** no egress events exist, **When** deletion report is generated, **Then** post-egress limitation is absent or uses the current default safe reason, without inventing external copies.

---

### User Story 3 - Streaming failures are observable without leaking content (Priority: P2)

As an operator, I want failed or interrupted storage streams to be visible as safe metadata, so we can diagnose playback/download reliability without exposing meeting content.

**Why this priority**: Streaming paths can fail after authorization. The system needs operational truth without logging private data.

**Independent Test**: Simulate storage iterator failure before first byte and mid-stream failure. Audit records denied/unavailable or interrupted states with safe reason codes only.

**Acceptance Scenarios**:

1. **Given** storage object is missing before streaming starts, **When** playback/download is requested, **Then** audit records denied/unavailable and no prepared-egress event is emitted.
2. **Given** storage fails after stream start, **When** the failure is captured by the chosen implementation, **Then** audit records a safe interrupted/failure status.
3. **Given** diagnostics are exported, **When** audit metadata is inspected, **Then** it contains no object keys, signed URLs, raw range headers, transcript text or audio data.

---

### User Story 4 - Existing consumers migrate safely (Priority: P2)

As a developer/operator, I want existing deletion/admin reports and tests to keep their safety intent while adopting clearer event names, so a vocabulary change does not accidentally remove post-egress protection.

**Why this priority**: Event names are already consumed by deletion reports, admin audit, readiness evidence and tests. A rename without migration could hide real egress history.

**Independent Test**: Seed legacy `download_completed`/`playback_completed`/`export_completed` events and new streaming lifecycle events. Deletion reports and admin audit handle both correctly during migration.

**Acceptance Scenarios**:

1. **Given** legacy egress events exist, **When** deletion report is generated after 101, **Then** legacy events still trigger post-egress limitations.
2. **Given** new event types are emitted, **When** admin audit filters by action/outcome, **Then** admins can still locate egress activity.
3. **Given** analytics or readiness evidence references old event types, **When** 101 ships, **Then** compatibility notes or migration mapping explain the change.

## Edge Cases

- Client disconnects before reading any streamed bytes.
- Client reads a partial range successfully.
- Client requests multiple ranges in separate requests.
- Storage iterator raises before first chunk.
- Storage iterator raises after some chunks.
- ASGI server or proxy buffers response differently from local tests.
- Request-scoped DB session is closed before post-stream background work.
- Background audit write fails after bytes are sent.
- Same user retries playback repeatedly.
- Admin downloads audio for a non-owned meeting.
- Export package is prepared but never downloaded.
- Share link is granted but never opened.
- Share link is opened after deletion starts.
- Deletion is requested while a stream is in flight.
- Existing legacy audit events predate 101.
- Audit/report evidence must stay metadata-only.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST distinguish egress authorization/preparation from confirmed full delivery when naming events or rendering report copy.
- **FR-002**: The system MUST record fail-closed metadata before or at the moment content can leave GRAF control, so an audit write failure cannot silently permit unaudited egress.
- **FR-003**: The deletion report MUST remain conservative: prepared or attempted content egress MUST produce a post-egress limitation unless the system can prove no bytes left GRAF control.
- **FR-004**: The deletion report MUST NOT claim full client receipt unless reliable completion evidence exists.
- **FR-005**: Playback range requests MUST be represented as streaming/range egress, not as full-file download completion.
- **FR-006**: Interrupted or failed streams SHOULD produce safe metadata states when the platform can observe them without risking unaudited egress.
- **FR-007**: Legacy `download_completed`, `playback_completed`, `export_completed`, `share_granted`, and `share_link_opened` events MUST remain understood by deletion reports during migration.
- **FR-008**: New egress event metadata MUST contain only allowlisted scalar fields and MUST NOT include storage object keys, signed URLs, authorization headers, raw cookies, transcript text, summaries or audio data.
- **FR-009**: Admin audit APIs and UI MUST show egress lifecycle states in understandable language.
- **FR-010**: Tests MUST cover prepared stream, range stream, interrupted stream where supported, legacy event compatibility, deletion report post-egress copy, and metadata redaction.

### Key Entities *(include if feature involves data)*

- **EgressAuditEvent**: Existing audit row describing content egress actions for a meeting.
- **EgressLifecycleState**: Future vocabulary for prepared/attempted/completed/interrupted/denied egress.
- **PostEgressLimitation**: Deletion-report row that explains possible external copies outside GRAF control.
- **StreamingEgressAttempt**: A playback/download response where bytes may leave incrementally through an iterator/range response.

## Out of Scope *(mandatory)*

- Rewriting playback normalization or m4a generation. That belongs to `099-review-m4a-normalization`.
- Changing sharing permissions.
- Promising universal erasure outside GRAF-controlled systems.
- Capturing raw byte-level telemetry, raw Range headers, IP addresses, user agents or content-bearing logs.
- Making deletion wait for client devices or external recipients.
- Blocking all egress until post-stream audit can be written; pre-egress safety remains required.

## Dependencies *(mandatory)*

- Current meeting egress audit table and admin audit readers.
- Current deletion report and `POST_EGRESS_REPORT_EVENT_TYPES` behavior.
- Current streaming playback/download implementation from the 090 security fix.
- `099-review-m4a-normalization` for the canonical playback artifact contract.
- Constitution deletion truth and metadata-only audit principles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of streamed playback/download requests emit an audit state that does not overclaim full delivery.
- **SC-002**: 100% of deletion reports after prepared/attempted egress include a post-egress limitation with precise safe wording.
- **SC-003**: 100% of legacy egress events still map to conservative deletion-report limitations.
- **SC-004**: 0 audit metadata fields expose storage object keys, signed URLs, auth tokens, cookies, transcript text, summary text or audio data.
- **SC-005**: 100% of playback range egress tests verify partial/range semantics separately from full download semantics.
- **SC-006**: 100% of supported interrupted-stream simulations produce either a safe interrupted audit state or a documented platform limitation without losing pre-egress audit.

## Assumptions

- Perfect proof of client-side receipt is not always available from the server.
- For deletion truth, conservative "possible external copy" is safer than pretending no egress happened.
- Event names may need migration aliases or compatibility mappings.
- The first implementation should prefer a small explicit vocabulary over a complex byte-level delivery ledger.
