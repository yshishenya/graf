# Implementation Plan: Real Playback Availability

**Branch**: `048-real-playback-availability` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/048-real-playback-availability/spec.md`

## Summary

Make playback visible and useful on the real owner review path by separating
review playback from artifact download/export policy, adding server-mediated
range playback, and upgrading the web/embedded review UI into a persistent
bottom player with timestamp seek and speaker timeline context. This fixes the
`046` gap where playback passed fixture validation only when tests manually set
`audio_download="allowed"`.

## Technical Context

**Language/Version**: Python 3.13 for server runtime/tests; Swift 6 only for
existing macOS embedded cabinet validation if the desktop wrapper changes.

**Primary Dependencies**: FastAPI, SQLAlchemy async, existing cabinet access,
existing artifact egress audit, MinIO-backed storage abstraction, server-rendered
web cabinet, WebKit embedded macOS cabinet.

**Storage**: Existing Postgres meeting, track artifact, processing result,
transcript, diarization, access, egress audit, deletion, and artifact-policy
tables; existing MinIO/object storage for retained `mic.wav` and `incoming.wav`.
No new table is required for 048.

**Testing**: Server contract, integration, unit, and web-shell tests under
`apps/server/tests`; browser runtime validation via Playwright/Chrome for web
and embedded pages; existing macOS focused tests only if embedded route policy
or app shell changes; `infra/scripts/ci-local.sh` before closeout.

**Target Platform**: Existing Linux/Docker server, browser web cabinet, and
macOS app embedded WebKit cabinet.

**Project Type**: FastAPI backend with server-rendered web UI embedded by the
native macOS app.

**Performance Goals**:

- Owner review playback availability is computed during meeting detail loading
  without an operator policy write.
- Browser playback route supports `Range` so initial load and seeking use
  stream-like browser behavior instead of forcing a user-visible download.
- Timestamp activation moves playback to the selected segment within one second
  in browser runtime validation.
- Review playback does not create duplicate processing results, duplicate
  meeting artifacts, or duplicate policy rows.

**Constraints**:

- Review playback is not the same as artifact download/export.
- The player must use a server-owned relative route; no signed URL, object key,
  storage path, credential, raw audio, private transcript text, private meeting
  title, or account identifier may appear in committed evidence.
- Unauthorized, deleted, deleting, audio-purged, transcript-only, processing,
  failed, missing-source, storage-unavailable, and unsafe-review-audio states
  must fail closed.
- Normal dual-track review playback must include both microphone and
  incoming/system sources or be unavailable with a safe reason.
- Web and embedded macOS review must use the same HTML/contract and preserve
  clean-room brand distance from Krisp.

**Scale/Scope**: One owner/workspace MVP review journey, existing retained
dual-track recordings, one server-mediated review playback route, desktop and
mobile viewport validation, and metadata-only evidence. Waveforms, transcript
editing, speaker reassignment, native Swift player controls, public links,
real AEC/noise suppression, and server-side cached review-stream materialization
are out of scope unless validation proves caching is required for MVP usability.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Plan Response |
|---|---|---|
| Capture-first MVP integrity | PASS | Uses retained artifacts after accepted capture; does not change live capture, permissions, routing, or local recording truth. |
| Visible consent and one-action stop | PASS | Does not alter active recording controls or indicators. |
| Data boundary and secret discipline | PASS | Server-mediated route only; no direct storage URL or desktop credential path. |
| Deletion truth and lifecycle accounting | PASS | Deleted, deleting, purged, and transcript-only states block playback and keep truth copy. |
| Spec-driven delivery | PASS | 048 has spec, clarification review, plan, research, data model, contract, quickstart, checklists, tasks, analyze, and implementation. |
| Metadata-only diagnostics/evidence | PASS | Evidence records availability, headers, durations, viewport results, and pass/fail counts only. |

No constitution violation is required.

## Project Structure

### Documentation (this feature)

```text
specs/048-real-playback-availability/
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
|   `-- review-playback-contract.md
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
`-- tests/
    |-- contract/
    |-- integration/
    `-- unit/

apps/macos/
`-- Shared/Tests/ only if embedded cabinet wrapper behavior changes
```

**Structure Decision**: Extend the existing cabinet review path. Do not create
a new frontend app, public file route, direct MinIO URL, desktop-specific audio
player, or MediaScribe/client credential path.

## Complexity Tracking

No constitution violations are required.

## Phase 0 Research Decisions

See [research.md](./research.md). Key decisions:

1. Review playback is separate from artifact download/export policy.
2. Playback route uses server-mediated range semantics, not public signed URLs.
3. The desired UX is a clean-room Krisp-like pattern: transcript-first detail
   plus persistent bottom player and speaker timeline.
4. Speaker lanes use diarization segment timing, not just speaker percentages.
5. Evidence remains metadata-only.

## Phase 1 Design Decisions

Design artifacts:

- [data-model.md](./data-model.md): review playback availability, range
  response, speaker timeline lane, and validation evidence.
- [contracts/review-playback-contract.md](./contracts/review-playback-contract.md):
  review response, playback route, UI contract, blocked states, and evidence.
- [quickstart.md](./quickstart.md): focused tests, browser runtime validation,
  macOS embedded parity, and repository gates.

## Post-Design Constitution Check

| Gate | Status | Design Response |
|---|---|---|
| Capture-first MVP integrity | PASS | No capture path changes; reads accepted retained audio artifacts only. |
| Visible consent and one-action stop | PASS | No active capture behavior changes. |
| Data boundary and secret discipline | PASS | Contract forbids direct storage URLs, signed URLs, object keys, credentials, and private paths. |
| Deletion truth and lifecycle accounting | PASS | Availability and route deny deleted/deleting/purged/transcript-only states. |
| Spec-driven delivery | PASS | Tasks and quickstart map to every FR/SC. |
| Metadata-only diagnostics/evidence | PASS | Quickstart forbids raw audio and private transcript content in evidence. |
