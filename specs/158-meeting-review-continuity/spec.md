# Feature Specification: Meeting Review Continuity

**Feature Branch**: `codex/158-meeting-review-continuity`

**Created**: 2026-08-17

**Status**: Implementation reconstructed in a clean worktree; pending focused validation, commit and PR

**Input**: User description: Improve speaker timeline resizing and discoverability, preserve playback while renaming speakers, and keep meeting navigation visible in web and embedded macOS review.

## Clarifications

- The current `96px` timeline height remains the session-local minimum; height is
  not persisted between sessions or devices.
- Browser and embedded review reuse the existing server-rendered markup,
  cabinet JavaScript/CSS, audio element, and tab/hash contract. No second audio
  element, router, analytics, or dependency is introduced.
- A successful rename reconciles the server-confirmed label in the existing DOM;
  authorization and access-loss responses continue through the existing recovery
  path, while audio state remains untouched on ordinary validation failures.
- The lane hint and resize affordance are capability-driven: unavailable audio
  or missing diarization must not advertise interaction.
- This slice has a `no deploy` release gate; commit, PR, merge, production
  deployment, and public release remain separate approval-gated work.

## User Scenarios & Testing

### User Story 1 - Expand the speaker timeline without losing context (Priority: P1)

As a meeting owner reviewing a recording with several speakers, I can expand the speaker timeline from its existing default height so that more complete speaker rows are visible without losing the playback position or pushing the review surface out of the window.

**Why this priority**: Speaker attribution is only useful when the owner can inspect every available lane. The current internal scroll hides rows and makes the review state easy to lose.

**Independent Test**: Render one, fitting, overflowing, and very large synthetic speaker sets in both web and embedded review, then exercise pointer and keyboard resize while asserting the default height, natural-height ceiling, viewport ceiling, playback position, and active-speaker state.

**Acceptance Scenarios**:

1. **Given** one speaker or a set of rows that fits the current default height, **when** the review loads, **then** the timeline remains at the current default height and does not show a resize affordance that promises a useful action.
2. **Given** more rows than the default height can show, **when** the owner drags the upper resize handle upward, **then** the panel grows from the default height toward the full rows while keeping names, tracks, and controls readable.
3. **Given** an expanded timeline, **when** the owner drags the handle down or uses the keyboard decrease/default action, **then** the height returns no lower than the existing default and the inner scroll remains available only when the viewport ceiling requires it.
4. **Given** a resize in progress, **when** playback is playing, paused, or a speaker lane is active, **then** the same audio element, current time, active state, scale, and lane width are preserved.

### User Story 2 - Rename a speaker without interrupting review (Priority: P1)

As a meeting owner, I can save a speaker name while listening or paused and continue reviewing the same recording state after the server confirms the name.

**Why this priority**: Renaming is a normal review action. A page reload that interrupts audio makes the timeline and naming workflow unreliable, especially in the embedded app.

**Independent Test**: Use a synthetic meeting detail with one audio element and exercise playing/success, paused/success, playing/failure, and paused/failure cases for both web and embedded form actions.

**Acceptance Scenarios**:

1. **Given** audio is playing, **when** a valid speaker name is saved successfully, **then** playback continues on the same media element with a monotonic current time and without a media-source reload.
2. **Given** audio is paused, **when** a valid speaker name is saved successfully, **then** playback remains paused at the same position.
3. **Given** the save fails, **when** the response is shown, **then** the last confirmed name remains visible, a retryable plain-language error is available, and the prior playing/paused state is unchanged.
4. **Given** a successful save, **when** focus is inspected, **then** focus remains on a predictable speaker control and the page does not jump to its beginning.

### User Story 3 - Understand and use speaker lanes as playback navigation (Priority: P1)

As a new reviewer, I can tell from the meeting review that speaker lanes are interactive and can activate a corresponding recording fragment without relying on hover-only discovery.

**Why this priority**: The existing click and keyboard behavior is hidden. A permanent, compact explanation and clear states reduce accidental review friction without adding onboarding or analytics.

