# Feature Specification: MVP Launch Proof

**Feature Branch**: `050-mvp-launch-proof`

**Created**: 2026-06-25

**Status**: Implemented, merged, released, and deployed; final claim remains pilot-blocked

**Input**: User description: "Составь пошаговый план и действуй внимательно по SDD Spec Kit, пока не будет реализован и перепроверен полноценный MVP. Перепроверь интерфейс приложения и веб кабинет. Очень аккуратно, ничего не сломай. Если нужно, используй Krisp как clean-room reference для веба и приложения."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove The Full Owner Journey (Priority: P1)

As the product owner, I want one current installed macOS app recording to reach the production web review page with transcript, diarization, playback, and stored outcomes, so that MVP readiness is based on a real end-to-end path rather than separate fixture proofs.

**Why this priority**: The product is only MVP-credible if the user can record, stop, upload, process, and review a meeting without operator-only hidden steps or stale status claims.

**Independent Test**: Can be tested by running one metadata-safe live journey from `/Applications/2brain Rec.app` through the production server, then opening the resulting review in web and embedded desktop review while recording only non-content evidence.

**Acceptance Scenarios**:

1. **Given** the currently released macOS app and production server are available, **When** the owner records and stops a meeting, **Then** the recording is queued or uploaded with clear local status and no hidden MediaScribe credentials on the desktop.
2. **Given** a structurally valid uploaded recording is finalized, **When** production processing runs, **Then** transcription, diarization, playback readiness, and stored outcomes are started or reused without an operator-only manual pickup.
3. **Given** processing completes, **When** the owner opens the production web review, **Then** the page shows transcript, speaker/diarization state, playback, timestamp seeking, speaker activity lanes, and stored outcomes for the accepted media revision.
4. **Given** the same meeting is opened from the macOS embedded cabinet, **When** the review loads, **Then** the visible status, transcript, playback, speaker timeline, and outcomes match the web cabinet.

---

### User Story 2 - Verify MVP Interface Quality (Priority: P1)

As a meeting owner, I want the web cabinet and installed app interface to feel coherent, readable, and trustworthy, so that I can understand what is recorded, what is processing, and what is ready without learning internal pipeline details.

**Why this priority**: The user explicitly flagged the review interface as a key MVP surface. A working backend still fails MVP if the playback/review UI is confusing, stale, clipped, or inconsistent with the app shell.

**Independent Test**: Can be tested with desktop-width, embedded macOS, and mobile-width review surfaces plus the installed app shell. Krisp may be used only as a clean-room pattern reference for transcript-first review, persistent playback, and speaker timelines.

**Acceptance Scenarios**:

1. **Given** a ready meeting review is opened in the web cabinet, **When** the page first renders, **Then** the active review tab shows the transcript/review content first and the persistent bottom playback area shows speaker rows and speech intervals.
2. **Given** the review is viewed in the macOS embedded cabinet, **When** the same route loads, **Then** native capture controls remain visible and the embedded review does not contradict web readiness or hide server/auth failures.
3. **Given** the review is viewed at mobile width, **When** the transcript, outcomes, and player are visible, **Then** text, controls, tabs, and speaker lanes do not overlap, clip, or require horizontal scrolling.
4. **Given** the production server is unavailable or the user session is missing, **When** the installed app opens the cabinet, **Then** the app shows server/auth truth instead of implying that everything is ready.

---

### User Story 3 - Keep Product Truth Current (Priority: P1)

As a product and release owner, I want status documents, readiness reports, launch gap registers, changelog, and release notes to match the deployed product, so that MVP decisions are made from current evidence.

**Why this priority**: Current status text can become stale after fast feature closeouts. Stale "branch-local" or "not deployed" language creates false blockers and false confidence at the same time.

**Independent Test**: Can be tested by reading the status artifacts after 050 and confirming they identify which blockers are closed, which remain, what production SHA/release proves, and what claim is allowed.

**Acceptance Scenarios**:

1. **Given** features 045 through 049 have been merged, released, and deployed, **When** current product status is read, **Then** it no longer describes those shipped slices as branch-local or awaiting closeout.
2. **Given** notes/action output is closed by stored outcomes, **When** readiness reports are generated or read, **Then** `notes-action-output` is no longer listed as a P1 blocker while evidence limitations remain explicit.
3. **Given** production user-rollout evidence is still incomplete or fails, **When** release/status text is read, **Then** the product does not claim `production_ready` or broad user rollout readiness.

---

### User Story 4 - Decide And Record The MVP Claim (Priority: P2)

As the owner, I want one clear final readiness decision after validation, so that the team knows whether to start internal pilot use, keep fixing MVP blockers, or defer a known limitation.

**Why this priority**: The goal is not only to ship code. The team needs a precise go/no-go claim grounded in evidence.

**Independent Test**: Can be tested by inspecting the 050 evidence pack and final readiness summary: every launch blocker has a state, evidence, owner, and next action.

**Acceptance Scenarios**:

1. **Given** all P1 MVP journey and UI gates pass, **When** the 050 closeout is read, **Then** it may claim `internal_pilot_candidate` with exact limitations and validation evidence.
2. **Given** any P1 gate fails, **When** the 050 closeout is read, **Then** it remains `pilot_blocked` and includes the smallest next fix path without hiding the failure.

### Edge Cases

