# Implementation Plan: Interactive Playback Timeline

**Branch**: `118-interactive-playback-timeline` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/118-interactive-playback-timeline/spec.md`

## Summary

Turn the existing fixed meeting player and speaker lanes into one time-aligned review surface. Reuse the retained `<audio>` player, canonical speaker turns, and server-rendered cabinet: align every track to one inner scale, seek through one client function, derive active lanes and transcript following from current audio time, and add a meeting-scoped speaker display-name override with existing access, CSRF, RLS, audit, and deletion boundaries. No new frontend framework or runtime dependency is required.

## Technical Context

**Language/Version**: Python 3.13 server; browser JavaScript and CSS already shipped by the cabinet.

**Primary Dependencies**: Existing FastAPI, Pydantic, SQLAlchemy/Alembic, Jinja cabinet templates, native HTML audio/range/details controls, pytest, Ruff. No new dependency.

**Storage**: Existing PostgreSQL meeting/transcript/diarization records plus one small meeting-scoped speaker display-name table.

**Testing**: Focused schema, view-model, rendering, web-route, deletion, RLS/migration, and cabinet integration tests; in-app browser interaction/design QA; `infra/scripts/ci-local.sh` at closeout.

**Risk / Validation Lane**: `high-risk-feature`. The slice changes shared transcript/playback UX and adds an authorized, audited meeting-content mutation, so the full Spec Kit sequence and repository gate apply.

**Release Gate**: This implementation lane excluded CD and production data mutation. The validated implementation was later merged through PR #3944 and released as `v2026.07.21.4`; this spec does not claim a separate production rollout proof.

**Target Platform**: GRAF server-rendered browser cabinet and the same cabinet embedded in the macOS app.

**Project Type**: Python web/API service with server-rendered UI and an embedded web surface.

**Performance Goals**: Playback-time UI synchronization stays frame-local and linear in the small visible speaker/turn set; review assembly adds one bounded query for meeting speaker names; rename uses one row lookup and one transaction.

**Constraints**: One canonical audio timeline; no provider data rewrite; no direct MediaScribe call; no speaker identity inference across meetings; no transcript text in audit/evidence; standard keyboard seeking and reduced-motion behavior preserved.

**Scale/Scope**: One meeting detail surface, its current accepted diarization result, up to the existing bounded transcript/turn response, and one optional name per canonical speaker. Merge/split, transcript editing, contact suggestions, and cross-meeting identity are excluded.

## Constitution Check

*GATE: Passed before Phase 0 research; re-checked after Phase 1 design.*

| Gate | Status | Plan Response |
|---|---|---|
| Capture-first MVP integrity | PASS | No capture, recording, source artifact, or routing behavior changes. |
| Visible consent and user control | PASS | Post-meeting review only; recording indicators and stop control are untouched. |
| Data boundary and secret discipline | PASS | Display names stay in GRAF-owned storage; no provider credential or direct client egress is added. |
| Deletion truth and lifecycle accounting | PASS | Speaker-name rows are meeting-scoped and explicitly purged with diarization-derived content. |
| Authorization and audit | PASS | Existing session access, CSRF, tenant RLS, privileged edit boundary, and metadata-only audit are reused. |
| User-facing review and accessibility | PASS | Native range semantics, visible focus, non-color active state, reduced motion, and no focus stealing are explicit. |
| Original design / brand distance | PASS | Screenshots are behavioral references; implementation stays inside the existing GRAF cabinet design system and icons. |
| Spec-driven delivery | PASS | Specify, clarify, plan, UX checklist, tasks, analyze, issue sync, and implement precede code. |
| Metadata-only evidence | PASS | Tests and QA use synthetic labels/timing and do not commit private screenshot content or meeting text. |

No constitution violation is required.

## Validation Plan

- Run focused contract/view-model/rendering tests for stable `speaker_key`, display-name projection, aligned scale metadata, transcript anchors, active intervals, and fallback states.
- Run focused browser/desktop route tests for owner/admin authorization, view-only denial, CSRF, validation, set/replace/clear, safe failures, audit metadata, and identical redirect/fragment behavior.
- Run migration/RLS and deletion tests proving workspace isolation and purge participation.
- Open a synthetic meeting-detail fixture in the in-app browser; test pointer and keyboard seek, speaker-lane seek including gaps, active/overlap states, transcript centering, reduced motion, rename/reload, embedded width, and console errors.
- Write `design-qa.md`, compare the implemented states to the supplied interaction references and GRAF design rules, and resolve P0-P2 findings before handoff.
- Run Ruff, `git diff --check`, the feature quickstart, and `infra/scripts/ci-local.sh` once at closeout.
- Do not run CD or production mutation in this feature lane.

## Project Structure

### Documentation (this feature)

```text
specs/118-interactive-playback-timeline/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── playback-speaker-review.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/schemas.py
├── cabinet/
│   ├── queries.py
│   ├── rendering.py
│   ├── speakers.py
│   ├── static/cabinet/{cabinet.css,cabinet.js}
│   └── web_routes/speakers.py
├── db/
│   ├── migrations/versions/0029_meeting_speaker_names.py
│   └── models/{__init__.py,processing.py}
└── deletion/service.py

apps/server/tests/
├── contract/test_cabinet_playback_contract.py
├── integration/test_cabinet_meeting_detail.py
├── integration/test_speaker_names.py
└── unit/{test_cabinet_view_models.py,test_cabinet_web_shell.py,test_deletion_service.py}
```

**Structure Decision**: Keep playback interaction in the existing cabinet asset files and review projection in the existing schema/query/view/render path. Add only one small speaker-name service/route module and one persistence model/migration because authorization, audit, RLS, and deletion cannot be safely represented as client-only state.

## Complexity Tracking

No constitution violations.

## Phase 0 Research Decisions

See [research.md](./research.md). The core decisions are one inset timeline scale matching the native range thumb geometry, one seek/sync function, canonical speaker keys separated from display names, and a single meeting-scoped override table.

## Phase 1 Design Decisions

See [data-model.md](./data-model.md), [contracts/playback-speaker-review.md](./contracts/playback-speaker-review.md), and [quickstart.md](./quickstart.md).

## Post-Design Constitution Check

| Gate | Status | Design Response |
|---|---|---|
| Capture and source truth | PASS | Design reads retained playback and accepted timing without offsets or source mutation. |
| Data boundary and secrets | PASS | New state is tenant-scoped, contains only a bounded display name, and never reaches external dependencies. |
| Deletion lifecycle | PASS | The purge path deletes display-name rows before final diarization state is reported purged. |
| Authorization and audit | PASS | Mutation requires authenticated session CSRF and creator/owner/admin capability; audit excludes the name and transcript text. |
| Accessibility and localization | PASS | Native range keyboard semantics remain; lanes expose buttons/names; current state is not color-only; Russian copy reuses cabinet conventions. |
| Brand distance | PASS | Supplied screenshots guide interaction only; no copied avatars, colors, icons, or layout system are introduced. |
| Spec-driven delivery | PASS | Contracts and validation map directly to FR-001 through FR-020. |

No unresolved critical design decision remains.

## Post-implementation reconciliation

- The three user stories and all 16 tasks are complete; focused validation,
  browser/embedded design QA, and the repository gate are recorded in
  `tasks.md`.
- The implementation is merged in PR #3944 and included in release
  `v2026.07.21.4`.
- No separate production deploy, rollout, or rollback claim is added by this
  documentation update; those remain an explicitly separate release boundary.
