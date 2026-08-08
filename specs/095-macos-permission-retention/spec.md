# Feature Specification: macOS Permission Retention And Relaunch Reliability

**Feature Branch**: `095-macos-permission-retention`

**Created**: 2026-07-09

**Status**: Historical local permission-retention fixture; public release path
superseded by Feature 130

**Current release policy**: This feature does not authorize local/self-signed,
ad-hoc or Apple Development publication. Current public macOS artifacts must
use Developer ID Application/Installer, notarization, stapling and Gatekeeper;
see [Feature 130](../130-developer-id-release/spec.md). The local identity
material below is retained only for isolated permission-continuity tests and
archived evidence.

**Input**: User direction: "095 - новая фича. Можно ли сделать так, что при
переустановке приложения разрешения для него не слетали в macOS. Каждый раз
выдавать заново разрешения для пользователя будет очень неудобно. И еще
модальное окно с разрешениями блокирует перезапуск приложения который делает
система при изменении разрешений. Пока только планирование и исследование
детальное. Ничего не меняй." Follow-up direction selected a no-paid-account
local signing path, then asked to proceed after local permission grants and the
quit/relaunch modal issue were reproduced as the likely same root class.

## Clarifications

### Session 2026-07-09

- Lane: high-risk product area. The slice touches macOS microphone and
  Screen/System Audio permissions, TCC continuity, local installer/signing,
  permission onboarding UX, app termination, and capture-adjacent user trust.
- Current product identity is `GRAF.app` with bundle id `pro.2brain.graf`.
  This identity is part of permission continuity and must not drift without an
  explicit migration plan.
- The first acceptable path is local and free for the owner's Mac: a stable
  locally trusted code-signing identity may be used to sign the app bundle so
  macOS sees the same designated requirement across local reinstalls.
- The free local path is not public distribution readiness. Developer ID
  Application signing, package signing, notarization, Apple Developer account
  membership, and stapled public installers remain a future paid release lane.
- The product must not bypass macOS TCC, automate hidden permission grants,
  reset TCC as part of normal install, or imply that an app can keep
  permissions after a signing identity, bundle id, or designated requirement
  change.
- Permission onboarding must appear only when permissions are missing or
  restricted. When microphone and Screen/System Audio are already granted, app
  launch and reinstall validation must not show the permission modal.
- System-initiated quit/relaunch, normal quit, installer/update relaunch, and
  permission-change relaunch must not be blocked by permission sheets or other
  app modals. The app may finish bounded cleanup, but it must answer macOS.
- Evidence must be metadata-only: bundle id, signing authority class,
  designated requirement shape, permission state labels, version, timestamps,
  and pass/fail outcomes are allowed; raw audio, transcript text, private
  meeting content, credentials, tokens, and unrelated private paths are not.
- The HAL virtual driver remains parked and must not become a prerequisite for
  retaining Screen/System Audio permission or validating this feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep Permissions Across Reinstall (Priority: P1)

A macOS user who has already granted GRAF microphone and Screen/System Audio
permission can install a newer local build of the same GRAF app without having
to grant those permissions again.

**Why this priority**: Repeated permission prompts make local testing and early
pilot use painful. The product depends on microphone and system-audio access,
so permission continuity is a core trust and usability requirement.

**Independent Test**: Install a GRAF build signed with the stable accepted
local signing identity, grant microphone and Screen/System Audio once, reinstall
a newer build with the same bundle id and designated requirement, launch the
app, and confirm both permissions are still granted and no permission modal is
shown.

**Acceptance Scenarios**:

1. **Given** `/Applications/GRAF.app` has bundle id `pro.2brain.graf`, is
   signed with the accepted stable local identity, and both permissions are
   granted, **When** a newer package signed by the same identity is installed,
   **Then** GRAF launches with microphone and Screen/System Audio marked
   granted and does not ask the user to grant them again.
2. **Given** the existing app was ad-hoc signed or signed by a different
   identity, **When** the user installs a stable signed build, **Then** the
   runbook and UI treat a one-time regrant as expected macOS behavior rather
   than a product success claim.
3. **Given** the local signing certificate/private key is replaced or lost,
   **When** a package is built with a new certificate, **Then** validation
   records signing drift and does not claim permission continuity for that
   reinstall.

---

### User Story 2 - Let macOS Quit And Relaunch The App (Priority: P1)

A user can grant or change permissions, then let macOS or the installer close
and relaunch GRAF without a permission modal trapping the application in a
state where macOS cannot quit it.

**Why this priority**: macOS permission changes and installer flows often
require app restart. A blocking sheet can make the app feel broken, prevent
updates, and leave the user stuck during the most sensitive onboarding step.

