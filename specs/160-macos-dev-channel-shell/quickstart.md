# Quickstart: macOS Dev Channel and Native Home

Run from `/Users/yshishenya/Documents/crisp`. Do not reset TCC or use private
meeting content.

## Focused checks

```sh
sh -n apps/macos/Scripts/build-dev-app.sh
sh -n apps/macos/Scripts/install-dev-app.sh
swift test --package-path apps/macos --filter DesktopCabinetConfigurationTests
swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests
swift test --package-path apps/macos --filter DevChannel
```

If the local Swift test environment cannot build WebKit targets, run the
repository's documented macOS validation lane and record the exact limitation.

## Dev metadata matrix

- first build/install to a temporary destination;
- bundle display name, bundle ID, code-signing requirement, outer/nested
  entitlements, native `CFBundleExecutable`, loopback `LSEnvironment`, and
  separate application-support names;
- no `SUFeedURL`, `SUPublicEDKey`, or production app path;
- second same-identity build/update and restart;
- production and Dev bundles present simultaneously;
- missing signer, ad-hoc signer, production URL, and non-loopback URL fail closed.

## Native navigation matrix

- meeting list, detail, settings, expired-session/login, external auth
  continuation, blocked external URL;
- Back and Forward only for safe WKWebView history;
- Reload on a safe first-party GET page;
- Home from list/detail/settings/auth recovery reaches the canonical meetings
  route;
- labels, help text, disabled states, keyboard shortcuts, and focus.

## Permission matrix

Use a real Mac only for the supported first-install/same-identity update smoke:
grant microphone and Screen & System Audio to Dev, restart/update/relaunch,
confirm status remains granted, then verify production remains a separate
identity. Denied/restricted/revoked states are observed without reset or
workaround.

## Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

Public notarization, appcast, production deployment, and release tag work are
not part of this slice.

## Recorded validation

2026-08-17, uncommitted Feature 160 slice:

- `sh -n apps/macos/Scripts/build-dev-app.sh` — PASS.
- `sh -n apps/macos/Scripts/install-dev-app.sh` — PASS.
- `swift test --package-path apps/macos --filter 'DevChannel|DesktopCabinetWorkspaceTests|DesktopCabinetConfigurationTests'` — PASS, 79 tests.
- Checks cover stable Dev metadata, explicit loopback origin, no production
  Sparkle feed keys, signer/designated-requirement gates, isolated recording /
  upload / meeting-detection namespaces, and Home accessibility identity.
- Native computer-use smoke after manual unlock — PARTIAL PASS: local email-code
  login, synthetic meetings list/detail, Reload, Back/Forward, Home from
  detail/settings, and one-rail settings navigation were observed. The
  installed bundle first-run permission sheet truthfully showed the Dev
  channel's current microphone/system-audio states; no TCC reset, workaround,
  or permission mutation was run. The full grant/deny/update matrix remains
  open for an explicit manual macOS Settings action.
- `GRAF_DEV_ORIGIN=http://127.0.0.1:8081 sh apps/macos/Scripts/install-dev-app.sh`
  — PASS; `/Applications/GRAF Dev.app` installed atomically. `codesign
  --verify --deep --strict` passed for both Dev and production bundles;
  `pro.2brain.graf.dev` and production `pro.2brain.graf` remained distinct.
- `infra/scripts/ci-local.sh --fast` — PASS, 1100 passed; lint and Python
  compile passed. The shared gate is complete; T014 remains open only for the
  permission/update portion of the native computer-use smoke.

2026-08-17 read-only permission follow-up:

- System Settings shows `GRAF Dev.app` enabled for «Запись экрана и
  системного звука».
- `GRAF Dev.app` is not yet present in the Microphone grant list and the
  installed app continues to show «Нужен доступ к микрофону».
- No toggle, TCC reset, database edit, hidden profile, or workaround was used.
  T014 remains open for an explicit first-install grant and same-identity
  update/relaunch check.

2026-08-17 permission identity fix and native update smoke:

- The installed bundle was reproduced with `CFBundleExecutable=GRAF` but a
  nested code identifier of `GRAF` while the outer bundle declared
  `pro.2brain.graf.dev`; macOS therefore did not list `GRAF Dev.app` under
  Microphone. The Dev builder now uses the native Mach-O executable as the
  bundle executable, sets loopback values through `LSEnvironment`, and signs
  both outer and nested code with `pro.2brain.graf.dev` and microphone
  entitlements.
- `GRAF_DEV_ORIGIN=http://127.0.0.1:8081 sh apps/macos/Scripts/install-dev-app.sh`
  — PASS after the packaging fix. `CFBundleExecutable=GRAF`, outer and nested
  identifiers are `pro.2brain.graf.dev`, and strict verification passes.
- Native computer-use smoke — PASS for first grant and relaunch: System
  Settings lists `GRAF Dev.app` as enabled under both «Микрофон» and «Запись
  экрана и системного звука»; the app reports «Микрофон и системный звук
  готовы».
- Same-identity update smoke — PASS: the designated requirement and nested
  identifier matched before and after a second install; after relaunch the
  app stayed ready and the production `GRAF.app` signature and permission row
  remained separate. No TCC reset, database edit, hidden profile, or driver
  workaround was used.

2026-08-17 final rebuild/relaunch follow-up:

- `GRAF_DEV_ORIGIN=http://127.0.0.1:8081 sh apps/macos/Scripts/install-dev-app.sh`
  — PASS after the final channel-aware title change. The installed process was
  quit and relaunched; the native window and menu identify themselves as
  `GRAF Dev`, while the bundle remains `pro.2brain.graf.dev` with the same
  designated requirement and loopback origin.
- The relaunch returned to the synthetic local meetings list with native Home,
  Back, Forward, and Reload controls in their expected states. The final
  installed Dev and production `GRAF` processes remained separate.
- `infra/scripts/ci-local.sh --fast` — PASS, 1100 tests; lint and Python
  compile passed. No TCC reset, database edit, hidden profile, driver
  workaround, production update, or public release was performed. T014 is
  PASS.
