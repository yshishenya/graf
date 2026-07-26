# Implementation Plan: Скачивание аудио владельцем по умолчанию

**Branch**: `codex/131-owner-audio-download` | **Date**: 2026-07-26 | **Spec**: [spec.md](./spec.md)

**Input**: User decision: владелец встречи скачивает готовое аудио без отдельного разрешения.

## Summary

Production metadata showed that the audio download request reaches the existing
server-mediated route and is rejected with `409` because the effective stored
workspace policy is `audio_download=disabled`. The existing egress state helper
is shared by the detail-page link and the direct download route, so the smallest
safe change is to resolve an implicit audio default as `owner_only` at that
single boundary. Explicit per-meeting denial and all non-owner checks remain
fail-closed; transcript, summary, package, playback, storage, and endpoints do
not change.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: FastAPI, SQLAlchemy async, existing cabinet access,
artifact egress, audit, and server-rendered web/embedded cabinet.

**Storage**: Existing Postgres `meeting_artifact_policies`, meeting/access,
validated playback artifact metadata, and server-owned object storage. No schema
or storage-boundary change.

**Testing**: Focused pytest integration/contract tests, `node --check` for the
unchanged cabinet JavaScript path, and `infra/scripts/ci-local.sh` at closeout.

**Risk / Validation Lane**: `high-risk-feature` — user-visible audio egress
policy changes a privacy boundary and affects authorization, audit, browser UI,
and embedded macOS UI. Full Spec Kit artifacts, focused tests, and repository CI
are required.

**Release Gate**: `no deploy` in this slice. Production CD dry-run and execute
remain separate release actions requiring a clean validated ref and explicit
approval.

**Target Platform**: Linux/Docker server, external browser cabinet, and the
existing macOS embedded WebKit cabinet.

**Project Type**: FastAPI backend with server-rendered cabinet UI embedded by
the native macOS app.

**Performance Goals**: Reuse the current one-pass egress state calculation;
owner-default resolution adds no database query, endpoint, or storage read.

**Constraints**: Do not expose signed/storage URLs, object keys, credentials,
raw audio, transcript text, or private meeting content in diagnostics or
evidence. Unknown policy sources remain blocked. Explicit denial, lifecycle,
authorization, validated-artifact, and metadata-only audit gates stay intact.

**Scale/Scope**: One existing audio artifact policy decision used by meeting
detail rendering and direct audio download. No mobile, capture, transcription,
or new client protocol work.

## Constitution Check

| Gate | Status | Plan response |
|---|---|---|
| Capture-first MVP integrity | PASS | Does not change capture, routing, buffering, permissions, or recording truth. |
| Visible consent and one-action stop | PASS | The change starts only after capture has already produced a retained artifact. |
| Data boundary and secret discipline | PASS | Existing server-mediated download and storage custody are reused; no URL or credential reaches clients. |
| Deletion truth and lifecycle accounting | PASS | Existing deletion fence, artifact validation, bounded failures, and metadata-only audit remain mandatory. |
| Auth, privacy, and egress | PASS | Owner-only is the implicit default; explicit override and non-owner access remain denied. |
| Clean-room UX | PASS | Existing GRAF menu/link and identical web/embedded route are reused; no reference UI is added. |
| Spec-driven delivery | PASS | This slice includes spec, research, plan, checklists, contract, quickstart, tasks, analyze, issue sync, and implementation validation. |

No constitution violation or migration is required.

## Validation Plan

1. Run focused egress integration tests for an owner with no policy row, an
   existing `workspace_default` disabled row, an explicit `meeting_override`
   denial, and a permitted non-owner under owner-only policy.
2. Run meeting-detail web/embedded tests proving the same existing download
   action is rendered for the owner when a validated playback artifact exists.
3. Run contract/security tests proving no new URL, storage identifier, secret,
   or content-bearing audit field is introduced.
4. Run the feature quickstart and then `infra/scripts/ci-local.sh` as the
   high-risk closeout gate. Evidence is metadata-only and uses synthetic
   artifacts.
5. Do not deploy from this implementation turn. A later release turn must
   run `infra/scripts/cd-remote.sh --dry-run`, obtain explicit approval, and
   only then consider execute/smoke.

## Project Structure

### Documentation (this feature)

```text
specs/131-owner-audio-download/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
├── contracts/
│   └── meeting-owner-audio-download.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/cabinet/egress.py
└── tests/
    ├── contract/test_recording_governance_ui_contract.py
    └── integration/
        ├── test_artifact_egress_policy.py
        └── test_cabinet_meeting_detail.py

CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Extend the existing shared egress decision path. The
detail template and macOS wrapper need no new implementation because both
already consume the same server-rendered capability and endpoint.

## Complexity Tracking

No constitution violations or new abstractions are required. The effective
policy helper is deliberately local to `cabinet/egress.py`; no new service,
endpoint, dependency, table, migration, or client permission model is added.

## Phase 0 Research Decisions

See [research.md](./research.md): production diagnosis, current call graph,
policy-source semantics, rejected alternatives, and compatibility with prior
playback/download separation.

## Phase 1 Design Decisions

- [data-model.md](./data-model.md) defines effective audio policy without a
  persistent schema change.
- [contracts/meeting-owner-audio-download.md](./contracts/meeting-owner-audio-download.md)
  defines the unchanged route/UI/audit boundary and source matrix.
- [quickstart.md](./quickstart.md) defines focused, browser/embedded parity,
  security, and repository-gate validation.

## Post-Design Constitution Check

| Gate | Status | Design response |
|---|---|---|
| Privacy boundary | PASS | Only the owner receives implicit `owner_only`; an explicit override or unknown source cannot be promoted. |
| Authorization | PASS | Current workspace membership, meeting access, share grant, deletion, and artifact checks execute unchanged. |
| Storage boundary | PASS | The route still materializes validated server-owned M4A bytes and never returns storage metadata. |
| Audit and evidence | PASS | Existing allowed/denied metadata-only events remain the source of truth. |
| Compatibility | PASS | `allowed`, `owner_only`, transcript/summary/package, playback, and existing test-fixture deny behavior are unchanged. |
| Validation | PASS | Tests cover both the UI capability and direct route so a silent `409` regression is caught. |
