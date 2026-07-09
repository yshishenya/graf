# Contract: macOS App Identity And Permission Continuity

## Purpose

Define the metadata that must be collected and the pass/fail rules for claiming
that a GRAF reinstall preserved macOS microphone and Screen/System Audio
permissions because the app identity stayed stable.

## Scope

In scope:

- `GRAF.app` bundle identity.
- Code signature and designated requirement metadata.
- Local self-signed, Apple Development, and Developer ID app signatures.
- Same-Mac reinstall and upgrade validation.
- Read-only permission state evidence.

Out of scope:

- MDM PPPC profiles.
- TCC database mutation.
- Public notarized installer acceptance.
- HAL driver install/repair/rollback.

## Identity Fields

Each accepted validation run records:

```text
appPath
bundleIdentifier
displayName
executableName
shortVersion
bundleVersion
signatureKind
signingAuthoritySummary
teamIdentifier
designatedRequirementShape
designatedRequirementStable
codesignVerified
```

`bundleIdentifier` must be `pro.2brain.graf`.

## Signature Classification

| Classification | Accepted For Permission Retention? | Accepted For Public Release? | Notes |
|----------------|------------------------------------|------------------------------|-------|
| `adhoc` | No | No | Useful only for fast local smoke when permission continuity is not being claimed. |
| `local_self_signed` | Yes, local owner Mac only | No | Requires explicit local validation flag and preserved private key/certificate. |
| `apple_development` | Yes, local/pre-release validation | No | TeamIdentifier is present, but this is not the final outside-store distribution identity. |
| `developer_id_application` | Yes | Only with release gate | App bundle identity for outside-store distribution; package signing/notarization still required for public release. |
| `unknown` | No | No | Fail closed. |

## Designated Requirement Rules

Accepted permission-retention evidence requires:

- non-ad-hoc app signature;
- `codesign --verify --deep --strict` succeeds;
- `codesign -dr -` produces a stable requirement shape that is not cdhash-only;
- current and prior accepted runs have the same continuity identity;
- bundle id remains `pro.2brain.graf`.

Fail closed when:

- the signature is ad-hoc;
- the designated requirement is cdhash-only;
- the signing certificate/private key was regenerated;
- the bundle id changed;
- validation cannot compare current and prior signing identity metadata.

## Permission State Rules

Accepted reinstall continuity requires:

- microphone state is `granted`;
- Screen/System Audio state is `granted`;
- the app's permission onboarding status is `ready=true`;
- permission onboarding is not presented on launch after reinstall.

Validation may use a combination of:

- app logs such as `desktop.permission_onboarding_checked`;
- app-visible permission preflight;
- bounded read-only TCC row summaries for `pro.2brain.graf`;
- manual System Settings observation.

Validation must not:

- reset TCC as part of normal install;
- mutate TCC databases;
- paste raw TCC database dumps into evidence;
- claim GRAF can force or preserve permissions after identity drift.

## Accepted Outcome Labels

| Label | Meaning |
|-------|---------|
| `permission_retention_pass` | Same bundle id and stable identity, both permissions granted after reinstall, no permission modal. |
| `signing_drift_not_accepted` | Bundle id or designated requirement changed; user may need one-time regrant. |
| `adhoc_not_accepted` | App is ad-hoc signed; permission-retention claim is invalid. |
| `permission_missing_blocked` | Identity is acceptable, but at least one permission is not granted. |
| `public_release_blocked` | Local validation passed, but Developer ID/notarization release requirements are not complete. |

## Evidence Safety

Allowed in evidence:

- bundle id;
- app path class such as `/Applications/GRAF.app`;
- app version;
- signing authority display name/class;
- TeamIdentifier presence/absence;
- bounded certificate fingerprint/checksum if needed for continuity;
- permission state labels;
- pass/fail status.

Forbidden in evidence:

- private keys or exported certificates;
- keychain passwords or app-specific passwords;
- raw audio, transcript text, private meeting content;
- tokens, signed URLs, credentials;
- unrelated private local file paths or screenshots.
