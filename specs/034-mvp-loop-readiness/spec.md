# Feature Specification: MVP Loop Readiness

**Feature Branch**: `034-mvp-loop-readiness`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "Continue toward MVP through the full SDD Spec Kit cycle. After accepted meeting review, desktop embedding, access/sharing/downloads, and retention/deletion execution, verify and harden the complete MVP value loop across the macOS app, web cabinet, production deployment, and reference-aligned review surfaces. Keep comparing against the final mockups and Krisp desktop/web reference as clean-room information architecture guidance, without copying Krisp visuals, copy, assets, private data, or proprietary behavior."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove The Complete Owner Value Loop (Priority: P1)

As the product owner preparing an internal MVP, I need one current, trustworthy readiness view that proves the loop from local recording to post-meeting review is connected end to end, so I can decide what still blocks a launchable pilot instead of relying on separate feature-level evidence.

**Why this priority**: The product is not MVP-ready just because individual slices pass. The first launch decision depends on whether recording, upload, processing, review, access, deletion truth, desktop embedding, and production smoke evidence all line up as one user journey.

**Independent Test**: Can be tested by running the documented MVP loop review and confirming that it produces a single evidence record showing the current state of each loop stage, the exact blocking gaps, and no private content leakage.

**Acceptance Scenarios**:

1. **Given** accepted feature slices for local capture, upload, processing, review, access, desktop embedding, and deletion truth exist, **When** the MVP loop readiness review is performed, **Then** each stage is classified as ready, degraded, blocked, not accepted, or out of scope with direct evidence links.
2. **Given** production currently reaches only `infra_smoke_ready`, **When** readiness is summarized, **Then** the summary explicitly avoids user-rollout, production-ready, or pilot-ready claims unless stronger evidence is present.
3. **Given** a stage has only synthetic evidence, **When** the readiness view is generated, **Then** the stage is marked as needing live app or production evidence before it can count as launch-ready.

---

### User Story 2 - Verify The Desktop App As The First Product Surface (Priority: P1)

As an internal MVP user, I need the macOS app to open into a usable meeting workspace with native recording trust controls still visible, so the product feels like a meeting assistant rather than a diagnostics console.

**Why this priority**: The Krisp clean-room audit and V8 design baseline both show that the first useful surface is a meeting cockpit. If the desktop app does not expose the accepted web-owned meeting library/review surface while preserving native capture authority, the MVP value loop is not launchable.

**Independent Test**: Can be tested by launching the macOS app, inspecting the initial workspace and embedded review routes, and capturing metadata-safe screenshots that show meeting list/detail access without raw audio, private transcript text, credentials, signed URLs, local paths, or Krisp-owned material.

**Acceptance Scenarios**:

1. **Given** the user opens the macOS app after signing in or having a configured cabinet route, **When** the first product surface appears, **Then** the user can see native recording trust state and a meeting workspace without needing to open diagnostics first.
2. **Given** a meeting has server identity and review content is available, **When** the user opens it from the desktop app, **Then** the embedded surface presents the meeting review route while native Record/Stop authority remains outside the embedded content.
3. **Given** the cabinet route is unavailable, expired, denied, or not configured, **When** the desktop app renders the workspace, **Then** the unavailable state is bounded, truthful, and does not expose private meeting existence or local diagnostic paths.

---

### User Story 3 - Confirm Web Cabinet Review And Governance Fit The Reference IA (Priority: P2)

As a reviewer of the MVP experience, I need the web cabinet and desktop-embedded review surfaces to match the intended information architecture, so transcript, playback, notes, sharing, export, deletion, and lifecycle truth are discoverable without turning the UI into a diagnostic tool.

**Why this priority**: Meeting review is the product's value realization step. The reference audit allows category-level learning such as dense meeting rows, review tabs, contextual assistant entry, playback, and governance actions, but forbids copying Krisp visuals, brand, exact copy, icons, assets, private content, or proprietary behavior.

**Independent Test**: Can be tested by reviewing desktop and browser screenshots against the V8/clean-room reference matrix and confirming that every visible action has an owned status: available, policy-gated, truthful placeholder, or out of scope.

**Acceptance Scenarios**:

1. **Given** a ready meeting exists, **When** a user opens the meeting detail in web or embedded desktop, **Then** transcript/playback/provenance, notes status, and governance actions are visible with truthful availability.
2. **Given** a meeting is still uploading, processing, failed, partial, deleting, or deleted, **When** the user opens the list or detail, **Then** the UI shows the correct lifecycle state and never fabricates transcript, notes, access, export, or deletion success.
3. **Given** the UI is compared to Krisp desktop/web reference, **When** the comparison is recorded, **Then** it describes only allowed IA/category lessons and confirms no copied visuals, private data, exact copy, brand assets, or proprietary behavior.

---

### User Story 4 - Exercise Policy And Lifecycle Boundaries Before Pilot (Priority: P2)

