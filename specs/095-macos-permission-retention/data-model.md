# Data Model: macOS Permission Retention And Relaunch Reliability

> Historical validation model. It describes local permission-continuity
> fixtures, not a public signing or distribution path; use Feature 130 for
> Developer ID release evidence.

This feature does not add product database tables. The model defines
metadata-only validation records and runtime concepts needed to prove local
permission continuity and safe termination.

## MacOSAppIdentity

Represents the installed app identity as macOS and validation tooling observe
it.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `appPath` | string | yes | Expected accepted path is `/Applications/GRAF.app`; evidence may use repo build paths for preinstall checks. |
| `bundleIdentifier` | string | yes | Must be `pro.2brain.graf` for this slice. |
| `displayName` | string | yes | Expected `GRAF`. |
| `executableName` | string | yes | Expected `GRAF`. |
| `shortVersion` | string | yes | CalVer package/app version, no leading `v`. |
| `bundleVersion` | string | yes | Same CalVer value unless a later release spec changes it. |
| `signatureKind` | enum | yes | `adhoc`, `local_self_signed`, `apple_development`, `developer_id_application`, `apple_distribution`, `unknown`. |
| `signingAuthoritySummary` | string | yes | Human-readable metadata only, for example `GRAF Local Code Signing` or `Developer ID Application`. |
| `teamIdentifier` | string/null | yes | Present for Apple team identities, `null`/`not_set` for local self-signed. |
| `designatedRequirementShape` | enum | yes | `certificate_root`, `apple_team_anchor`, `cdhash_only`, `unknown`. |
| `designatedRequirementStable` | boolean | yes | True only when current and prior accepted DR shape match for the continuity identity. |
| `codesignVerified` | boolean | yes | Result of `codesign --verify --deep --strict`. |

Validation rules:

- `bundleIdentifier` must equal `pro.2brain.graf`.
- Accepted permission-retention runs require `codesignVerified=true`.
- `signatureKind=adhoc` or `designatedRequirementShape=cdhash_only` cannot
  satisfy permission-retention continuity.
- `signatureKind=local_self_signed` is acceptable only for local owner-machine
  validation and must not be treated as public distribution readiness.

## SigningContinuityIdentity

Represents the signing identity used for local reinstall validation.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `identityName` | string | yes | Local display name, for example `GRAF Local Code Signing`. |
| `identityClass` | enum | yes | `local_self_signed`, `apple_development`, `developer_id_application`, `unknown`. |
| `privateKeyPresent` | boolean | yes | Local validation only; do not commit key material. |
| `trustedForCodeSigning` | boolean | yes | Required for local self-signed validation. |
| `continuityFingerprintRecorded` | boolean | yes | Evidence may record a bounded fingerprint/checksum as metadata, not private key material. |
| `createdOrImportedAt` | timestamp/null | no | Optional local evidence timestamp. |
| `exportBackupStatus` | enum | no | `not_checked`, `backed_up_securely`, `not_backed_up`, `not_applicable`. |

Validation rules:

- The identity name alone is not sufficient continuity evidence. Validation
  must compare certificate/DR metadata or an accepted fingerprint.
- If `privateKeyPresent=false`, new builds cannot be signed and continuity is
  blocked.
- If the local certificate is regenerated, continuity must be treated as
  broken until permissions are granted again under the new identity.

## PermissionGrantState

Represents the permission state relevant to MVP desktop recording startup.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `bundleIdentifier` | string | yes | Must match `MacOSAppIdentity.bundleIdentifier`. |
| `microphone` | enum | yes | `granted`, `denied`, `restricted`, `unknown`. |
| `screenSystemAudio` | enum | yes | `granted`, `denied`, `restricted`, `unknown`. |
| `ready` | boolean | yes | True only when both permissions are granted. |
| `observedBy` | enum | yes | `app_preflight`, `tcc_readonly`, `manual_system_settings`, `combined`. |
| `observedAt` | timestamp | yes | Local validation timestamp. |
| `permissionOnboardingExpected` | boolean | yes | False when `ready=true`. |

Validation rules:

- Accepted reinstall continuity requires `microphone=granted`,
  `screenSystemAudio=granted`, and `ready=true` after reinstall.
- Permission state evidence must not include raw private TCC database dumps.
  Record service labels and auth values only when needed for metadata proof.

## TerminationModalState

Represents UI state that can block quit/relaunch if not cleared.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `permissionOnboardingPresented` | boolean | yes | SwiftUI permission sheet visibility. |
| `permissionRequestInProgress` | boolean | yes | Prevents stale spinner/request UI from persisting across termination. |
| `meetingDetectionPromptPresented` | boolean | yes | Other desktop prompt that can block termination. |
| `attachedSheetCount` | integer | yes | AppKit sheets attached to app windows at termination request time. |
| `dismissAttempted` | boolean | yes | True once lifecycle delegate attempts to dismiss sheets/prompts. |
| `dismissedBeforeReply` | boolean | yes | True when modal state no longer blocks termination reply. |

Validation rules:

- Termination validation must cover at least one path with permission
  onboarding visible.
- Accepted quit/relaunch requires modal state to be dismissed or no longer
  blocking before the app replies or the timeout path fires.

## ValidationEvidence

Metadata-only evidence record for quickstart and closeout.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `scenarioId` | string | yes | Stable id from quickstart, for example `reinstall-retains-permissions`. |
| `result` | enum | yes | `pass`, `fail`, `blocked`, `not_run`, `not_accepted`. |
| `appIdentity` | MacOSAppIdentity/null | no | Required for signing/install scenarios. |
| `permissionState` | PermissionGrantState/null | no | Required for permission scenarios. |
| `terminationState` | TerminationModalState/null | no | Required for quit/relaunch scenarios. |
| `commands` | array[string] | yes | Metadata-safe command names/arguments. No secrets. |
| `startedAt` | timestamp | yes | Local validation timestamp. |
| `completedAt` | timestamp/null | no | Null when blocked/not_run. |
| `notes` | string | no | Must not include forbidden content. |

Validation rules:

- Evidence cannot be `pass` when forbidden-content scan fails.
- Evidence cannot be `pass` for local self-signed builds if it claims public
  Developer ID/notarization readiness.
- `blocked` must name the concrete missing prerequisite, such as missing
  signing identity, missing permission grant, or unavailable full Xcode tests.
