# Data Model: Desktop UI Polish

No schema or persistence changes.

## Embedded Workspace

- Represents the server-rendered cabinet inside the native macOS shell.
- Layout attributes: max width, horizontal padding, centered/expanded behavior.
- Validation: uses available desktop space without horizontal overflow.

## Meeting Row

- Existing entity rendered from `MeetingListItem`.
- Visible attributes: title, duration, status label, planned action slots, date.
- Validation: compact height, stable columns, long-title truncation.

## Native Inspector Rail

- Existing SwiftUI shell region for capture controls, upload truth, recording trust, diagnostics.
- Visible states: collapsed idle rail, expanded rail, active-recording expanded state.
- Validation: stop/upload truth remain reachable while center workspace keeps priority.

## Clean-Room Reference Observation

- A metadata-safe note about layout rhythm only.
- Must not include private screenshots, transcript text, account identifiers, or copied assets.
