# Feature Specification: Assisted Auto-Recording

**Feature Branch**: `011-assisted-auto-recording`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Fix the product requirements for Krisp-class assisted auto-recording. 2brain Rec should sit in the background and help capture all real meetings, but must first launch as detect-and-ask for approved routed meetings and only later allow automatic recording after evidence proves false-positive safety."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect And Ask For Approved Routed Meetings (Priority: P1)

As a macOS meeting user, I want 2brain Rec to notice when I have likely joined an approved meeting through the 2brain virtual microphone and speaker, then ask whether to record, so that I do not forget capture while still staying in control.

**Why this priority**: This is the safest first product step toward "records all meetings." It delivers the main user value without creating surprise or invisible recordings from weak signals.

**Independent Test**: Enable detect-and-ask mode, join approved meeting targets through `2brain Rec Microphone` and `2brain Rec Speaker`, and verify that 2brain Rec shows a visible prompt with start/skip controls and metadata-only evidence explaining why the meeting candidate was detected.

**Acceptance Scenarios**:

1. **Given** detect-and-ask is enabled, workspace policy permits recording, and the user has acknowledged assisted recording rules, **When** an approved target starts a stable call through both 2brain virtual devices, **Then** 2brain Rec shows a visible prompt to record instead of starting hidden capture.
2. **Given** a prompt is shown for a detected meeting candidate, **When** the user chooses record, **Then** recording starts with a persistent local indicator, one-action stop, and trigger evidence `assisted_detect_and_ask`.
3. **Given** a prompt is shown for a detected meeting candidate, **When** the user dismisses or skips it, **Then** 2brain Rec does not re-prompt for the same candidate until the candidate ends or a defined cooldown expires.
4. **Given** a likely meeting candidate is detected but the route, policy, storage, or visible indicator gate is not ready, **When** the detector evaluates the candidate, **Then** no recording prompt is shown unless the blocker and recovery action can be presented truthfully.

---

### User Story 2 - Block False Positives From Non-Meeting Audio (Priority: P1)

As a privacy-conscious user, I want media playback, system audio, browser audio settings, prejoin tests, and app launches to never start or prompt recording as if they were meetings, so that 2brain Rec does not capture conversations or sounds I did not intend to record.

**Why this priority**: False positives are the primary product and trust risk for assisted auto-recording. A recorder that starts or nags from ordinary audio cannot be safely piloted.

**Independent Test**: Run the false-positive matrix with music/video playback, notification sounds, Zoom/Teams launch-only, browser audio settings, prejoin/device tests, and unsupported browser tabs while 2brain virtual devices are installed; verify no recording starts and no misleading meeting prompt appears.

**Acceptance Scenarios**:

1. **Given** only `2brain Rec Speaker` is active from media playback or arbitrary system output, **When** the detector evaluates activity, **Then** it blocks meeting detection as `speaker_only_audio`.
2. **Given** a supported browser is open on a non-approved domain or an approved service landing/settings/new/join page, **When** virtual-device activity occurs, **Then** the detector records blocked metadata and does not prompt to record.
3. **Given** Zoom, Teams, or another meeting app is launched but no stable in-meeting context exists, **When** the process or helper opens audio briefly, **Then** 2brain Rec records a non-meeting candidate or short stream and does not prompt.
4. **Given** audio settings, speaker test, microphone test, or prejoin surfaces use the virtual devices, **When** the detector evaluates the activity, **Then** it blocks or remains in detecting state without user-facing recording prompt.

---

### User Story 3 - Preserve Visible Capture Control (Priority: P1)

As a user, I want every assisted recording to be visibly distinguishable from manual recording and stoppable with one action, so that I can always tell when capture is active and stop it immediately.

**Why this priority**: The constitution requires visible consent and control. Assisted recording is unacceptable if the user cannot identify and stop it immediately.

**Independent Test**: Start a recording from a detect-and-ask prompt and verify the tray/widget/control surface shows assisted recording state, elapsed time, source target label, and one-action stop before capture is considered active.