**Independent Test**: Render available audio with diarization, unavailable audio, no diarization, a narrow viewport, keyboard focus, and reduced-motion preferences; inspect the visible hint, cursor/focus/pressed states, accessible name, and equivalent Enter/Space action.

**Acceptance Scenarios**:

1. **Given** playable audio and at least one interactive speaker lane, **when** the review is displayed before any hover, **then** a compact visible hint explains that pressing a lane moves playback to its fragment.
2. **Given** audio is unavailable or speaker lanes are unavailable, **when** the review is displayed, **then** no hint or resize affordance claims that an unavailable lane can be used.
3. **Given** a lane has pointer hover, keyboard focus, or active press, **when** the state changes, **then** cursor, focus ring, and pressed styling communicate the same action without obscuring rows, player, or resize control.
4. **Given** focus is on a lane, **when** the reviewer uses Enter or Space, **then** playback seeks to the corresponding time and existing transcript/source navigation semantics remain intact.

### User Story 4 - Keep the recording/results choice available while reading (Priority: P1)

As a reviewer reading a long transcript or outcome, I can switch between the recording/transcript and outcomes from the current scroll position in both browser and embedded review.

**Why this priority**: Meeting review is a two-surface task. Losing the tab choice on long content makes the most important result difficult to reach and creates inconsistent web/embedded behavior.

**Independent Test**: Render long synthetic transcript and outcome panels, scroll the main review container in web and embedded layouts, and verify a single compact sticky tab strip, selected accessibility state, hash/deep-link behavior, source jumps, keyboard navigation, narrow viewport, and reduced-motion behavior.

**Acceptance Scenarios**:

1. **Given** a long transcript or outcome, **when** the main review content scrolls, **then** the compact recording/outcomes tab strip remains visible without duplicating the page header or covering readable content.
2. **Given** either tab is selected, **when** the review is loaded or switched, **then** the visual selected state, `aria-selected`, panel relationship, and existing `#recording`/`#outcomes` hash semantics agree.
3. **Given** an outcome source reference, **when** it is activated from any scroll position, **then** the recording tab opens and the exact transcript turn and timestamp remain reachable below the sticky strip.
4. **Given** the review is embedded, narrow, keyboard-focused, or using reduced motion, **when** the same flows are exercised, **then** the layout remains usable and does not create a second sticky header or horizontal overflow.

### Edge Cases

- A single row, an exact fit, a partially hidden final row, and a very large speaker set must each produce a truthful resize affordance and bounded height.
- The viewport may be too short to show every row; the timeline may retain internal scrolling only in that case and must not push the fixed player or main review out of view.
- A speaker save may return a validation, authorization, unavailable, or redirect-to-login response; no private detail content may be removed by a local action error.
- A partial HTML update or repeated initialization must not create a second audio element, duplicate event listeners, duplicate sticky strips, or reset the selected tab.
- Audio may be unavailable, diarization may be pending, or the recording may be in a degraded state; interactive copy must match the actual capability.
- Hash deep links and source references must continue to work after refresh and after switching tabs.
- User preference for timeline height is intentionally session-local; persistence across sessions is out of scope.

## Requirements

### Functional Requirements

