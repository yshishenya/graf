# Research: Calendar Settings UI

**Feature**: 063-calendar-settings-ui

## Decision: Reuse the 060 calendar backend as the source of truth

**Rationale**: Feature 060 already owns provider presets, read-only source connection, server-owned credentials, selectable calendars, sync state, upcoming events, desktop prompt events, and meeting-to-calendar context links. 063 is a user settings layer, so duplicating provider or sync behavior would create a second source of truth and expand privacy risk.

**Alternatives considered**:

- Build a new calendar settings backend: rejected because 060 already exists and this would duplicate credential/sync boundaries.
- Add provider-specific UI logic directly in the cabinet: rejected because provider capability differences already belong behind 060 capability state.

## Decision: Use the existing server-rendered cabinet and component primitives

**Rationale**: The current cabinet has a Russian server-owned shell, navigation model, templates, dark work-focused styling, buttons, icon buttons, inputs, selects, checkboxes, chips, badges, status labels, loaders, empty states, unavailable states, and dialogs. Calendar settings should be a calm working settings screen, not a new app or marketing page.

**Alternatives considered**:

- Introduce a separate frontend application: rejected because it adds dependencies and a second UX stack for one settings surface.
- Build the calendar settings UI in the macOS native layer only: rejected because the web cabinet is also a required surface and credentials/provider flows are server-owned.

## Decision: Connected sources start with zero selected calendars

**Rationale**: Calendar accounts often contain many personal, delegated, shared, and noisy calendars. Selecting none by default is the safest privacy posture. The source can be connected but inactive until the user explicitly chooses calendars in the selection interface.

**Alternatives considered**:

- Select the primary/default calendar automatically: rejected because the primary calendar can still contain private or noisy events.
- Select all readable calendars automatically: rejected because it maximizes privacy exposure and prompt noise.
- Require selection before connection completes: rejected because connection success and calendar selection are different recovery states; users should be able to connect first, then choose.

## Decision: Allow empty selected-calendar state in the settings contract

**Rationale**: The 063 UX explicitly supports "connected, selection needed" and "all calendars deselected" states. The settings contract must allow an empty selected calendar list, even if the existing 060 API contract currently requires at least one selected calendar for the patch operation.

**Alternatives considered**:

- Keep the existing minimum-one selection rule: rejected because it contradicts the clarified spec and prevents privacy-safe deselection.
- Represent "none selected" as a disconnected source: rejected because connection and selection are separate concepts with different user actions.

## Decision: Treat overlap as a conflict only during the shared time interval

**Rationale**: If one event is 12:00-13:00 and another is 12:30-13:30, only 12:30-13:00 is ambiguous. Outside that interval, the single active event may be treated as the current candidate. If recording is already active, 2brain Rec must not switch context automatically.

**Alternatives considered**:

- Treat both full event windows as conflicted: rejected because it hides useful current-event context before/after the actual overlap.
- Pick the earliest or longest event automatically: rejected because recording-context mistakes are privacy-sensitive.

## Decision: Deduplicate only by stable provider event identity or same meeting link

**Rationale**: Similar titles, organizers, or close start times are too weak to merge meetings safely. Stable provider event ID or same meeting link is a stronger signal that the same meeting appears through multiple selected calendars.

**Alternatives considered**:

- Deduplicate by title and time: rejected because different meetings often share generic titles.
- Never deduplicate: rejected because true duplicate event copies would create noise and false duplicate-recording concern.

## Decision: Default event categories favor timed meeting-like events

**Rationale**: By default, 2brain Rec should include timed events with participants or a meeting link/location. All-day events and private/free-busy prompt candidates stay off until the user opts in. This reduces noise and avoids surprising prompts for busy blocks, reminders, holidays, or private holds.

**Alternatives considered**:

- Include all timed events: rejected because many calendars contain blocks with no meeting intent.
- Include every selected-calendar event: rejected because it creates high noise and privacy risk.
- Ask during setup: rejected because the first-use flow is already doing provider connection and calendar selection; event category controls remain available in settings.

## Decision: Stale sync threshold is 24 hours or latest failed sync

**Rationale**: A 24-hour threshold is simple for users and testable for implementation. If the latest sync fails, the source should show stale/error confidence even when an older successful sync exists. The state belongs first on the source row/card, with details nearby and preview warning only when stale data affects preview confidence.

**Alternatives considered**:

- 6-hour threshold: rejected as too noisy for normal calendar settings.
- 7-day threshold: rejected as too stale for meeting prompts.
- No threshold in 063: rejected because acceptance tests would interpret stale state inconsistently.

## Decision: Embedded macOS cabinet routes to server-owned settings

**Rationale**: The macOS app already separates native recording truth from embedded cabinet content. 063 should make the Settings destination useful while preserving the native active-recording strip and one-action Stop outside the embedded view.

**Alternatives considered**:

- Rebuild settings as native SwiftUI: rejected because it duplicates the web cabinet and creates parallel credential UI.
- Open an external browser for normal settings: rejected because the embedded cabinet must work without confusing handoff. Provider authorization may still open provider-controlled steps when necessary.

## Decision: Use UI/read-model contracts instead of new provider contracts

**Rationale**: Provider adapter behavior was designed in 060. 063 needs contracts for what the user-facing settings surface can show, which actions it offers, how it maps unsafe states into safe Russian copy, and how the embedded macOS shell hosts it.

**Alternatives considered**:

- Write a new provider adapter contract: rejected because 063 does not add provider adapters.
- Skip contracts because the feature is UI: rejected because settings state, sync health, overlap handling, and embedded native boundaries are externally observable product contracts.
