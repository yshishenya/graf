# Feature Specification: Complete Recording Workflows

**Feature Branch**: `121-recording-workflows`

**Created**: 2026-07-21

**Status**: Visual direction approved; implementation remains gated by refreshed checklists, analysis, and issue sync

**Input**: User request: "Implement all recording-related functions, design the interface and backend/frontend behavior in detail, study Krisp and internet best practices, describe everything first, create a prototype before implementation, use Langfuse from the first AI-enabled version, and make important asynchronous external work durable."

> Historical contract note: Feature 121 deliberately simplified the meeting
> prompt by removing the countdown, automatic expiry start, checkbox, and app
> list. That temporary decision is superseded for verified native meeting
> targets by Feature [124-restore-automatic-recording](../124-restore-automatic-recording/spec.md).
> Keep the Feature-121 history intact, but treat Feature 124 as the current
> owner of those restored recording behaviors.

## Product Scope Boundary

This feature completes one coherent owner workflow around an audio meeting:
capture readiness, deliberate start, visible active controls, durable local
custody, synchronization and processing truth, review, transcript-linked
playback, summary templates, controlled sharing, export entry points, deletion,
and recovery. It converges existing accepted capabilities instead of creating a
second recorder, processing pipeline, review surface, access system, or export
model.

The macOS MVP remains app-owned, system-audio-first audio capture with explicit
microphone capture. Bot participation, camera capture, screen-video recording,
live coaching, a second audio-routing mode, and generalized or unscoped hidden
automatic recording are outside this feature. The verified target-scoped
workflow is owned by Feature 124 and requires its own safety gates.

Krisp is a clean-room workflow benchmark only. GRAF MUST use its own Russian
copy, information architecture, visual expression, assets, controls, data
model, and implementation. Competitive behavior that weakens local custody,
silently starts capture, destroys earlier material, or makes public sharing
implicit is explicitly rejected.

The interaction contract is intentionally smaller than the internal model. The
daily path is `Начать запись → Остановить → Итоги → Поделиться`. Each state has
one primary action; healthy device and pipeline details stay quiet; advanced
sharing and governance appear only after an explicit request. The authoritative
screen/state map is [ux-ia.md](./ux-ia.md).

## Clarifications

### Session 2026-07-21

- Q: Does "all recording functions" include bot, camera, or screen-video capture? → A: No; complete the existing audio meeting lifecycle first and reserve those modes for separately approved slices.
- Q: What is the safe sharing default? → A: Invite-only, summary-only, view access; broader audiences, content, and permissions require explicit owner action.
- Q: How should summary regeneration handle owner edits? → A: Preserve accepted revisions and require an explicit replacement decision; never silently destroy edits.
- Q: Is meeting detection allowed to start recording silently? → A: No; the
  current contract is visible target-scoped detection. Feature 124 restores the
  designed eight-second prompt/countdown, automatic start on expiry, immediate
  start, skip, and per-target opt-in; arbitrary or unapproved audio remains
  forbidden.
- Q: Is Pause sufficient as the product privacy action? → A: Yes; do not add a second app-level microphone mute control.
- Q: How much of the backend lifecycle should the normal UI expose? → A: One current human status and one next action; pipeline stages, retries, provenance, and policy details stay behind contextual disclosure.
- Q: What is the meeting-detail IA? → A: Exactly two content tabs (`Итоги`, `Расшифровка`), a persistent player, Share, and a More menu; no permanent control-center rail or lifecycle stepper.
- Q: Should the user configure every sharing dimension? → A: No; the first Share screen is invite-only, summary-only, view-only, with broader content/audiences revealed only on request and only when policy permits them.
- Q: Where do the selected model and generation settings live? → A: Each outcome format has a versioned Langfuse prompt whose `config` is the single editable source for the selected LiteLLM model route, generation parameters, and strict response schema; the initial route is private `gpt-5.6-luna`, while LiteLLM retains only upstream routing and secret custody.
- Q: Should every outcome format use the same prompt? → A: No. Each built-in format has its own Langfuse prompt/config and evaluation lifecycle; personal templates use one safe structured custom prompt rather than creating an unbounded Cloud prompt per user.
- Q: What does `Авто` do? → A: `Авто` is its own conservative general-outcome prompt with a stable schema; it does not run a hidden meeting-type classifier or silently switch to another format.
- Q: Should GEPA and JEPA both optimize prompts? → A: Use GEPA for offline reflective prompt optimization. JEPA is a representation-learning/pretraining architecture, not a prompt optimizer, and is excluded unless a later request identifies a different concrete JEPA tool and separately approves model-training scope.
- Q: Must debugging systems receive transcript content? → A: Yes. Langfuse
  receives the complete request/transcript/raw response/validated result and
  Temporal History stores the complete transcript in plaintext. Feature 121
  does not encrypt, redact, mask, truncate, or delete those observability copies.

### Session 2026-07-23 — candidate lifecycle and recovery

- The first usable transcript may trigger one policy-owned `Авто` generation.
  This is the only implicit generation. Every later format change or
  regeneration is an explicit owner action.
- Automatic work is limited to retrying the same durable candidate after a
  transient worker, provider, or prompt-control dependency failure and to
  reconciling already-retained response delivery. It never creates a second
  candidate, repeats an ambiguous provider call, or replaces an accepted set.
- Prompt/model/config changes, template edits, sharing changes, reloads, and
  provider remaps never silently regenerate an existing meeting. A new request
  pins the currently promoted Langfuse version and creates a new candidate.
- A transcript/source revision change invalidates queued or generating work
  before egress and prevents acceptance of a stale candidate. The accepted
  pointer remains current; the owner may explicitly request a new candidate
  from the new source revision.
- Candidate revisions are retained. A ready candidate is previewable by its
  owner, `Использовать` performs the atomic compare-and-swap acceptance, and
  dismiss/reject does not delete history. Shared viewers and exports always
  read the accepted pointer only.
- Meeting reload, a second browser tab, or a new authorized owner device must
  recover the server-persisted pending/ready candidate; browser session storage
  is only a performance hint, never the source of truth. At most one current
  candidate is promoted in the primary meeting view; older candidates remain
  available in owner-only history.
- A failed candidate exposes a bounded reason and whether retry is safe. Only
  transient failures offer `Повторить`; schema-invalid, stale, deleted,
  authorization, configuration, and ambiguous-provider failures explain the
  next action without a blind retry.

## User Scenarios & Testing

### User Story 1 - Start A Trustworthy Recording (Priority: P1)

