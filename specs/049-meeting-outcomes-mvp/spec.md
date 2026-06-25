# Feature Specification: Meeting Outcomes MVP

**Feature Branch**: `049-meeting-outcomes-mvp`

**Created**: 2026-06-25

**Status**: Draft

**Input**: User description: "Continue toward full MVP through the full SDD/Spec Kit cycle, carefully rechecking the macOS app and web cabinet. The current MVP blocker is that notes/action output is truthful but not launchable. Make meeting outcomes real enough for MVP: stored summary, decisions, action items, follow-ups, risks, questions, and timestamped evidence in web and macOS embedded review, while preserving privacy, deletion, access, processing speed, and clean-room UX."

## Clarifications

### Session 2026-06-25

- Q: Does 049 close the MVP blocker through provider-reported summary status alone, or only through stored launch-safe outcome content? → A: Only stored launch-safe outcome content can close `notes-action-output`; provider-reported summary availability without stored reviewable sections remains blocked.
- Q: What is the accepted generation ownership rule for MVP planning? → A: Follow the PRD rule: use approved server-side generation only, prefer MediaScribe summary when useful, otherwise use a 2brain-owned generation path; desktop clients never call generation providers directly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Stored Meeting Outcomes (Priority: P1)

As a meeting owner, I want a processed meeting to show stored meeting outcomes in the review page so that I can quickly understand the meeting without reading the whole transcript first.

**Why this priority**: The PRD requires basic AI notes for MVP, and the current readiness evidence keeps `notes-action-output` as a P1 blocker. Truthful placeholders are safer than fake notes, but they do not complete the MVP value loop.

**Independent Test**: Can be fully tested with one processed owner meeting that has transcript and diarization results. The owner opens web review and sees stored summary, decisions, action items, follow-ups, risks, questions, and source/timestamp evidence where the transcript supports them.

**Acceptance Scenarios**:

1. **Given** a processed owner meeting has transcript content and outcome generation succeeds, **When** the owner opens web meeting review, **Then** the page shows stored outcomes instead of deferred or blocked notes/action states.
2. **Given** an outcome statement is shown, **When** the owner inspects it, **Then** the statement includes enough source context to trace it to transcript time or segment evidence.
3. **Given** no decisions, action owners, due dates, risks, or follow-ups can be inferred, **When** outcomes are shown, **Then** the page says "not found" or "not inferable" for that category rather than inventing content.

---

### User Story 2 - Keep Outcomes Honest During Processing And Failure (Priority: P1)

As a meeting owner, I need outcomes to show accurate generation state so that I can trust transcript review even when notes are still processing, unavailable, blocked, or partial.

**Why this priority**: Outcome generation must improve the review loop without blocking transcript/playback review or creating false confidence.

**Independent Test**: Can be tested with meetings in ready, processing, failed, dependency-unavailable, transcript-only, partial-output, and no-inferable-content states. Transcript and playback remain reviewable when allowed, and outcomes show truthful category-level states.

**Acceptance Scenarios**:

1. **Given** transcript review is ready but outcomes are still processing, **When** the owner opens review, **Then** transcript, diarization, and playback remain available while outcomes show a processing state.
2. **Given** outcome generation fails or a dependency is unavailable, **When** the owner opens review, **Then** outcome categories show blocked/unavailable truth without hiding transcript or playback.
3. **Given** only some outcome categories are available, **When** the owner opens review, **Then** available categories show stored content and missing categories show truthful category-level state.

---

### User Story 3 - Match Web And macOS Embedded Review (Priority: P1)

As a meeting owner using the macOS app, I want the embedded meeting review to show the same outcomes and truth states as the web cabinet so that I do not have to switch surfaces after recording.

**Why this priority**: The product uses the native app for capture and server-owned review for results. MVP credibility depends on both surfaces showing the same meeting outcome truth.

**Independent Test**: Can be tested with the same processed meeting opened in web review and in the macOS embedded cabinet route. The outcome categories, states, source context, and unavailable copy match.

**Acceptance Scenarios**:

1. **Given** stored outcomes are available in web review, **When** the same meeting opens in the macOS embedded cabinet, **Then** the embedded review shows the same outcome categories and state labels.
2. **Given** outcome generation is processing, partial, failed, or unavailable, **When** the same meeting opens in web and embedded review, **Then** both surfaces show matching truth states and preserve transcript/playback review.
3. **Given** a compact or mobile-width review surface, **When** outcomes render, **Then** outcome cards, transcript, and bottom playback controls do not overlap or overflow.

---

### User Story 4 - Preserve Privacy, Access, Deletion, And Evidence Boundaries (Priority: P1)

