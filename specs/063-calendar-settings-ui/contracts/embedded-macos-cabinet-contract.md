# Embedded macOS Cabinet Contract

**Feature**: 063-calendar-settings-ui

## Purpose

Define how the macOS app hosts Calendar settings without moving calendar credentials or recording authority into the desktop client.

## Hosting Contract

- Calendar settings are rendered by the server-owned cabinet inside the embedded macOS cabinet.
- The embedded flow must reach the same settings hierarchy as the web cabinet: `Настройки -> Интеграции -> Календари`.
- Normal settings management must not require a confusing external browser handoff.
- Provider-controlled authorization may open an external provider step only when necessary, with clear return/recovery state in the embedded settings screen.

## Native Recording Boundary

The native macOS shell remains authoritative for active recording truth:

- active recording indicator stays visible when recording is active;
- one-action Stop remains visible and available when policy permits;
- calendar settings must not cover or replace native recording controls;
- changing calendar settings must not start, stop, hide, or switch an active recording.

## Credential Boundary

- Desktop app must not store provider credentials.
- Desktop app must not display app passwords, provider tokens, refresh tokens, raw provider payloads, signed links, or passcodes.
- Credential submission and storage remain server-owned.

## Embedded Unavailable States

If the embedded cabinet loses network/auth or cannot load settings:

- show sign-in-required or unavailable state in the embedded content;
- keep native Record/Stop controls available where policy permits;
- do not imply that manual recording requires calendar connection;
- do not show raw transport, token, or provider error payloads.

## Prompt Settings Boundary

Calendar prompt preferences may affect whether join/open and at-start record prompts surface. They must not enable automatic recording in 063.

If multiple overlapping events are current:

- the prompt must require explicit event choice before assigning calendar context; or
- the user may continue recording without calendar context.

If a recording is already active:

- a later overlapping calendar event must not switch recording context automatically.

## Validation Contract

The macOS validation path must prove:

- the embedded settings destination opens;
- native active-recording strip remains visible above/around embedded content when active;
- one-action Stop remains reachable;
- provider credentials are not stored or displayed by desktop;
- unavailable/auth states do not block manual recording controls;
- prompt settings do not enable auto-record.