As a meeting participant, I want to see whether microphone and system audio are
ready and deliberately start recording, so that I know what will be captured
before any meeting content is stored or processed.

**Why this priority**: Every later transcript, summary, share, and export is
invalid if capture began without informed control or with hidden source loss.

**Independent Test**: Exercise manual start and detect-and-ask from ready,
permission-denied, source-missing, offline, and already-recording states; verify
that capture starts only from an allowed state and the user can always identify
the active sources.

**Acceptance Scenarios**:

1. **Given** microphone and system-audio permissions are ready, **When** the user starts a recording, **Then** GRAF immediately shows an active local indicator, elapsed time, captured sources, Pause, and one-action Stop.
2. **Given** a supported meeting is detected, **When** GRAF offers to record, **Then** the prompt identifies the meeting context, allows Start or Not now, and does not start capture by itself.
3. **Given** a required permission or source is unavailable, **When** the user attempts to start, **Then** capture fails closed with a specific recovery action and no false recording state.
4. **Given** the user has no network connection, **When** local capture prerequisites are ready, **Then** the user can record locally and sees that synchronization will wait for connectivity.

---

### User Story 2 - Control And Recover An Active Recording (Priority: P1)

As a participant in an active meeting, I want obvious Pause, Resume, and Stop
controls in the app and menu bar, so that I can protect private moments and end
capture without navigating away from my work.

**Why this priority**: Visible control and a reliable stop path are core privacy
and safety requirements.

**Independent Test**: Run an active recording through pause, resume, source
loss, network loss, app-window changes, application relaunch, and stop; verify
one consistent state and a recoverable local artifact.

**Acceptance Scenarios**:

1. **Given** capture is active, **When** the user pauses, **Then** both product-owned audio sources stop contributing meeting content, elapsed state clearly reads Paused, and Stop remains available.
2. **Given** capture is paused, **When** the user resumes, **Then** capture continues on the same meeting timeline and the privacy interval remains represented without fabricating speech.
3. **Given** a source becomes degraded or unavailable, **When** recording continues or stops, **Then** GRAF shows truthful source status and preserves usable material without claiming complete capture.
4. **Given** the app exits unexpectedly after durable content exists, **When** it launches again, **Then** it offers a bounded recovery/finalization path instead of silently deleting or duplicating the meeting.
5. **Given** any app route is visible, **When** recording is active, **Then** one-action Stop remains locally available and cannot be hidden by embedded web content.

---

### User Story 3 - Follow Local Custody, Upload, And Processing (Priority: P1)

As a meeting owner, I want the stopped recording to appear immediately and
show distinct local, synchronization, transcription, playback, and summary
states, so that I understand what is safe, what is pending, and what can be
retried.

**Why this priority**: A stopped recording must remain useful even when the
network or an external processor fails.

**Independent Test**: Stop recordings while online and offline, then exercise
upload retry, duplicate requests, processing delay/failure, relaunch, and final
success; verify one meeting identity and no loss of the local copy before
accepted custody.

**Acceptance Scenarios**:

1. **Given** capture stops successfully, **When** finalization completes, **Then** the meeting appears in the local list with duration, source truth, local custody, and the next automatic action.
2. **Given** upload is interrupted, **When** connectivity returns, **Then** synchronization resumes idempotently without creating a duplicate meeting or requiring a new recording.
3. **Given** transcription or summary processing is delayed or fails, **When** the owner opens the meeting, **Then** each artifact has its own truthful state and a retry appears only when user action is safe and supported.
4. **Given** server custody is accepted, **When** local cleanup becomes eligible, **Then** GRAF preserves the configured custody/deletion policy and never removes the last usable copy merely because a request was attempted.

---

### User Story 4 - Review One Complete Meeting Workspace (Priority: P1)

As a meeting owner or authorized reviewer, I want playback, transcript,
speakers, outcomes, and actions in one meeting workspace, so that I can move
from a moment in audio to its words and results without switching tools.

**Why this priority**: Review is the primary value delivered after capture.

**Independent Test**: Open ready, processing, partial, failed, unauthorized,
deleting, and deleted meetings in browser and embedded desktop; verify the same
authorized state, synchronized playback/timestamps, and no leaked content.

**Acceptance Scenarios**:

1. **Given** playback and transcript are ready, **When** the reviewer plays or seeks, **Then** the active transcript turn and speaker context follow the same meeting time.
2. **Given** speaker attribution is uncertain, **When** the reviewer opens speaker tools, **Then** GRAF distinguishes confirmed, suggested, and unknown identities without inventing a person.
3. **Given** transcript is ready but summary is not, **When** the reviewer opens the meeting, **Then** transcript and playback remain available while summary shows its independent state.
4. **Given** the reviewer lacks access or deletion has begun, **When** the meeting is requested, **Then** audio, transcript, summary, participants, and private metadata are not disclosed.
5. **Given** the same meeting is opened in the browser and desktop cabinet, **When** state changes, **Then** both surfaces converge without making the embedded browser the authority for active capture.

---

### User Story 5 - Generate Notes From A Chosen Template (Priority: P1)

As a meeting owner, I want useful built-in summary templates and personal
templates, so that a project sync, one-to-one, client update, interview, or
general meeting produces an appropriate result without manual reformatting.

**Why this priority**: The supplied reference specifically calls for a fast
template selector and custom templates, and notes are a core post-meeting job.

**Independent Test**: Select a built-in template, create and edit a personal
template, set a default, apply a per-meeting override, regenerate a summary,
and inspect revision and sharing behavior.

**Acceptance Scenarios**:

1. **Given** a transcript-backed meeting, **When** the owner opens the summary selector, **Then** GRAF shows `Авто`, at most four recent/recommended formats, and `Все форматы`, while create/manage actions remain in Settings.
2. **Given** no override exists, **When** summary processing begins, **Then** the allowed default template is used and its identity is visible on the meeting.
3. **Given** a different template is selected, **When** GRAF generates a candidate, **Then** the accepted notes remain visible/current until the candidate succeeds and the owner explicitly chooses `Использовать`.
4. **Given** a built-in template is selected for customization, **When** the owner edits it, **Then** GRAF creates a personal copy and does not mutate the built-in definition.
5. **Given** a shared meeting uses a personal template, **When** a recipient views the notes, **Then** they see only the authorized rendered result, not the reusable template definition.
6. **Given** summary generation is interrupted by a worker restart or transient provider outage, **When** processing resumes, **Then** the same candidate continues or reaches a bounded failure state without duplicate publication or loss of the accepted summary.
7. **Given** Langfuse telemetry export is unavailable but an exact promoted prompt/config snapshot is pinned, **When** a summary is generated, **Then** generation continues and its authoritative state remains in GRAF rather than depending on telemetry delivery.
8. **Given** a product owner promotes a compatible Langfuse prompt version that selects another approved LiteLLM model route or generation settings, **When** a new candidate is requested, **Then** the same product flow works without a GRAF code change while the exact prompt/config and actual provider/model provenance are recorded.
9. **Given** an operator starts prompt optimization, **When** GEPA finishes, **Then** it creates an evaluated candidate version and evidence without changing the protected `production` label until a human explicitly approves promotion.

