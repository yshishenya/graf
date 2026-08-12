# GRAF macOS Installer

This directory owns the local macOS installer package and recovery scripts.

## MVP Scope

- The system-audio MVP ships as one desktop-app-only universal installer.
- The installer contains native `arm64` and `x86_64` slices and requires macOS
  14.5 or later.
- The retired virtual-driver component is not part of the product or build.

Silent install, MDM, fleet deployment, and enterprise deployment are out of scope for this feature.

## Local Interactive Installer Build

Use the native Apple `pkgbuild`/`productbuild` flow for local development:

```sh
sudo DevToolsSecurity -enable
spctl developer-mode enable-terminal
sh apps/macos/Installer/Scripts/build-local-installer.sh
open apps/macos/.build/installer/graf.pkg
```

By default, the script builds:

- both native SwiftPM release slices (`arm64-apple-macosx14.5` and
  `x86_64-apple-macosx14.5`) and merges them into one executable;
- the local SwiftUI app bundle at `apps/macos/RecApp/.build/GRAF.app`;
- a desktop-app component package;
- an interactive product installer at `apps/macos/.build/installer/graf.pkg`.

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

The package is universal and does not include a virtual audio driver or restart
`coreaudiod`. This is intentional for the system-audio MVP.

Verify the slices before opening the package:

```sh
lipo -archs apps/macos/RecApp/.build/GRAF.app/Contents/MacOS/GRAF
pkgutil --payload-files apps/macos/.build/installer/components/graf-desktop-app.pkg
```

The first command must report `arm64 x86_64` (order may vary). The public
download flow intentionally exposes this single package to both supported Mac
architectures.

After installing, verify the local result with:

```sh
open "/Applications/GRAF.app"
```

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
- For local development, `build-local-installer.sh` may ad-hoc sign the `.app`
  only when Developer Tools Security is enabled. Apple application signing is
  required for pre-release builds. The product package itself remains unsigned
  unless `DEVELOPER_ID_INSTALLER_IDENTITY` is set in the environment. Unsigned
  packages are acceptable only for local validation.

## Safety Rules

- Updates must not interrupt active capture or an active call.
- Uninstall must remove app-managed application artifacts where macOS permits.
- Partial cleanup must be reported truthfully with a manual remediation step.
