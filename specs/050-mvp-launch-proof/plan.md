# Implementation Plan: MVP Launch Proof

**Branch**: `050-mvp-launch-proof` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/050-mvp-launch-proof/spec.md`

## Summary

Feature 050 is the MVP closeout proof slice. It does not add a new product
surface first. It proves the current owner value loop across installed macOS
app, production server processing, web review, embedded macOS review, playback,
transcript, diarization, stored outcomes, and release/readiness truth. Any
discovered P1 UI or flow gap is fixed inside the same slice, then the proof is
re-run. The final claim remains `pilot_blocked` unless every P1 gate has direct
metadata-safe evidence.

## Technical Context

**Language/Version**: Python >=3.13 for server code and evidence harnesses; Swift 6.0
package targeting macOS 14+ for the desktop app; JavaScript/Node for browser
runtime verifiers.

**Primary Dependencies**: FastAPI, SQLAlchemy/Alembic, MinIO, Temporal,
MediaScribe server dependency, SwiftUI/AppKit/WebKit, Screen/System Audio and
microphone capture stack, Playwright or in-app Browser for UI proof.

**Storage**: Production Postgres and MinIO on the `2brain.dev` deployment host;
metadata-only feature evidence under `specs/050-mvp-launch-proof/evidence/` and
current readiness docs under `docs/evidence/050-mvp-launch-proof/`.

**Testing**: `pytest` through `uv run --extra dev`, macOS `swift test`, focused
browser runtime scripts, production health/smoke commands, and full
`infra/scripts/ci-local.sh`.

**Target Platform**: macOS installed app plus production web/API at
`https://rec.2brain.pro` running on `2brain.dev`.

**Project Type**: Hybrid desktop app + server-rendered web cabinet + backend
processing service + deployment/runbook evidence.

**Performance Goals**: Representative processing evidence must be recorded
against the product target of processing one hour of audio in no more than
three minutes. The feature may only claim the target as passed when direct
timing evidence proves it.

**Constraints**: Evidence must be metadata-only. Desktop clients must never
send audio directly to MediaScribe or hold MediaScribe credentials. The
macOS native capture controls must remain visible regardless of server/web
state. Playback must remain server-mediated and must not expose signed URLs,
storage keys, or local paths.

**Scale/Scope**: Internal MVP owner flow for the current macOS app and one
production deployment. This slice does not broaden public links, external
sharing, transcript editing, waveform generation, real AEC/noise suppression,
signed/notarized external distribution, or generalized auto-start.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. 050 validates the current
  system-audio-first macOS path and does not revive virtual-driver routing.
- **Visible consent and user control**: PASS. Native Record/Stop/Pause/Resume
  truth remains part of the proof and must stay visible outside WebKit.
- **Data boundary and secret discipline**: PASS. Evidence is metadata-only;
  desktop MediaScribe credentials remain forbidden.
- **Deletion truth and lifecycle accounting**: PASS. 050 validates that
  outcome/playback/readiness proof does not weaken existing deletion wording or
  lifecycle boundaries.
- **Spec-driven delivery**: PASS. This plan follows specify, clarify, plan,
  checklist, tasks, analyze, issue sync, implement, and validation.
- **Product URL governance**: PASS after patch-level constitution correction to
  `https://rec.2brain.pro` public URL while keeping `2brain.dev` as deployment
  host.

## Project Structure

### Documentation (this feature)

```text
specs/050-mvp-launch-proof/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── mvp-readiness-contract.md
│   └── interface-proof-contract.md
├── checklists/
│   ├── requirements.md
│   ├── ux.md
│   ├── security.md
│   └── infra.md
├── evidence/
│   ├── validation-log.md
│   ├── browser-runtime-check.cjs
│   └── mvp-closeout-report.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── readiness/
│   ├── cabinet/
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
├── agent-guidance/
└── evidence/050-mvp-launch-proof/

infra/scripts/
```

**Structure Decision**: Use the existing server, macOS, documentation, and
deployment surfaces. Add no new application package. Add only focused harnesses,
tests, evidence records, and targeted product fixes discovered by the proof.

## Phase 0: Research

See [research.md](./research.md). Decisions cover live evidence boundaries,
Krisp clean-room usage, production journey proof, processing-time measurement,
readiness claim semantics, and safe handling of stale status documents.

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md), [contracts/mvp-readiness-contract.md](./contracts/mvp-readiness-contract.md),
[contracts/interface-proof-contract.md](./contracts/interface-proof-contract.md), and
[quickstart.md](./quickstart.md).

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. Contracts require explicit capture
  truth and no clean speakerphone claim from 050.
- **Visible consent and user control**: PASS. Interface contract requires
  native controls to remain visible during embedded review.
- **Data boundary and secret discipline**: PASS. Contracts prohibit raw audio,
  transcript text, private titles, account identifiers, tokens, signed URLs,
  storage keys, and local private paths in committed evidence.
- **Deletion truth and lifecycle accounting**: PASS. Status updates must not
  weaken deletion copy or outcome deletion accounting.
- **Spec-driven delivery**: PASS. Tasks and analyze are required before
  implementation.

## Complexity Tracking

No constitution violations or extra architecture layers are introduced.
