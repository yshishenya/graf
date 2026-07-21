# Feature Specification: MVP Loop Live Evidence

**Feature Branch**: `035-mvp-loop-live-evidence`

**Created**: 2026-06-16

**Status**: Implemented validation evidence; current claim remains pilot-blocked

**Input**: User description: "Continue toward MVP through the full SDD Spec Kit
cycle, verifying carefully against the reference desktop app and web product.
After 022, the next validation-only slice must prove whether the installed
desktop app, web owner review, backend readiness artifacts, forbidden-content
scans, and production user journey can support an MVP claim without expanding
feature behavior."

## Clarifications

### Session 2026-06-16

- Q: Are there any critical unresolved user choices before planning? → A: No;
  the slice is validation-only, uses `/Applications/2brain Rec.app` for desktop
  runtime evidence, permits safe fixture data when live private web evidence
  cannot be committed, and forbids stronger MVP/pilot claims while any P0/P1
  gap remains.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove Installed Desktop Capture Loop (Priority: P1)

As the product owner, I need evidence from the stable installed
`/Applications/2brain Rec.app` bundle that a real user can start, pause,
resume, stop, and review a local recording state with visible capture controls,
so that desktop evidence is tied to the same bundle path that has macOS
permissions.

**Why this priority**: The MVP begins with trustworthy local capture. Evidence
from a development bundle or synthetic-only run is not strong enough for a live
MVP loop claim.

**Independent Test**: Use only the installed `/Applications/2brain Rec.app`
bundle to perform a metadata-safe Record/Pause/Resume/Stop pass, capture
screenshots of each state, validate the latest artifact manifest, and record the
resulting evidence without private audio or transcript content.

**Acceptance Scenarios**:

1. **Given** the permissioned installed app is open from `/Applications`, **When**
   the owner starts recording, pauses, resumes, and stops, **Then** evidence
   captures visible active/paused/stopped states and the latest artifact
   validates with meeting-mute-truth metadata.
2. **Given** the installed app cannot produce an accepted local artifact, **When**
   the evidence pack is generated, **Then** the launch status remains blocked
   with the specific failing gate and no MVP readiness claim.

---

### User Story 2 - Prove Owner Web Review Loop (Priority: P1)

As the product owner, I need the web owner review surface to be checked against
the same live journey evidence so that meeting list/detail review, transcript
or placeholder truth, governance actions, and upload/review identity are
represented honestly in the readiness record.

**Why this priority**: A desktop recording alone is not the product MVP. The MVP
loop requires owner review surfaces and truthful notes/action availability or a
clear launch blocker.

**Independent Test**: Open the owner web/cabinet route with safe fixture or
live metadata-only evidence, capture list/detail/governance states, and update
the readiness evidence without private meeting content.

**Acceptance Scenarios**:

1. **Given** the owner review surface is available, **When** the reviewer opens
   meeting list and detail states, **Then** the evidence records which stages
   are ready, degraded, blocked, or deferred and why.
2. **Given** notes/action output is not available as a launchable capability,
   **When** the readiness report is updated, **Then** it keeps the notes/action
   stage truthful instead of implying generated notes exist.

---

### User Story 3 - Produce Decision-Ready MVP Claim (Priority: P1)

As a launch decision maker, I need a single metadata-safe readiness pack that
states exactly whether 2brain Rec is `mvp_loop_ready`, still `pilot_blocked`, or
only `infra_smoke_ready`, so that the next product move is based on current
proof rather than hopeful status text.

**Why this priority**: The user explicitly wants movement toward launch, not
another partial implementation that leaves the readiness claim ambiguous.

**Independent Test**: Generate the readiness report, launch gap register,
current status update, changelog entry, issue sync, and validation log from the
same evidence set; verify that any P0/P1 gap prevents MVP/pilot claims.

**Acceptance Scenarios**:

1. **Given** all live desktop/web/backend/policy gates pass, **When** the
   readiness pack is generated, **Then** it may claim `mvp_loop_ready` with
   traceable evidence for every required stage.
2. **Given** any P0/P1 gate remains missing or weak, **When** the readiness pack
   is generated, **Then** it must keep the strongest allowed claim bounded and
   list the blocker, owner area, evidence needed, and next action.

---

### User Story 4 - Preserve Clean-Room Reference Alignment (Priority: P2)

As the product owner, I need the live 2brain desktop/web surfaces compared
against the Krisp desktop/web reference lessons without copying protected
expression, so that the interface can move toward product quality while
remaining original.

**Why this priority**: Reference comparison guides quality, but the launch gate
must not introduce brand, copy, layout, or private-data similarity risk.

**Independent Test**: Produce a clean-room comparison note that records allowed
lessons, intentional differences, and brand-distance checks for the live
surfaces used in the readiness pack.

**Acceptance Scenarios**:

1. **Given** reference observations exist, **When** the comparison note is
   written, **Then** it describes generic product lessons and forbids copied
   Krisp copy, colors, layout, icons, private screenshots, or account data.

### Edge Cases

- The installed desktop bundle is not the latest build or is launched from the
  wrong path.
- macOS microphone or Screen/System Audio permission is stale, denied, or bound
  to a different bundle path.
