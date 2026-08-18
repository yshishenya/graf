# Quickstart: validate the no-account macOS path

This is a metadata-only validation runbook. Do not record a meeting or include
audio, transcript text, credentials, or private meeting content in evidence.

## Build the local package

On a Mac with the existing local signing identity:

```sh
GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \
GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Inspect the staged app before sharing it:

```sh
codesign --verify --deep --strict apps/macos/RecApp/.build/GRAF.app
plutil -p apps/macos/RecApp/.build/GRAF.app/Contents/Info.plist \
  | grep -E 'CFBundleIdentifier|NSMicrophoneUsageDescription|NSAudioCaptureUsageDescription|NSScreenCaptureUsageDescription'
codesign -d --entitlements :- apps/macos/RecApp/.build/GRAF.app 2>&1 \
  | grep -F 'com.apple.security.device.audio-input'
```

The no-account `.pkg` is expected to lack a package-level Developer ID
signature. Do not call that artifact notarized or Gatekeeper-ready.
The app signature must contain `com.apple.security.device.audio-input`; if it
does not, stop distribution and rebuild the package.

## Colleague installation path

1. Download the package from the GRAF page and open it in Finder.
2. If macOS blocks it, use the one-time **Open Anyway** action in System
   Settings → Privacy & Security, or Control-click the package/application in
   Finder and choose **Open**.
3. Complete the installer, launch `/Applications/GRAF.app`, and do not run
   `sudo spctl --master-disable`, TCC reset commands, or driver installers.
   If both `GRAF.app` and `GRAF Dev.app` are installed, grant access to the
   exact app channel you are launching; macOS keeps their permission grants
   separate. Do not use a `.build` copy while validating the installed app.
4. In GRAF choose **Разрешить микрофон**. Accept the normal macOS prompt while
   the state is unknown. If the state is **Отклонено**, choose
   **Открыть настройки macOS** and enable GRAF in Microphone.
5. Open **Запись экрана и системного звука**, enable GRAF, return to GRAF, and
   choose **Перезапустить GRAF**. If the permission was enabled manually after
   the running process first observed a missing state, GRAF must show
   **Нужно обновить** and keep recording blocked until the restart. The old
   process must exit within ten seconds.
6. After relaunch, verify that the onboarding sheet is absent only when both
   statuses are granted and that the record control remains manual.

If macOS shows the app as enabled but the running GRAF process still reports a
missing permission or cannot start system audio, do not reset TCC. Choose
**Проверить снова**; GRAF checks the native ScreenCaptureKit path without
recording even when Core Graphics says the permission is granted. If the check
still fails, turn access off and on only for the exact running app (`GRAF` or
`GRAF Dev`), then choose **Перезапустить GRAF**. The permission is applied to a
fresh process only.
The onboarding names the current app copy; that name must match the row enabled
in System Settings because separate bundle IDs have separate macOS permissions.

## Focused repository checks

```sh
sh -n apps/macos/Installer/Scripts/build-local-installer.sh
swift test --package-path apps/macos --filter 'AppControlAccessibilityTests|SystemAudioPermissionUXTests|InstallerLifecycleEvidenceTests|InstallerPackagingTests'
infra/scripts/ci-local.sh
```

If a clean external Mac still cannot add GRAF to Microphone, capture only these
metadata facts: macOS version, GRAF bundle identifier, app path, signature
identity, and the UI state. Do not collect the TCC database or meeting data.

## Sparkle bootstrap and update path

The manually trusted `v2026.07.24.1` package is updater-disabled. Install the
first updater-enabled bootstrap once:

```sh
GRAF_VERSION=2026.07.24.2 \
GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \
GRAF_UPDATE_FEED_URL="https://rec.2brain.pro/static/public/downloads/graf-appcast.xml" \
GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Verify that the installed `GRAF.app` contains the feed URL and the public key
from `apps/macos/Installer/UpdateSigningKey.json`. The bootstrap does not
install updates silently: users can use GRAF's **Check for Updates** action, and
scheduled checks only notify. Every future archive must pass the protected
Sparkle signing workflow and retain the same bundle/signing lineage.

The public publication order is versioned ZIP/PKG and checksums first,
`graf-appcast.xml` last. A new Mac still needs the one-time Finder/System
Settings trust step; Developer ID/notarization is a separate public channel.

## Post-merge integration validation

- Feature 159 integration commit: `b9ba98bf`.
- Permission-focused Swift suite, including ScreenCaptureKit recovery,
  permission gate, UX, installer and accessibility contracts: 73 tests passed.
- Shell syntax, `git diff --check` and `validate-no-legacy-audio-driver.sh`:
  PASS.
- The external clean-Mac permission smoke remains open as T099/#4528; no TCC
  reset, TCC database read/write, PPPC profile, driver or virtual audio device
  was used.
- No production deploy, public macOS publication or private meeting data was
  used in this validation.