---

### User Story 6 - Share The Minimum Necessary Content (Priority: P1)

As a meeting owner, I want to invite people or broaden access with clear
audience, content, and permission controls, so that recipients receive exactly
what I intended and access can be revoked.

**Why this priority**: Meeting audio and transcript are sensitive; a copied
link must never silently become public.

**Independent Test**: Complete the default invite-only, summary-only, view-only
flow without seeing a capability matrix; then deliberately expand content or an
allowed broader audience, revoke each grant, and exercise unauthorized,
expired, deleted, and copied-link access.

**Acceptance Scenarios**:

1. **Given** a private meeting, **When** Share opens, **Then** the owner and current grants are visible and the default new grant is invite-only, summary-only, view access.
2. **Given** the owner enters an email, **When** the identity cannot be safely matched or invited under workspace policy, **Then** GRAF explains the restriction without revealing whether an unrelated private account exists.
3. **Given** the owner selects workspace, team, or anyone-with-link access, **When** they save, **Then** the broader audience and exposed content are restated before activation and recorded as a policy change.
4. **Given** access is invite-only, **When** the owner needs a link, **Then** Copy link appears only for an existing recipient-bound grant and does not broaden access as a side effect.
5. **Given** a grant is revoked or a meeting begins deletion, **When** the recipient reopens or refreshes, **Then** access is blocked immediately within GRAF-controlled systems.

---

### User Story 7 - Export Or Delete With Lifecycle Truth (Priority: P2)

As a meeting owner, I want discoverable export and deletion actions that obey
the same authorization and lifecycle rules as review, so that I can take data
out or remove it without misleading promises.

**Why this priority**: These are necessary completion actions, but the dedicated
canonical transcript/summary export slice remains the source of truth for
format behavior.

**Independent Test**: Open export and delete from the meeting workspace as
owner, permitted viewer, denied user, and during processing/deletion; verify
artifact-specific availability, revision truth, audit metadata, and post-egress
copy.

**Acceptance Scenarios**:

1. **Given** an artifact and export format are available under the dedicated export contract, **When** the owner selects Export, **Then** the meeting workspace presents the canonical options and does not implement a parallel exporter.
2. **Given** a recipient may view but not export, **When** they open actions, **Then** export is absent or disabled with a policy reason and no direct egress path is exposed.
3. **Given** deletion is requested, **When** the owner confirms the named meeting and scope, **Then** access blocks immediately, progress remains visible, normal GRAF meeting artifacts are purged, and dependency/backup limits are stated truthfully.
4. **Given** deletion copy is shown, **When** the owner reviews the scope, **Then** GRAF explicitly states that the retained plaintext Generation Call ledger, Langfuse observations, and Temporal History remain for observability and does not present them as failed purge artifacts.

---

### User Story 8 - Use The Workflow Accessibly In Russian (Priority: P2)

As a keyboard, screen-reader, reduced-motion, or narrow-window user, I want the
recording workflow to remain operable and understandable, so that safety and
meeting value do not depend on precise pointer use or English technical terms.

**Why this priority**: Accessibility is part of safe recording control and the
existing product baseline is Russian-first.

**Independent Test**: Complete readiness, start, pause/resume/stop, template
selection, sharing, export entry, and deletion using keyboard and assistive
technology in desktop, browser, and embedded layouts.

**Acceptance Scenarios**:

1. **Given** a modal or popover opens, **When** keyboard navigation begins, **Then** focus enters a meaningful control, stays within a modal, closes with Escape when safe, and returns to the opener.
2. **Given** recording status changes, **When** assistive technology is active, **Then** the status and available safety actions are announced without repeating elapsed time continuously.
3. **Given** color, animation, or sound is unavailable, **When** state changes, **Then** text, iconography, and control labels still communicate the state.
4. **Given** a supported narrow layout, **When** Share or Templates opens, **Then** all fields, scope warnings, and primary actions remain visible without horizontal scrolling.

### Edge Cases

- The user starts just as a meeting-detection prompt expires or a calendar event changes.
- Start is requested twice from different visible controls, or another local recording is active.
- Microphone permission is granted while system-audio permission remains denied, or vice versa.
- A selected input device disappears, the default device changes, or the machine sleeps during capture.
- System audio becomes silent while the microphone remains active; silence alone does not prove a broken source.
- Pause, Resume, and Stop arrive in rapid or repeated order.
- The app crashes during capture, finalization, upload, or local cleanup.
- A recording reaches the configured maximum duration or available local storage becomes unsafe.
- The network flaps or authentication expires during a resumable upload.
- A duplicate finalize/upload request arrives after the server has accepted the meeting.
- Playback is ready while transcript or summary is partial, failed, or reprocessing.
- Transcript text exists without confident diarization or speaker identity.
- A summary template is deleted, disabled, or edited after a meeting pinned it.
- Regeneration finishes after the owner has changed or shared an older summary revision.
- The same generation request is delivered more than once after a timeout or worker restart.
- A format-specific Langfuse prompt/config changes while an older candidate is queued or retried.
- The selected Langfuse model route is missing, disabled, remapped in LiteLLM,
  or returns a model that does not honor the pinned strict JSON schema.
- Langfuse is unavailable on a cold worker with no verified last-known-good
  promoted snapshot; AI generation must wait without blocking recording or
  transcription and without inventing code-owned model defaults.
- A GEPA run is interrupted, resumed, produces a lower-quality candidate,
  overfits its development split, or finishes after the source production
  prompt has changed.