**Acceptance Scenarios**:

1. **Given** the user accepts a detect-and-ask prompt, **When** recording starts, **Then** the local indicator changes to an assisted recording state before the first accepted recorded frame.
2. **Given** assisted recording is active, **When** the user presses Stop from tray, widget, or the main control surface, **Then** recording stops in one action and suppresses restart for the same candidate.
3. **Given** the visible indicator cannot be shown or becomes unavailable, **When** assisted recording would start or is active, **Then** start is blocked or recording fails closed with a truthful reason.

---

### User Story 4 - Collect Evidence Before Auto-Record Rollout (Priority: P2)

As an internal tester or admin, I want metadata-only evidence for detected, prompted, blocked, discarded, and recorded candidates, so that the team can prove the detector is safe before enabling true auto-recording.

**Why this priority**: The selected rollout path is detect-and-ask first. True auto-recording must be earned by measured false-positive evidence, not assumed from one signal.

**Independent Test**: Enable detect-only diagnostics, run approved meetings and non-meeting false-positive scenarios, and inspect metadata-only evidence that explains each decision without raw audio, transcript text, meeting content, credentials, or signed URLs.

**Acceptance Scenarios**:

1. **Given** detect-only diagnostics are enabled, **When** an approved routed meeting starts, **Then** 2brain Rec records candidate evidence but does not prompt or record.
2. **Given** a candidate is blocked, **When** evidence is exported, **Then** the reason includes the relevant blocker such as `target_context_unknown`, `speaker_only_audio`, `prejoin_or_settings_surface`, or `virtual_route_not_active`.
3. **Given** a candidate is prompted or recorded, **When** evidence is exported, **Then** it includes policy state, user acknowledgement state, target classification, route state, stability window, indicator state, and decision outcome.

---

### User Story 5 - Future Auto-Record For Proven High-Confidence Cases (Priority: P3)

As an internal MVP user, I want 2brain Rec to automatically start recording only for proven approved meeting cases after detector evidence is accepted, so that important meetings are captured without manual action while preserving privacy gates.

**Why this priority**: This is the strategic product goal, but it must follow detect-and-ask evidence because the blast radius of false positives is high.

**Independent Test**: After accepted detector evidence and explicit enablement, run high-confidence approved meetings and verify recording starts automatically only when every hard gate passes, with assisted auto-start evidence and visible control.

**Acceptance Scenarios**:

1. **Given** auto-record-approved mode is explicitly enabled for internal MVP after evidence acceptance, **When** a high-confidence approved routed meeting candidate remains stable, **Then** recording starts automatically with visible assisted-auto state and one-action stop.
2. **Given** auto-record-approved mode is enabled, **When** any hard gate fails, **Then** the system blocks auto-start and records the reason without starting capture.
3. **Given** the user manually stops an auto-started recording, **When** the same candidate remains active, **Then** 2brain Rec does not auto-restart it during the suppression window.

---

### User Story 6 - Automatic Meeting And Artifact Naming (Priority: P3)

As a user, I want 2brain Rec to give new recordings useful names automatically, so that I can find meetings later without naming every recording by hand.

**Why this priority**: Auto-recording increases the number of captured meetings. Without reliable naming, the user gets a pile of indistinguishable recordings and the product feels noisy.

**Independent Test**: Start assisted candidates with calendar-linked, platform-titled, unknown, and policy-restricted contexts; verify that each recording gets a useful UI title, a safe filesystem artifact name, and metadata explaining the naming source and confidence.

**Acceptance Scenarios**:

1. **Given** a detected meeting matches a calendar event, **When** the recording is created, **Then** the UI title uses the calendar event title unless policy requires generic names.
2. **Given** no calendar title is available but the approved meeting platform exposes a safe meeting title, **When** the recording is created, **Then** the UI title uses the platform title with source confidence recorded.
3. **Given** no reliable title source is available, **When** the recording is created, **Then** the UI uses a clear fallback such as `Meeting - Jun 4, 2026 14:30` and marks the title as needing review.
4. **Given** a recording has a useful UI title, **When** local artifacts are saved, **Then** the filesystem name uses a sanitized date/time/title/session pattern that avoids sensitive or unsafe content.
5. **Given** the user renames a recording, **When** the meeting is displayed or exported later, **Then** the user title is preserved without changing the stable recording identity.

