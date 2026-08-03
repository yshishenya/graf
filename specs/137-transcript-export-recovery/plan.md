# Implementation Plan: transcript-export-recovery

**Branch**: `codex/137-transcript-export-recovery` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/137-transcript-export-recovery/spec.md`

## Summary

Сделать готовые transcript/summary/package доступными владельцу записи при
отсутствии явного запрета, опубликовать первый детерминированный baseline как
current только при отсутствии принятого результата и восстановить AI-итоги,
если провайдер прислал правильный `transcript_segment_id`, но неверный
`sequence`. Явные `meeting_override`, shared-viewer ограничения, accepted
outcome history, revision/result fences и fail-closed проверки сохраняются.

Минимальный технический путь: один effective-policy helper в общем egress
слое, opt-in публикация baseline из доверенного processing-import/reconcile
пути и канонизация source reference по известному segment ID в общем
валидаторе. Новая схема БД, endpoint и провайдер не нужны.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy async, PostgreSQL, Temporal, MediaScribe, pytest

**Storage**: PostgreSQL metadata/transcripts/outcomes; owner-controlled object storage for media artifacts

**Testing**: focused pytest unit/integration/contract tests plus `infra/scripts/ci-local.sh --fast`

**Risk / Validation Lane**: `high-risk-feature`; this changes transcript/summary egress, AI result publication and a production repair path.

**Release Gate**: `no deploy` in this task; a production reconcile or deployment requires a later `cd-remote.sh --dry-run` and explicit approval.

**Target Platform**: Linux server containers and PostgreSQL-backed GRAF cabinet

**Project Type**: web service with server-rendered cabinet and maintenance script

**Performance Goals**: no additional provider call or export round trip; policy resolution remains one metadata lookup per existing egress request.

**Constraints**: preserve server-mediated egress, RLS/tenant context, deletion fences, immutable revision provenance, accepted-result immutability and metadata-safe evidence.

**Scale/Scope**: existing meeting/outcome/export flows; repair is bounded by an explicit meeting ID or operator limit.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- PASS — capture boundary is untouched; this slice consumes the existing
  server-side processing result and does not add a desktop audio path.
- PASS — transcript/summary/audio/package egress remains server-mediated and
  uses the existing access, policy and audit checks.
- PASS — explicit deny, non-owner access, deletion, revision and result-hash
  fences remain fail-closed; no transcript or meeting text enters committed
  evidence.
- PASS — AI source references are accepted only for known pinned segment IDs;
  canonicalizing a known ID to its stored sequence does not broaden source
  ownership.
- PASS — no provider credentials, raw media, new external dependency or
  observability deletion/redaction policy is introduced.

## Validation Plan

1. Run focused unit tests for prompt source-reference normalization and focused
   integration tests for policy/effective egress and outcome publication.
2. Cover the four user stories with synthetic fixtures: owner/no policy,
   explicit deny and non-owner, initial baseline publish/reconcile and accepted
   outcome preservation, valid-ID/wrong-sequence recovery and unknown-ID
   rejection, plus processed-result readiness while the immutable meeting
   status remains pending.
3. Run `git diff --check` and
   `infra/scripts/ci-local.sh --fast`. The full lane remains the release gate;
   this task adds only a narrow RLS maintenance-helper migration and does not
   execute it against production.
4. Do not execute a production reconcile or deployment. If approved later,
   first run the production dry-run and then a bounded `--execute` reconcile
   with metadata-only verification.

## Project Structure

### Documentation (this feature)

```text
specs/137-transcript-export-recovery/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── cabinet/egress.py                 # effective policy and capability states
├── outcomes/prompts.py               # pinned source-ref validation
├── outcomes/service.py                # baseline publication/reconcile fence
├── processing/submit.py               # trusted import call site
├── db/tenant_context.py               # maintenance operation guard
└── db/migrations/versions/0043_outcome_initial_baseline_reconciliation.py
                                      # RLS allowlist migration

apps/server/scripts/
└── reconcile_initial_outcomes.py      # bounded dry-run/execute repair

apps/server/tests/
├── unit/test_outcome_prompts.py
├── integration/test_artifact_egress_policy.py
├── integration/test_transcript_export_egress.py
└── integration/test_meeting_outcomes_generation.py
```

**Structure Decision**: keep the existing server service boundaries. Policy
normalization belongs in `cabinet/egress.py`, outcome state transitions in the
outcome service, provider-input repair in the shared validator, and the
production backlog repair in the existing `apps/server/scripts` maintenance
convention. One narrow migration is required to register the new maintenance
operation in the production RLS helper; no new package is justified.

## Complexity Tracking

No constitution violations. The slice reuses existing egress, outcome,
tenant-context and test helpers.
