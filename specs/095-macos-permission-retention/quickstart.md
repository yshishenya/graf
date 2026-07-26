# Quickstart: macOS Permission Retention And Relaunch Reliability

> Historical/test-fixture quickstart. The local/self-signed commands below are
> not a release path and must not be used for a GitHub Release, public host or
> appcast. For current publication use
> [Feature 130](../130-developer-id-release/quickstart.md) and the
> [Installer README](../../apps/macos/Installer/README.md).

Run from repository root unless a step says otherwise.

## Prerequisites

- macOS 14.5+.
- Full Xcode or Command Line Tools sufficient for SwiftPM macOS tests.
- Local administrator rights for installing a package to `/Applications`.
- A stable code-signing identity for the historical permission-retention
  fixture. The former free local fixture uses `GRAF Local Code Signing`.
- No active GRAF recording before install, reinstall, or quit/relaunch tests.
- User grants microphone and Screen/System Audio manually when macOS prompts.

Do not reset TCC, mutate TCC databases, commit certificates, commit packages, or
include raw audio/transcript/private meeting content in evidence.

## 1. Static Spec And Contract Checks

```sh
rg -n "NEEDS CLARIFICATION|\\[FEATURE NAME\\]|\\[DATE\\]|TODO|TBD" \
  specs/095-macos-permission-retention \
  --glob '!quickstart.md'

rg -n "rawAudio|transcriptText|meetingContent|signedUrl|password|apiKey|BEGIN (RSA|OPENSSH|PRIVATE) KEY" \
  specs/095-macos-permission-retention \
  apps/macos/Installer \
  apps/macos/RecApp/App/TwoBrainRecApp.swift \
  apps/macos/Shared/Tests
```

Expected:

- no unresolved template or clarification markers;
- forbidden-content matches, if any, are policy text only.

## 2. Historical Fixture Signing Preflight

```sh
security find-identity -v -p codesigning
```

Expected:

- `GRAF Local Code Signing` or another accepted app signing identity is listed
  as valid.

If no valid identity exists, local permission-retention validation is blocked.
Create/import a local identity outside git, then rerun the preflight.

## 3. Focused Swift Tests

```sh
swift test --package-path apps/macos --filter 'AppControlAccessibilityTests|SystemAudioPermissionGateTests|SystemAudioPermissionUXTests|InstallerLifecycleEvidenceTests'
```

Expected:

- focused tests pass;
- if the local toolchain cannot run SwiftPM XCTest, record the exact limitation
  and do not close the feature until an accepted macOS validation host runs it.

## 4. Installer Script Syntax

```sh
sh -n apps/macos/Installer/Scripts/build-local-installer.sh
sh -n apps/macos/Installer/Scripts/install-user-app.sh
```

Expected:

- both scripts parse.

## 5. Build Historical Local Signed Fixture Package

```sh
GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \
GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
sh apps/macos/Installer/Scripts/build-local-installer.sh \
  apps/macos/.build/installer/graf-local.pkg
```

Expected:

- build succeeds;
- the app bundle is signed with the requested local identity;
- the package exists at `apps/macos/.build/installer/graf-local.pkg`;
- output or docs make clear this package is local validation only.

Inspect the staged app before install:

```sh
codesign --verify --deep --strict "apps/macos/RecApp/.build/GRAF.app"
codesign -dv --verbose=4 "apps/macos/RecApp/.build/GRAF.app" 2>&1
codesign -dr - "apps/macos/RecApp/.build/GRAF.app" 2>&1
/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "apps/macos/RecApp/.build/GRAF.app/Contents/Info.plist"
```

Expected:

- verify succeeds;
- bundle id is `pro.2brain.graf`;
- signature is not ad-hoc;
- designated requirement is not cdhash-only.

## 6. First Install And Manual Permission Grant

```sh
sudo installer -pkg apps/macos/.build/installer/graf-local.pkg -target /
open -n "/Applications/GRAF.app"
```

