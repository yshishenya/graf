# Quickstart

Build a local universal installer on macOS:

```sh
GRAF_VERSION=YYYY.MM.DD.N \
GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Verify the app binary and package component:

```sh
lipo -archs apps/macos/RecApp/.build/GRAF.app/Contents/MacOS/GRAF
pkgutil --payload-files apps/macos/.build/installer/components/graf-desktop-app.pkg
sh apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only
```

Expected architecture output is `arm64 x86_64` (order may vary). Public
release builds must use the Developer ID/notarization procedure in
`apps/macos/Installer/README.md`; an ad-hoc build is local evidence only.
