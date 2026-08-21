# Implementation Plan: Canonical Provider Speaker Turns

**Branch**: `182-canonical-speaker-turns` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/182-canonical-speaker-turns/spec.md`

## Summary

Replace GRAF's three winner-takes-all speaker reconstructions with one pure
canonicalization function. Contract-valid provider-attributed rows become the
canonical temporal turns; raw ASR rows remain separate unattributed evidence.
Unsafe provider results degrade to one mixed/uncertain ASR projection, with
metadata-only diagnostics and no guessed speaker or deduplication. Stable
meeting-local speaker keys preserve the raw provider key without exposing it as
the editable display label.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2, openpyxl; no new dependency

**Storage**: Existing PostgreSQL `processing_results`, `transcript_segments`, `diarization_segments`, `meeting_speaker_names`, and `processing_audit_events`; no migration planned

**Testing**: pytest unit, contract, and PostgreSQL integration suites

**Risk / Validation Lane**: `high-risk-feature` because this changes transcription truth, speaker identity, diagnostics, public API/export contracts, and downstream AI input

**Release Gate**: No commit, deploy, or MediaScribe change. Stop after local validation and request separate approval.

**Target Platform**: GRAF Linux server and browser cabinet

**Project Type**: Python web service with server-rendered cabinet UI

**Performance Goals**: Deterministic linear or sort-dominated canonicalization for existing meeting-scale segment counts; no provider or model call

**Constraints**: Preserve source Decimal timestamps; never infer a winner; diagnostics contain no transcript/audio/provider payload; existing records remain readable; normal recording and manual upload converge

**Scale/Scope**: One GRAF canonical speaker-turn model and its review, timeline, export, VTT, rename, outcomes, and import-diagnostic consumers

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- **Capture-first integrity — PASS**: capture, audio artifacts, upload retry, and
  MediaScribe runtime are unchanged. The change starts after GRAF receives a
  provider result.
- **Visible control — PASS**: recording controls and consent behavior are not
  touched.
- **Data and secret boundary — PASS**: canonicalization is local to GRAF.
  Diagnostics allow only IDs, versions, counts, bounded statuses, and a hash;
  fixtures are synthetic.
- **Deletion truth — PASS**: no new content store is introduced. Audit metadata
  uses the existing meeting lifecycle and redaction boundary.
- **Distribution integrity — PASS**: macOS packaging and update paths are out of
  scope.
- **Spec-driven delivery — PASS**: mandatory clarify, plan, domain checklists,
  tasks, analyze, issue sync, implementation, quickstart, and repository gate
  are required.
- **Provider boundary — PASS**: GRAF validates and presents the received result;
  MediaScribe code, configuration, runtime, and deployment remain unchanged.

### Post-design re-check

The design uses existing result/segment/name/audit storage and one shared pure
model. No schema migration, new service, dependency, or constitution exception
is required. Provider defects and GRAF projection defects remain separately
named in diagnostics and validation evidence.

## Validation Plan

1. Write synthetic failing tests before implementation for 2/3-turn ASR
   overlaps, below-50-percent winner, 40 ms unknown, triplicated full text,
   invalid timing/chronology/conservation, and stable 1/2/11-label fixtures.
2. Prove normal-recording/manual-upload parity and stable saved-name binding.
3. Compare API transcript, speaker timeline, Markdown, CSV, XLSX, SRT, VTT,
   JSON, and outcomes from the same canonical model, including degraded state.
4. Prove sub-millisecond input ordering and boundaries remain stable while
   renderers round only their output.
5. Prove audit diagnostics contain only allowlisted metadata and all required
   counts/status/version/hash fields.
6. Run the focused commands in [quickstart.md](quickstart.md), then
   `infra/scripts/ci-local.sh --fast` as the repository gate.
7. Inspect `git diff`, scan changed/fixture files for forbidden content, verify
   zero MediaScribe external repository/runtime/config/deploy changes, and stop
   without commit or deploy.

## Project Structure

### Documentation (this feature)

```text
specs/182-canonical-speaker-turns/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── canonical-speaker-turns.md
│   └── diagnostics.md
├── checklists/
│   ├── requirements.md
│   ├── transcription-data-contract.md
│   ├── diagnostics-privacy.md
│   └── infra-provider-boundary.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/schemas.py
├── cabinet/
│   ├── view_models.py
│   ├── exports.py
│   ├── rendering.py
│   └── speakers.py
├── domain/speaker_turns.py
├── mediascribe/
│   ├── schemas.py
│   ├── client.py
│   └── import_results.py
├── outcomes/service.py
├── processing/
│   ├── audit.py
│   ├── store.py
│   └── submit.py
└── tests/
    ├── unit/
    ├── contract/
    └── integration/
```

**Structure Decision**: Keep the shared canonical model in one pure domain
module and reuse it from review, timeline, exports, outcomes, and the GRAF
MediaScribe adapter. Persist only bounded status/diagnostics through existing
result and audit fields.

## Complexity Tracking

No constitution violations require justification.