As a workspace owner, I need access, sharing, downloads, retention, deletion, local purge, and external dependency limits to be visible and truthful in the same readiness pass, so sensitive meeting data is not launched with misleading control claims.

**Why this priority**: MVP positioning depends on owner-controlled data. Access and deletion controls that are present but unverified can create more risk than missing controls.

**Independent Test**: Can be tested by using safe fixture or production-smoke meetings to exercise policy-visible states and confirming that the readiness evidence distinguishes controlled storage, local desktop purge, backup expiry, MediaScribe, Langfuse, workflow/temp payloads, diagnostics, and post-egress limits.

**Acceptance Scenarios**:

1. **Given** a user can access a meeting, **When** the readiness pass evaluates sharing, downloads, export, retention, and deletion surfaces, **Then** each action is classified with owner/team/shared/denied/policy-gated/deleted truth and metadata-only audit evidence.
2. **Given** a deletion or retention state exists, **When** the user reads the UI and report text, **Then** the copy says what 2brain Rec controls and does not promise universal erasure outside controlled systems.
3. **Given** local purge tasks are pending, failed, unreachable, expired, or acknowledged, **When** readiness is summarized, **Then** local desktop state is not overclaimed as complete until the device-scoped evidence supports it.

---

### User Story 5 - Produce A Launch Gap Register And Next-Slice Decision (Priority: P3)

As the product owner, I need the readiness pass to produce a concrete launch gap register, so the next Spec Kit slice is chosen from evidence rather than intuition.

**Why this priority**: After 034, the team should know whether the next slice is live app evidence, auth/onboarding, assistant notes, installer signing/notarization, mute truth, external sharing, admin settings, or pilot runbook work.

**Independent Test**: Can be tested by inspecting the readiness report and confirming every remaining launch gap has an owner area, severity, evidence status, and recommended next slice or explicit deferral.

**Acceptance Scenarios**:

1. **Given** the readiness pass finds blockers, **When** the launch gap register is produced, **Then** every blocker has a severity, affected user journey, current evidence, missing evidence, and next action.
2. **Given** a gap is intentionally deferred from MVP, **When** it appears in the register, **Then** the reason and guardrail are explicit.
3. **Given** all P1 loop stages pass with strong evidence, **When** the next product slice is selected, **Then** the recommendation focuses on the highest remaining launch risk rather than repeating already accepted feature work.

### Edge Cases

- The app launches without an authenticated web session or cabinet base route.
- Production smoke passes but no live desktop screenshot or real app navigation evidence exists.
- A meeting is uploaded and processing, but transcript or notes are not ready.
- A meeting is deleted or deleting while desktop or web still has stale list/detail state.
- A user has a shared link or team access but lacks download/export permission.
- Local desktop purge is pending, failed, expired, acknowledged, or assigned to an unreachable device.
- Evidence screenshots or logs accidentally contain private account strings, email addresses, local paths, transcript text, raw audio filenames, signed URL material, or Krisp-owned/private content.
- Reference review reveals category alignment but visual or wording similarity is too close to Krisp.
- The current public endpoint is healthy, but deployment evidence only proves infrastructure smoke and not user rollout readiness.
- Existing product status documents contradict current GitHub, production, or feature evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The readiness feature MUST define the complete MVP owner value loop from local recording through upload, server processing, meeting list, meeting detail, transcript/playback review, notes/action output, sharing/export/download, deletion/retention truth, and desktop/web access.
- **FR-002**: The readiness output MUST classify every loop stage as `ready`, `degraded`, `blocked`, `not accepted`, or `out of scope`.
- **FR-003**: Each loop-stage classification MUST cite current evidence from feature specs, validation artifacts, production smoke output, runtime app screenshots, or direct endpoint/runtime checks.
- **FR-004**: Evidence that is synthetic, fixture-only, local-only, or production-infrastructure-only MUST be labeled as such and MUST NOT be used to claim stronger user rollout readiness.
- **FR-005**: The macOS app readiness review MUST verify that native capture controls, visible recording state, and one-action stop remain outside server-rendered embedded content.
- **FR-006**: The macOS app readiness review MUST verify that the first product surface is a meeting workspace or bounded unavailable state, not a diagnostics-first console.
- **FR-007**: The desktop-embedded readiness review MUST cover meeting list, ready detail, processing/degraded detail, unavailable/auth state, and upload-to-review continuity when evidence is available.
- **FR-008**: The web cabinet readiness review MUST cover meeting list, search/filter/sort affordances, status rows, ready detail, transcript/playback/provenance, notes/action output, access/sharing/export/download, and deletion/retention visibility.
- **FR-009**: The feature MUST include a clean-room reference comparison that uses Krisp only for allowed information-architecture/category lessons and explicitly rejects copied visuals, copy, icons, assets, colors, proprietary behavior, and private data.
- **FR-010**: The readiness evidence MUST scan committed text and screenshot payloads for forbidden private or secret-bearing content before the feature can be accepted.
- **FR-011**: The readiness pass MUST distinguish `infra_smoke_ready`, internal pilot readiness, user rollout readiness, and production readiness as separate claims.
- **FR-012**: The readiness pass MUST include production health and deployment evidence for the currently deployed commit when production claims are made.
- **FR-013**: The readiness pass MUST include a launch gap register with severity, affected journey, current evidence, missing evidence, recommended next action, and deferral reason when applicable.
- **FR-014**: The feature MUST update product status documentation so completed slices are not listed as future work and the next product slice is evidence-based.
- **FR-015**: The feature MUST preserve the local/server UI authority boundary from ADR `001`: active capture remains native/local while review, transcript, notes, sharing, admin, retention, deletion, audit, and fleet surfaces remain server/web-owned unless a later spec changes scope.
- **FR-016**: The readiness review MUST show truthful lifecycle copy for deletion and retention and MUST NOT promise universal erasure outside systems controlled by 2brain Rec.
- **FR-017**: The readiness pass MUST cover policy visibility for owner, team, shared, denied, policy-gated, deleted, deleting, expired, and local-purge states where those states are implemented.
- **FR-018**: The readiness pass MUST call out unresolved MVP launch blockers including, at minimum, meeting-app mute truth, signed/notarized installer evidence, browser/target gaps, live app evidence gaps, and any missing notes/action output.
- **FR-019**: The readiness evidence MUST be safe to commit: no raw audio, transcript text from private meetings, credentials, tokens, signed URLs, passwords, private account identifiers, private emails, live local filesystem paths, or Krisp private captures.
- **FR-020**: The feature MUST produce an independently reviewable acceptance summary that states whether 034 proves MVP loop readiness, proves only partial readiness, or blocks launch until named gaps are resolved.