- The orchestration or tracing dependency becomes unavailable before dispatch, during generation, or after the candidate is stored.
- A custom template contains unsafe markup, excessive instructions, or an unsupported block.
- The owner invites themselves, duplicates a grant, pastes several addresses, or uses mixed-case/whitespace variants.
- A team/workspace membership changes after a broad audience grant is created.
- Anyone-with-link is disabled by policy, expires, is rotated, or is revoked while a recipient page is open.
- The same user receives access through more than one grant; effective access is deterministic.
- A summary-only viewer follows a transcript, playback, participant, export, or private-template URL directly.
- Export begins just before deletion, permission revocation, or result revision change.
- Deletion races with upload, processing, summary regeneration, sharing, and export generation.
- Browser and embedded desktop tabs show stale states after a lifecycle transition.
- Private meeting content appears in an error, analytics event, log, screenshot, diagnostic bundle, or committed evidence; this is always a failure.

## Requirements

### Functional Requirements

#### Capture readiness and control

- **FR-001**: GRAF MUST expose microphone and system-audio readiness before a recording starts.
- **FR-002**: GRAF MUST keep manual Start available whenever capture prerequisites and policy allow it.
- **FR-003**: Meeting detection MUST be detect-and-ask by default for a target
  without a persisted target-scoped rule. For a verified native target, Feature
  124 MUST show the visible eight-second countdown with immediate start, skip,
  and per-target opt-in, and MUST start only after countdown expiry or an
  explicit user action; it MUST never start for arbitrary or unapproved audio.
- **FR-004**: Recording start MUST be idempotent and MUST NOT create two simultaneous local recordings from repeated controls.
- **FR-005**: Active capture MUST show textual state, elapsed time, Pause, and one-action Stop locally; healthy source detail MUST stay compact and expand only on request or failure.
- **FR-006**: Pause MUST suppress product-owned meeting-content capture for both sources and MUST record a privacy interval without fabricated audio or speech.
- **FR-007**: Resume MUST continue the same meeting identity and timeline.
- **FR-008**: Stop MUST remain available from the main app and menu-bar surface while active or paused.
- **FR-009**: Permission, device, source, and policy failures MUST fail closed with a specific recovery action and no false ready/recording claim.
- **FR-010**: GRAF MUST preserve truthful degraded-source state when only part of the expected meeting audio is available.

#### Local custody and processing lifecycle

- **FR-011**: Stopping a recording MUST produce one durable local meeting identity before optional network processing can be considered successful.
- **FR-012**: Capture, finalization, local custody, upload, transcription, playback, summary, and deletion MUST remain distinct internal states, while the normal UI MUST collapse them into one current human status and reveal details only when they change an available action.
- **FR-013**: Upload and finalization retries MUST be idempotent and MUST NOT create duplicate meetings or duplicate processing jobs.
- **FR-014**: Offline capture MUST remain available when local safety prerequisites pass and MUST identify deferred synchronization.
- **FR-015**: Unexpected exit recovery MUST prefer finalizing or preserving recoverable material over silent deletion.
- **FR-016**: Local cleanup MUST NOT remove the last usable copy before configured custody and deletion conditions are satisfied.
- **FR-017**: A failure in one derived artifact MUST NOT hide independently ready artifacts.
- **FR-018**: User-triggered retry MUST appear only for safe, supported recovery paths; automatic work MUST not be presented as a required repair button.

#### Meeting review workspace

- **FR-019**: GRAF MUST provide one authorized meeting workspace with exactly two primary content tabs (`Итоги`, `Расшифровка`), a persistent player, Share, and a More menu for secondary actions; speakers, access, export, and deletion MUST be contextual flows rather than permanent panels.
- **FR-020**: Playback position, transcript timestamps, active turn, and speaker context MUST use the same meeting timeline.
- **FR-021**: Speaker attribution MUST distinguish confirmed, suggested, unconfirmed, and unknown identities.
- **FR-022**: Meeting content MUST remain absent from list responses, unauthorized responses, diagnostics, and metadata-only operational evidence.
- **FR-023**: Browser and embedded desktop review MUST use the same server-owned authorization and meeting lifecycle truth.
- **FR-024**: Embedded review MUST NOT own or obscure active capture controls.
- **FR-025**: Processing, partial, failed, deleting, deleted, and unavailable states MUST be truthful and artifact-specific, but MUST NOT be rendered as a permanent lifecycle stepper or multi-panel dashboard.

#### Summary templates and revisions

- **FR-026**: GRAF MUST use an allowed `Авто` default and provide a concise per-meeting format selector with at most four recommended/recent formats plus `Все форматы`; personal-format creation and management MUST live in Settings.
- **FR-027**: GRAF MUST provide built-in templates for general summary, outline, meeting minutes, project sync, weekly team meeting, one-to-one, client update, interview, and sales/discovery use cases using original GRAF naming and structure.
- **FR-028**: Workspace owners MUST be able to choose an allowed default template; meeting owners MUST be able to select a per-meeting override.
- **FR-029**: Users MUST be able to create, edit, duplicate, archive, and delete personal custom templates.
- **FR-030**: Built-in templates MUST be immutable; customization MUST create a personal copy.
- **FR-031**: A template MUST define a bounded ordered set of supported sections, output language, and detail level, and MUST reject unsafe or unsupported content.
- **FR-032**: Every generated summary MUST record template identity/version, source transcript/result revision, exact format-specific Langfuse prompt/config version and hash, output schema version, selected LiteLLM model route, and actual provider/model identity when returned.
- **FR-033**: Regeneration MUST create a candidate revision and MUST NOT silently overwrite accepted notes or owner edits.
- **FR-033a**: The first usable transcript MAY trigger one policy-owned `Авто`
  generation. Subsequent format changes and regenerations MUST require an
  explicit owner action; automatic retries MUST reuse the same candidate and
  durable workflow identity and MUST never replace an accepted pointer.
- **FR-033b**: A candidate MUST pin its source transcript/result revision,
  template version, exact Langfuse prompt/config snapshot, schema, and request
  actor. A source revision change MUST prevent stale candidate publication or
  acceptance while preserving the accepted pointer; a new candidate requires
  an explicit owner request.
- **FR-033c**: Candidate state MUST be recoverable from the server after reload,
  a second tab, or a new owner device. Browser storage MAY cache a poll URL but
  MUST NOT be the only record. Owners MUST be able to preview a ready candidate
  before acceptance; reject/dismiss MUST retain the revision for history.
- **FR-033d**: User-visible candidate failures MUST expose a bounded reason,
  retryability, and next action. Only transient dependency/worker failures MAY
  offer retry; invalid structured output, stale source/template, deletion,
  authorization, configuration, and ambiguous provider outcomes MUST NOT offer
  a blind retry.
