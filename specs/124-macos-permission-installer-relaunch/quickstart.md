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
```

The no-account `.pkg` is expected to lack a package-level Developer ID
signature. Do not call that artifact notarized or Gatekeeper-ready.

## Colleague installation path

1. Download the package from the GRAF page and open it in Finder.
2. If macOS blocks it, use the one-time **Open Anyway** action in System
   Settings → Privacy & Security, or Control-click the package/application in
   Finder and choose **Open**.
3. Complete the installer, launch `/Applications/GRAF.app`, and do not run
   `sudo spctl --master-disable`, TCC reset commands, or driver installers.
4. In GRAF choose **Разрешить микрофон**. Accept the normal macOS prompt while
   the state is unknown. If the state is **Отклонено**, choose
   **Открыть настройки macOS** and enable GRAF in Microphone.
5. Open **Запись экрана и системного звука**, enable GRAF, return to GRAF, and
   choose **Перезапустить GRAF**. The old process must exit within ten seconds.
6. After relaunch, verify that the onboarding sheet is absent only when both
   statuses are granted and that the record control remains manual.

## Focused repository checks

```sh
sh -n apps/macos/Installer/Scripts/build-local-installer.sh
swift test --package-path apps/macos --filter 'AppControlAccessibilityTests|SystemAudioPermissionUXTests|InstallerLifecycleEvidenceTests|InstallerPackagingTests'
infra/scripts/ci-local.sh
```

If a clean external Mac still cannot add GRAF to Microphone, capture only these
metadata facts: macOS version, GRAF bundle identifier, app path, signature
identity, and the UI state. Do not collect the TCC database or meeting data.
