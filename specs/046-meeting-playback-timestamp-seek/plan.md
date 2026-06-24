# Implementation Plan: Meeting Playback Timestamp Seek

**Branch**: `046-meeting-playback-timestamp-seek` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/046-meeting-playback-timestamp-seek/spec.md`

## Summary

Close the MVP meeting-review playback gap by adding policy-aware retained-audio
playback and transcript timestamp seek to the existing server-owned web cabinet
and desktop embedded review. The feature extends the current review contract
and cabinet shell; it does not add public audio links, transcript editing,
waveform generation, video, or echo/noise suppression.

## Technical Context

**Language/Version**: Python 3.13 for server runtime and tests; Swift 6 only
for existing desktop embedded review regression checks if needed.

**Primary Dependencies**: FastAPI, SQLAlchemy async, existing cabinet access and
artifact egress policy, MinIO-backed server storage, server-rendered web
cabinet, WebKit embedded desktop cabinet.

**Storage**: Existing Postgres meeting, track artifact, processing result,
transcript, diarization, access, artifact policy, egress audit, retention, and
deletion tables; existing MinIO object storage for retained track artifacts.
No new persistent table is required for MVP playback.

**Testing**: Server contract, integration, unit, and web-shell tests under
`apps/server/tests`; optional macOS focused tests for embedded cabinet shell if
the desktop bridge contract changes; full `infra/scripts/ci-local.sh` before
PR readiness.

**Target Platform**: Existing 2brain Rec Linux/Docker server plus browser web
cabinet and macOS embedded WebKit review surface.

**Project Type**: FastAPI backend with server-rendered web UI embedded by the
native macOS desktop app.

**Performance Goals**:

- For an authorized processed meeting, playback availability appears with the
  rest of meeting detail in one page load.
- Timestamp activation seeks to the selected segment within one second in
  browser runtime checks.
- Playback authorization and unavailable-state checks use existing meeting
  policy state without creating duplicate meetings, artifacts, or egress rows.

**Constraints**:

- No raw storage path, signed URL, credential, private local path, transcript
  content, or private meeting content may appear in logs, diagnostics,
  screenshots, or committed evidence.
- Playback must be server-mediated and policy-gated; browser and desktop
  surfaces must not receive object-storage URLs.
- Unauthorized, deleted, deleting, audio-purged, transcript-only, processing,
  and failed states must not expose playable audio.
- Desktop clients still never call MediaScribe directly and never store
  MediaScribe credentials.
- UI must remain original 2brain Rec clean-room design, Russian-first, keyboard
  accessible, and responsive without horizontal overflow.

**Scale/Scope**: One owner/workspace MVP review journey, one server-mediated
review audio stream per meeting, existing dual-track artifacts, desktop and
mobile viewports, and metadata-only validation evidence. For normal dual-track
meetings, the review stream represents both retained microphone and
incoming/system sources; if it cannot, playback fails closed with a truthful
unavailable reason. Public links, waveform generation, editing, video,
generated notes/actions, and AEC/noise suppression remain outside this slice.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Plan Response |
|---|---|---|
| Capture-first MVP integrity | PASS | Uses accepted retained recording artifacts; does not change live capture, permissions, or routing. |
| Visible consent and one-action stop | PASS | Does not change active capture behavior or stop controls. |
| Data boundary and secret discipline | PASS | Playback is server-mediated; no direct object-storage or dependency URL is exposed. |
| Deletion truth and lifecycle accounting | PASS | Deleted, deleting, purged, and transcript-only states block playback and show truthful copy. |
| Spec-driven delivery | PASS | Spec, plan, research, data model, contract, quickstart, checklist, tasks, analyze, and implementation are used. |
| Metadata-only diagnostics/evidence | PASS | Validation records statuses, durations, and seek behavior only; no private audio or transcript text. |

No constitution violation is required.

## Project Structure

### Documentation (this feature)

```text
specs/046-meeting-playback-timestamp-seek/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- checklists/
|   |-- requirements.md
|   |-- security.md
|   `-- ux.md
|-- contracts/
|   `-- playback-review-contract.md
|-- evidence/
|   `-- validation-log.md
`-- tasks.md
```

### Source Code (repository root)

```text
apps/server/
|-- src/twobrain_rec_server/api/
|   |-- cabinet.py
|   `-- schemas.py
|-- src/twobrain_rec_server/cabinet/
|   |-- egress.py
|   |-- playback_audio.py
|   |-- queries.py
|   |-- view_models.py
|   `-- web.py
|-- src/twobrain_rec_server/storage/
|   `-- minio_client.py
`-- tests/
    |-- contract/
    |-- integration/
    `-- unit/

apps/macos/
`-- Shared/Tests/ or RecApp tests only if embedded cabinet routing contracts change
```

**Structure Decision**: Extend the existing cabinet review and artifact policy
surface. Do not create a new playback service, public file URL layer, desktop
audio dependency, or separate frontend app.

## Complexity Tracking

No constitution violations are required.

## Phase 0 Research Decisions

See [research.md](./research.md). Key decisions:

1. Use a server-mediated playback route that reuses existing access and artifact
   policy truth.
2. Represent playback availability in the meeting review contract with explicit
   unavailable reasons and safe metadata.
3. Make transcript timestamp labels activatable controls with segment start
   seconds as the seek target.
4. Keep the MVP player simple: play/pause, progress/current time, duration,
   speed options, and transcript seek; no waveform.
5. Require dual-track review playback to represent both retained speech sources
   or fail closed.
6. Keep validation evidence metadata-only.

## Phase 1 Design Decisions

Design artifacts:

- [data-model.md](./data-model.md): playback availability, policy states,
  transcript seek targets, and validation evidence.
- [contracts/playback-review-contract.md](./contracts/playback-review-contract.md):
  review response, playback route, web/desktop behavior, and blocked states.
- [quickstart.md](./quickstart.md): focused validation commands, browser runtime
  checks, and evidence requirements.

## Post-Design Constitution Check

| Gate | Status | Design Response |
|---|---|---|
| Capture-first MVP integrity | PASS | Playback reads retained artifacts after capture; no capture path changes. |
| Visible consent and one-action stop | PASS | No active-capture behavior changes. |
| Data boundary and secret discipline | PASS | Contract forbids storage URLs, signed URLs, credentials, private paths, and content in evidence. |
| Deletion truth and lifecycle accounting | PASS | Playback availability is denied for deleted, deleting, audio-purged, transcript-only, unauthorized, processing, and failed states. |
| Spec-driven delivery | PASS | Design artifacts map to checklists, tasks, and validation gates. |
| Metadata-only diagnostics/evidence | PASS | Quickstart and contract require metadata-only proof. |