- **FR-034**: A format change MUST generate a candidate while the accepted summary stays visible/current; only after the candidate succeeds may the owner choose `Использовать`, and dismissing or failing the candidate MUST preserve the accepted revision without an up-front replace/preserve question.
- **FR-035**: Sharing a rendered summary MUST NOT grant access to a personal reusable template definition.

#### Sharing and collaboration

- **FR-036**: Sharing MUST model audience, exposed content, and allowed actions independently in policy, while the UI MUST sequence those decisions through progressive disclosure rather than present a capability matrix.
- **FR-037**: The default share configuration MUST be invite-only, summary-only, view access.
- **FR-038**: Supported audiences MUST be invited identities, active workspace, and anyone-with-link when workspace policy permits. Selected-team access MUST remain absent and fail-closed until GRAF has a canonical same-workspace team directory and membership authority; Feature 121 MUST NOT invent team UUIDs or infer teams from labels.
- **FR-039**: Supported content scopes MUST distinguish summary-only from the full authorized meeting bundle.
- **FR-040**: Shared access MUST be view-only in the normal flow; download/export MUST remain owner actions and any later recipient-download capability MUST be an explicit advanced per-recipient permission bounded by policy and artifact availability.
- **FR-041**: The first Share surface MUST show a person/email field, `Пригласить`, current viewers with revoke actions, and one collapsed `Что увидят: только итоги` row; role, public-link, workspace/team, and capability detail MUST remain hidden until relevant.
- **FR-042**: Copy link MUST preserve the current access policy and MUST NOT broaden access; invite-only Copy link MUST appear only for an existing recipient-bound grant, and public Copy link MUST appear only after explicit link access is enabled.
- **FR-043**: Broader-than-invite-only access MUST require an explicit scope review before activation.
- **FR-044**: Link grants MUST support rotation, optional expiration, revocation, and abuse-resistant access checks.
- **FR-045**: Revocation, membership loss, expiration, and deletion MUST block subsequent GRAF-controlled access without requiring sign-out.
- **FR-046**: Authorization MUST prevent summary-only viewers from reaching transcript, playback, participant, export, or private-template routes directly.
- **FR-047**: Share notifications and errors MUST not reveal the existence of unrelated private accounts or meetings.
- **FR-048**: Sharing policy changes and access outcomes MUST produce metadata-only audit evidence.

#### Export, deletion, and lifecycle integration

- **FR-049**: The meeting workspace MUST consume the dedicated canonical transcript/summary export contract and MUST NOT create a second export source of truth.
- **FR-050**: Export availability MUST follow artifact readiness, selected revision, content scope, role, and workspace policy.
- **FR-051**: Existing server-mediated recording downloads MUST remain distinct from transcript/summary export and from review playback permission.
- **FR-052**: Whole-meeting deletion MUST immediately block new access, sharing, playback, export, inference, candidate publication, and acceptance, and MUST cancel pending durable work without deleting retained observability copies.
- **FR-053**: Deletion status MUST distinguish normal GRAF meeting-artifact completion from backup expiry, external/dependent copies, and the intentionally retained plaintext Generation Call ledger, Langfuse observations, and Temporal History.
- **FR-054**: Export and deletion races MUST resolve deterministically in favor of deletion once deletion begins.

#### Security, privacy, accessibility, and operations

