# Implementation Plan: MVP Owner Journey Proof

**Branch**: `051-mvp-owner-journey-proof` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/051-mvp-owner-journey-proof/spec.md`

## Summary

Feature 051 closes the P1 launch blockers left by 050. It proves a fresh
installed-app owner journey through production upload, finalization,
processing, web review, embedded macOS review, transcript, diarization,
playback, speaker timeline, stored outcomes, and representative timing. It
also re-checks the web cabinet and macOS interface against the accepted
2brain Rec design direction and Krisp-style interaction expectations without
copying Krisp. If the proof fails, 051 keeps the product honestly
`pilot_blocked` and records the exact remaining gate.

## Technical Context

**Language/Version**: Python >=3.13 for server code, tests, and metadata
probes; Swift 6.0 package targeting macOS 14+ for the desktop app; JavaScript
/ Node for browser/runtime verification.

**Primary Dependencies**: FastAPI, SQLAlchemy/Alembic, Postgres, MinIO,
Temporal, server-side MediaScribe dependency, SwiftUI/AppKit/WebKit,
Screen/System Audio and microphone capture stack, Playwright-compatible browser
automation or existing browser verifier harnesses.

**Storage**: Production Postgres and MinIO on `2brain.dev`; local metadata-only
evidence under `specs/051-mvp-owner-journey-proof/evidence/` and generated
status evidence under `docs/evidence/051-mvp-owner-journey-proof/`.

**Testing**: `pytest` through `uv run --extra dev`, macOS `swift test`, focused
browser runtime scripts, production health/smoke commands, metadata-only
production probes, and full `infra/scripts/ci-local.sh`.

**Target Platform**: Installed macOS app at `/Applications/2brain Rec.app` and
production web/API at `https://rec.2brain.pro` running on `2brain.dev`.

**Project Type**: Hybrid desktop app + server-rendered web cabinet + backend
processing service + production evidence/runbook slice.

**Performance Goals**: Record direct timing evidence against the product target
of processing one hour of audio in no more than three minutes. Separate raw
processing duration from owner-visible queue/finalize-to-review wait.

**Constraints**: Evidence must be metadata-only. Desktop clients must never
send audio directly to MediaScribe or hold MediaScribe credentials. Native
capture controls must remain visible independently of web/server state. Review
playback remains server-mediated and must not expose signed URLs, storage keys,
or local private paths.

**Scale/Scope**: Internal MVP owner proof for the current macOS app and one
production deployment. This slice does not broaden public links, external
sharing, transcript editing, waveform generation, real echo/noise suppression,
signed/notarized external distribution, or generalized auto-start.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. 051 validates the accepted
  system-audio-first macOS path and does not revive virtual-driver routing.
- **Visible consent and user control**: PASS. Native Record/Stop/Pause/Resume
  truth remains part of the proof and must stay visible outside WebKit.
- **Data boundary and secret discipline**: PASS. Evidence is metadata-only;
  desktop MediaScribe credentials remain forbidden.
- **Deletion truth and lifecycle accounting**: PASS. 051 must not weaken
  existing outcome/playback/deletion lifecycle accounting or deletion copy.
- **Spec-driven delivery**: PASS. This plan follows specify, clarify, plan,
  checklist, tasks, analyze, issue sync, implement, and validation.
- **Product URL governance**: PASS. Public validation target remains
  `https://rec.2brain.pro`; deployment host remains `2brain.dev`.

## Project Structure

### Documentation (this feature)

```text
specs/051-mvp-owner-journey-proof/
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
├── evidence/051-mvp-owner-journey-proof/
└── agent-guidance/

infra/scripts/
```

**Structure Decision**: Reuse the accepted server, macOS, docs, and deployment
surfaces. Add no new app package or database table unless a failing P1 proof
shows an existing production path cannot record the required metadata. Prefer
focused tests, metadata probes, evidence reports, and narrow fixes in existing
modules.

## Phase 0: Research

See [research.md](./research.md). Decisions cover owner journey evidence,
stored outcomes proof, representative timing, clean-room UI checking,
macOS installed-app proof, and readiness claim rules.

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md),
[contracts/owner-journey-proof-contract.md](./contracts/owner-journey-proof-contract.md),
[contracts/interface-proof-contract.md](./contracts/interface-proof-contract.md),
[contracts/timing-proof-contract.md](./contracts/timing-proof-contract.md), and
[quickstart.md](./quickstart.md).

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. Contracts require real installed-app
  journey truth and do not claim clean speakerphone audio.
- **Visible consent and user control**: PASS. Interface contract requires
  native controls and one-action stop truth to remain visible.
- **Data boundary and secret discipline**: PASS. All contracts prohibit raw
  audio, transcript text, private outcomes, private titles, account identifiers,
  tokens, signed URLs, storage keys, cookies, and private local paths in
  committed evidence.
- **Deletion truth and lifecycle accounting**: PASS. Outcome proof must preserve
  deletion accounting and denied/deleted/deleting visibility boundaries.
- **Spec-driven delivery**: PASS. Tasks and analyze are required before
  implementation.

## Complexity Tracking

No constitution violations or extra architecture layers are introduced.
