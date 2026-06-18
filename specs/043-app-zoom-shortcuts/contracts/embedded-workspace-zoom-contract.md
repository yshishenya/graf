# Embedded Workspace Zoom Contract

## Purpose

Define the observable behavior required for app-level zoom shortcuts in the
desktop meeting workspace.

## Keyboard Commands

- Command-Plus and Command-Equals increase workspace zoom by one supported step.
- Command-Minus decreases workspace zoom by one supported step.
- Command-0 resets workspace zoom to 100%.
- Existing Command-Shift-R recording and Escape stop shortcuts remain unchanged.

## Supported Values

- Default: 100%.
- Minimum: 80%.
- Maximum: 140%.
- Step: 10 percentage points.
- Repeated commands clamp at the supported bounds.

## Persistence

- The app persists the current supported zoom value locally.
- A saved supported value is restored on the next app launch.
- Missing, invalid, non-finite, or out-of-range persisted values fall back to
  the default value.

## Embedded Workspace Application

- The current zoom value applies to the embedded meeting workspace when the web
  surface is created.
- The current zoom value updates the embedded workspace without reloading the
  current route.
- Zoom changes do not mutate request URLs, workspace headers, auth state, upload
  queue state, recording state, or deletion state.

## Native Shell Boundary

- Native Record, Stop, upload truth, and local audio readiness controls are not
  scaled by this feature.
- The visible capture indicator and one-action stop remain reachable after every
  supported zoom command.
- User-facing copy avoids implementation labels such as "web view".

## Validation Evidence

- XCTest proves command mapping, stepping, clamping, reset, persistence fallback,
  WebKit bridge application, and native-shell boundary invariants.
- Manual smoke proves the keyboard shortcuts work in the running app when a
  cabinet URL is configured.