---

### Edge Cases

- Virtual speaker activity exists without virtual microphone activity because the browser or system is playing ordinary audio.
- Virtual microphone activity exists without an approved app, approved domain, or meeting-room context.
- A meeting app launches, updates, opens a notification, or creates helper processes without an active meeting.
- A browser opens audio settings, permission prompts, device tests, landing pages, or prejoin screens.
- The meeting is silent for a while but the approved routed meeting context remains active.
- The meeting lasts less than the short-session threshold.
- User starts manual recording while a detected candidate exists.
- User presses Stop or Skip, then the app sees continuing virtual-device activity for the same candidate.
- The app loses route readiness, storage safety, policy validity, or indicator availability while a candidate is being evaluated.
- The current meeting target is supported for manual recording smoke but not yet approved for assisted detection.
- Diagnostic export is requested after detection decisions involving browser tabs, meeting titles, or source app metadata.
- Calendar title exists but workspace policy disables descriptive names.
- Calendar title includes emails, meeting URLs, ticket numbers, or sensitive project names.
- Platform/browser title contains a generic product label, meeting code, URL fragment, or noisy suffix.
- Two recordings receive the same sanitized title and start time.
- User renames a recording while local artifact filenames already exist.

### Naming Strategy Options

This feature defines four acceptable naming strategies. Planning must select the default and may expose stricter strategies by policy.

#### Option A - Conservative Date Fallback

Use only date, time, target type, and a short stable session suffix.

Example UI title: `Zoom Meeting - Jun 4, 2026 14:30`
Example artifact folder: `2026-06-04_14-30_zoom-meeting_8f3a2c`

**Use when**: privacy policy disables descriptive titles, title confidence is low, or the source target is unknown.

**Trade-off**: safest and predictable, but less helpful for finding meetings later.

#### Option B - Calendar-First Descriptive Title

Use the matched calendar event title for the UI title and a sanitized calendar title slug in the artifact name.

Example UI title: `Weekly Product Sync`
Example artifact folder: `2026-06-04_14-30_weekly-product-sync_8f3a2c`

**Use when**: the candidate matches a calendar event by time and meeting/link evidence, and policy allows descriptive names.

**Trade-off**: best user experience for scheduled meetings, but calendar titles can contain sensitive business context and must be policy-controlled.

#### Option C - Platform/Browser Context Title

Use a safe meeting title exposed by the approved platform, browser tab, or meeting room context when no calendar match exists.

Example UI title: `Customer Discovery Call`
Example artifact folder: `2026-06-04_14-30_customer-discovery-call_8f3a2c`

**Use when**: a meeting platform provides a real meeting-room title, not just a product name, landing page, meeting code, URL, or device settings title.

**Trade-off**: useful for ad hoc meetings, but higher false-title risk than calendar data and must pass negative-title filters.

#### Option D - User-Confirmed Smart Title

Create an initial safe fallback, then suggest a better title after the meeting from approved metadata or user notes, requiring user confirmation before replacing the title.

Example UI title before confirmation: `Meeting - Jun 4, 2026 14:30`
Example suggested title: `Roadmap Review With Design`

**Use when**: richer naming would require potentially sensitive content or post-meeting inference.

**Trade-off**: best long-term organization, but should not be part of the first assisted auto-recording rollout unless explicitly planned because it increases privacy and inference scope.

### Recommended Default Naming Policy

The default policy for this feature is Option B when a high-confidence calendar match exists, Option C when a safe approved platform title exists, and Option A otherwise. Option D is deferred unless a later spec explicitly allows post-meeting title suggestions.

