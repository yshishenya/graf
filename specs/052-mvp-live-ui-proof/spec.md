# Feature Specification: MVP Live Owner Journey And UI Proof

**Feature Branch**: `052-mvp-live-ui-proof`

**Created**: 2026-06-25

**Status**: Draft

**Input**: User description: "Составить пошаговый план и действовать через SDD/Spec Kit до полноценного MVP: перепроверить полный путь установленного macOS приложения и веб кабинета, аккуратно ничего не сломать, при необходимости смотреть и сравнивать KRISP web/app reference, кликать и hover, пока не будет уверенности в MVP."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fresh Recording Reaches Review (Priority: P1)

As an owner, I can start and stop a fresh recording in the installed macOS app, let it upload and process, then open the production cabinet and see a usable review page with transcript, diarization, playback, speaker timeline, and meeting outcomes.

**Why this priority**: This is the core MVP promise. Without a current live owner journey from installed app to production review, the product remains `pilot_blocked` even if isolated parts work.

**Independent Test**: Perform one current metadata-safe owner journey from the installed app through production review. The test passes only when the candidate can be traced from recording creation to review availability without relying on private audio/text in committed evidence.

**Acceptance Scenarios**:

1. **Given** the installed app is available and the owner is allowed to record, **When** the owner records, stops, uploads, finalizes, and waits for processing, **Then** the production review state shows accepted media, imported transcript, diarization, playback availability, speaker timeline, and meeting outcomes for the same candidate.
2. **Given** any step fails or remains unavailable, **When** the readiness status is reported, **Then** the product keeps the claim at `pilot_blocked` and names the exact open gate.
3. **Given** evidence is captured for the journey, **When** it is stored in the repository, **Then** it contains metadata only and excludes raw audio, transcript text, generated private notes, account identifiers, cookies, tokens, signed URLs, storage object keys, and private local paths.

---

### User Story 2 - MVP Timing Is Proven Or Bounded (Priority: P1)

As the product owner, I can tell whether representative one-hour audio finishes processing within the target of no more than three minutes, or see a truthful blocker if the target is not proven.

**Why this priority**: The product goal is fast post-meeting transcription. A short smoke candidate cannot prove the one-hour processing target.

**Independent Test**: Use representative production-safe metadata for a near-one-hour candidate or approved equivalent timing proof. The test passes only when the proof covers enough duration to support or reject the target honestly.

**Acceptance Scenarios**:

1. **Given** a representative long candidate exists, **When** its processing timeline is evaluated, **Then** the result states whether the full processing path meets the three-minute-per-hour target.
2. **Given** no representative long candidate exists, **When** readiness is reported, **Then** the timing gate remains open with a clear next action and no stronger MVP claim is made.

---

### User Story 3 - Web And Desktop Review Feel Coherent (Priority: P1)

As an owner, I can use the production web cabinet and the macOS embedded cabinet without false-ready states, broken playback controls, hidden speaker activity, unreadable layouts, or confusing differences between the two surfaces.

**Why this priority**: The user judges the product through the review surface. Playback, speaker timeline, transcript, outcomes, and cabinet truth must be understandable before MVP.

**Independent Test**: Review the web and desktop cabinet surfaces against the same meeting state and compare them to a KRISP reference only for interaction patterns and information architecture, not for copying visual identity.

**Acceptance Scenarios**:

1. **Given** a ready meeting is open in web review, **When** the owner uses playback controls, timestamp seek, speaker timeline lanes, transcript, and outcomes, **Then** the surface remains readable, stable, and clear about available and unavailable actions.
2. **Given** the same meeting is opened inside the macOS cabinet, **When** the owner uses the same review workflow, **Then** the embedded surface preserves native recording/upload truth and presents the same review state as web.
3. **Given** KRISP web/app reference is inspected, **When** 2brain Rec UI is evaluated, **Then** the notes identify useful interaction expectations and brand-distance risks without copying private content or trade dress.

---

### User Story 4 - Launch Claim Is Truthful (Priority: P2)

As the product owner, I can read one simple closeout and know whether the product is still `pilot_blocked`, an `internal_pilot_candidate`, or blocked by named remaining gates.

**Why this priority**: The team needs a single truth source after verification. Overstating readiness is worse than leaving a blocker visible.

**Independent Test**: Produce a metadata-only closeout table that maps every launch gate to pass, blocked, unproven, or out of scope, with evidence links.

**Acceptance Scenarios**:

1. **Given** all P1 gates pass, **When** closeout is generated, **Then** the product may be raised to `internal_pilot_candidate` with supporting evidence.
2. **Given** one or more P1 gates are blocked or unproven, **When** closeout is generated, **Then** the claim remains `pilot_blocked` and the open gates are listed plainly.