- **FR-055**: The desktop app MUST NOT call MediaScribe directly or store MediaScribe credentials.
- **FR-056**: Ordinary product logs, analytics, screenshots, audit, diagnostics, and committed evidence MUST exclude raw audio, transcript/summary text, credentials, tokens, signed-URL secrets, passwords, and private meeting content. Langfuse observations and Temporal History are the explicit internal-MVP exceptions defined in FR-071 and FR-088: Langfuse retains complete plaintext meeting/model content, while Temporal History is required to retain the complete plaintext canonical transcript and may contain other execution content.
- **FR-057**: All meeting, template, share, revision, export, and deletion data MUST remain user/workspace scoped and protected by tenant isolation. Prompt-optimization control/provenance MUST instead remain deployment-global, synthetic-only, and accessible exclusively to the least-privilege deployment-operator role defined in FR-082.
- **FR-058**: Recording, sharing, regeneration, export, and deletion actions MUST state their privacy consequences before irreversible or broadened effects; deletion copy MUST disclose retained observability content without adding a settings toggle.
- **FR-059**: Every interactive control MUST have a Russian accessible name, visible keyboard focus, logical tab order, and non-color state cue.
- **FR-060**: Modal dialogs MUST trap focus, support safe Escape close, and return focus to their opener.
- **FR-061**: Status changes MUST be announced without continuously announcing elapsed recording time.
- **FR-062**: The workflow MUST remain usable in supported narrow desktop and responsive browser layouts without hiding Stop, scope warnings, or primary actions.
- **FR-063**: New functionality MUST reuse the current GRAF design system and clean-room visual baseline rather than introduce a parallel UI kit.
- **FR-064**: Every normal state MUST have at most one visually primary action; confirmation MUST be reserved for broader sharing, deletion, or another irreversible consequence.
- **FR-065**: Plain Escape MUST close the active popover/dialog when safe and MUST NOT stop an active recording.
- **FR-066**: Feature 121 MUST add no new global navigation destination; recording remains a persistent native layer, while post-meeting work stays within existing Meetings and Settings surfaces.
- **FR-067**: Each built-in outcome format, including `Авто`, MUST resolve its own promoted self-contained Langfuse prompt/config; `Авто` MUST generate a conservative general outcome without a separate classifier, and personal structured templates MUST use one bounded custom prompt. Every prompt MUST treat transcript variables as untrusted data, and every result MUST pass the exact pinned strict response schema plus local validation before candidate storage.
- **FR-068**: A committed generation request MUST survive process restarts and transient inference/prompt dependency outages and use deterministic idempotency. Observability delivery MUST NOT add a user-visible state or toggle; once a candidate is locally validated and stored, the ordinary ready/failed outcome state applies and any previously accepted result remains visible.
- **FR-069**: Automatic retry MUST be limited to transient failures; invalid input, authorization, deletion, stale source/template, configuration, and structured-output failures MUST terminate with a bounded non-sensitive reason.
- **FR-070**: Langfuse observability MUST be enabled for AI generation from the first shipped version. After a completed response is retained, export MUST remain durably `pending` and retry with deterministic trace/observation identity until Langfuse confirms it, without repeating the model call; this delivery MUST NOT block a locally validated candidate, recording, transcription, or acceptance. Langfuse MUST NOT become the authority for meeting, workflow, acceptance, or deletion truth. Prompt/config availability remains separate: an exact verified promoted snapshot may cover control-plane outage, but no code-owned model default may substitute for it.
- **FR-071**: Every completed outcome model call whose response reaches GRAF MUST create exactly one Langfuse `generation` observation containing the exact compiled logical model request, complete pinned canonical transcript revision, raw model response, and locally validated result. Related AI-workflow observations MAY contain the same plaintext meeting/model content when useful for debugging. GRAF MUST NOT encrypt, redact, mask, truncate, or delete this observability content. A call that may have left GRAF but crashes before response persistence MUST remain `ambiguous`; missing content MUST NOT be fabricated. Raw audio and runtime credentials MUST NOT be deliberately attached as observability attributes, but credential-like text inside the canonical transcript MUST remain unchanged without a masking pipeline.
- **FR-072**: Work that can outlive a request, calls a retryable external dependency, or must survive process restart MUST use the existing durable orchestration boundary; synchronous authorization, validation, reads, atomic database mutations, and accepted-summary pointer changes MUST remain direct application transactions.
- **FR-073**: Deletion MUST be checked before new external inference and before candidate publication, MUST prevent later acceptance, and MUST request cancellation of pending durable work without relying on cancellation as the deletion authority. Cancellation applies to work before model egress/publication; once a completed Generation Call is retained, its sole observability publisher MUST continue deterministic Langfuse delivery until confirmed because retained observability is not a deletion target.
- **FR-074**: Model inference egress MUST use one operator-approved HTTPS LiteLLM base URL; the approved Langfuse generation observation is a separate observability egress and MUST NOT execute inference. The selected LiteLLM model route MUST come from the exact pinned Langfuse Prompt Config, initially `gpt-5.6-luna`; gateway endpoints, credentials, provider secrets, and upstream routes MUST NOT be stored in Langfuse or prompt variables.
- **FR-075**: A promoted Langfuse prompt version MUST be able to change the selected approved model route and all allowlisted request-level generation settings without API, Temporal workflow, or application-code changes. LiteLLM MAY independently remap that route to another approved upstream provider; each generation MUST record selected route plus actual provider/model provenance when returned.
- **FR-076**: GRAF and LiteLLM client-side retries MUST be disabled for the model call so Temporal owns durable retry; every response MUST pass the pinned strict JSON schema and local validation before candidate publication.
- **FR-077**: The first Temporal activity MUST resolve the selected format's explicit `production` label or a verified last-known-good export of that same promoted version, validate a strict allowlist and safety/budget ceilings, and atomically persist the exact self-contained uncompiled prompt/config snapshot, version, and canonical hash. Later label, config, route, or worker changes MUST NOT mutate the queued candidate.
- **FR-078**: Internal production Langfuse egress MUST use the configured `https://cloud.langfuse.com` private project and environment. The project MUST NOT use public trace publishing, and access MUST remain limited by operator-managed Langfuse project roles. GRAF MUST retain trace/observation IDs for correlation but MUST NOT implement trace deletion, content retention enforcement, content masking, or a tracing kill-switch in Feature 121; retention and access are operator-managed Langfuse settings.
- **FR-079**: Temporal and Langfuse MUST share W3C TraceContext through the stable Temporal Python SDK tracing interceptor. One deterministic context MUST correlate prompt resolution, plaintext transcript snapshotting, the model-call generation, validation, persistence, and export. Every real call MUST carry the Temporal activity attempt; replay, export retry, and idempotent no-call paths MUST NOT create a second generation/cost observation. Langfuse v4 observation attributes MUST propagate `environment`, `user_id`, `session_id`, tags, prompt version, full relevant input/output content, and selected/actual model provenance when returned. Token usage MUST be the exact normalized LiteLLM/provider value when returned and otherwise `unknown`; cost MUST use an exact returned value or Langfuse's configured model-price calculation and otherwise remain `unknown`, never fabricated.
- **FR-080**: Langfuse Prompt Config MUST follow one of the exact closed profiles in `contracts/recording-workflow-contract.md`: outcome, GEPA reflection, or metric-specific judge. Unknown fields, network destinations, credentials, headers, tools, retry/fallback policy, provider secrets, remote schema references, and arbitrary passthrough MUST be rejected; GRAF MUST explicitly project validated fields into the LiteLLM request. Application safety/budget ceilings constrain but do not supply model defaults.
- **FR-081**: Prompt improvement MUST use `gepa==0.1.4` as an optional offline evaluation dependency, invoke the same zero-client-retry LiteLLM execution and structured-validation path as production, and MUST NOT add DSPy or a second production inference stack. GEPA reflection and LLM quality judging MUST each use an exact promoted Langfuse prompt/config version rather than a code-owned model or settings.
- **FR-082**: Deployment-operator-triggered prompt optimization MUST run outside ordinary cabinet/workspace APIs as a durable deployment-scoped `PromptOptimizationWorkflow` with pinned production prompt/config, immutable synthetic train/development/held-out dataset manifests, shared integrity-checked checkpoints, an immutable absolute deadline, resumable GEPA state, heartbeats, and durable cost/token/call reservations. Workspace administrators MUST NOT be able to start, approve, promote, or roll back this project-global control plane.
- **FR-083**: After held-out gates pass, GEPA MAY publish an exact numeric candidate prompt version with no manually assigned candidate/staging/production label; Langfuse-managed `latest` MUST be ignored. Candidate config MUST be re-read and match the source config's canonical JSON SHA-256. Production promotion MUST be serialized per prompt, recheck the recorded expected source before update, clear cache, and post-verify the resulting label; this is conflict detection, not a native compare-and-swap guarantee. Protected `production` labels plus a sole deployment-service mutation credential/path are a rollout gate. If that capability is unavailable, automated promotion MUST remain disabled. Promotion also requires hard schema/privacy gates, calibrated held-out quality, cost/latency ceilings, deployment-operator approval, and a rollback version; no optimizer or judge may auto-promote.
- **FR-084**: Feature 121 prompt optimization MUST use synthetic, versioned, owner-controlled dataset manifests only; real meeting-derived optimization remains out of scope. Langfuse observations and Temporal History MAY contain the complete plaintext synthetic inputs, outputs, reflection, judge feedback, and optimizer state needed to debug each actual call and run.
- **FR-085**: The optimizer control plane MUST pin `graf/prompt-optimization/reflection` plus the three independently calibrated judge prompts `graf/evaluation/meeting-outcome-faithfulness`, `graf/evaluation/meeting-outcome-action-items`, and `graf/evaluation/meeting-outcome-completeness`. Their exact prompt versions, config hashes, model routes, schemas, and evaluator versions MUST be recorded for each run. GEPA may change only outcome prompt text; candidate model/settings/schema must match the source canonical config hash after exact-version re-read.
- **FR-086**: Each prompt-optimization execution MUST have one deterministic Langfuse trace ending at promotion, rejection, or expiry; its workflow, task, reflection, judge, and result observations MAY contain complete plaintext synthetic content. A later rollback MUST use a separate linked trace. An application-owned fenced call ledger MUST reuse durable-success calls across resume. Expired in-flight reservations become conservatively charged `ambiguous`; GRAF MUST NOT claim exactly-once provider egress. Callbacks MUST be non-throwing and MUST NOT control budget, cancellation, or durability. Replay and approval wait MUST NOT create a model-call observation.
- **FR-087**: Reflection and judge prompt versions MUST pass their own control-prompt deployment gates before receiving `production`. Reflection requires exact GEPA 0.1.4 placeholders/delimiters, native-parser smoke, variable/schema preservation, anti-copy regression, and bounded-cost smoke. Each judge requires human-labelled synthetic calibration, invalid-output reporting, metric agreement thresholds, and deployment-operator approval. Existing optimization runs remain pinned to prior exact versions.
- **FR-088**: Outcome-generation Temporal History MUST retain the complete pinned canonical transcript in plaintext. Feature 121 MUST NOT add a transcript PayloadCodec, application-layer encryption, redaction, masking, truncation, or GRAF-managed History deletion. Workflow/activity payloads and failure details MAY contain full content when required for execution and debugging; Search Attributes and Memo MUST remain bounded operational indexes rather than transcript storage.
- **FR-089**: Snapshot activities MUST split the complete canonical transcript into deterministic plaintext UTF-8 chunks no larger than 192 KiB before serialization, then reduce a chunk further when JSON escaping or envelope overhead would make its canonical serialized payload exceed 256 KiB. The complete canonical transcript/snapshot MUST stay at or below 8 MiB, and the execution MUST stay below Temporal's 2 MiB single-payload limit, 4 MiB transaction limit, and 10 MiB practical History target. Oversized input MUST fail before model generation with an explicit unsupported-size reason and no silent omission.
- **FR-090**: Meeting deletion MUST cancel pending outcome work before a candidate can be published or accepted, but MUST NOT cancel deterministic Langfuse delivery for an already completed retained Generation Call and MUST NOT delete closed or cancelled Temporal workflow histories. Deletion reporting MUST state that full plaintext Temporal History and Langfuse observations remain under operator-managed platform retention and MUST NOT present those retained copies as failed GRAF deletion artifacts.
- **FR-091**: Before a completed model response is acknowledged, GRAF MUST atomically store one plaintext `Generation Call` ledger row containing the exact logical request, complete transcript, raw response, validated result, original timestamps, and deterministic observation identity. Genuine provider retries create separate call rows; Langfuse export retry reuses the same row/observation and never repeats inference. The row MUST remain retained for debugging and MUST NOT be cleared or deleted by meeting deletion.
- **FR-092**: Transcript chunks MUST use deterministic candidate/source/snapshot/chunk identity and one shared assembler MUST validate complete count/order, duplicates, contiguous indices, UTF-8 validity, and final SHA-256 before model execution. No encrypted or alternate transcript representation may replace the complete plaintext snapshot in Temporal History.