- Production health is green but the authenticated cabinet session is expired or missing.
- Upload succeeds but processing dependency is unavailable, slow, duplicated, or stuck.
- A recording is structurally valid but audio quality is degraded by speakerphone echo or leakage.
- A review has transcript but no stored outcomes, no playback, no diarization, or only one retained audio source.
- Speaker diarization has more speakers than the visible timeline color set.
- The web review and embedded macOS route show different states for the same meeting.
- The app shows cached green cabinet state after server restart or network failure.
- Evidence collection must avoid raw audio, transcript text, private meeting titles, account identifiers, tokens, signed URLs, object keys, or local private paths.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST collect or generate a metadata-safe 050 evidence pack for the current production release and installed macOS app.
- **FR-002**: The system MUST verify a real owner journey from installed macOS recording through production upload/finalize, server processing, and web review, or mark the exact blocking gate as failed.
- **FR-003**: The system MUST verify that production processing starts or reuses transcription and outcome work after accepted finalization without requiring operator-only manual pickup for the normal MVP path.
- **FR-004**: The system MUST verify that the production review page exposes transcript, diarization/speaker labels, playback, timestamp seeking, speaker activity lanes, and stored outcomes when the accepted meeting has those artifacts.
- **FR-005**: The system MUST verify that the macOS embedded cabinet and web cabinet show consistent meeting review truth for the same meeting.
- **FR-006**: The system MUST verify that the installed macOS app never treats a configured cabinet URL, cached route, or login page as proof of healthy authenticated cabinet readiness.
- **FR-007**: The system MUST verify desktop-width, embedded macOS, and mobile-width review layouts for overlap, clipping, hidden primary controls, horizontal overflow, and stale active tabs.
- **FR-008**: The system MUST use Krisp only as a clean-room interaction reference and MUST NOT copy Krisp assets, brand expression, screenshots, private content, proprietary copy, or icons into committed artifacts.
- **FR-009**: The system MUST keep all evidence metadata-only and must not commit raw audio, transcript text, generated private outcome text, account identifiers, credentials, tokens, signed URLs, storage object keys, private meeting titles, or local private paths.
- **FR-010**: The system MUST update product status, readiness reports, launch gap registers, changelog/release notes, and feature evidence so they match the deployed state after 045 through 049.
- **FR-011**: The system MUST remove `notes-action-output` from active P1 launch blockers only when stored outcome evidence is current and linked.
- **FR-012**: The system MUST keep `production_ready` and broad `user_rollout_ready` excluded unless live production user journey evidence proves every P1 gate.
- **FR-013**: The system MUST record processing time evidence for at least one long or representative recording and compare it to the target of processing one hour of audio in no more than three minutes, or mark the target as unproven/failed.
- **FR-014**: The system MUST leave any failed or unverified MVP gate visible with owner, severity, next action, and claim impact.
- **FR-015**: The system MUST preserve existing capture, upload, access, deletion, privacy, and server-mediated playback boundaries while fixing any discovered MVP UI or flow gaps.

### Key Entities

- **MVP Readiness Evidence Pack**: Metadata-only set of validation logs, screenshots or screenshot notes, command outputs, production smoke IDs, release links, and claim decisions for 050.
- **Owner Journey Gate**: A required step in the user path, such as local recording, upload, finalization, processing, review playback, transcript, diarization, outcomes, or embedded review.
- **Interface Audit Finding**: A web or macOS UI issue with surface, severity, reproduction, evidence, fix status, and claim impact.
- **Launch Gap**: A remaining blocker or deferred item with severity, owner, next action, and whether it blocks `mvp_loop_ready`, `internal_pilot_candidate`, `user_rollout_ready`, or `production_ready`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A 050 evidence pack shows every P1 owner journey gate as passed, failed, or explicitly blocked with direct evidence; no gate is left as assumed.
- **SC-002**: At least one current production owner review is validated in both web and macOS embedded review for transcript, diarization/speaker state, playback, timestamp seek, speaker timeline, and stored outcomes without committing private content.
- **SC-003**: Browser validation across desktop, embedded, and mobile-width review surfaces reports zero horizontal overflow, zero framework/runtime errors, and no incoherent overlap in the transcript, outcomes, tabs, or player.
- **SC-004**: Installed macOS app validation proves native capture controls remain visible and cabinet readiness/auth/server-down states are truthful.
- **SC-005**: Processing time evidence for a representative long recording is recorded against the target of no more than three minutes per one hour of audio, with pass/fail/unproven stated plainly.
- **SC-006**: Current status and readiness artifacts no longer contain stale branch-local or not-deployed claims for shipped 045 through 049 behavior.
- **SC-007**: The final 050 closeout states exactly one allowed readiness claim: `internal_pilot_candidate` if all P1 gates pass, otherwise `pilot_blocked` with concrete next fixes.

## Assumptions

- The MVP platform remains macOS with the installed app at `/Applications/2brain Rec.app`.
- Production server validation targets the current deployed `2brain Rec` service and release train.
- The owner can provide or create a fresh recording during validation when a real live journey is required.
- Speakerphone echo/noise suppression is not accepted runtime behavior in this slice; 050 may record it as a remaining quality limitation unless a separate accepted feature implements it.
- Signed/notarized external distribution, public links, external-recipient sharing, transcript editing, waveform polish, native Swift playback controls, and generalized assisted auto-start remain outside this feature unless a P1 MVP proof gate cannot pass without a narrow fix.
