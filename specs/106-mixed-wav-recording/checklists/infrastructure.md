# Processing and Infrastructure Requirements Checklist: Чистый единый аудиопоток

**Purpose**: Validate server ingest, MediaScribe, playback normalization and operational compatibility requirements before implementation.

**Created**: 2026-07-17

**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [processing contract](../contracts/processing-lifecycle-and-rollback.md)

## Contract Completeness

- [X] CHK001 Are source-kind-specific exact role-set requirements defined separately for historical `initial_recording`, v5 `initial_mixed_recording` and `manual_upload`? [Completeness, Plan §4, Processing Contract §Server Validation]
- [X] CHK002 Are v5 descriptor requirements for WAV codec/rate/channels and M4A codec/rate/channels specified at both session creation and finalization boundaries? [Completeness, Plan §4, Data Model §Server Revision And Artifacts]
- [X] CHK003 Is the requirement that source kind and role set are validated together explicit enough to prevent an accepted but unprocessable revision? [Clarity, Research §Finding: server seam, Processing Contract §Server Validation]
- [X] CHK004 Are multipart field count, filename extension and `audio/wav` content type requirements precise for a v5 MediaScribe submission? [Measurability, Processing Contract §MediaScribe Egress]
- [X] CHK005 Are polling/import idempotency, unknown submission outcome and revision/workspace isolation requirements complete for normal, restart and retry flows? [Coverage, Spec §FR-008/FR-012, Processing Contract §MediaScribe Egress]

## Lifecycle And Compatibility

- [X] CHK006 Are v5 playback candidate reuse requirements consistent with the existing playback-normalization lifecycle and its authoritative source fingerprint? [Consistency, Plan §4, Processing Contract §Playback and Deletion]
- [X] CHK007 Are v3/v4 historic dual endpoint/worker retention and eventual retirement conditions stated without making them active v5 acceptance dependencies? [Completeness, Spec §FR-010/FR-013, Plan §5]
- [X] CHK008 Is the order of additive server compatibility, v5 desktop canary, rollback and later dual cleanup specified so no accepted package becomes unreadable? [Coverage, Processing Contract §Control Period and Rollback]
- [X] CHK009 Are API/OpenAPI, storage, Temporal and deletion compatibility impacts identified even though a database migration is intentionally excluded? [Dependency, Plan §Technical Context, Data Model §Server Revision And Artifacts]

## Operational And Evidence Requirements

- [X] CHK010 Are timeout, temp-storage, malformed-result and unavailable-provider requirements sufficiently explicit to yield safe, bounded statuses rather than silent retry loops? [Coverage, Spec §FR-012, Data Model §Processing State]
- [X] CHK011 Are operational evidence requirements limited to safe identifiers, hashes, counts, durations and statuses while excluding payload content and secrets? [Consistency, Plan §Constraints/§Validation Plan]
- [X] CHK012 Are local synthetic end-to-end and installed-app hardware evidence requirements distinguished from separately approved deployed/provider proof? [Clarity, Quickstart §Synthetic end-to-end path/§Closeout]
- [X] CHK013 Is the no-new-dependency/no-new-worker/no-new-table constraint reconciled with all required compatibility and failure-state requirements? [Consistency, Plan §Technical Context/§Structure Decision]

## Review Result

- Requirements review passed on 2026-07-17; the v5 package has an explicit server boundary, bounded operational outcomes and a separate deployment gate.