If macOS asks for microphone or Screen/System Audio permission, grant them
manually in System Settings. Relaunch GRAF if macOS asks for a restart after
permission changes.

Confirm installed identity:

```sh
codesign --verify --deep --strict "/Applications/GRAF.app"
codesign -dv --verbose=4 "/Applications/GRAF.app" 2>&1
codesign -dr - "/Applications/GRAF.app" 2>&1
```

Expected:

- installed app verifies;
- installed app has the same bundle id and signing continuity identity as the
  staged app.

## 7. Permission State Snapshot

Use app logs and bounded read-only TCC summaries.

```sh
tail -n 80 "$HOME/Library/Logs/GRAF/graf.log"
```

Expected log shape:

```text
desktop.permission_onboarding_checked detail=reason=app_appeared microphone=granted systemAudio=granted ready=true
```

Optional read-only TCC summaries:

```sh
sqlite3 "$HOME/Library/Application Support/com.apple.TCC/TCC.db" \
  "select service,client,auth_value from access where client='pro.2brain.graf' and service='kTCCServiceMicrophone';"

sudo sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select service,client,auth_value from access where client='pro.2brain.graf' and service='kTCCServiceScreenCapture';"
```

Expected:

- microphone row for `pro.2brain.graf` has allowed state;
- Screen/System Audio row for `pro.2brain.graf` has allowed state;
- evidence records only service/client/auth summary, not full database dumps.

## 8. Reinstall And Permission Retention (Historical Fixture)

Build or reuse a second package signed with the same continuity identity and a
new version if needed.

```sh
GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \
GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
sh apps/macos/Installer/Scripts/build-local-installer.sh \
  apps/macos/.build/installer/graf-local-reinstall.pkg

sudo installer -pkg apps/macos/.build/installer/graf-local-reinstall.pkg -target /
open -n "/Applications/GRAF.app"
```

Expected:

- permissions remain granted after reinstall;
- no permission onboarding modal appears;
- app log records `ready=true`;
- `codesign -dr -` output shape matches the first accepted install.

Record result as `permission_retention_pass` only when all expected conditions
are true.

## 9. Quit And Relaunch With Permission Modal State

Run with no active recording.

For a normal granted-permission quit:

```sh
osascript -e 'tell application "GRAF" to quit'
```

Expected:

- the app exits;
- latest log includes `app_termination_cleanup_requested` and
  `app_termination_cleanup_completed`;
- reason is `cleanup_finished` or the bounded timeout path.

For a permission-modal path, use a controlled local state where onboarding is
visible, then run the same quit command. Do not reset TCC from an installer or
automated product path. If manual revocation is used for testing, record that
the user explicitly changed System Settings.

Expected:

- permission sheet does not prevent macOS from closing the app;
- modal state is cleared;
- termination reply happens within 10 seconds.

## 10. Metadata-Only Evidence

Create or update:

```text
specs/095-macos-permission-retention/validation/implementation-evidence.md
```

Record:

- feature lane;
- signing identity class;
- bundle id;
- app/package version;
- designated requirement shape;
- permission state labels;
- reinstall result;
- quit/relaunch result;
- focused test results;
- forbidden-content scan result;
- local CI result.

Do not record private keys, passwords, exported certificates, raw audio,
transcripts, private meeting content, tokens, signed URLs, or unrelated private
local paths.

## 11. Repository Gate

Before closeout/PR:

```sh
infra/scripts/ci-local.sh
```

Expected:

- full local CI passes;
- if blocked by environment, record the exact blocker and do not claim feature
  closeout until a suitable host runs the gate.

## 12. Current Public Release Boundary

The local fixture above cannot establish public release readiness. The current
public path is the Developer ID-only flow in Feature 130:

- `Developer ID Application` app signing;
- `Developer ID Installer` package signing;
- Apple notarization and stapling;
- Gatekeeper execute/install validation;
- manual `.pkg` migration when the predecessor is historical local/self-signed,
  with no appcast replacement.
