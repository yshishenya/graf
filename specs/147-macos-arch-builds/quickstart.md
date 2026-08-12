# Quickstart: Universal macOS Installer

## 1. Build the universal installer locally

From the repository root:

```sh
GRAF_VERSION=2026.08.12.1 \
GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Expected output:

```text
apps/macos/.build/installer/graf.pkg
```

Local ad-hoc signing is for packaging validation only. Public distribution
requires approved Developer ID signing, notarization, and stapling.

## 2. Validate the final app slices

```sh
file apps/macos/RecApp/.build/GRAF.app/Contents/MacOS/GRAF
lipo -archs apps/macos/RecApp/.build/GRAF.app/Contents/MacOS/GRAF
pkgutil --payload-files apps/macos/.build/installer/components/graf-desktop-app.pkg
```

Expected architecture output contains both `arm64` and `x86_64`; the package
payload contains the app-only product and no legacy driver component.
The latest metadata-only validator receipt is recorded in
`specs/147-macos-arch-builds/evidence/universal-installer.md`.
Focused and repository-gate results are summarized in
`specs/147-macos-arch-builds/evidence/validation-summary.md`.

## 3. Render the public page

```sh
cd apps/server
pytest -q tests/unit/test_public_landing.py tests/contract/test_public_landing_contract.py
```

Expected result: `/download` renders one universal installer link and the
fingerprinted public static asset exists.

## 4. Cross-architecture checks

- On Apple Silicon, launch the installed app and confirm the native process
  architecture is `arm64`.
- On a supported Intel Mac, install the same package and confirm the native
  process architecture is `x86_64`.
- Confirm capture permissions, manual Record/Stop, local visible capture state,
  and cabinet login remain unchanged.

## 5. Closeout

```sh
infra/scripts/ci-local.sh
```

Do not run production deployment or publish the package from this quickstart.
