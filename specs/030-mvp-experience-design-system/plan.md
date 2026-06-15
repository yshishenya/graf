# Implementation Plan: MVP Product Experience And Design System

**Branch**: `030-mvp-experience-design-system` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/030-mvp-experience-design-system/spec.md`

## Summary

Create the product/design foundation for the first launchable `2brain Rec`
experience. This slice does not implement production UI or capture behavior.
It produces the launch scope map, desktop trust-shell UX, browser web cabinet
UX, embedded desktop cabinet subset rules, cross-surface status model, design
system direction, prototype source plan, clean-room Krisp benchmark, and
implementation-ready backlog for follow-up slices.

The planned value proof is an owner value loop across a platform desktop shell
and web: a user records in the native shell or uploads owned media, sees
truthful current status in both surfaces, watches transcription progress, and
receives a complete meeting review with transcript, playback context, speaker
assignment, summary, decisions, action items, status provenance, and
deletion/access entry points.

## Technical Context

**Language/Version**: Markdown design artifacts in repository; Figma Design as
preferred visual/prototype source; StitchFlow 1.4.0 as fallback artifact
pipeline; downstream implementation targets Swift 6.0 macOS app and Python
FastAPI server/web surfaces already present in this repository.

**Primary Dependencies**: Existing desktop upload slice `014`, the parallel
`015-mediascribe-processing-pipeline` worktree/branch for processing status and
transcript import contracts, auth/account specs `028` and `029`, PRD/status
docs, ADR `001-local-trust-shell-and-server-dashboard`, constitution 2.0.0,
Figma Starter-compatible workflow where possible, StitchFlow fallback outputs
(`DESIGN.md`, screenshots, HTML/code checkpoints, project metadata).

**Storage**: No production storage changes in this slice. Design artifacts are
stored under `specs/030-mvp-experience-design-system/`; external prototype
metadata and links are recorded in repo handoff artifacts without secrets.

**Testing**: Spec quality checklist, future UX/security/brand-distance
checklists, route visibility matrix review, cross-surface status walkthrough,
prototype path review, visual screenshot QA, text overflow/accessibility scan,
and clean-room brand-distance review.

**Target Platform**: macOS MVP desktop shell plus browser web cabinet at
`https://rec.2brain.dev` once later implementation slices exist. Future Windows
and Linux desktop shells reuse the same server-owned product UI contract while
keeping their own native capture, permission, local buffer, tray/menu, and
route-guard implementations.

**Project Type**: Product/design-system planning slice for a native macOS
desktop app plus server web cabinet. No production app code is authorized.

**Performance Goals**:

- Prototype and written artifacts cover at least 95% of primary MVP owner
  journeys without inventing missing states.
- 100% of launch-critical status states are consistent across desktop app and
  web cabinet in the cross-surface status contract.
- 100% of embedded desktop cabinet routes are reviewed against the native
  capture boundary.

**Constraints**:

- Capture-critical state, visible indicator, Stop, permissions, local artifact
  truth, upload queue truth, tray/menu status, diagnostics, and recovery actions
  remain native/local for each platform shell.
- Variable product UI is server/web-owned and embedded through an allowlisted
  cabinet subset, not duplicated as native macOS/Windows/Linux views.
- Speaker assignment is desktop-available only through the embedded
  server-owned product UI; native shells do not own diarization or speaker
  editing logic.
- Desktop embedded cabinet is an allowlisted subset, not the full web product.
- Full browser cabinet may contain routes intentionally absent from desktop.
- Manual upload is audio-first: audio files and common video/meeting files may
  be accepted, but MVP value is audio extraction, transcript, notes, and review.
- No copied Krisp UI, copy, icons, assets, brand expression, proprietary flows,
  or model behavior.
- Design/prototype artifacts must not contain credentials, raw meeting content,
  signed URLs, tokens, passwords, or live local paths.

