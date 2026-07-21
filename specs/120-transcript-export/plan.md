# Implementation Plan: Canonical Transcript And Summary Export

**Branch**: `120-transcript-export` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/120-transcript-export/spec.md`

## Summary

Add one server-owned, immutable export snapshot pinned to a selected processing
result and the current stored outcome set. TXT, MD, CSV, JSON, SRT, and XLSX are
pure projections of that snapshot; the existing raw transcript contract remains
unchanged. Reuse feature 113 turn derivation after hardening unknown/boundary
semantics, feature 049 stored outcomes, and feature 017 access, egress, audit,
deletion, and post-egress truth. Generate all six formats on demand in the
request transaction. Do not add an export table, background workflow, object
storage artifact, package redesign, or provider call in this slice.

## Technical Context

**Language/Version**: Python 3.13 server; Jinja HTML, cabinet CSS, and vanilla
JavaScript for browser and embedded macOS cabinet surfaces.

**Primary Dependencies**: Existing FastAPI, Pydantic v2, SQLAlchemy 2 async,
Jinja, feature 113 canonical-turn view models, feature 049 outcome models, and
feature 017 egress/audit policy. Add `openpyxl` only for standards-compliant
write-only XLSX generation; no other runtime dependency.

**Storage**: Existing PostgreSQL processing results, raw transcript/diarization
rows, meeting-scoped speaker names, outcome sets/items, artifact policies, and
egress audit events. Export bytes are generated on demand and not persisted.

**Testing**: Focused pytest unit, contract, integration, PostgreSQL/RLS, and
server-rendered cabinet tests; generated-file parsing checks; in-app browser
keyboard/screen-reader/design QA; Ruff, `git diff --check`, and
`infra/scripts/ci-local.sh` at closeout.

**Risk / Validation Lane**: `high-risk-feature`. This changes transcript and
summary egress, authorization, audit, deletion truth, shared API contracts, and
user-facing UX, so clarify, plan/research, checklist, tasks, clean analyze,
issue sync, implementation, and repository validation are mandatory.

**Release Gate**: No deploy in this planning/implementation lane. Production
deployment requires a separate release approval, dry-run, execute, smoke, and
rollback evidence.

**Target Platform**: Linux/Docker GRAF server, browser cabinet, and the same
server-owned meeting detail embedded by the macOS app.

**Project Type**: FastAPI web/API service with server-rendered product UI.

**Performance Goals**: Ready 60-minute TXT/MD/CSV/JSON/SRT responses within
five seconds; XLSX/combined generation exposes progress within one second and
finishes within thirty seconds in the supported test environment. Snapshot
assembly and text serializers are linear in raw rows, turns, and outcome items.

**Constraints**: Raw segments remain durable truth; structured/caption formats
use one canonical turn per row/cue; no invented pause text or confirmed speaker;
no provider call; no content or secrets in logs/audit/evidence; access,
artifact policy, readiness, deletion, and audit fail closed; existing raw/plain
download and package manifest behavior remain truthful and compatible.

**Scale/Scope**: One meeting, one explicitly selected terminal processing
result, one current stored outcome set, six formats, three content scopes, and
the fixture matrix in `quickstart.md`. PDF, DOCX, ZIP, batch, public links,
integrations, translation, retranscription, audio export, and draft export are
excluded.

## Constitution Check

*GATE: Passed before Phase 0 research; re-checked after Phase 1 design.*

| Gate | Status | Plan Response |
|---|---|---|
| Capture-first MVP integrity | PASS | Post-processing export does not change native capture, routing, upload, or playback-source truth. |
| Visible consent and user control | PASS | No recording action is added; export is an explicit post-meeting user action. |
| Data boundary and secret discipline | PASS | Server builds GRAF-owned provider-neutral bytes; credentials, signed URLs, object keys, provider jobs, raw audio, and private paths are excluded. |
| Deletion truth and lifecycle accounting | PASS | Every request re-checks lifecycle; no controlled copy is retained; copy states that already downloaded files cannot be revoked by GRAF. |
| Authorization and audit | PASS | Feature 017 policy and metadata-only fail-closed audit are reused for transcript, summary, and combined scopes. |
| AI and external dependency boundary | PASS | Summary is read from the current stored outcome set; export never regenerates or calls STT/LLM providers. |
| User-facing review and accessibility | PASS | Existing cabinet/dialog primitives, focus management, keyboard operation, non-color states, localization, and safe errors are required. |
| Original design / brand distance | PASS | Competitor research informs capabilities only; GRAF layout, language, icons, and styles remain original. |
| Spec-driven delivery | PASS | Implementation remains blocked until checklist, tasks, and read-only analyze are clean. |
| Metadata-only evidence | PASS | Fixtures are synthetic; audit, logs, screenshots, specs, and receipts contain no private meeting content. |

No constitution violation is required.

## Architecture Decisions

### 1. One immutable export snapshot and revision pinning

The export route resolves access, policy, meeting lifecycle, requested
`processing_result_id`, current `MeetingOutcomeSet` when selected, raw rows,
speaker names, and outcome items in one short database transaction. It builds a
frozen provider-neutral snapshot before any serializer runs. Snapshot identity
is the tuple of meeting, processing result, outcome-set id/content hash,
canonical-turn policy version, and export schema version. A newer result or
outcome cannot enter an in-flight snapshot.

Feature 113 remains the single turn rule. Its current helper is hardened so an
unconfirmed/unknown row becomes a non-mergeable singleton canonical turn rather
than disappearing or becoming confirmed `SPEAKER_00`; result, stable speaker
key, attribution state, source role, overlap, invalid timing, and the inclusive
one-second boundary are explicit inputs. UI display groups are derived only by
TXT/MD renderers and never replace snapshot turns.

### 2. On-demand artifacts; no durable generated-copy model

All selected formats are bounded meeting text and are generated directly into a
response buffer. This satisfies revision pinning and idempotency without a new
table, Temporal workflow, MinIO object, expiry worker, or deletion branch.
`Content-Length`, content hash, renderer version, and byte length are available
before the completion audit is committed. If validated XLSX/combined exports
later exceed the thirty-second or memory budget, a separate slice may introduce
the already specified short-lived artifact lifecycle.

### 3. Serializers and escaping

One serializer dispatch consumes only the snapshot. TXT/MD optionally group
short adjacent readable runs but keep child turn timestamps. CSV uses Python's
`csv` writer, UTF-8 with BOM for spreadsheet compatibility, stable columns, and
neutralizes formula-leading untrusted cells. Markdown backslash-escapes ASCII
punctuation and never emits raw HTML. JSON uses sorted keys, UTF-8, stable list
order, integer milliseconds, and an explicit schema version. SRT emits one cue
per eligible canonical turn with `HH:MM:SS,mmm`, strips/escapes markup-like
input, preserves valid overlap, rejects invalid intervals, and emits no gap cue.

XLSX uses `openpyxl` write-only workbooks because OOXML is a multi-part standard
and hand-writing it would add more custom code and interoperability risk than
one focused dependency. Cells containing untrusted text are always written as
strings, never formulas. The fixed sheets are `Transcript`, `Summary`,
`Action Items`, and `Metadata`; unavailable sections remain explicit.

### 4. Stored summary model and turn references

`MeetingOutcomeSet` plus ordered `MeetingOutcomeItem` rows are the saved summary
source. The snapshot records outcome-set id, generator/template version,
content hash, category states, source processing result, and item order. Existing
segment references are resolved to canonical turn ids when possible; unresolved
raw references stay explicit and are never guessed. Export does not call the
outcome generator and does not mutate outcome items.

### 5. API, egress, policy, audit, and deletion

Keep `/downloads/transcript` and the existing manifest-only `/exports` package
contract unchanged. Add a versioned canonical file route under
`/api/v1/cabinet/meetings/{meeting_id}/content-exports` and a metadata-only
capability endpoint for the dialog. The service reuses `artifact_egress_states`,
`resolve_artifact_policy`, `record_egress_audit_event`, safe problem details,
and deletion checks. Content is returned only after the completion audit
persists. Audit allowlisting expands only for format, content scope, pinned
revision ids/versions, renderer version, outcome, and byte length.

Transcript, summary, and combined decisions are evaluated separately; combined
requires both component permissions/readiness. Deletion-in-progress, revoked
access, policy denial, missing/partial content, unsupported format, revision
mismatch, serializer failure, or audit failure returns no export bytes.

### 6. UI/UX/IA

Meeting detail gains one contextual `Экспорт` action shared by transcript and
summary, while the Files/governance panel shows the current availability state.
The existing dialog/sheet primitives present content scope first, then compatible
format groups, options, revision/readiness metadata, and a concise safe preview.
The preview is structural/sample-free by default so it cannot leak content.

Submitting shows an accessible progress state, disables duplicate submission,
and restores focus on success/failure. Errors retain the user's selection and
provide retry or a truthful disabled reason. Keyboard order, Escape/close,
focus trap/return, visible focus, screen-reader labels/live status, reduced
motion, localization, embedded width, and non-color status cues are validation
requirements.

### 7. Fixture matrix and quickstart

`quickstart.md` covers 0.9/1.0/1.1/3/51/138-second gaps (including the requested
0.9/1.1/3/51/138 matrix), A→B→A, unknown/unconfirmed, source boundary,
overlap, invalid timing, partial, missing summary, more than one hour, Russian
punctuation/formula prefixes, access denied, policy denied, deletion in
progress, audit failure, revision race, deterministic rerun, and provider swap.

## Validation Plan

- Unit-check snapshot assembly, boundary/unknown semantics, timestamp helpers,
  escaping, deterministic filenames, and every serializer with synthetic data.
- Parse CSV with Python `csv`, JSON with `json`, XLSX with `openpyxl`, and SRT
  with a strict fixture parser; compare all canonical rows/cues to one snapshot.
- Contract-check additive schemas, allowlisted format/content scopes, media
  types, filenames, stable JSON version, and compatibility of raw/plain routes.
- Integration-check owner/permitted/view-only/denied users, separate and
  combined policy, partial/missing/deleted states, audit fail-closed, content
  redaction, and revision-race pinning.
- Run PostgreSQL/RLS checks for tenant isolation and current-policy re-checks.
- Exercise meeting detail and embedded view in the in-app browser for dialog,
  preview, progress, failure, retry, keyboard, screen-reader, focus, reduced
  motion, responsive layout, and console/overflow behavior.
- Run Ruff, `git diff --check`, the commands in `quickstart.md`, and
  `infra/scripts/ci-local.sh` before implementation closeout/PR.
- Do not run CD or production mutation in this feature lane.

## Project Structure

### Documentation (this feature)

```text
specs/120-transcript-export/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── export-api.md
│   └── export-formats.md
├── checklists/
│   ├── requirements.md
│   └── export.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── pyproject.toml
├── src/twobrain_rec_server/
│   ├── api/{cabinet.py,schemas.py}
│   └── cabinet/
│       ├── exports.py
│       ├── egress.py
│       ├── queries.py
│       ├── view_models.py
│       ├── rendering.py
│       ├── review_policy_rendering.py
│       ├── templates.py
│       ├── static/cabinet/{cabinet.css,cabinet.js}
│       └── templates/cabinet/pages/meeting_detail_content.html
└── tests/
    ├── contract/{test_transcript_export_contract.py,test_transcript_export_no_secret_egress.py}
    ├── integration/{test_transcript_export_egress.py,test_cabinet_meeting_detail.py}
    └── unit/{test_transcript_exports.py,test_cabinet_view_models.py,test_cabinet_web_shell.py}

