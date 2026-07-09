# Contract: Local Signing Runbook

## Purpose

Define the local, free signing path for owner-machine validation. This contract
exists so local permission-retention testing can proceed without an Apple
Developer account while keeping public distribution claims honest.

## Local Identity

Recommended local identity name:

```text
GRAF Local Code Signing
```

The identity must:

- include a private key available to `codesign`;
- be trusted locally for code signing;
- be preserved across local builds;
- stay outside git and committed evidence;
- be treated as local-only validation material.

The identity display name alone is not continuity. If a new certificate is
created with the same name, validation must treat it as a different identity
until permissions are granted again.

## Preflight Commands

Run from repository root.

```sh
security find-identity -v -p codesigning
```

Expected:

- the chosen identity is listed as valid;
- if no valid identity exists, local signing is blocked until one is created or
  imported.

After a package/app build, inspect:

```sh
codesign --verify --deep --strict "/Applications/GRAF.app"
codesign -dv --verbose=4 "/Applications/GRAF.app" 2>&1
codesign -dr - "/Applications/GRAF.app" 2>&1
```

Expected for local self-signed validation:

- verify succeeds;
- `Authority` includes the local signing identity;
- `TeamIdentifier` may be absent or not set;
- designated requirement is certificate-root shaped, not cdhash-only.

## Build Contract

The accepted implementation should support an explicit local-self-signed path,
for example:

```sh
GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \
GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
sh apps/macos/Installer/Scripts/build-local-installer.sh \
  apps/macos/.build/installer/graf-local.pkg
```

Expected:

- app bundle is signed with the requested identity;
- package is produced without requiring Apple Developer membership;
- the script output clearly identifies this as local validation only;
- the default path still rejects accidental non-Apple signing for release-like
  builds unless the explicit local flag is set.

## Install Contract

Install through the normal package path:

```sh
sudo installer -pkg apps/macos/.build/installer/graf-local.pkg -target /
```

For interactive local testing, using `osascript` to request administrator
privileges is acceptable, but the committed runbook must not embed passwords.

Expected:

- `/Applications/GRAF.app` exists;
- `codesign --verify --deep --strict` succeeds;
- `CFBundleIdentifier` is `pro.2brain.graf`;
- package-level signing may be absent for local validation only.

## Public Distribution Boundary

Local self-signed validation does not satisfy:

- Apple Developer account enrollment;
- Developer ID Application signing;
- Developer ID Installer package signing;
- notarization;
- stapling;
- public download Gatekeeper readiness;
- enterprise/fleet PPPC policy.

Any release note, changelog entry, or status doc must keep this boundary
visible.

## Failure Handling

| Failure | Required Handling |
|---------|-------------------|
| No valid signing identity | Block local permission-retention validation; do not fall back to ad-hoc for continuity claims. |
| Identity exists but package script rejects it | Implement explicit local self-signed allow flag or document blocked state. |
| Signature verifies but DR is cdhash-only | Mark `adhoc_not_accepted`. |
| Same identity name, different cert | Mark `signing_drift_not_accepted`. |
| Package builds but app fails launch | Block acceptance and inspect signature/runtime logs metadata-only. |
| User revokes permissions manually | Do not claim reinstall failure; record permission state as missing and ask for explicit regrant. |
