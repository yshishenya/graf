# Telemetry And Diagnostics Checklist: 092 Automatic Meeting Detection

**Date**: 2026-07-08

## Contract Quality

- [x] Telemetry schema requires `candidateFilterVersion`.
- [x] Telemetry schema distinguishes `redacted` from `raw_candidate_allowed`.
- [x] Telemetry schema requires `server_candidate_upload` for raw candidate
  identity.
- [x] Telemetry schema requires score at least `4` for server candidate upload.
- [x] Admin review schema exposes bounded safe candidate fields and allowed
  actions.

## Candidate Filtering

- [x] VKS-candidate scoring includes stable mic attribution, duration,
  recurrence, manual-record-nearby, calendar/join hint, VKS name tokens, and
  vendor hints.
- [x] Explicit non-target matches block upload.
- [x] Browsers, Krisp/audio utilities, system services, media players, audio
  editors, games, screen recorders, and known utilities are suppressed before
  upload.
- [x] Low-score unknown apps remain local aggregate evidence only.
- [x] Candidate upload is rate-limited to at most one candidate rollup per app per
  day.

## Operational Evidence

- [x] Known target health tracks observed, clean end, short test, prejoin-like,
  missed manual start, expected signal absent, and degraded health.
- [x] Quickstart requires forbidden-content scans.
- [x] Resource metrics include CPU, memory, disk, upload attempts, parser restarts,
  and dropped event counts.
- [x] Telemetry data model includes local and server retention limits.
- [x] Admin review queue separates candidates, known target health, and registry
  drafts.

## Implementation Validation Requirements

- [x] Requirements specify validation that raw unified-log lines are not stored
  locally after parsing.
- [x] Requirements specify upload payload validation against full paths and raw
  URLs.
- [x] Requirements specify validation that admin "mark non-target" produces a
  client-consumable suppression rule in the next registry.
