# Implementation Plan: MVP Live Owner Journey And UI Proof

**Branch**: `052-mvp-live-ui-proof` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/052-mvp-live-ui-proof/spec.md`

## Summary

Feature 052 is the final MVP proof-and-fix slice after 051 kept the product at
`pilot_blocked`. It must prove a current installed-app owner journey through
production review, stored outcomes, playback, transcript, diarization, speaker
timeline, web/desktop cabinet coherence, and representative processing timing.
If proof is missing or a gate fails, 052 keeps the claim honest and records the
smallest next action instead of raising readiness.

## Technical Context

**Language/Version**: Python >=3.13 for server tests and metadata probes; Swift
6.0 package targeting macOS 14+ for desktop validation; JavaScript/Node for
browser/runtime checks.

**Primary Dependencies**: Existing FastAPI/SQLAlchemy/Postgres/MinIO/Temporal
server stack, server-side MediaScribe integration, SwiftUI/AppKit/WebKit macOS
app, existing Playwright-compatible browser verifier patterns, and production
deploy scripts.

**Storage**: Production Postgres/MinIO metadata on `2brain.dev`; metadata-only
052 evidence under `specs/052-mvp-live-ui-proof/evidence/`; generated readiness
docs under `docs/evidence/052-mvp-live-ui-proof/`.

**Testing**: Focused server `pytest` through `uv run --extra dev`, focused
macOS `swift test`, browser runtime verifier, production health/probe checks,
feature quickstart, and full `infra/scripts/ci-local.sh` before release.

**Target Platform**: Installed macOS app at `/Applications/2brain Rec.app`,
production web/API at `https://rec.2brain.pro`, deployment host `2brain.dev`.

**Project Type**: Hybrid macOS desktop app, server-rendered web cabinet,
backend processing service, and production evidence/runbook slice.

**Performance Goals**: Prove or explicitly keep open the target of processing
one hour of representative audio in no more than 180 seconds. Separate
processing duration from queue/finalize-to-review wait when evidence allows.

**Constraints**: Evidence remains metadata-only. Desktop must not hold
MediaScribe credentials or send audio directly to MediaScribe. Native recording
truth stays visible independently of web cabinet state. Review playback remains
server-mediated and must not expose signed URLs, object keys, or private paths.

**Scale/Scope**: Internal owner MVP proof for the current macOS app and
production deployment. 052 does not add public links, transcript editing,
waveform polish, native Swift playback controls, notarized external
distribution, or real speakerphone AEC/noise suppression unless one of those
directly blocks the P1 owner journey claim.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. 052 validates the accepted
  system-audio-first path and does not revive virtual-driver routing.
- **Visible consent and user control**: PASS. Native Record/Stop truth remains
  required evidence and cannot be hidden by cabinet state.
- **Data boundary and secret discipline**: PASS. Probes and evidence are
  metadata-only; desktop MediaScribe credentials remain forbidden.
- **Deletion truth and lifecycle accounting**: PASS. Stored outcomes/playback
  proof must preserve existing deletion and denied/deleting/deleted boundaries.
- **Spec-driven delivery**: PASS. The slice follows specify, clarify, plan,
  checklist, tasks, analyze, issue sync, implement, validation, PR, release,
  and deploy.
- **Product URL governance**: PASS. Public URL remains
  `https://rec.2brain.pro`; deployment host remains `2brain.dev`.

## Project Structure

### Documentation (this feature)

```text
specs/052-mvp-live-ui-proof/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── owner-journey-proof-contract.md
│   ├── interface-proof-contract.md
│   └── timing-proof-contract.md
├── checklists/
│   ├── requirements.md
│   ├── ux.md
│   ├── security.md
│   └── infra.md
├── evidence/
│   ├── validation-log.md
│   ├── production-owner-journey-probe.py
│   ├── browser-runtime-check.cjs
│   ├── installed-app-check.md
│   ├── timing-proof.md
│   ├── ui-reference-review.md
│   ├── mvp-closeout-report.md
│   └── pr-draft.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── readiness/
│   ├── cabinet/
│   ├── outcomes/
│   ├── processing/
│   └── api/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

apps/macos/
├── RecApp/
├── Shared/
│   └── Tests/
└── Installer/

docs/
├── current-product-status.md
├── evidence/052-mvp-live-ui-proof/
└── agent-guidance/

infra/scripts/
```

**Structure Decision**: Reuse existing 050/051 readiness, production probe,
browser verifier, macOS cabinet, release, and deploy patterns. Add no new
schema, dependency, service, or UI surface unless a 052 proof gate exposes a
specific product defect that cannot be fixed inside an existing path.

## Phase 0: Research

See [research.md](./research.md). Decisions cover fresh owner journey proof,
stored outcomes proof, timing proof, KRISP clean-room UI reference, production
session boundaries, and evidence-safe closeout.

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md),
[contracts/owner-journey-proof-contract.md](./contracts/owner-journey-proof-contract.md),
[contracts/interface-proof-contract.md](./contracts/interface-proof-contract.md),
[contracts/timing-proof-contract.md](./contracts/timing-proof-contract.md), and
[quickstart.md](./quickstart.md).

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. Contracts require installed-app proof
  but do not claim clean speakerphone audio or revive driver routing.
- **Visible consent and user control**: PASS. Interface contract requires
  native controls and truthful capture/upload state.
- **Data boundary and secret discipline**: PASS. All evidence contracts forbid
  private content, credentials, cookies, tokens, signed URLs, object keys, and
  private paths.
- **Deletion truth and lifecycle accounting**: PASS. 052 cannot weaken existing
  deletion/accounting behavior for playback or outcomes.
- **Spec-driven delivery**: PASS. Checklists, tasks, analyze, issue sync, and
  implementation validation remain required before closeout.

## Complexity Tracking

No constitution violations or extra architecture layers are introduced.