- The recording artifact validates but contains degraded incoming/system audio
  due to no active meeting source.
- Web owner review requires authentication, has no uploaded live meeting
  identity, or can only be demonstrated with safe fixture data.
- Existing readiness reports still contain stale blockers already resolved by
  022.
- Evidence scans find private local paths, private emails, raw audio,
  transcript text, credentials, signed URLs, or private reference screenshots.
- The clean-room reference review identifies a surface that feels too close to
  the reference product.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The evidence pack MUST launch and verify the installed
  `/Applications/2brain Rec.app` bundle as the desktop runtime source.
- **FR-002**: The evidence pack MUST capture metadata-safe desktop screenshots
  for idle or ready, active recording, paused recording, resumed recording, and
  stopped/list states, unless a state is impossible; impossible states MUST be
  recorded as blockers.
- **FR-003**: The evidence pack MUST validate the latest local artifact manifest
  after the desktop pass and record meeting-mute-truth, privacy segment,
  local-mic, incoming/system-audio, saved/degraded/failed, and no-content-scan
  truth.
- **FR-004**: The evidence pack MUST cover owner web review list/detail and
  governance states with either safe live metadata or clearly labeled fixture
  evidence.
- **FR-005**: The readiness report MUST reconcile desktop, web, backend,
  policy/lifecycle, clean-room reference, and forbidden-content evidence into a
  single claim summary.
- **FR-006**: The readiness report MUST NOT claim `mvp_loop_ready`,
  `internal_pilot_candidate`, `user_rollout_ready`, or `production_ready` while
  any P0/P1 launch gap lacks strong evidence.
- **FR-007**: The launch gap register MUST list each remaining blocker with
  severity, affected journey, current evidence, missing evidence, owner area,
  and next action.
- **FR-008**: The feature MUST update `docs/current-product-status.md` and
  `CHANGELOG.md` to reflect the strongest proven claim and the next product
  slice.
- **FR-009**: The feature MUST include a validation log with command evidence
  for desktop artifact validation, server readiness tests, relevant macOS tests,
  forbidden-content scans, and app process path checks.
- **FR-010**: The feature MUST verify that all committed evidence is safe to
  store in git and contains no raw audio, transcript text, private meeting
  content, private account identifiers, private emails, credentials, tokens,
  signed URLs, live private local filesystem paths, or private reference
  screenshots.
- **FR-011**: The feature MUST preserve clean-room reference rules by recording
  allowed product lessons and intentional differences without copying Krisp
  expression.
- **FR-012**: The feature MUST NOT implement new capture, transcription,
  notes/action generation, sharing, deletion, installer, or production
  deployment behavior; any missing capability MUST remain a launch gap or a
  separately specified follow-up slice.
- **FR-013**: The evidence pack MUST be reproducible enough that another
  reviewer can identify the app build, route, command, screenshot, artifact, and
  readiness record used for each claim.

### Key Entities *(include if feature involves data)*

- **Live Evidence Pack**: Metadata-safe bundle of screenshots, command results,
  readiness JSON/Markdown, gap register, validation log, and reference notes.
- **MVP Loop Stage**: A product journey segment such as local capture, upload,
  processing, web review, notes/actions, access/egress, deletion, or desktop
  embedding with status, evidence, and claim impact.
- **Launch Gap**: A blocker or deferred risk with severity, affected journey,
  current evidence, missing evidence, owner area, and next action.
- **Readiness Claim**: The strongest allowed product status after evidence is
  evaluated, such as `infra_smoke_ready`, `pilot_blocked`, or
  `mvp_loop_ready`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every P1 user story has at least one committed metadata-safe
  evidence artifact or an explicit blocker row explaining why evidence is
  unavailable.
- **SC-002**: The final readiness report has zero stale references that name a
  completed feature as the next required slice.
- **SC-003**: Forbidden-content scans over the committed evidence return no
  disallowed raw audio, transcript, credential, token, signed URL, private
  account, or private reference screenshot matches.
- **SC-004**: The latest local artifact validator passes for the desktop
  recording used in the evidence pack, or the readiness claim remains blocked
  with the validator failure recorded.
- **SC-005**: Server readiness tests and relevant macOS validation tests pass in
  the final validation log.
- **SC-006**: The final claim summary contains exactly one strongest claim and
  its blocker rationale is traceable to launch gap records.

## Assumptions

- The 022 `meeting-mute-truth` slice is accepted and available as the baseline
  for this validation-only work.
- The permissioned desktop QA path is `/Applications/2brain Rec.app`.
- Authenticated web review may use safe fixture data if live private meeting
  content cannot be committed.
- Reference comparison may use previously captured sanitized notes or new
  metadata-safe observations; private Krisp screenshots must not be committed
  unless explicitly scrubbed and approved as safe.
- Production rollout remains out of scope unless the evidence proves a
  production user journey without adding new deployment behavior.

## Out Of Scope

- New notes/action generation.
- New capture adapters for third-party meeting-app mute.
- Public unauthenticated sharing or external-recipient invitations.
- Installer signing/notarization.
- Production deploy changes or data migrations.
- UI redesign beyond evidence-backed readiness and clean-room comparison notes.
