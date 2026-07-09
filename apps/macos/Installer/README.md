# GRAF macOS Installer

This directory owns the local macOS installer package and recovery scripts.

## MVP Scope

- System-audio MVP local install defaults to the desktop app only.
- Driver install, repair, rollback, uninstall, and Core Audio restart are parked
  for future driver diagnostics unless an explicit driver flag is set.
- User-visible restart-required and manual-cleanup states remain required for
  future driver work, but are not MVP recording prerequisites.

Silent install, MDM, fleet deployment, and enterprise deployment are out of scope for this feature.

## Local Interactive Installer Build

Use the native Apple `pkgbuild`/`productbuild` flow for local development:

```sh
sudo DevToolsSecurity -enable
spctl developer-mode enable-terminal
sh apps/macos/Installer/Scripts/build-local-installer.sh
open apps/macos/.build/installer/graf-local.pkg
```

By default, the script builds:

- the local SwiftUI app bundle at `apps/macos/RecApp/.build/GRAF.app`;
- a desktop-app component package;
- an interactive product installer at `apps/macos/.build/installer/graf-local.pkg`.

The app bundle and package version use the product CalVer release train without
the git tag prefix: `YYYY.MM.DD.N`. When `GRAF_VERSION` is not set, the script
selects the next same-day CalVer counter from `CHANGELOG.md`. For a deliberate
release candidate, pass the exact version explicitly:

```sh
GRAF_VERSION=YYYY.MM.DD.N \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

The matching git tag and GitHub Release add the leading `v`, for example
`vYYYY.MM.DD.N`.

The default package does not include the proof HAL driver component and does not
restart `coreaudiod`. This is intentional for the system-audio MVP pivot.

After installing, verify the local result with:

```sh
open "/Applications/GRAF.app"
```

To build the parked driver diagnostics package explicitly, opt in:

```sh
GRAF_INCLUDE_DRIVER_COMPONENT=1 \
  GRAF_ALLOW_COREAUDIOD_RESTART=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Do not use the driver opt-in path for system-audio MVP acceptance.

Local development may use ad-hoc app signing only when Developer Tools Security
is enabled. If it is disabled, macOS can install the `.app` successfully but
kill it through AMFI before app diagnostics are written. Check the local state
with:

```sh
DevToolsSecurity -status
```

## Local Self-Signed Permission-Retention Builds

For owner-machine validation without an Apple Developer account, use a stable
locally trusted code-signing identity such as `GRAF Local Code Signing`. This
path is intended to prove that macOS sees the same `pro.2brain.graf` app
identity across local reinstalls, so granted microphone and Screen/System Audio
permissions do not need to be granted again on every build.

Preflight the local identity:

```sh
security find-identity -v -p codesigning
```

Build explicitly as local-only:

```sh
GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \
GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Then inspect the app identity:

```sh
codesign --verify --deep --strict "apps/macos/RecApp/.build/GRAF.app"
codesign -dv --verbose=4 "apps/macos/RecApp/.build/GRAF.app" 2>&1
codesign -dr - "apps/macos/RecApp/.build/GRAF.app" 2>&1
```

Keep the same certificate/private key pair. Recreating a certificate with the
same display name is signing drift and may make macOS ask for permissions
again. Do not commit exported certificates, private keys, passwords, or
generated signed packages.

This local self-signed path is not public release readiness. It does not create
an Apple Developer TeamIdentifier, Developer ID signature, notarization ticket,
or stapled Gatekeeper-ready installer.

Signed pre-release builds must use an Apple application signing identity
(`Apple Development`, `Developer ID Application`, `Apple Distribution`, or
legacy `Mac Developer`). Check available identities with:

```sh
security find-identity -v -p codesigning
```

Then build with:

```sh
GRAF_APP_SIGN_IDENTITY="Apple Development: Your Name (TEAMID)" \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

For packaging-only tests on locked-down hosts, use:

```sh
GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Legacy `TWO_BRAIN_REC_*` environment names are still accepted as fallbacks for
older local runbooks, but new commands should use `GRAF_*`.

Do not run `packagesbuild` for the local installer path. The working local
path is `Scripts/build-local-installer.sh`.

## Signing Policy

- Developer ID signing and notarization are required before production release.
- Local certificates, private keys, app-specific passwords, API keys, notarization credentials, and generated signed artifacts must stay outside git.
- Build scripts may reference environment variables or local keychain identities by name, but must not embed secret values.
- Local self-signed app signing is allowed only when
  `GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1` is set. It is accepted for
  single-machine permission-retention validation, not for public distribution.
- Public distribution still requires Apple Developer Program access, a
  Developer ID Application certificate for the app, a Developer ID Installer
  certificate when package signing is needed, successful notarization, and
  stapling/verification before release.
- For local development, `build-local-installer.sh` may ad-hoc sign the `.app`
  only when Developer Tools Security is enabled. Apple application signing is
  required for pre-release builds. The product package itself remains unsigned
  unless `DEVELOPER_ID_INSTALLER_IDENTITY` is set in the environment. Unsigned
  packages are acceptable only for local validation.

## Safety Rules

- Updates must not interrupt active capture or an active call.
- Uninstall must remove app-managed virtual audio artifacts where macOS permits.
- Uninstall must attempt to restore previous physical microphone and speaker choices where macOS permits.
- Partial cleanup must be reported truthfully with a manual remediation step.