**Independent Test**: Open the permission onboarding sheet in a controlled
state, request normal app quit and a simulated system/installer termination,
and confirm GRAF dismisses modal UI, runs bounded cleanup, and replies to macOS
within the accepted timeout.

**Acceptance Scenarios**:

1. **Given** the permission onboarding sheet is visible, **When** macOS asks
   GRAF to terminate, **Then** GRAF dismisses the sheet, stops any pending
   permission request UI state, completes bounded cleanup, and allows
   termination within 10 seconds.
2. **Given** meeting detection or another desktop prompt is visible, **When**
   macOS asks GRAF to terminate, **Then** the prompt is cleared and cannot block
   the termination reply.
3. **Given** no recording is active and all permissions are already granted,
   **When** the user quits GRAF, **Then** the app quits cleanly without showing
   permission onboarding during the quit path.

---

### User Story 3 - Build Free Local Signed Packages Safely (Priority: P2)

The owner can build and install a local GRAF package without an Apple Developer
account while still getting a stable local app identity that is good enough for
single-machine permission retention testing.

**Why this priority**: The current owner has no Apple Developer account or
Developer ID certificate. A free path is needed now for local validation, while
the product must keep public distribution requirements truthful.

**Independent Test**: Create or reuse a local code-signing identity, run the
documented build command, inspect the generated app and package metadata, and
confirm the installed app signature is valid and stable across two local
build/install cycles.

**Acceptance Scenarios**:

1. **Given** the local signing identity exists in the user's keychain, **When**
   the owner builds the local installer with that identity, **Then** the app is
   signed with the named identity and the package can be installed locally
   without embedding certificate material or secrets in git.
2. **Given** no Apple Developer account exists, **When** local signing
   validation is reviewed, **Then** the docs explicitly state that this path is
   local-only and does not create a notarized public installer.
3. **Given** a future public release is planned, **When** release readiness is
   checked, **Then** Developer ID Application signing, Developer ID Installer
   signing, notarization, and stapling remain open release-gate requirements.

---

### User Story 4 - Keep Permission UX Truthful (Priority: P2)

A user sees permission recovery UI only when it is needed, with copy that
explains what is missing and does not blame the user or promise impossible macOS
behavior.

**Why this priority**: Permission prompts are high-trust UX. The app must be
clear when permissions are missing, quiet when they are granted, and honest
when signing drift or macOS policy requires a regrant.

**Independent Test**: Run the permission matrix for granted, denied,
restricted, and signing-drift states; confirm UI and diagnostics show the
correct state without blocking quit/relaunch or claiming that GRAF can force
macOS permissions.

**Acceptance Scenarios**:

1. **Given** both permissions are granted, **When** GRAF launches after a
   reinstall, **Then** no permission modal appears and diagnostics record
   `ready=true`.
2. **Given** one permission is missing or restricted, **When** the user opens
   GRAF, **Then** the UI names the missing permission and offers the existing
   recovery action without starting recording.
3. **Given** permission continuity cannot be proven because the signing
   requirement changed, **When** validation runs, **Then** the evidence records
   `signing_drift` and excludes the run from permission-retention acceptance.

### Edge Cases

- The app is installed first as ad-hoc and later as local self-signed.
- The same identity name exists but points to a different certificate/private
  key pair.
- The certificate expires but the existing signed app remains valid under the
  local macOS subsystem policy being validated.
- `CFBundleIdentifier` changes, the display name changes, or legacy
  `/Applications/2brain Rec.app` cleanup runs during install.
- Screen/System Audio permission is granted in the system TCC database while
  microphone permission is granted in the user TCC database.
- macOS System Settings is open on the privacy pane during quit/relaunch.
- A modal sheet is attached to the main window, a sheet is already detached, or
  the app has no main window at termination time.
- A recording is active when quit/update is requested. Existing capture safety
  rules still apply: visible state and one-action Stop remain required, and
  this feature must not hide active capture.
- The installer package is unsigned but the app bundle is signed. Local
  validation may accept this only for local owner testing, not public release.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: GRAF MUST keep `CFBundleIdentifier=pro.2brain.graf` for this
  slice unless a separate migration spec defines permission migration and user
  impact.
- **FR-002**: Local permission-retention validation MUST use a non-ad-hoc app
  signature with a stable designated requirement across reinstall attempts.
- **FR-003**: The local free signing path MUST support a locally trusted
  self-signed code-signing identity without requiring an Apple Developer
  account, while keeping all private keys, certificates, passwords, and
  generated signed packages out of git.
