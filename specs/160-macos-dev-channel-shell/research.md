# Research: macOS Dev Channel and Native Home

**Date**: 2026-08-17

## Current-state facts

- The disposable `apps/macos/Scripts/build-local-app.sh` creates
  `GRAF Local.app`, uses `pro.2brain.graf.local`, and enforces a loopback
  origin, but signs ad hoc and is not an installed Dev channel.
- The public installer uses `pro.2brain.graf`, Developer ID release gates, and
  Sparkle metadata. It must remain untouched for the public contract.
- `DesktopCabinetConfiguration` already rejects non-loopback local URLs,
  separates the local auth cookie, and prevents local fallback to production.
- `EmbeddedCabinetNavigationController` already uses WKWebView's safe
  back-forward list and canonical meetings fallback. It has Back/Forward/Reload
  but no Home button.
- `AppUpdateConfiguration` only initializes Sparkle for the production bundle
  with valid production feed/trust keys; omitting those keys makes Dev updater
  unavailable rather than pointing it at production.
- Local recordings, upload queue, and meeting-detection files currently share
  the `GRAF` application-support root. A channel-aware root is required to
  prevent production/Dev mixing.

## Decisions

1. Add one small channel helper that maps production, disposable local, and
   installed Dev to stable application-support namespaces. Preserve production
   `GRAF` and legacy migration fallback; use `GRAF Dev` for Dev.
2. Add a dedicated `build-dev-app.sh`/install entrypoint rather than changing
   the disposable local script or public installer. The entrypoint signs with
   the named local identity, verifies it, writes a Dev Info.plist without
   Sparkle keys, and installs atomically after all checks pass.
3. Add Home to the existing native control strip and reuse the existing
   fallback request/route policy. The button is disabled on the canonical list
   and otherwise loads only the safe first-party meetings URL.

## Permission boundary

The only supported way to retain permissions is stable app identity through a
normal same-channel update. TCC is never edited, reset, bypassed, or represented
as portable between production and Dev.