UI meeting titles may be descriptive when policy allows it. Local artifact filenames must be more conservative: date/time, sanitized title slug, and a short stable suffix. Filenames must not include raw URLs, meeting codes, participant emails, credentials, transcript-derived text, or unsanitized platform titles.

Title confidence values:

- `user_confirmed`: user renamed or accepted the title.
- `calendar`: title came from a high-confidence calendar match.
- `platform`: title came from an approved platform or browser meeting context.
- `generic`: title came from date/time and target fallback.
- `needs_review`: title is useful enough to display but should be presented as reviewable.

Title source must be recorded separately from recording identity so the user can rename meetings without breaking artifact identity, upload identity, audit trails, or deletion accounting.

### Desktop UI Authority And Server-Driven UI Options

Assisted auto-recording depends on a local trust surface. The desktop app must
therefore use a hybrid UI authority model rather than a fully server-rendered
desktop interface.

#### Option A - Fully Local Native Desktop UI

All desktop screens and flows are rendered locally by the platform-native app.

**Use when**: the surface controls capture, visible indicators, stop,
permissions, driver lifecycle, route health, local buffer safety, diagnostics,
or offline pending recordings.

**Trade-off**: strongest trust and offline behavior, but duplicates more UI
work across future platforms.

#### Option B - Fully Server-Rendered Desktop UI

The desktop app displays server-rendered remote UI for most or all product
flows.

**Use when**: not accepted for capture-critical surfaces.

**Trade-off**: faster cross-platform iteration, but unsafe for active capture
truth because server/network availability must not control whether the user can
see or stop recording.

#### Option C - Server-Driven Native UI Schema

The server sends versioned schema that the desktop app renders using local
native components.

**Use when**: non-critical settings, policy explanations, help content,
onboarding copy, or admin-constrained forms need remote configuration.

**Trade-off**: more flexible than hard-coded UI, safer than remote WebView UI,
but requires schema versioning, cached fallbacks, and strict rejection of
unknown or unsafe actions.

#### Option D - Hybrid Trust Shell And Web Dashboard

The local/native desktop app owns capture-critical trust surfaces, while the
server web dashboard owns post-meeting, transcript, notes, admin, retention,
deletion, audit, and device-fleet views.

**Use when**: default architecture for this feature and future platforms.

**Trade-off**: requires disciplined shared contracts and design-system parity,
but preserves local trust while avoiding duplicated dashboard/admin UI on every
desktop platform.

### Recommended UI Authority Policy

The default architecture is Option D. Option A applies inside the local trust
shell. Option C may be used only for non-critical server-synced content and
forms. Option B is rejected for capture-critical surfaces.

Local/native desktop surfaces are authoritative for active capture state,
visible indicator state, one-action stop, assisted detection prompts, route
readiness, driver recovery, local buffer safety, local recording artifact truth,
offline pending recordings, and diagnostics export.

Server/web surfaces are authoritative for uploaded meeting records, transcripts,
notes, search, sharing, admin policy editing, retention/deletion dashboard,
audit views, device fleet, and workspace management.

