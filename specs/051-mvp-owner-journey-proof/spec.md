# Feature Specification: MVP Owner Journey Proof

**Feature Branch**: `051-mvp-owner-journey-proof`

**Created**: 2026-06-25

**Status**: Draft

**Input**: User description: "Продолжай по Spec Kit/SDD, действуй внимательно, перепроверяй каждый шаг, ничего не ломай. Дойди до полноценного MVP, перепроверь интерфейс приложения и веб кабинет. Если нужно, используй Krisp как reference для веба и приложения."

## Scope Summary

This feature closes the remaining P1 MVP launch blockers left by `050-mvp-launch-proof`. It must prove, on current production and the installed macOS app, that an owner can record a meeting, stop it, upload it, reach production review, see transcript, diarization, playback, speaker timeline, and stored outcomes, and get a truthful readiness claim. If any P1 proof cannot pass, the feature must leave the product explicitly `pilot_blocked` with the exact next action rather than inventing readiness.

This feature may include narrow product fixes required to make the proof true. It must not silently broaden into future polish such as signed/notarized public installer distribution, public links, transcript editing, waveform polish, generalized assisted auto-start, or real echo cancellation/noise suppression.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove The Fresh Owner Journey (Priority: P1)

As the product owner, I want a fresh installed-app recording to go through production upload, processing, and review, so that MVP readiness is based on a real current journey rather than stale fixtures or separate partial proofs.

**Why this priority**: The strongest remaining 050 blocker is lack of a fresh owner journey. The product cannot honestly become an MVP candidate until this path is proven or the blocking failure is named.

**Independent Test**: Start from `/Applications/2brain Rec.app`, create or use a fresh metadata-safe recording, let it upload/finalize/process on production, then open the resulting meeting in web and embedded review while recording only statuses, counts, timings, and non-content evidence.

**Acceptance Scenarios**:

1. **Given** the installed macOS app and production server are available, **When** the owner records and stops a meeting, **Then** the app shows truthful local recording, upload, and review states without hiding capture controls or sending audio directly to MediaScribe.
2. **Given** the recording package is structurally valid and accepted by production, **When** finalization completes, **Then** processing starts or reuses the correct workflow without an operator-only manual pickup for the normal MVP path.
3. **Given** production processing completes, **When** the owner opens the resulting review, **Then** transcript, diarization or speaker state, playback, timestamp seek, speaker activity timeline, and stored outcomes are available or each missing artifact has a truthful blocked state.
4. **Given** any step fails or remains unproven, **When** the 051 closeout is read, **Then** the readiness claim remains `pilot_blocked` with the failed gate, evidence, and next action.

---

### User Story 2 - Prove Stored Outcomes On Production (Priority: P1)

As a meeting owner, I want summaries, decisions, action items, and related outcome sections to be stored and visible for the production meeting, so that the MVP review is useful after transcription and diarization.

**Why this priority**: 049 closed the basic stored-outcomes product gap, but 050 found the current production candidate had missing outcomes. The MVP cannot rely only on fixture-backed outcome proof.

**Independent Test**: Use the fresh production candidate from User Story 1 or an explicitly identified current production candidate, then prove outcome category states, counts, and source coverage without committing private generated text.

**Acceptance Scenarios**:

1. **Given** a production meeting has transcript-backed processing results, **When** outcome generation/import runs, **Then** outcome rows exist for launch-safe categories or each category records `not_found`, `not_inferable`, `blocked`, or `failed` truth.
2. **Given** the owner opens web review, **When** the outcomes area renders, **Then** it shows stored outcome sections or truthful empty/blocked states without fabricating unsupported content.
3. **Given** the same meeting is opened in the embedded macOS cabinet, **When** review loads, **Then** outcome availability and blocked states match the web cabinet.

---

### User Story 3 - Prove Processing Speed Against The MVP Target (Priority: P1)

As the product owner, I want representative processing timing evidence, so that the product can honestly say whether one hour of audio can be processed in no more than three minutes.

**Why this priority**: The user defined "fast" as no more than three minutes of processing for a one-hour recording. The 050 candidate was short and could not prove the target.

**Independent Test**: Run or inspect a representative long production journey and record metadata-only duration, finalize-to-review timing, processing duration, queue/wait time, and pass/fail against the three-minute-per-hour target.

**Acceptance Scenarios**:

1. **Given** a representative long recording is available or created, **When** it is processed, **Then** the evidence records audio duration, processing duration, finalize-to-review duration, and the pass/fail result against the target.
2. **Given** only a shorter recording is available, **When** timing evidence is recorded, **Then** the target remains `unproven` rather than extrapolated into a pass.
3. **Given** queueing or dependency latency dominates the user wait, **When** evidence is recorded, **Then** the report separates raw processing time from owner-visible wait time.

