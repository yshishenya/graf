# macOS Native Handoff

## Implement In Native App

- Desktop trust shell/home frame.
- Active recording indicator and Stop.
- Permission recovery.
- Upload queue truth.
- Minimal server connection/session/policy badge for route guard only.
- Tray/menu compact status.
- Embedded cabinet container and route guard.

## Must Stay Native

- Active capture state.
- Stop.
- Permission state.
- Local artifact truth.
- Upload queue truth and local retry/recovery.
- Platform host behavior: window chrome, tray/menu-bar integration, system
  permissions, local diagnostics, and fail-closed embedded route guard.

## Must Come From Embedded Web/Backend

- Meeting list, processing status, meeting review, notes/actions, upload
  metadata, account/workspace summaries, recent meeting summaries, and speaker
  assignment.
- Speaker assignment in desktop must load the same server-owned panel as the
  browser cabinet, including speaker names, merge state, confidence, segment
  evidence, save conflicts, and retry/error states.
- The native macOS app may host and frame these surfaces, but must not duplicate
  product workflow logic that should be shared by future Windows and Linux
  shells.

## Do Not Implement Here

- Full browser admin/billing/team/help/legal.
- Direct MediaScribe or object-storage credentials.
- Hidden or arbitrary assisted auto-start.
