# Research: macOS Permission Retention And Relaunch Reliability

## Decision: Use Stable Code Identity Instead Of Ad-hoc Builds

Use a stable app bundle id (`pro.2brain.graf`) and a non-ad-hoc code signature
whose designated requirement remains stable across local reinstall cycles.
Permission-retention acceptance must reject ad-hoc builds and signing drift.

**Rationale**: Apple documents code signing requirements and designated
requirements as the mechanism macOS subsystems can use to recognize the same
code identity over time. Apple's archived code signing note also explains that
many macOS subsystems care about valid and stable designated requirements, and
that self-signed identities can work for policies that do not require an
Apple-trusted anchor. The local observation before this spec matched that
model: ad-hoc signing produced a cdhash-shaped identity that changes across
builds, while a local self-signed code-signing certificate produced a stable
certificate-root designated requirement for the installed app.

**Sources**:

- Apple TN3127, "Inside Code Signing: Requirements":
  https://developer.apple.com/documentation/technotes/tn3127-inside-code-signing-requirements
- Apple TN2206, "macOS Code Signing In Depth":
  https://developer.apple.com/library/archive/technotes/tn2206/_index.html

**Consequences**:

- Local permission-retention validation needs a stable signing identity before
  the user grants permissions.
- Reinstalling builds signed with a different local certificate, a regenerated
  self-signed certificate, or ad-hoc signing cannot be accepted as continuity.
- The bundle id is part of the identity boundary and must remain stable.

## Decision: Support A Free Local Self-Signed Identity For Owner Validation

Accept a locally trusted self-signed code-signing identity as the no-paid
owner-machine path. Require an explicit build flag or runbook step so nobody
confuses the local path with Apple Developer distribution readiness.

**Rationale**: The user has no Apple Developer account, Developer ID
Application certificate, or Developer ID Installer certificate. A local
self-signed identity is enough to produce a stable local app code identity on
the same Mac for validation, but it does not provide the Apple Developer Team
Identifier, notarization ticket, or Gatekeeper distribution posture expected
for public downloads.

**Consequences**:

- The local certificate/private key must be preserved. Recreating a certificate
  with the same display name is not continuity.
- Generated certificates, private keys, exported identities, and packages stay
  outside git.
- Build/installer docs must label local self-signed signing as owner/local
  validation only.

## Decision: Keep Developer ID And Notarization As A Separate Paid Release Gate

Do not attempt Developer ID signing or notarization in this slice. Record the
future public-distribution path instead: Apple Developer account, Developer ID
Application certificate for the app bundle, Developer ID Installer certificate
for a signed package when needed, notarization through Apple's notary service,
and stapling/verification before public release.

**Rationale**: Apple positions notarization as the outside-the-Mac-App-Store
distribution workflow for Developer ID-signed software. Apple's notarization
documentation and WWDC material describe notary service submission and
`notarytool` as the command-line path. That workflow requires Apple Developer
program credentials and certificates, which are outside the current free local
request.

**Sources**:

- Apple, "Notarizing macOS software before distribution":
  https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- Apple, "Resolving common notarization issues":
  https://developer.apple.com/documentation/security/resolving-common-notarization-issues
- Apple Notary API:
  https://developer.apple.com/documentation/notaryapi
- Apple WWDC21, "Faster and simpler notarization for Mac apps":
  https://developer.apple.com/videos/play/wwdc2021/10261/

**Consequences**:

- Public installer/download readiness remains blocked until the paid release
  lane is approved.
- Local packages may be unsigned at the package level only for local owner
  validation, provided the app bundle identity is stable and verified.
- Changelog/release notes must not claim notarized distribution from this
  feature.

## Decision: Do Not Bypass Or Reset TCC

GRAF must continue requesting and observing macOS permissions through the
normal OS paths. Validation may inspect TCC state locally for metadata-only
proof, but the product must not automate hidden grants, reset permissions, or
modify TCC databases.

**Rationale**: Apple requires explicit user authorization for microphone access
on macOS, and ScreenCaptureKit/system capture is guarded by the user's privacy
settings. GRAF's trust model depends on respecting those OS decisions.
Permission continuity should come from stable app identity, not from bypassing
the permission system.

**Sources**:

- Apple, "Requesting Authorization for Media Capture on macOS":
  https://developer.apple.com/documentation/bundleresources/requesting-authorization-for-media-capture-on-macos
- Apple ScreenCaptureKit documentation:
  https://developer.apple.com/documentation/screencapturekit/

**Consequences**:

- `tccutil reset` may be mentioned only as a manual testing escape hatch, never
  as an installer or app behavior.
- Evidence records state names such as `granted`, `denied`, `restricted`, or
  `unknown`, not private OS database contents beyond the bundle id/service
  rows needed for local validation.

## Decision: Dismiss App Modals Before Termination Cleanup Reply

The app lifecycle path must clear permission onboarding, in-progress permission
request UI state, meeting-detection prompts, and attached sheets when macOS
requests termination. Cleanup remains bounded by the existing 10-second
termination reply path.

**Rationale**: The user observed macOS failing to close the app when permission
modal UI was visible. Permission changes can require relaunch. A modal sheet
must not hold the app in a state where the app never answers macOS
termination.

**Consequences**:

- The app can still perform normal cleanup, but the modal layer cannot block
  the cleanup request or termination reply.
- Tests may use source-level assertions for AppKit sheet dismissal because
  SwiftPM XCTest does not launch the full signed app lifecycle.
- Manual installed-app validation remains required for the real quit/relaunch
  behavior.

## Decision: Keep The HAL Driver Parked

The feature must not install, repair, restart, or validate the parked HAL
virtual driver as part of permission retention.

**Rationale**: The current product baseline is macOS system-audio-first.
Permission retention for microphone and Screen/System Audio does not need the
virtual driver. Adding driver behavior would broaden risk into CoreAudio
restart, rollback, and future advanced-routing work.

**Consequences**:

- `GRAF_INCLUDE_DRIVER_COMPONENT` remains off for the quickstart and acceptance
  path.
- Any driver signing, repair, or rollback work needs a separate spec.

## Alternatives Considered

### Continue Ad-hoc Signing

Rejected. Ad-hoc signatures are convenient for local build speed, but their
identity is not stable enough for the permission-retention acceptance target.

### Pay For Apple Developer Program Now

Deferred. This is the correct public distribution path, but the user explicitly
asked whether a no-pay path exists and currently has no account or certificates.

### Use MDM PPPC Profiles

Out of scope. PPPC profiles are relevant for managed fleets, not the current
owner-machine local validation path. They require admin/fleet policy decisions
and do not replace user-facing product permission UX.

### Remove Permission Onboarding Entirely

Rejected. The app still needs truthful recovery UI when permissions are missing
or restricted. The fix is to suppress onboarding when ready and dismiss modals
for termination, not to hide permission state.

### Force Quit Without Cleanup

Rejected. GRAF must preserve capture safety and bounded cleanup. The accepted
path is modal dismissal plus the existing termination reply bound.