### Key Entities

- **Recording Session**: One local audio capture lifecycle with source readiness, active/paused intervals, finalization, custody, and recovery truth.
- **Meeting**: The durable owner/workspace-scoped identity connecting capture, artifacts, results, review, access, export, and deletion.
- **Artifact Readiness**: Independent state for local package, upload, transcript, playback, summary, and deletion-sensitive derivatives.
- **Transcript Revision**: A selected provider-neutral transcript/speaker-turn result used by review, summaries, and export.
- **Summary Template**: A built-in or personal versioned definition containing a bounded set of supported summary sections.
- **Summary Revision**: A candidate or accepted rendered result pinned to a template version and transcript revision.
- **Share Grant**: An audience grant with content scope, role, lifecycle, and optional link expiry/rotation state.
- **Export Request**: A revision-pinned, policy-checked egress action owned by the dedicated export contract.
- **Deletion Request**: The whole-meeting lifecycle operation that wins races and records controlled versus external limits.
- **Metadata Audit Event**: Content-free evidence of sensitive state transitions and access/egress outcomes.
- **Generation Attempt**: One durable, idempotent attempt to create a candidate from pinned source, template, prompt-recipe, and schema versions with bounded model retry, a complete plaintext Temporal transcript snapshot, and a deterministically delivered Langfuse generation observation.
- **Generation Call**: One retained plaintext provider-call ledger row with deterministic call/observation identity, original timestamps, exact logical request, complete transcript, available raw response/validated result, and pending/confirmed/not-required delivery state.
- **Temporal Workflow Run**: Temporal's workflow/run identity used to correlate, cancel, and inspect outcome execution; its History is retained under operator-managed retention without a separate deletion ledger.
- **Prompt Config Snapshot**: The immutable validated prompt, model settings,
  response schema, schema/adapter versions, and hash resolved from one promoted
  Langfuse version for a generation request.
- **Prompt Optimization Run**: One deployment-scoped durable GEPA run pinned to a source prompt,
  immutable synthetic dataset splits, budgets, exact candidate version, aggregate evaluation,
  approval state, and rollback target; its synthetic content may be fully
  observable in Temporal History and Langfuse.

## Success Criteria

### Measurable Outcomes