### Key Entities *(include if feature involves data)*

- **MvpLoopStage**: A named step in the owner value loop, with scope, owner surface, status, evidence, and blocking gaps.
- **ReadinessEvidence**: A metadata-only reference to proof such as a command result, screenshot, endpoint response, production deploy output, feature artifact, GitHub issue/PR state, or runtime observation.
- **LaunchGap**: A remaining launch blocker or deferred item, with severity, user impact, current evidence, missing evidence, next action, and owner area.
- **ReferenceComparison**: A clean-room comparison record that separates allowed category lessons from forbidden visual/copy/asset/proprietary similarity.
- **ReadinessClaim**: A bounded statement such as `infra_smoke_ready`, `desktop_loop_verified`, `pilot_blocked`, or `mvp_loop_ready`, with required evidence and explicit exclusions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of MVP loop stages defined by FR-001 have a current status, evidence link, and launch-gap decision in the readiness summary.
- **SC-002**: At least one desktop-app readiness capture and one web/embedded review capture are recorded or explicitly marked unavailable with a blocker reason before acceptance.
- **SC-003**: 100% of committed readiness text and screenshot payloads pass the forbidden-content scan before merge.
- **SC-004**: The readiness summary distinguishes infrastructure, internal pilot, user rollout, and production readiness claims with no ambiguous "ready" wording.
- **SC-005**: Product status documentation no longer lists completed features 016, 017, 018, or 033 as future work and identifies the next evidence-based product slice.
- **SC-006**: The clean-room reference comparison records zero copied Krisp visuals, exact copy, icons, brand assets, private screenshots, private account content, or proprietary behavior.
- **SC-007**: Every P0/P1 launch blocker in the gap register has a proposed next action or explicit deferral before the feature can be accepted.
- **SC-008**: A reviewer can determine in under 10 minutes from the acceptance summary whether 2brain Rec is MVP-loop-ready, partially ready, or blocked.

## Assumptions

- Features `016`, `017`, `018`, and `033` are accepted foundations for this readiness pass unless current evidence contradicts them.
- `infra_smoke_ready` is the strongest production deployment claim currently allowed without additional pilot/user rollout evidence.
- Live reference inspection should use only clean-room category lessons and metadata-safe screenshots; private Krisp content must stay out of committed artifacts.
- This feature may use safe synthetic data when live private content would be unsafe, but synthetic evidence must be labeled and cannot substitute for live app evidence where the claim requires live app behavior.
- The initial MVP remains macOS-only; Windows/Linux/mobile are out of scope for this feature.
- The feature may recommend later slices, but it does not implement unrelated future capabilities unless they are required to prove the MVP loop.
- Browser-only admin settings, external-recipient public sharing, billing, legal hold, and broad assisted auto-start remain outside this feature unless the readiness pass identifies them as explicit pilot blockers.

## Out Of Scope

- Implementing public unauthenticated meeting links or external-recipient invitation policy.
- Implementing broad assisted auto-start or generalized meeting detection.
- Resolving meeting-app mute truth beyond identifying its current launch risk.
- Implementing signed/notarized installer distribution, unless selected as a follow-up slice after this readiness pass.
- Reintroducing virtual-driver routing as an MVP dependency.
- Copying Krisp UI, copy, brand, assets, icons, private screenshots, account data, or proprietary behavior.