Server-provided policy, feature flags, approved targets, naming policy,
consent/legal profile, localization, and non-critical help content may constrain
or annotate desktop UI. They must not be required to display active capture
truth or stop active capture. If server state is stale or unreachable, active
capture remains stoppable locally and new assisted auto-start fails closed
unless a valid cached policy explicitly authorizes it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support `manual_only`, `detect_only_diagnostics`, `detect_and_ask`, and `auto_record_approved` assisted recording modes.
- **FR-002**: The first accepted rollout mode for this feature MUST be `detect_and_ask`; `auto_record_approved` MUST remain future/internal-only until detector evidence is accepted.
- **FR-003**: The system MUST require workspace policy permission and explicit user acknowledgement before any assisted prompt or assisted recording can occur.
- **FR-004**: The system MUST evaluate active virtual-device routing separately for microphone and speaker and MUST NOT treat generic device publication as meeting evidence.
- **FR-005**: The system MUST treat arbitrary system audio, media playback, notification sounds, music, videos, and non-approved apps as ineligible for assisted recording.
- **FR-006**: The system MUST NOT prompt or start assisted recording from speaker-only audio unless a later approved exception explicitly supersedes this feature.
- **FR-007**: The system MUST require approved target evidence before showing a recording prompt or auto-starting recording.
- **FR-008**: Approved target evidence MUST distinguish native app identity, browser identity, browser meeting domain or room context, and unsupported or unknown targets.
- **FR-009**: Browser targets MUST be considered approved only when the page context indicates a real meeting room or call surface, not merely an approved product domain.
- **FR-010**: The detector MUST include negative classifications for audio settings, prejoin, device test, landing, new-meeting, join, and non-meeting pages when these can be identified.
- **FR-011**: The detector MUST use a stability window before prompting or recording so brief stream opens, process launches, and device tests do not become meeting prompts.
- **FR-012**: Natural silence MUST NOT stop or block an active routed meeting candidate when explicit client activity and meeting context remain valid.
- **FR-013**: Sessions shorter than 30 seconds MUST NOT be represented as successful meeting recordings; they MUST be discarded or represented as metadata-only short candidates unless the user explicitly saved them.
- **FR-014**: A detect-and-ask prompt MUST offer clear record and skip/dismiss outcomes without implying recording has already started.
- **FR-015**: A skipped or manually stopped candidate MUST suppress re-prompting or auto-restart for the same candidate until the candidate ends or a cooldown expires.
- **FR-016**: Assisted recordings MUST display a persistent local indicator and one-action stop before the system treats capture as active.
- **FR-017**: Assisted recording state MUST be distinguishable from manual recording state in user-facing status, accessibility labels, and diagnostics.
- **FR-018**: If the visible indicator cannot be shown, assisted recording MUST be blocked or failed closed.
- **FR-019**: Assisted recording MUST require route readiness, storage safety, permission validity, and recording prerequisite gates equivalent to or stricter than manual recording.
- **FR-020**: The system MUST record metadata-only evidence for every detected, prompted, blocked, skipped, discarded, started, stopped, degraded, or failed assisted candidate.
- **FR-021**: Evidence MUST include trigger mode, decision outcome, target classification, policy state, user acknowledgement state, virtual mic/speaker activity state, route readiness state, stability window result, visible indicator state, and blocker reason when blocked.
- **FR-022**: Evidence and diagnostics MUST NOT include raw audio, transcript text, meeting content, credentials, tokens, signed URLs, passwords, or live credential paths.
- **FR-023**: Assisted recording MUST NOT cause the desktop app to send audio directly to MediaScribe or store MediaScribe credentials.
- **FR-024**: The feature MUST preserve manual recording start/stop regardless of assisted mode when workspace policy permits manual recording.
- **FR-025**: The feature MUST preserve the current separation between driver-owned routing/client activity and app-owned recording/transcription decisions.
- **FR-026**: True `auto_record_approved` enablement MUST be gated by accepted detector evidence showing no false-positive auto-starts across the required matrix.
- **FR-027**: The required false-positive matrix MUST include media playback, notification sounds, browser audio settings, prejoin/device tests, Zoom/Teams launch-only, unsupported browser tabs, and approved app non-meeting states.
- **FR-028**: The required positive matrix MUST include approved routed meeting targets from the current MVP support list that are explicitly accepted for assisted detection.
- **FR-029**: Unsupported, skipped, unknown, or best-effort targets MUST be recorded as blocked or not accepted, not passed.
- **FR-030**: External/customer workspaces MUST NOT enable assisted auto-recording until workspace notice/legal policy requirements are selected and accepted.
- **FR-031**: The system MUST generate a user-facing title for each assisted meeting candidate or recording using the approved naming policy.
- **FR-032**: The system MUST support at least conservative fallback naming, calendar-first descriptive naming, and approved platform/browser context naming.
- **FR-033**: The default naming policy MUST use a high-confidence calendar title first, a safe approved platform/browser title second, and a generic date/time fallback otherwise.
- **FR-034**: The system MUST generate filesystem-safe artifact names using date/time, sanitized title slug, and a stable short session suffix.
- **FR-035**: Default artifact names MUST NOT include raw URLs, meeting codes, participant emails, credentials, tokens, transcript-derived text, or unsanitized platform titles.
- **FR-036**: The system MUST allow the user to rename a meeting without changing the stable recording identity, artifact identity, audit identity, or deletion identity.
- **FR-037**: The system MUST record title source and confidence as metadata for every generated or user-edited title.
- **FR-038**: The system MUST support a policy mode that uses generic names only when descriptive calendar or platform names are considered sensitive.
- **FR-039**: Post-meeting smart title suggestions from inferred content MUST remain out of scope unless a later spec explicitly approves the privacy and consent model.
- **FR-040**: Capture-critical desktop trust surfaces MUST be local/native and remain usable without server-rendered UI.
- **FR-041**: Server-rendered UI or remote WebView UI MUST NOT own active capture truth, visible indicator availability, one-action stop, route health truth, local storage safety, permission recovery, driver recovery, or capture authorization gates.
- **FR-042**: Server-provided policy, feature flags, approved targets, consent/legal profile, naming policy, localization, and non-critical help content MAY constrain or annotate local desktop UI only when the local app validates and enforces the resulting state.
- **FR-043**: If server policy is stale or unavailable, active capture MUST remain locally stoppable and new assisted auto-start MUST fail closed unless a valid cached policy explicitly authorizes it.
- **FR-044**: Post-meeting review, transcript, notes, search, sharing, admin policy, retention, deletion, audit, and device-fleet surfaces SHOULD live in the server web dashboard unless a platform-specific offline workflow requires local UI.
- **FR-045**: Multiplatform UI reuse MUST rely on shared state contracts, design tokens, localization keys, and policy schemas rather than server control of capture-critical UI.