- **FR-004**: The build/runbook MUST distinguish local self-signed validation,
  Apple Development builds, Developer ID Application builds, Developer ID
  Installer package signing, and notarized public distribution.
- **FR-005**: The installer/build validation MUST expose metadata-only app
  identity evidence: bundle id, app path, version, signing authority class,
  TeamIdentifier when present, designated requirement shape, and whether the
  signature is ad-hoc, local self-signed, Apple Development, or Developer ID.
- **FR-006**: Reinstalling a package with the same bundle id and stable
  designated requirement MUST preserve granted microphone and Screen/System
  Audio permissions in accepted validation on the same Mac.
- **FR-007**: Validation MUST fail closed when the app is ad-hoc signed, the
  bundle id changes, the designated requirement changes, or the signing
  certificate/private key cannot be proven to be the same continuity identity.
- **FR-008**: Permission onboarding MUST be suppressed when microphone and
  Screen/System Audio permissions are both granted.
- **FR-009**: Permission onboarding MUST remain recovery UI only; it MUST NOT
  start recording, bypass TCC, automate hidden system setting changes, or reset
  TCC.
- **FR-010**: App termination MUST dismiss permission onboarding and other
  desktop modal prompts before or during termination cleanup so they cannot
  block macOS quit/relaunch.
- **FR-011**: App termination MUST reply to macOS within 10 seconds when no
  active recording shutdown blocker exists, and MUST record metadata-only
  reason values for cleanup finish or timeout.
- **FR-012**: This feature MUST NOT add HAL virtual driver installation,
  CoreAudio restart, driver repair, driver rollback, or virtual-device routing
  as a prerequisite for MVP permission retention.
- **FR-013**: This feature MUST preserve existing visible recording state,
  manual Record/Stop, one-action Stop, and capture permission fail-closed
  behavior.
- **FR-014**: Diagnostics and evidence MUST remain metadata-only and MUST NOT
  include raw audio, transcript text, private meeting content, credentials,
  tokens, signed URLs, passwords, or private user documents.
- **FR-015**: The changelog and release/readiness notes MUST state that local
  self-signed signing is an owner/local validation path, not public release
  readiness.

### Key Entities

- **MacOSAppIdentity**: The installed app identity as macOS sees it: bundle id,
  display name, executable path, version, signing authority class, TeamIdentifier
  if present, and designated requirement shape.
- **PermissionGrantState**: The app-observable microphone and Screen/System
  Audio permission state, plus whether GRAF considers startup capture-ready.
- **SigningContinuityIdentity**: The certificate/private key and designated
  requirement anchor used to sign local builds for permission-retention
  validation.
- **TerminationModalState**: Permission onboarding, permission request
  in-progress state, meeting-detection prompt state, and attached sheets that
  must not block termination.
- **ValidationEvidence**: Metadata-only proof of build, install, permission,
  launch, and termination outcomes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the same Mac, after one accepted local signing identity is
  established and both permissions are granted, two consecutive reinstall
  cycles of `GRAF.app` keep microphone and Screen/System Audio permissions
  granted without showing the permission onboarding modal.
- **SC-002**: Accepted permission-retention evidence includes a non-ad-hoc
  signature, unchanged bundle id, unchanged designated requirement shape, and
  granted microphone plus Screen/System Audio states.
- **SC-003**: A quit request while permission onboarding is visible completes
  within 10 seconds and records a cleanup-finished or timeout reason; the
  permission sheet is not left blocking macOS.
- **SC-004**: The focused macOS tests covering `AppControlAccessibilityTests`
  and `SystemAudioPermissionGateTests` pass before closeout.
- **SC-005**: The feature quickstart reinstall and quit/relaunch scenarios pass
  with metadata-only evidence and no forbidden-content findings.
- **SC-006**: Full local CI passes before feature closeout/PR because this is a
  high-risk macOS permissions and UX slice.

## Assumptions

- The feature targets the current owner/development Mac first. Fleet/MDM PPPC
  profiles, enterprise deployment, and multi-user policy management are out of
  scope for this slice.
- A stable local certificate/private key can be preserved on the target Mac for
  repeated local builds. If it is deleted or regenerated, macOS may treat the
  app as a different code identity.
- Apple Developer account enrollment, Developer ID certificates, package
  signing, notarization, and stapling are deferred until a paid release lane is
  approved.
- Existing Screen/System Audio permission implementation continues to use
  Apple's capture permission APIs; this feature stabilizes identity and UX
  around that permission, not the capture engine itself.
- The installer remains desktop-app-only by default. The parked HAL driver is
  not part of MVP permission-retention acceptance.
