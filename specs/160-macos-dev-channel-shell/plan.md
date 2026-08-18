# Implementation Plan: macOS Dev Channel and Native Home

**Branch**: `codex/160-macos-dev-channel-shell` | **Date**: 2026-08-17 |
**Spec**: [spec.md](spec.md)

## Summary

Add a channel-aware local storage helper, a separate signed/loopback Dev build
and install command, and a Home action to the existing WKWebView native
navigation controls. Production build/update code stays unchanged.

## Technical Context

- **Runtime**: Swift Package Manager macOS app, WKWebView, Sparkle, shell
  packaging scripts.
- **Source paths**:
  `DesktopCabinetConfiguration.swift`,
  `EmbeddedCabinetWebView.swift`,
  `DesktopCabinetWorkspaceView.swift`,
  local recording/upload/meeting-detection stores, and
  `apps/macos/Scripts/`.
- **Validation**: Swift focused tests, shell syntax/static contracts, bundle
  metadata/codesign checks, and native computer-use smoke when the Mac is
  unlocked.
- **Risk lane**: `high-risk-feature` (permissions, signing, storage
  isolation, native navigation).
- **Release gate**: no public release/deploy; Developer ID publication remains
  a separate explicit approval gate.

## Design

1. Add `GrafAppChannel` with explicit environment parsing and channel-specific
   application-support names. Inject environment into path helpers for tests;
   preserve existing production and legacy fallback behavior.
2. Add an installed Dev script that builds the existing Swift product, creates
   `GRAF Dev.app` with `pro.2brain.graf.dev`, a loopback launcher, no Sparkle
   feed keys, and a stable named signing identity. Verify all metadata before
   atomically replacing only `/Applications/GRAF Dev.app`.
3. Reuse `DesktopCabinetConfiguration.meetingsURL()` as Home target and add a
   guarded `goHome()` method plus accessibility identifier to the existing
   controller/control strip. Keep WKWebView history and route policy as truth.

## Constitution Check

- PASS: no capture source or legacy routing is revived.
- PASS: permission handling remains native and honest; no TCC mutation.
- PASS: production signing/updater identity remains untouched.
- PASS: local Dev has no server credentials and loopback-only origin.
- PASS: no new route/history system or dependency.

## Quick validation

Run Swift tests for configuration/navigation/path isolation, shell static tests,
and the Dev script in a temporary build destination. Then run native manual
smoke for permissions, coexistence, Home, Back/Forward/Reload, auth, settings,
and blocked external URLs using metadata-only evidence.
