# Quickstart: Safe macOS App Updates

## 1. Orient to the feature

```sh
git branch --show-current
cat .specify/feature.json
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected:

- branch `105-macos-app-updates`;
- feature directory `specs/105-macos-app-updates`;
- no unrelated worktree changes.

## 2. Resolve and run focused tests

```sh
swift package resolve --package-path apps/macos
swift test --package-path apps/macos --filter AppUpdateControllerTests
swift test --package-path apps/macos --filter EmbeddedCabinetUpdateBridgeTests
swift test --package-path apps/macos --filter InstallerLifecycleEvidenceTests
```

Run focused server contracts:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/unit/test_cabinet_template_sections.py \
  tests/contract/test_cabinet_static_assets_contract.py
```

Expected: the updater state/capture gate, menu/sidebar bridge, embedded-only slot, and packaging contract pass.

## 3. Validate an updater-disabled local build

```sh
GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh

sh apps/macos/Scripts/validate-app-updates.sh \
  apps/macos/RecApp/.build/GRAF.app
```

Expected:

- the app builds and embeds the pinned updater framework;
- no placeholder feed or public key is present;
- manual update UI reports that trusted updates are unavailable;
- no insecure fallback opens or installs anything.

## 4. Prepare release signing outside git

Locate the Sparkle tools installed by SwiftPM:

```sh
find apps/macos/.build/artifacts -type f \
  \( -name generate_keys -o -name generate_appcast -o -name sign_update \) -print
```

Create/import the EdDSA private key only in an approved operator keychain or secret file outside the repository. Record only the public key for the build environment. Never commit the private key, exported key file, password, Developer ID certificate, or notarization credentials.

## 5. Build a release-like updater-enabled app

```sh
GRAF_VERSION=YYYY.MM.DD.N \
GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \
GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
GRAF_UPDATE_FEED_URL="https://<trusted-staging-host>/graf-appcast.xml" \
GRAF_SPARKLE_PUBLIC_ED_KEY="<public-key-only>" \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Expected Info.plist settings:

- automatic checks enabled;
- 86,400-second interval;
- automatic download/install disabled;
- system profiling disabled;
- archive verification before extraction enabled;
- signed feed required.

Inspect identity and nested signatures:

```sh
codesign --verify --deep --strict "apps/macos/RecApp/.build/GRAF.app"
codesign -dv --verbose=4 "apps/macos/RecApp/.build/GRAF.app" 2>&1
codesign -dr - "apps/macos/RecApp/.build/GRAF.app" 2>&1
plutil -p "apps/macos/RecApp/.build/GRAF.app/Contents/Info.plist"
```

## 6. Generate a controlled update

Build an older version and a newer version with the same application signing identity and update public key. Use the official Sparkle key/appcast tools through:

```sh
GRAF_VERSION=YYYY.MM.DD.N \
GRAF_PREVIOUS_APP_BUNDLE=/absolute/path/to/previous/GRAF.app \
GRAF_UPDATE_RELEASE_NOTES=/absolute/path/to/release-notes.md \
GRAF_UPDATE_DOWNLOAD_BASE_URL="https://<trusted-staging-host>/downloads" \
GRAF_SPARKLE_PRIVATE_KEY_FILE=/absolute/path/outside/repository/to/private-key \
GRAF_REQUIRE_RELEASE_PROVENANCE=1 \
  sh apps/macos/Installer/Scripts/prepare-app-update.sh
```

For production staging, first push the clean release commit and its exact
`vYYYY.MM.DD.N` tag. The provenance gate requires that tagged commit to match
the published `origin/master` branch. A local candidate may omit the gate,
but it must not be copied to the production feed.

Expected output under `apps/macos/.build/updates/`:

- `GRAF-YYYY.MM.DD.N.zip`;
- `graf-appcast.xml`;
- signed release notes when external notes are used;
- metadata-only validation summary.

Serve these artifacts from a trusted HTTPS staging origin. Do not use plain HTTP or a private URL requiring credentials in the app.

For an approved production release, attach the ZIP, package, checksums, and
Russian notes to the GitHub Release. Publish the versioned archive and package
before replacing `graf-appcast.xml`; replace the appcast last, then fetch the
public files and compare every SHA-256 with the reviewed local artifacts.

## 7. Exercise client behavior

From the older installed build:

1. Choose `GRAF > Check for Updates…` and verify a newer version is offered.
2. Dismiss the dialog and verify `Доступно обновление` remains in the left sidebar.
3. Activate the badge and verify the same standard update offer returns.
4. Start a recording, choose install, and verify recording and one-action stop remain available while relaunch is deferred.
5. Stop recording and wait for finalization; verify the cached update proceeds or is offered within 60 seconds without another feed request.
6. Install and relaunch; verify `CFBundleVersion` changed and the sidebar badge disappeared.
7. Publish a corrupted/wrong-key fixture to staging; verify it is rejected and the old app remains launchable.

On systems where ScreenCaptureKit is slow, explicitly prove that a start taking
more than 60 seconds and a stop approaching the former 60-second boundary both
finish within the 120-second deadlines. Neither transition may produce a false
`capture_failed`, and the updater must keep relaunch deferred throughout.

## 8. Verify permission retention

Use the existing helper without resetting TCC:

```sh
sh apps/macos/Scripts/validate-macos-permission-retention.sh permissions
sh apps/macos/Scripts/validate-macos-permission-retention.sh installed-identity
```

Run the same commands before and after two sequential same-identity updates. Expected: microphone and Screen/System Audio permissions remain granted and the designated requirement/signing lineage remains compatible.

## 9. Full local gate

```sh
swift test --package-path apps/macos
sh apps/macos/Scripts/validate-app-updates.sh \
  apps/macos/RecApp/.build/GRAF.app
infra/scripts/ci-local.sh
```

## 10. Explicit owner-only release gate

For controlled owner Macs only, after explicit approval, validate the final
self-signed app and signed update artifacts together:

```sh
GRAF_REQUIRE_OWNER_ONLY_UPDATE_TRUST=1 \
  sh apps/macos/Scripts/validate-app-updates.sh \
  /absolute/path/to/new/GRAF.app \
  /absolute/path/to/previous/GRAF.app \
  /absolute/path/to/GRAF-YYYY.MM.DD.N.zip \
  /absolute/path/to/graf-appcast.xml
```

This lane requires the same `GRAF Local Code Signing` certificate and private
key, one manual trusted bootstrap on each controlled Mac, explicit release
approval, and truthful release notes that Developer ID/notarization are absent.
It is not public distribution readiness.

## 11. Public release gate

Do not publish from the local-only path. Public activation additionally requires:

- Developer ID Application signing of the app and nested updater code;
- hardened runtime and secure timestamps;
- notarization, stapling, and Gatekeeper acceptance;
- signed appcast/archive/release notes;
- old-to-new update and rollback smoke;
- two-update permission-retention proof;
- explicit release/deploy approval.

Validate those final artifacts together before approval:

```sh
GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1 \
  sh apps/macos/Scripts/validate-app-updates.sh \
  /absolute/path/to/new/GRAF.app \
  /absolute/path/to/previous/GRAF.app \
  /absolute/path/to/GRAF-YYYY.MM.DD.N.zip \
  /absolute/path/to/graf-appcast.xml
```

The bootstrap release still requires one final manual `.pkg` install for users on older builds that do not contain the updater.