### Key Entities *(include if feature involves data)*

- **Assisted Recording Mode**: The user/workspace state that determines whether the system is manual-only, detecting silently for QA, asking before recording, or eligible for future approved auto-record.
- **Meeting Candidate**: A metadata-only observation that virtual-device activity may correspond to a meeting. Includes candidate ID, source target, virtual mic/speaker activity, stability timing, route state, and decision status.
- **Target Classification**: The system's determination of whether an app, process, browser, domain, room context, or meeting surface is approved, blocked, unknown, or not accepted.
- **Negative Signal**: Evidence that a candidate is likely not a real meeting, such as media playback, audio settings, prejoin, device test, landing page, launch-only state, or speaker-only audio.
- **Assisted Recording Decision**: The outcome of evaluating a candidate: detected only, prompted, skipped, blocked, started manually from prompt, auto-started in future mode, discarded short, stopped, degraded, or failed.
- **Suppression Window**: A temporary rule created when the user skips a prompt or stops an assisted recording, preventing repeated prompts or restart for the same candidate.
- **Assisted Evidence Record**: Metadata-only audit/diagnostic record explaining why the system detected, prompted, blocked, discarded, started, or stopped assisted recording.
- **Meeting Title**: The user-facing display name for a meeting or recording. It may be generated from calendar, platform, or fallback metadata and may later be edited by the user.
- **Artifact Name**: The filesystem-safe local folder or file prefix used for saved recording artifacts. It is derived conservatively and must not be the stable recording identity.
- **Title Confidence**: Metadata describing whether a title is user-confirmed, calendar-derived, platform-derived, generic, or needs review.
- **Naming Policy**: Workspace or local policy that controls whether descriptive titles are allowed or generic-only names must be used.
- **Local Trust Shell**: The native desktop UI surfaces that show and control active capture, route truth, visible indicators, stop actions, driver recovery, local buffers, and diagnostics.
- **Server Dashboard Surface**: Web UI served by the self-hosted backend for uploaded meetings, transcripts, notes, admin policy, retention, deletion, audit, and fleet views.
- **Server-Driven UI Schema**: A versioned server-provided description rendered by native desktop components for non-critical content or forms. It is not allowed to own active capture controls.
- **Shared UI State Contract**: Cross-platform contract for states such as recording, route, policy, indicator, candidate, upload, deletion, device health, feature flags, and naming policy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the false-positive matrix, there are zero assisted recording starts from media playback, notification sounds, browser audio settings, prejoin/device tests, Zoom/Teams launch-only, unsupported browser tabs, and approved app non-meeting states.
- **SC-002**: In the initial detect-and-ask rollout, there are zero hidden or invisible recordings; every recording started from a prompt has a visible indicator and one-action stop before capture is active.
- **SC-003**: Approved routed meeting candidates in the positive matrix are detected and eligible for a prompt within 15 seconds of stable in-meeting virtual-device activity.
- **SC-004**: At least 95% of accepted positive-matrix runs produce a correct prompt or a truthful blocked reason; no run may be marked passed without target and route evidence.
- **SC-005**: Skipping a prompt or manually stopping assisted recording prevents repeated prompts or auto-restart for the same candidate during the suppression window in 100% of tested cases.
- **SC-006**: Sessions shorter than 30 seconds are discarded or marked metadata-only in 100% of tested short-stream cases unless explicitly saved by user action.
- **SC-007**: Diagnostic bundles for assisted detection pass metadata-only redaction checks with no raw audio, transcript text, meeting content, credentials, tokens, signed URLs, passwords, or live credential paths.
- **SC-008**: Manual recording remains available and unchanged for approved manual flows in all assisted mode configurations where workspace policy permits recording.
- **SC-009**: `auto_record_approved` cannot be enabled until accepted evidence records show zero false-positive auto-starts across the required matrix.
- **SC-010**: External/customer workspace configuration blocks assisted auto-recording until required notice/legal policy setup is complete.
- **SC-011**: 100% of assisted recordings receive a non-empty UI title and a filesystem-safe artifact name.
- **SC-012**: In naming validation, filenames contain no raw URLs, meeting codes, participant emails, credentials, tokens, transcript-derived text, or unsafe filesystem characters.
- **SC-013**: User rename preserves the same recording identity, artifact identity, audit identity, and deletion identity in 100% of tested cases.
- **SC-014**: Generic-only naming policy prevents descriptive calendar and platform titles from appearing in filenames and default UI titles in 100% of tested cases.
- **SC-015**: Active capture state and one-action stop remain visible and usable during server outage in 100% of local trust-shell validation cases.
- **SC-016**: Remote UI/schema validation rejects any server-provided action that attempts to hide active capture, remove Stop, misrepresent route health, or bypass local capture gates in 100% of tested cases.
- **SC-017**: Future platform planning identifies native trust-shell responsibilities separately from shared dashboard surfaces before implementation begins.

## Assumptions

- The product remains macOS driver-first for MVP and assisted recording depends on active `2brain Rec Microphone` and `2brain Rec Speaker` routing unless a later spec creates an explicit exception.
- Detect-and-ask is the first rollout mode for this feature; true automatic recording is a later internal capability gated by evidence.
- Manual recording, visible indicator, local recording persistence, and local recording artifact format remain the accepted baseline capabilities that assisted recording can invoke.
- Audio energy is not a reliable meeting detector; natural silence can occur during real meetings and must not by itself stop detection or recording.
- Browser and native target evidence may be imperfect; unknown or unsupported evidence must block assisted recording instead of guessing.
- Current MVP candidate targets include Telemost, Chrome, Opera, and Zoom only where the feature's own validation explicitly accepts them for assisted detection. Yandex Browser remains not accepted until separately validated.
- MediaScribe transcription, upload, server ingest, dashboard notes, retention, deletion workflows, and meeting-app mute truth are out of scope for this feature unless later specs supersede this boundary.
- Meeting naming uses metadata available before or during candidate creation. Transcript/audio-derived smart titles are deferred to a later feature because they change the privacy and inference scope.
- The desktop trust shell remains native per platform; shared dashboard/admin surfaces may be web-based and reused across platforms.
