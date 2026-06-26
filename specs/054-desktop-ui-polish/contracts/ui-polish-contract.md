# UI Polish Contract

## Scope

This contract covers meeting list density, embedded workspace fill, left navigation, and right inspector rail layout for 054.

## Required Invariants

- Embedded web list MUST include `desktop-embedded` and a workspace max-width of at least `1040px`.
- Embedded list row desktop height MUST be between `44px` and `52px`.
- Meeting list rows MUST keep title, duration, status, action slots, and date in stable columns.
- Native shell collapsed inspector MUST remain present in idle mode.
- Native shell expanded inspector MUST not exceed `288px`.
- Native capture controls, upload truth, recording trust, and diagnostics MUST remain reachable.
- Detail pages MUST preserve tabs, playback shell, transcript, right-panel governance, deletion truth, and speaker timeline.
- No rendered HTML or Swift copy may introduce KRISP brand copy, private reference content, credentials, or local private paths.

## Validation

Use [quickstart.md](../quickstart.md). Passing focused server and macOS tests is required before marking tasks complete.