- **FR-001**: The speaker timeline MUST retain its existing default height as the minimum height and MUST expose a resize affordance only when at least one complete speaker row is hidden at that height.
- **FR-002**: The resize affordance MUST allow pointer dragging from the upper boundary and a keyboard-equivalent increase, decrease, default, and maximum action; its focus, cursor, and accessible value state MUST be visible and understandable.
- **FR-003**: The maximum expanded height MUST be the smaller of the natural height of all complete rows and the available review viewport; when the viewport is the limiting factor, only the remaining overflow MAY scroll inside the timeline.
- **FR-004**: Resizing MUST preserve the single existing audio element, current playback position, playing/paused state, active speaker state, time scale, and lane width.
- **FR-005**: Speaker-lane interaction MUST expose a compact always-visible hint only when playable audio and at least one interactive lane are present; it MUST not use modal onboarding, analytics, or hover-only instruction.
- **FR-006**: Each interactive lane MUST expose an accessible name that states activation moves playback to the corresponding recording fragment, and pointer hover, keyboard focus, and pressed state MUST provide consistent feedback.
- **FR-007**: Enter and Space on an interactive lane MUST perform the same seek action as pointer activation, including the existing transcript follow and reduced-motion behavior.
- **FR-008**: A successful speaker rename MUST update the confirmed speaker labels in place without reloading the page or replacing the existing audio element; playing audio MUST continue and paused audio MUST remain paused at its current position.
- **FR-009**: A failed speaker rename MUST keep the last confirmed label and playback state, show a retryable plain-language error, and preserve the current private meeting detail surface unless the response proves session loss or access loss.
- **FR-010**: A successful rename MUST leave focus on a predictable speaker control without scrolling the review to the top, in both web and embedded surfaces.
- **FR-011**: The recording/transcript and outcomes tab strip MUST remain visible while the meeting content scrolls, with only the compact tab area sticky and with an offset that does not obscure browser or embedded content.
- **FR-012**: Tab selection MUST preserve existing `aria-selected`, `aria-controls`, keyboard arrow/Home/End behavior, and `#recording`/`#outcomes` hash semantics; source references MUST still open the exact transcript turn and timestamp.
- **FR-013**: Web and embedded meeting review MUST reuse the same behavior and state contract, including unavailable audio, missing diarization, narrow viewport, keyboard focus, reduced motion, and partial-update initialization.
- **FR-014**: The implementation MUST not add timeline-height persistence, a second audio element, a new router/history system, an onboarding system, or new external dependencies.

### Key Entities

- **Speaker lane**: One named or provisional speaker row with a label, percentage, time segments, interaction state, and optional rename control.
- **Timeline height state**: Session-local visual height constrained by the default, natural row height, and current viewport; it is not persisted as product data.
- **Meeting review surface**: The shared web/embedded meeting detail containing tab panels, transcript, outcomes, playback, and source references.
- **Playback continuity state**: The existing audio element's source, current time, playing/paused state, playback scale, and active lane state.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In synthetic review matrices, 100% of fitting speaker sets hide the resize affordance, and 100% of overflowing sets expose it with a minimum equal to the current default height.
- **SC-002**: In pointer and keyboard resize scenarios, 100% of assertions retain the same audio element identity, playback state, current-time monotonicity, and active lane state.
- **SC-003**: In playing, paused, success, and failure rename scenarios, 100% retain the expected playback state; successful cases perform zero full-page reloads.
- **SC-004**: In web and embedded long-content scenarios, reviewers can switch to either tab from the current scroll position with one focused keyboard or pointer action, without horizontal overflow or duplicate sticky navigation.
- **SC-005**: In accessibility contract checks, every available interactive lane has a non-empty action-oriented accessible name and an equivalent keyboard activation path.
- **SC-006**: Focused contract and integration checks pass for the changed surfaces, followed by the repository fast validation lane before this slice is proposed for review.

## Assumptions

- The existing server-rendered meeting review remains the source of truth for labels, segments, permissions, and tab panels.
- The browser and embedded macOS shell intentionally share the same meeting-detail templates and cabinet static assets.
- The existing fixed playback bar and main scroll container remain in place; this slice only makes their relationship safe during resizing and sticky navigation.
- A default timeline height of 96px is the current product baseline and must not be reduced by this slice.
- A successful speaker rename response contains enough server-rendered detail to update the confirmed label, while authorization/access recovery remains owned by existing recovery helpers.
- Manual visual checks will use synthetic or staged data only; no real transcript, audio, or private meeting content will be committed.

## Out of Scope

- Changing speaker attribution, diarization, playback API, transcript data, outcome generation, or accepted-result behavior.
- Persisting timeline height across sessions or devices.
- Replacing the existing meeting tab/hash model with a client-side router.
- Adding analytics, modal onboarding, new external packages, or copying competitor visual design.
