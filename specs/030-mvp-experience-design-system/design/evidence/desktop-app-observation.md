# Desktop App And Tray Observation

## Observed Facts

- Installed app: local 2brain Rec macOS app.
- Version: `0.1.0`.
- Bundle id: `pro.2brain.rec`.
- Runtime: process launched successfully as the local 2brain Rec app binary.
- Current window title: `2brain Rec`.
- Current first viewport is a native SwiftUI diagnostics/readiness surface:
  driver diagnostics, recording status, system audio recording controls, input
  meters, audio health, route diagnostics, browser target validation, buffer
  state, and diagnostic log summary.
- Current primary user value is hidden behind technical readiness language. The
  app does not show a meeting library, account/workspace cabinet, server
  processing status, manual media upload, transcript review, or meaningful
  post-recording next step in the first viewport.
- Safe clicks performed on 2026-06-11:
  - `Refresh audio device status` updated only the diagnostic last-event text.
  - `Run audio readiness check` updated only the diagnostic last-event text.
- `Record System Audio` was intentionally not clicked during audit because it
  would start local capture.

## Design Implications

- The current app is useful as engineering diagnostics but is not a launchable
  user-facing product surface.
- The first screen must become a cabinet-first product home: readiness and
  Record/Stop remain native and visible, while the main content shows meetings,
  upload, processing, and account state.
- Driver/advanced routing diagnostics should move behind recovery/diagnostics,
  not occupy the first viewport.
- The design must specify tray/menu bar behavior because the product needs
  compact current-status access and one-action Stop outside the main window.
- Diagnostics should remain available, but only as a secondary recovery or
  support surface. The default path must be the owner value loop.

## Target Desktop Shell

- Persistent local recording truth.
- One-action Stop.
- Permission recovery separated from account/server auth.
- Upload queue truth after Stop.
- Compact tray/menu status with no hidden recording.
- Embedded cabinet only for safe account/upload/review routes.
- First viewport shows the embedded cabinet subset by default.
- Native capture strip remains pinned above server content in every route.
