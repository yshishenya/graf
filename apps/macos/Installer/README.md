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
open apps/macos/.build/installer/2brain-rec-local.pkg
```

By default, the script builds:

- the local SwiftUI app bundle at `apps/macos/RecApp/.build/2brain Rec.app`;
- a desktop-app component package;
- an interactive product installer at `apps/macos/.build/installer/2brain-rec-local.pkg`.

The app bundle and package version use the product CalVer release train without
the git tag prefix: `YYYY.MM.DD.N`. When `TWO_BRAIN_REC_VERSION` is not set, the
script selects the next same-day CalVer counter from `CHANGELOG.md`. For a
deliberate release candidate, pass the exact version explicitly:

```sh
TWO_BRAIN_REC_VERSION=YYYY.MM.DD.N \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

The matching git tag and GitHub Release add the leading `v`, for example
`vYYYY.MM.DD.N`.

The default package does not include the proof HAL driver component and does not
restart `coreaudiod`. This is intentional for the system-audio MVP pivot.

After installing, verify the local result with:

```sh
open "/Applications/2brain Rec.app"
```

To build the parked driver diagnostics package explicitly, opt in:

```sh
TWO_BRAIN_REC_INCLUDE_DRIVER_COMPONENT=1 \
  TWO_BRAIN_REC_ALLOW_COREAUDIOD_RESTART=1 \
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

Signed pre-release builds must use an Apple application signing identity
(`Apple Development`, `Developer ID Application`, `Apple Distribution`, or
legacy `Mac Developer`). Check available identities with:

```sh
security find-identity -v -p codesigning
```

Then build with:

```sh
TWO_BRAIN_REC_APP_SIGN_IDENTITY="Apple Development: Your Name (TEAMID)" \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

For packaging-only tests on locked-down hosts, use:

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Do not run `packagesbuild` on `Packages/2brain-rec.pkgproj`. That file is not
a Packages.app project in the format expected by the `packagesbuild` CLI. The
working local path is `Scripts/build-local-installer.sh`.

## Signing Policy

- Developer ID signing and notarization are required before production release.
- Local certificates, private keys, app-specific passwords, API keys, notarization credentials, and generated signed artifacts must stay outside git.
- Build scripts may reference environment variables or local keychain identities by name, but must not embed secret values.
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