As a privacy or security owner, I need meeting outcomes to follow the same data boundary as transcript and audio so that generated content does not leak meeting content or survive deletion truth incorrectly.

**Why this priority**: Outcomes are derived meeting content. They must be governed like transcript and audio, not treated as harmless metadata.

**Independent Test**: Can be tested through access, export/download, deletion, retention, diagnostics, and evidence scenarios. Unauthorized viewers cannot see outcomes; deleted/deleting meetings block outcomes; committed evidence contains no meeting content.

**Acceptance Scenarios**:

1. **Given** a viewer is denied or not authenticated, **When** they try to open a meeting, **Then** no outcome content or outcome existence detail is exposed.
2. **Given** a meeting is deleting, deleted, or audio/transcript retention state prevents review, **When** review renders, **Then** outcomes are blocked with truthful lifecycle copy.
3. **Given** diagnostics, logs, release evidence, screenshots, or traces are recorded, **When** they are reviewed, **Then** they contain metadata-only outcome state and no generated meeting content.

---

### User Story 5 - Update MVP Readiness Truth (Priority: P2)

As the product owner, I want readiness docs, release notes, and status evidence to say whether notes/actions are now launchable so that the full MVP audit is not based on stale blockers.

**Why this priority**: The current product status and readiness evidence are no longer fully synchronized after recent 047/048 closeouts, and `notes-action-output` is the next P1 blocker.

**Independent Test**: Can be tested by reading current status, readiness report, launch gap register, changelog, release notes, and validation evidence. They must agree on whether `notes-action-output` is closed, still blocked, or explicitly deferred.

**Acceptance Scenarios**:

1. **Given** outcome implementation and validation pass, **When** readiness evidence is regenerated, **Then** `notes-action-output` is removed from P0/P1 blockers only if stored launchable outcomes are proven.
2. **Given** some categories remain unavailable by design, **When** status docs are reviewed, **Then** they explain the exact limitation in simple Russian without overclaiming full AI assistant behavior.

### Edge Cases

- Transcript is empty, too short, unsupported-language, malformed, or only contains silence markers.
- Transcript has overlapping speakers, missing timestamps, duplicated segment sequence, or uncertain speaker labels.
- Outcome generation succeeds for summary but finds no decisions, action owners, due dates, risks, or follow-ups.
- Outcome generation times out or exceeds the user-visible budget while transcript/playback are already ready.
- External dependency is unavailable, returns malformed output, returns unsafe content, or returns content without source evidence.
- User opens review while outcomes are being generated, then refreshes after completion.
- Meeting is shared with a user who can view transcript but cannot download/export summary artifacts.
- Meeting is deleting/deleted while outcome generation is queued or running.
- Retention policy expires outcomes before transcript, or transcript before outcomes.
- Outcome content includes personal data or sensitive statements that must remain meeting-scoped and deletion-accounted.
- Mobile-width review has bottom playback visible while outcome cards are long.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST create and store launchable meeting outcomes for processed meetings when transcript content is available and policy allows outcome generation.
- **FR-002**: Stored outcomes MUST support these categories: summary, key discussion points, decisions, action items, follow-ups, risks/blockers, questions, and important timestamped evidence.
- **FR-003**: Each outcome item that states a meeting fact, decision, action, risk, question, or quote MUST include transcript time or segment evidence when such evidence exists.
- **FR-004**: The system MUST NOT invent owners, due dates, decisions, commitments, attendees, risks, or follow-ups. If a field is not inferable, the stored outcome or category state MUST say so.
- **FR-005**: Outcome availability MUST be category-level. Summary can be available while decisions, action items, follow-ups, risks, or questions are unavailable, not found, processing, or blocked.
- **FR-006**: A meeting review MUST show "available" outcome state only for categories with stored launch-safe content or explicit stored "not found/not inferable" results.
- **FR-007**: Transcript, diarization, and playback review MUST remain available when allowed even if outcome generation is processing, failed, unavailable, or partial.
- **FR-008**: Web review and macOS embedded review MUST show matching outcome categories, states, source context, and unavailable reasons for the same meeting and viewer.
- **FR-009**: Outcome generation MUST start or be reusable after a meeting reaches a transcript-ready processing state, without creating duplicate outcome records for the same media revision.
- **FR-010**: Outcome processing MUST be idempotent and retry-safe; retries MUST preserve prior accepted output unless a new successful generation explicitly supersedes it.
- **FR-011**: The system MUST record outcome provenance, including source transcript revision, generation status, provider/dependency class, model or template version when available, start/end timestamps, latency, and safe failure reason.
- **FR-012**: Outcomes MUST be treated as meeting content for access control, retention, deletion, export/download policy, audit, and lifecycle reporting.
- **FR-013**: Unauthorized, unauthenticated, denied, deleting, deleted, retention-blocked, transcript-unavailable, unsafe-output, and dependency-unavailable states MUST fail closed without exposing outcome content.
- **FR-014**: Diagnostics, logs, Langfuse traces, screenshots, release notes, and committed evidence MUST remain metadata-only by default and MUST NOT contain generated outcome text, transcript text, raw audio, prompts with meeting content, credentials, signed URLs, private paths, or private meeting identifiers.
- **FR-015**: User-facing copy for outcome states, release notes, and status docs MUST be simple Russian by default.
- **FR-016**: Outcome generation MUST NOT delay transcript/playback review from becoming visible. If outcomes are slower than the budget, the review page MUST show transcript/playback with an outcome processing state.
- **FR-017**: For a one-hour transcript in local validation, outcome orchestration MUST add no more than 30 seconds to the review loop when dependencies respond normally, and MUST fail into a user-safe processing/blocked state instead of blocking review indefinitely.
- **FR-018**: The readiness report and current product status MUST be updated so `notes-action-output` is closed only when stored launchable outcomes are proven; otherwise it remains an explicit blocker or owner-approved deferral.
- **FR-019**: This feature MUST NOT add AI chat, transcript editing, speaker editing, public links, external-recipient invitations, real-time coaching, CRM sync, or a new desktop-to-LLM direct egress path.

