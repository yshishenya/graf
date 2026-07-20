# Implementation Plan: Canonical Speaker Turns for Transcript Review

**Branch**: `113-transcript-speaker-turns` | **Date**: 2026-07-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/113-transcript-speaker-turns/spec.md`

## Summary

Keep the existing raw transcript segments as the compatibility source and add a
server-derived `speaker_turns` read model for review. The existing transcript
and diarization mapping in `cabinet/view_models.py` is the seam: after a row has
an established speaker label, a small deterministic pass groups same-speaker
rows within the inclusive one-second gap rule and preserves source ids/timing.
The server-rendered cabinet reads derived turns, while raw segments remain in
the response for playback precision, compatibility, and provider replacement.
No provider call, client credential path, database table, migration, or new
runtime dependency is needed.

## Technical Context

**Language/Version**: Python 3.13 server; existing Pydantic and SQLAlchemy models.

**Primary Dependencies**: FastAPI/Pydantic response schemas, existing cabinet
view-model and server-rendered cabinet code, pytest, Ruff. No new dependency.

**Storage**: Existing Postgres `processing_results`, `transcript_segments`, and
`diarization_segments` remain the source of truth. Derived turns are computed
for the review response and are not persisted in this slice.

**Testing**: Focused server contract, view-model, and rendering tests; then
`infra/scripts/ci-local.sh` as the required repository gate.

**Risk / Validation Lane**: `high-risk-feature`. This changes the shared
transcription/review contract and user-visible meeting content, and must follow
the full Spec Kit sequence with metadata-only evidence.

**Release Gate**: No deploy in this slice. A production rollout requires the
normal release/deploy approval and smoke evidence after merge.

**Target Platform**: Linux/Docker GRAF server plus browser and embedded macOS
cabinet review surfaces. macOS capture and provider submission remain outside
the change.

**Project Type**: Server web/API service with server-rendered review UI and
existing macOS embedded client.

**Performance Goals**: One linear pass over the already loaded review rows;
no additional provider request and no more than one derived turn per eligible
source sequence. A one-hour transcript remains within the existing review
response budget.

**Constraints**: Raw transcript text and timing must remain recoverable; no
provider-specific fields or credentials may enter the client contract; no
unsafe merge across speaker, processing result, source role, unknown mapping,
or invalid timing; no raw content in diagnostics/evidence.

**Scale/Scope**: One selected processing result and its bounded transcript /
diarization rows per meeting review. No persisted backfill table, search/export
redesign, diarization tuning, or provider migration is included.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Plan Response |
|---|---|---|
| Capture-first MVP integrity | PASS | No capture, audio routing, permission, recording, or playback-source behavior changes. |
| Visible consent and user control | PASS | This is post-processing/review only; visible capture and one-action stop remain unchanged. |
| Data boundary and secret discipline | PASS | Clients receive only GRAF-owned transcript data; provider credentials and external job details stay server-side. |
| Deletion truth and lifecycle accounting | PASS | No new durable artifact is introduced; derived turns disappear with the existing meeting data. |
| External dependency boundary | PASS | No new MediaScribe call or provider coupling; the canonical rule is server-owned and rebuildable. |
| User-facing review and accessibility | PASS | Existing escaped server-rendered transcript surface is reused; raw rows remain available and timestamp seeking is preserved. |
| Spec-driven delivery | PASS | Specify, clarify, plan, checklist, tasks, analyze, issue sync, and implement are required before code. |
| Metadata-only evidence | PASS | Fixtures and receipts use synthetic ids/text and exclude audio, private transcript content, secrets, and signed URLs. |

No constitution violation is required.

## Validation Plan

- Run `tests/contract/test_transcript_turn_contract.py` for the additive
  response shape and raw/derived compatibility.
- Run focused `test_cabinet_view_models.py` cases for mapping, one-second
  inclusive threshold, pairwise gaps, speaker/source/result boundaries,
  unknown labels, idempotence, and seek timing.
- Run focused `test_cabinet_web_shell.py` cases proving rendered transcript rows
  prefer turns and remain escaped.
- Run Ruff on the changed server files and `git diff --check`.
- Run `infra/scripts/ci-local.sh` because this is shared high-risk transcript
  behavior.
- Do not run `infra/scripts/cd-remote.sh` or perform a provider switch/backfill;
  those are separate release/operations gates.

## Project Structure

### Documentation (this feature)

```text
specs/113-transcript-speaker-turns/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── canonical-transcript-turns.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/api/schemas.py
apps/server/src/twobrain_rec_server/cabinet/view_models.py
apps/server/src/twobrain_rec_server/cabinet/rendering.py
apps/server/tests/contract/test_transcript_turn_contract.py
apps/server/tests/unit/test_cabinet_view_models.py
apps/server/tests/unit/test_cabinet_web_shell.py
```

**Structure Decision**: Reuse the existing server-owned transcript schema,
view-model, and rendering paths. Add one small derivation helper in the current
view-model module and one additive schema field. Do not add a new service,
repository layer, persistence table, client transcription adapter, or runtime
dependency.

## Complexity Tracking

No constitution violations.

## Phase 0 Research Decisions

See [research.md](./research.md). The important choices are server-side
post-diarization derivation, raw-segment preservation, a one-second inclusive
pairwise rule, and no provider/storage changes.

## Phase 1 Design Decisions

See:

- [data-model.md](./data-model.md) for raw and derived entities, boundaries,
  and lifecycle.
- [contracts/canonical-transcript-turns.md](./contracts/canonical-transcript-turns.md)
  for the additive response contract and compatibility behavior.
- [quickstart.md](./quickstart.md) for focused checks and the full repository
  gate.

## Post-Design Constitution Check

| Gate | Status | Design Response |
|---|---|---|
| Capture-first MVP integrity | PASS | Design stops at imported transcript review and does not alter capture or source artifacts. |
| Visible consent and user control | PASS | No recording start, notice, or stop behavior is changed. |
| Data boundary and secret discipline | PASS | The new field is GRAF-owned, provider-neutral, and content is kept inside existing authorized review egress. |
| Deletion truth and lifecycle accounting | PASS | Turns are ephemeral derived data with no independent retention or deletion state. |
| External dependency boundary | PASS | Equivalent canonical provider inputs yield the same turns; no client/provider coupling is introduced. |
| User-facing review and accessibility | PASS | Existing timestamp controls, escaped text, and server-rendered structure are reused. |
| Spec-driven delivery | PASS | The design maps each story to independently testable tasks with exact paths. |
| Metadata-only evidence | PASS | Quickstart and tests forbid real meeting content and provider payloads in committed artifacts. |

No unresolved critical design decision remains.
