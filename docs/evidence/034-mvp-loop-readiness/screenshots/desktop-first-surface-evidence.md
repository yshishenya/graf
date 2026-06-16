# Desktop First-Surface Evidence

Feature: `034-mvp-loop-readiness`

Status: `blocked_for_live_capture`

## Safe Evidence

- Command: `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|DesktopLocalPurge'`
- Result: `28 passed`
- Captured: `2026-06-16`
- Scope: verifies that the desktop shell opens to the meeting workspace route, keeps native Record/Stop and upload truth outside embedded web content, blocks non-review cabinet routes, and preserves metadata-only local purge acknowledgements.

## Live Capture Boundary

No live desktop screenshot is committed in this file. A metadata-safe live app screenshot or an explicit product-owner acceptance of this blocker is still required before claiming `desktop_loop_verified`.

## Forbidden Content Boundary

This note contains no raw audio, transcript text, private email, signed URL, token, local user path, or private Krisp screenshot.