### Edge Cases

- The owner is not authenticated in the web cabinet or embedded cabinet.
- Production health is green, but the owner route is unavailable or session-bound.
- A meeting has transcript and diarization but no stored outcome rows.
- Playback is available in one surface but not the other.
- Speaker timeline lanes are present but visually hidden, clipped, or not tied to transcript/playback time.
- A representative long timing candidate is unavailable.
- KRISP reference inspection exposes private account or meeting content; committed evidence must summarize only interaction findings.
- The installed app is running an older build than the deployed server expects.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST verify a current installed-app-to-production owner journey before raising the MVP claim above `pilot_blocked`.
- **FR-002**: The verification MUST link one fresh candidate across recording, upload, finalization, processing, transcript, diarization, playback, speaker timeline, and outcomes states.
- **FR-003**: The verification MUST distinguish direct production evidence from local fixture, synthetic, or historical evidence.
- **FR-004**: The product MUST keep `production-stored-outcomes-evidence` open until a current production candidate has stored outcome states and counts.
- **FR-005**: The product MUST keep `processing-time-target-evidence` open until representative long-audio timing proves or disproves the three-minute-per-hour target.
- **FR-006**: The product MUST keep owner review claims bounded when an authenticated owner session or current owner meeting is unavailable.
- **FR-007**: Web review MUST expose transcript, diarization, playback, timestamp seek, speaker timeline, and outcome availability in a coherent owner flow when the meeting is ready.
- **FR-008**: The macOS embedded cabinet MUST preserve native recording/upload truth while presenting the same meeting review state as web for ready meetings.
- **FR-009**: UI verification MUST cover desktop-width web, compact web, and macOS embedded review states.
- **FR-010**: UI verification MUST include speaker activity lanes in the bottom timeline and confirm they are readable and tied to the reviewed meeting.
- **FR-011**: UI verification MUST compare relevant KRISP web/app interaction patterns only as clean-room reference guidance and MUST NOT copy protected content, private account data, or brand trade dress.
- **FR-012**: Evidence and closeout artifacts MUST be metadata-only and MUST exclude raw audio, transcript text, generated private outcome text, account identifiers, cookies, tokens, signed URLs, storage object keys, and private local paths.
- **FR-013**: If any P1 gate is blocked or unproven, the closeout MUST state the exact gate, why it remains open, and the smallest next action.
- **FR-014**: If a defect blocks a P1 gate, the implementation MUST fix the smallest product path that owns the defect and rerun the relevant evidence gate.
- **FR-015**: Product status, changelog, release notes, and readiness docs MUST use the same final readiness claim.

### Key Entities *(include if feature involves data)*

- **Owner Journey Candidate**: A current recording candidate traced by metadata from local app creation through production review readiness.
- **Launch Gate**: A named readiness condition with status, evidence, blocker reason, and allowed claim impact.
- **Review Surface**: A web or macOS embedded owner-facing view of one meeting's transcript, playback, timeline, and outcomes.
- **Reference Observation**: A metadata-safe note from KRISP inspection describing interaction expectations, not private content or copied design.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One fresh owner journey is classified with direct evidence for every P1 step: record, stop, upload, finalize, process, review, transcript, diarization, playback, speaker timeline, and outcomes.
- **SC-002**: The readiness claim is internally consistent across closeout, product status, changelog, and release notes in 100% of updated artifacts.
- **SC-003**: Web and macOS embedded review verification covers at least desktop web, compact web, and embedded desktop states with zero critical layout or false-ready findings.
- **SC-004**: Speaker timeline verification confirms at least one visible speaker lane set for a ready meeting or records a blocking defect.
- **SC-005**: Timing proof either demonstrates processing at or below 180 seconds per one hour of representative audio or leaves the timing gate explicitly open.
- **SC-006**: Forbidden-content scans over new 052 evidence and docs return no committed private audio, transcript text, generated private outcome text, account identifiers, cookies, tokens, signed URLs, storage object keys, or private local paths.
- **SC-007**: If all P1 gates pass, the product may be labeled `internal_pilot_candidate`; otherwise the final claim remains `pilot_blocked` with named open gates.

## Assumptions

- The baseline is `master` after release `v2026.06.25.8`.
- The installed app path is `/Applications/2brain Rec.app`.
- The production public URL is `https://rec.2brain.pro`.
- KRISP is used as clean-room reference for workflow expectations only; 2brain Rec keeps its own design language.
- Raw meeting content is never committed as evidence.
- Signed/notarized external installer distribution, public links, waveform polish, transcript editing, real speakerphone AEC/noise suppression, and native Swift playback controls remain outside this slice unless they directly block the P1 owner journey proof.