---

### User Story 4 - Verify Web And macOS Review Interface Quality (Priority: P1)

As a meeting owner, I want the web cabinet and macOS embedded review to be readable, coherent, and truthful, so that I can trust the transcript, playback, speaker timeline, and outcomes without learning internal pipeline details.

**Why this priority**: A working pipeline is not a usable MVP if the review UI is confusing, clipped, stale, or inconsistent. The user specifically asked to re-check the app interface and web cabinet carefully.

**Independent Test**: Run browser/runtime validation and visual inspection across ordinary web, mobile-width web, desktop embedded review, and mobile-width embedded review. Krisp may be used only as a clean-room reference for interaction patterns such as transcript-first review, persistent bottom player, timestamp seek, and speaker timeline lanes.

**Acceptance Scenarios**:

1. **Given** a ready meeting review is open in the web cabinet, **When** the page renders, **Then** the transcript/review content is primary and the bottom playback area shows time, controls, and speaker activity lanes without overlap or horizontal overflow.
2. **Given** transcript timestamps are visible, **When** the owner selects a timestamp, **Then** playback seeks to that area and the visible review state remains stable.
3. **Given** the same review opens inside the macOS app, **When** the embedded cabinet loads, **Then** native Record/Stop/upload truth stays visible outside the web surface and server/auth states are not falsely shown as ready.
4. **Given** the production server is down, slow, or the user session is missing, **When** the app opens the cabinet, **Then** it shows server/auth truth instead of a cached green state.

---

### User Story 5 - Publish A Truthful MVP Readiness Decision (Priority: P2)

As the release owner, I want one final readiness decision with evidence, so that the team knows whether to start internal pilot use or keep fixing launch blockers.

**Why this priority**: The outcome of 051 is a product decision, not just code. If all P1 gates pass, the product can become an internal pilot candidate; otherwise it must remain blocked with a small next path.

**Independent Test**: Inspect the 051 evidence pack, readiness report, launch gap register, changelog, PR, release notes, and production health proof after implementation.

**Acceptance Scenarios**:

1. **Given** all P1 gates pass, **When** the final readiness report is read, **Then** the allowed claim is `internal_pilot_candidate` with exact limitations.
2. **Given** any P1 gate fails or lacks direct evidence, **When** the final readiness report is read, **Then** the allowed claim is `pilot_blocked` and the failed gate remains visible.
3. **Given** a release is prepared, **When** release notes are published, **Then** they are in simple Russian and describe what changed, what was verified, what is still limited, and how to roll back or proceed.

### Edge Cases

- Production health is green but the authenticated cabinet session is expired or missing.
- The app has a configured cabinet URL but the server is down or returns a login page.
- Upload succeeds but processing is delayed, duplicated, unavailable, or stuck.
- A production meeting has transcript and diarization but no stored outcomes.
- Outcome generation produces no safe evidence for one or more categories.
- Playback is available but download/export is policy-blocked.
- Diarization reports more speakers than the visible timeline color set.
- The web review and embedded review show different readiness, playback, speaker, or outcome states.
- A recording is structurally valid but speakerphone echo/noise makes transcription quality poor.
- Long-recording evidence is unavailable, too short, or dominated by queue/dependency wait.
- Evidence collection risks exposing raw audio, transcript text, private outcome text, account identifiers, tokens, signed URLs, object keys, private meeting titles, or local private paths.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST create a 051 metadata-only evidence pack for the current production release, installed macOS app, web cabinet, and embedded review.
- **FR-002**: The system MUST verify a fresh installed-app owner journey from record/stop through production upload, finalization, processing, and review, or mark the exact failed or unproven gate.
- **FR-003**: The system MUST verify that desktop upload and server finalization do not require the desktop client to call MediaScribe or store MediaScribe credentials.
- **FR-004**: The system MUST verify that accepted production processing starts or reuses the correct workflow without normal-path operator-only manual pickup.
- **FR-005**: The system MUST verify production transcript availability, diarization or speaker-state availability, playback availability, timestamp seeking, and bottom speaker timeline visibility for the reviewed meeting.
- **FR-006**: The system MUST verify stored outcome category states on production, including counts and evidence states, without committing generated private outcome text.
- **FR-007**: The system MUST expose truthful web and embedded review states when transcript, diarization, playback, timeline, or outcomes are missing, blocked, failed, partial, deleted, or still processing.
- **FR-008**: The system MUST verify representative processing timing against the target of no more than three minutes per one hour of audio, or explicitly keep the timing gate unproven/failed.
- **FR-009**: The system MUST separate raw provider/workflow processing time from owner-visible wait time when recording timing evidence.
- **FR-010**: The system MUST validate web cabinet, mobile-width web, desktop embedded review, and mobile-width embedded review for overlap, clipping, horizontal overflow, console/runtime errors, stale active tabs, and missing primary controls.
- **FR-011**: The system MUST validate that the installed macOS app keeps native capture/upload truth visible outside the embedded web review.
- **FR-012**: The system MUST validate that macOS cabinet readiness/auth/server-down state cannot be inferred from a configured URL, cached route, or login page alone.
- **FR-013**: The system MUST use Krisp only as a clean-room interaction reference and MUST NOT copy Krisp assets, private content, brand expression, proprietary icons, or screenshots into committed artifacts.
- **FR-014**: The system MUST keep committed evidence metadata-only and MUST NOT commit raw audio, transcript text, private generated outcome text, account identifiers, credentials, tokens, signed URLs, storage object keys, private meeting titles, cookies, or private local paths.
- **FR-015**: The system MUST update current product status, readiness report, launch gap register, validation log, changelog, and release notes so they match the final deployed state.
- **FR-016**: The system MUST remove P1 launch blockers only when direct current evidence proves them closed.
- **FR-017**: The system MUST keep `production_ready` and broad `user_rollout_ready` excluded unless a separate production rollout gate proves them.
- **FR-018**: The system MUST allow `internal_pilot_candidate` only when every P1 051 gate passes with direct evidence.
- **FR-019**: The system MUST leave P2 items such as signed/notarized public installer distribution and wider browser-target hardening visible as follow-up gaps unless they become necessary for a P1 proof.
- **FR-020**: The system MUST preserve existing capture, upload, access, deletion, privacy, server-mediated playback, and desktop-auth boundaries while fixing any discovered MVP flow or UI gaps.