**Scale/Scope**: Design-ready MVP blueprint with the active Figma v8 clean
Russian review candidate: 17 top-level frames across compact provider sign-in,
guided macOS permissions, desktop meeting workspace, auto-detected meeting
prompt, active recording native chrome, inline upload/processing, transcript
review, speaker assignment lanes, settings with recording/theme policy, browser
meetings list, browser meeting detail, share/export/delete governance,
shared upload sheet, command search/filter overlay, light-theme proof, and
component/QA rules. V8 supersedes the v5-v7.4 prototype lineage for
implementation review. V5.1/V5.2 remain historical coverage
evidence only after stakeholder and five-critic reviews found flow, density,
settings, technical-copy, and visual-quality blockers. The current v8 evidence
shows 92 valid `ON_CLICK` reactions, frame-bound overflow `0`, bad button
heights `0`, bad chip heights `0`, visible forbidden implementation copy `0`,
and a completed stakeholder visual approval pack; final stakeholder visual
acceptance remains the open handoff gate.
The plan must
incorporate the current `014` desktop upload foundation and stay aligned with
the separate `015` processing pipeline worktree/branch, then produce
implementation-ready follow-up candidates for remaining dashboard, access,
deletion, design-system, and desktop/web polish work.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. This design slice preserves the
  system-audio-first macOS MVP path and does not revive virtual-driver routing
  or alter capture implementation.
- **Visible consent and user control**: PASS. Native desktop trust shell keeps
  visible recording truth and one-action Stop outside server-rendered content.
- **Data boundary and secret discipline**: PASS. Artifacts are design-only,
  metadata-only, and explicitly forbid secrets, credentials, raw audio,
  transcript text from real meetings, signed URLs, and live paths.
- **Deletion truth and lifecycle accounting**: PASS. Deletion/access entry
  points and copy must use truthful "2brain Rec controls" language and avoid
  universal erasure promises.
- **Spec-driven delivery with testable gates**: PASS. Spec and clarification
  are complete; this plan creates research, data model, UI contracts, and
  quickstart before checklist/tasks/analyze.

## Project Structure

### Documentation (this feature)

```text
specs/030-mvp-experience-design-system/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cross-surface-status-contract.md
│   ├── prototype-handoff-contract.md
│   └── route-visibility-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/
│   └── Sources/
│       ├── Capture/
│       ├── Upload/
│       └── Shared/
└── Shared/
    ├── Sources/
    └── Tests/

apps/server/
├── src/twobrain_rec_server/
│   ├── api/
│   ├── auth/
│   ├── ingest/
│   └── observability/
└── tests/

docs/
├── adr/
├── integrations/
└── current-product-status.md
```

**Structure Decision**: Keep this feature's outputs in `specs/030-*`. The
source code tree is referenced only for downstream implementation mapping:
macOS native trust-shell slices belong under `apps/macos`, server/web cabinet
and API slices under `apps/server`, and product governance references under
`docs`. No production source files are changed by this planning slice.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

## Phase 0 Research Summary

See [research.md](./research.md). Key decisions:

- Use a hybrid experience model: native desktop trust shell plus full browser
  cabinet and allowlisted embedded desktop cabinet subset.
- Define value around the owner value loop, not a full account/admin/business
  suite.
- Use Figma as preferred prototype source and StitchFlow as documented fallback.
- Treat route visibility and cross-surface status as explicit contracts.
- Keep Krisp research clean-room and category-level only.

## Phase 1 Design Summary

See:

- [data-model.md](./data-model.md)
- [contracts/route-visibility-contract.md](./contracts/route-visibility-contract.md)
- [contracts/cross-surface-status-contract.md](./contracts/cross-surface-status-contract.md)
- [contracts/prototype-handoff-contract.md](./contracts/prototype-handoff-contract.md)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. Contracts keep capture-critical UI
  local/native and do not authorize capture implementation changes.
- **Visible consent and user control**: PASS. Prototype requirements include
  active recording indicator, Stop, server-offline/stale states, and rejection
  of server-loaded content that obscures capture truth.
- **Data boundary and secret discipline**: PASS. Prototype handoff contract
  requires sanitized sample data, no real meeting content, no credentials, and
  recorded export warnings for external design tools.
- **Deletion truth and lifecycle accounting**: PASS. Meeting review and deletion
  entry-point states use truthful lifecycle language and preserve local/server/
  external dependency boundaries for later execution slices.
- **Spec-driven delivery with testable gates**: PASS. Research, data model,
  contracts, quickstart, and AGENTS plan reference are present for the next
  checklist/tasks/analyze stages.
