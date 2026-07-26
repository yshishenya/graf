# Quickstart: Developer ID-only release flow

Run from the repository root. All commands below are validation commands; use
real identities/profile names only in the local Keychain and never commit them.

## 1. Check the public identities

```sh
security find-identity -p codesigning -v
```

The public lane must select `Developer ID Application: ...` and
`Developer ID Installer: ...`.

## 2. Build a public candidate

```sh
GRAF_VERSION=YYYY.MM.DD.N \
GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1 \
GRAF_APP_SIGN_IDENTITY='Developer ID Application: ...' \
DEVELOPER_ID_INSTALLER_IDENTITY='Developer ID Installer: ...' \
GRAF_UPDATE_FEED_URL='https://host.example/graf-appcast.xml' \
sh apps/macos/Installer/Scripts/build-local-installer.sh \
  "$PWD/apps/macos/.build/release/GRAF-YYYY.MM.DD.N.pkg"
```

Submit the app ZIP and package with `xcrun notarytool`, staple both artifacts,
then run the public validator and package checks from the release checklist.

## 3. Validate the one-time legacy migration

```sh
apps/macos/Installer/Scripts/validate-developer-id-bootstrap.sh \
  /path/to/new/GRAF.app \
  /path/to/previous/GRAF.app \
  /path/to/notarized/GRAF-YYYY.MM.DD.N.pkg
```

Expected output includes `publication=manual-pkg-only` and
`appcast_staged=no`. Do not call `prepare-app-update.sh` for this transition and
do not replace the live appcast.

## 4. Validate the next ordinary update

Use the already migrated `.app` as the predecessor and run
`validate-app-updates.sh` with `GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1`, the
candidate ZIP and the staged appcast. The command must report ordinary
Developer ID continuity and preserve the feed/public key.

## 5. Documentation and repository gates

```sh
sh -n apps/macos/Scripts/validate-app-updates.sh \
  apps/macos/Installer/Scripts/build-local-installer.sh \
  apps/macos/Installer/Scripts/validate-developer-id-bootstrap.sh
swift test --package-path apps/macos --filter InstallerLifecycleEvidenceTests
infra/scripts/ci-local.sh
infra/scripts/cd-remote.sh --dry-run
```

Finally run the active-path audit described in
`docs/agent-guidance/release-and-validation.md`. A legacy phrase is acceptable
only beneath a historical receipt or isolated disposable fixture heading.