### Key Entities

- **Owner Journey Gate**: A required step in the MVP path, including installed-app launch, record, stop, upload, finalization, processing, review, transcript, diarization, playback, speaker timeline, outcomes, and embedded review.
- **Production Candidate**: A meeting/revision used for proof, represented only by metadata-safe IDs or redacted references in local evidence and never by private content in committed files.
- **Processing Timing Evidence**: Metadata-only duration record containing audio duration, queue/wait duration, provider/workflow processing duration, finalize-to-review duration, and pass/fail/unproven outcome.
- **Interface Audit Finding**: A UI issue or pass result with surface, viewport, severity, reproduction, evidence, status, and claim impact.
- **MVP Readiness Decision**: Final claim chosen from `pilot_blocked` or `internal_pilot_candidate` for this feature, plus explicit excluded claims and remaining gaps.
- **Launch Gap**: A remaining blocker or deferred item with severity, journey, missing evidence, next action, and claim impact.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every P1 owner journey gate in 051 is recorded as pass, fail, blocked, or unproven with direct evidence; zero P1 gates are left assumed.
- **SC-002**: At least one current production owner review is validated in both web and macOS embedded review for transcript, diarization or speaker state, playback, timestamp seek, speaker timeline, and stored outcomes without committing private content.
- **SC-003**: Production outcome evidence records category states and counts for the selected candidate; stored outcomes are either proven present or the blocker remains open.
- **SC-004**: Representative timing evidence records audio duration, owner-visible wait, and processing duration, then states pass/fail/unproven against the three-minute-per-hour target.
- **SC-005**: Browser/runtime validation across web desktop, web mobile-width, embedded desktop, and embedded mobile-width reports zero horizontal overflow, zero incoherent overlap, and zero blocking console/runtime failures in the transcript, outcomes, tabs, player, and speaker timeline.
- **SC-006**: Installed macOS validation proves native capture controls remain visible and cabinet ready/auth/server-down states are truthful.
- **SC-007**: Current status and readiness artifacts contain no stale branch-local or not-deployed claims for shipped 045 through 050 behavior.
- **SC-008**: Final closeout states exactly one allowed readiness claim: `internal_pilot_candidate` if all P1 gates pass, otherwise `pilot_blocked`.
- **SC-009**: Full local CI and production deploy/smoke gates pass before release/deploy is claimed complete.

## Assumptions

- The MVP platform remains macOS with the installed app at `/Applications/2brain Rec.app`.
- Production validation targets `https://rec.2brain.pro` on the current 2brain Rec deployment.
- The owner can create or provide a fresh recording when live owner journey proof requires it.
- Existing server-mediated playback, transcript, diarization, and stored outcomes features should be reused rather than replaced.
- Real echo cancellation/noise suppression is not accepted behavior in this slice; speakerphone quality can remain a clearly stated limitation.
- Signed/notarized public macOS installer distribution is a P2 launch gap unless pilot distribution explicitly requires it before internal use.
- Evidence may include redacted IDs, counts, statuses, timings, safe screenshots, and local command outputs, but not private content or secrets.