CHANGELOG.md
```

**Structure Decision**: Add one bounded `cabinet/exports.py` module for frozen
snapshot types, assembly, format dispatch, and serializers. Keep authorization,
audit, lifecycle, and response delivery in existing `cabinet/egress.py`; keep
canonical derivation in the existing view-model seam and harden it once for all
consumers. Dynamic dialog markup follows the cabinet's existing escaped,
trusted-component renderer seam, while the page template owns only its
placement; this avoids introducing a parallel template/rendering owner.
Do not add a repository layer, export persistence model, migration,
Temporal workflow, frontend framework, or client/provider adapter.

## Phase 0 Research

See [research.md](./research.md). The decisions are one scope-first export
dialog, separate transcript/summary truth, optional speaker/timestamp controls
that never change machine rows, terminal-only default, safe structural preview,
one canonical snapshot, and standards-based serializers.

## Phase 1 Design

- [data-model.md](./data-model.md): snapshot, selection, canonical/raw rows,
  summary projection, policy decision, and ephemeral artifact lifecycle.
- [contracts/export-api.md](./contracts/export-api.md): capability and canonical
  file routes, request/response, policy, revision, error, and audit behavior.
- [contracts/export-formats.md](./contracts/export-formats.md): columns, sheets,
  JSON envelope, human projections, escaping, and SRT semantics.
- [quickstart.md](./quickstart.md): focused fixture matrix and end-to-end gates.

## Post-Design Constitution Check

| Gate | Status | Design Response |
|---|---|---|
| Source and provider truth | PASS | Raw rows remain unchanged; all serializers read one GRAF-owned snapshot and never a provider response. |
| Authorization and secret discipline | PASS | Existing server policy and allowlisted metadata audit gate all bytes; no secret-bearing field enters a contract. |
| Lifecycle and deletion truth | PASS | No controlled export copy persists; deletion and access are re-checked in the export transaction and post-egress limits remain explicit. |
| AI boundary | PASS | Only the selected saved outcome set is read; no generation or repair occurs. |
| Accessibility and localization | PASS | Dialog, progress, errors, focus, keyboard, screen-reader, reduced-motion, responsive, and Russian-text requirements are mapped to validation. |
| Brand distance | PASS | Competitor capabilities are summarized in research; implementation reuses GRAF primitives and original copy. |
| Spec-driven delivery | PASS | Contracts and fixture matrix map to story-scoped tasks and a read-only analyze gate before code. |
| Metadata-only evidence | PASS | Synthetic fixtures and explicit no-content audit/log contracts cover every evidence path. |

No unresolved critical design decision remains.

## Complexity Tracking

No constitution violation or complexity exception is required. The single new
runtime dependency is limited to XLSX writing; it replaces a custom OOXML
implementation and is covered by a generated-workbook parse check.