- **SC-001**: At least 9 of 10 first-time users can identify both capture sources and deliberately start a ready recording in under 30 seconds.
- **SC-002**: In every tested active or paused screen, Stop is reachable with one action and by keyboard in at most three focus moves from the current control.
- **SC-003**: Repeated Start, Stop, finalize, and upload requests produce exactly one meeting identity and one accepted processing lifecycle in all race scenarios.
- **SC-004**: After a simulated crash at each capture/finalize/upload boundary, every durable test recording is recovered/finalized or preserved with truthful recovery state; none disappears silently.
- **SC-005**: An owner can move from a transcript turn to matching playback and back with no visible timeline divergence greater than one second.
- **SC-006**: An owner can choose or create a template, generate a candidate summary, and accept or preserve it without losing the prior accepted revision.
- **SC-007**: An owner can invite a viewer to summary-only access in under 20 seconds without encountering a role/capability matrix, while no Copy link action broadens access.
- **SC-008**: Revocation, expiry, membership removal, or deletion blocks every protected meeting-content route on the next request.
- **SC-009**: Browser and embedded desktop render the same artifact/access/lifecycle state for 100% of the required matrix while active capture stays locally controlled.
- **SC-010**: Keyboard-only and screen-reader validation completes Start, Pause, Resume, Stop, template selection, Share, export entry, and delete confirmation with no focus escape, unlabeled control, or color-only state.
- **SC-011**: Forbidden-content scans find zero meeting content in ordinary product logs, analytics, screenshots, audit, diagnostics, and committed evidence; exact complete content is present in the specified Langfuse observations, Temporal History, and retained Generation Call ledger.
- **SC-012**: Focused checks and canonical local CI pass before implementation is offered for commit or PR; production and release claims remain separately gated.
- **SC-013**: In every required prototype state, at least 9 of 10 evaluators can identify what is happening, whether the recording is safe, whether action is required, and the single next action within three seconds.
- **SC-014**: In restart, duplicate-dispatch, timeout, rate-limit, telemetry-outage, and deletion-race tests, each request produces at most one publishable candidate and never changes the accepted summary automatically; prompt-control outage succeeds only from the exact verified promoted snapshot or remains in a truthful bounded dependency wait.
- **SC-015**: A synthetic trace proves the full canonical transcript, exact compiled logical request, raw response, and validated result are readable in Langfuse. A raw Temporal History export and the retained Generation Call row each reconstruct the same complete plaintext transcript byte-for-byte, including a credential-like spoken marker, while the Generation Call also retains the exact model request/response/result without masking or truncation.
- **SC-016**: Promoting a compatible Langfuse version that changes the selected route from `gpt-5.6-luna` and/or its generation settings requires zero GRAF code or workflow-schema changes; independently remapping a route in LiteLLM also requires no GRAF change, and both cases retain exact config plus actual provenance.
- **SC-017**: Configuration and smoke checks prove the configured private Langfuse destination/environment with no public trace publishing, current SDK-compatible observation shape, prompt linkage, selected/actual model provenance, exact-or-unknown token usage/cost, deterministic Temporal-to-Langfuse correlation, complete plaintext transcript in Temporal History, payload ceilings, fail-open durable trace delivery, and truthful retained-observability deletion copy before AI outcome rollout.
- **SC-018**: A synthetic prompt-optimization exercise survives mid-iteration failure and resume on a second worker, emits no forbidden content, reuses durable-success model calls, conservatively accounts ambiguous calls, produces a rollbackable exact candidate, passes all hard gates and held-out comparisons before deployment-operator approval, and leaves the prior `production` label unchanged until serialized expected-source promotion.
- **SC-019**: Reflection or judge model/settings change without GRAF code/workflow-schema changes only after the control prompt's parser/preservation or human-labelled calibration gate and deployment-operator promotion; a subsequent synthetic run pins the new exact versions, produces one bounded optimization trace across restart/approval, and a later rollback produces a separate linked trace.

## Assumptions

- Russian dark desktop/browser UI remains the primary baseline, with responsive and light-theme parity rather than separate feature sets.
- Existing manual controls, Pause/Resume truth, local package, upload queue, processing, review/playback, speaker tools, outcomes, login-required sharing/downloads, deletion, and tenant isolation are reused.
- Feature `106-mixed-wav-recording` remains the source of truth for new-recording package and hardware acceptance; this feature does not weaken or duplicate it.
- Merged feature `120-transcript-export` in this synchronized baseline remains the source of truth for TXT, MD, CSV, XLSX, versioned JSON, and SRT behavior; its open representative-reviewer gate limits general-release claims but not contract composition.
- Feature `118-interactive-playback-timeline` remains the source of truth for playback/timeline behavior.
- Public links and external invitations are opt-in capabilities and remain blocked until policy, abuse, identity, delivery, and legal gates in this feature pass.
- A global cross-meeting task hub, transcript text editing, media trimming, screen video, bots, and live coaching are not required for the first independently shippable owner workflow.
- Summary generation remains transcript-backed and preserves not-found/not-inferable truth.
- The owner-controlled LiteLLM gateway is the sole model-inference boundary. Langfuse initially selects the private `gpt-5.6-luna` route; gateway credentials and the exact approved base URL are provisioned later through operator secret/config files before live smoke.
- Langfuse Cloud is the versioned prompt/model-settings authority and approved plaintext observability dependency, not the meeting, workflow, acceptance, or deletion source of truth. Internal production uses `https://cloud.langfuse.com`; GRAF pins an exact promoted snapshot and may cache only an integrity-checked export of that same version.
- The operator accepts the complete plaintext canonical transcript and any other execution/failure content that naturally enters Temporal Service for the internal MVP. The exact full model request/response/result is guaranteed in Langfuse and the retained Generation Call ledger rather than deliberately duplicated into Temporal History. Feature 121 adds no PayloadCodec, key ring, Codec endpoint, transcript redaction, or workflow-history deletion.
- "Important durable work" means bounded asynchronous external work that can outlive an HTTP request or needs restart-safe retry. It does not include ordinary reads, authorization checks, local capture control, or atomic database commands.

## Dependencies And Out Of Scope

### Dependencies

- Existing capabilities and readiness truth listed in `docs/current-product-status.md`.
- Accepted integration boundaries from features `030`, `017`, `018`, `049`, `106`, `118`, and merged `120`, subject to T002 branch sync/re-verification.
- Existing Temporal cluster/worker boundary, owner-controlled LiteLLM gateway, and Langfuse Cloud project, with runtime credentials provisioned only through ignored secret files or an operator secret store.

### Out Of Scope

- Bot participation, camera capture, screen-video capture, live transcription overlays, and real-time coaching.
- Reviving removed audio routing, virtual devices, or a second capture implementation.
- Claiming third-party meeting-app mute interception; product Pause/Resume remains the accepted privacy control.
- Generalized or unscoped policy-gated automatic recording; the verified,
  target-scoped workflow is owned by Feature 124 and is not removed by this
  historical Feature-121 boundary.
- A second app-level microphone mute control.
- Global action-item management across meetings.
- Collaborative comments and direct recipient editing of transcript, notes, or templates.
- Editing raw transcript text, trimming media, replacing source media, or reprocessing media revisions.
- Mobile and Windows clients.
- Production deployment, release publication, signed/notarized app distribution, or user-rollout claims in the planning/prototype phase.