### Key Entities *(include if feature involves data)*

- **Meeting Outcome Set**: The stored outcome result for one meeting and media revision, including status, category states, provenance, lifecycle state, and safe failure reason.
- **Outcome Category**: One of summary, key discussion points, decisions, action items, follow-ups, risks/blockers, questions, or evidence.
- **Outcome Item**: A stored user-visible item in a category, including text, optional owner/due date fields, confidence/truth state, and transcript source evidence.
- **Outcome Source Evidence**: Transcript segment, timestamp, or source-role reference used to support an outcome item without exposing private evidence in diagnostics.
- **Outcome Generation Attempt**: A durable, retry-safe processing attempt with dependency status, timing, provider/template metadata, and metadata-only audit fields.
- **Outcome Readiness Claim**: The product-readiness state that determines whether the former `notes-action-output` blocker is closed, blocked, partial, or explicitly deferred.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a processed owner meeting with transcript content, web review and macOS embedded review show stored outcome categories instead of deferred notes/action placeholders.
- **SC-002**: For outcome items that include facts, decisions, actions, risks, questions, or quotes, 100% of items include transcript time or segment evidence, or the category explicitly states that evidence is unavailable and the item is not shown as trusted.
- **SC-003**: For no-inferable-content cases, 100% of tested categories show "not found/not inferable" rather than fabricated decisions, owners, due dates, or follow-ups.
- **SC-004**: For processing, failed, dependency-unavailable, unsafe-output, transcript-unavailable, deleted/deleting, and unauthorized states, no outcome content is exposed and transcript/playback visibility remains governed by its own existing policy.
- **SC-005**: A one-hour transcript validation run records outcome orchestration latency at or below 30 seconds with normal fake/local dependencies, or records a safe non-blocking outcome processing/blocked state without delaying transcript/playback review.
- **SC-006**: Browser runtime validation across desktop web, mobile-width web, and macOS embedded review reports no horizontal overflow, no incoherent overlap, matching outcome states, and metadata-only evidence.
- **SC-007**: Forbidden-content scans over committed 049 evidence, specs, release notes, and diagnostics return no generated outcome text, transcript text, raw audio, credentials, signed URLs, private local paths, or private meeting identifiers.
- **SC-008**: Readiness output, launch gap register, `docs/current-product-status.md`, changelog, GitHub issue closure text, and release notes agree on whether `notes-action-output` is closed, still blocked, partial, or explicitly deferred.

## Assumptions

- Existing owner auth, meeting access, transcript/diarization import, playback, retention, deletion, and desktop embedded cabinet surfaces remain the foundation.
- Outcome generation is server-owned. Desktop clients never send transcript or audio directly to an outcome-generation dependency and never store provider credentials.
- MediaScribe transcript/diarization output remains the source input for outcomes. If an approved summary dependency returns useful summary content, it can be stored as source material, but launchable meeting outcomes still need 2brain-owned storage, category truth, provenance, and deletion accounting.
- MVP may ship with category-level "not found/not inferable" states for decisions, due dates, owners, risks, or follow-ups when the transcript does not support them.
- Manual outcome editing, manual regeneration UI, AI chat, transcript editing, and speaker reassignment are outside this feature unless a later spec adds them.
- Real echo/noise suppression remains outside this feature; outcomes must work with the transcript quality that the existing processing pipeline produces and must not claim clean audio.
