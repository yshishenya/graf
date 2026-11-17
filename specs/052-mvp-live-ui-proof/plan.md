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
feature quickstart, and required GitHub `governance-fast`, `macos-pr`, `pr-metadata` on the exact head and checked base before merge. Local wide CI is diagnostic only; a frozen release candidate requires one authoritative GitHub `release-full`.

**Target Platform**: Single local macOS acceptance app at `/Applications/GRAF Dev.app` through the existing dev-harness (availability/version/occupancy first),
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
  checklist, tasks, analyze, issue sync, implement, converge, validation, PR,
  and separate release/deploy gates.
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

## T020 continuation — 2026-11-17

**Lane**: high-risk product / existing Active Spec Kit slice (diagnostic
truth, privacy and auth metadata), not a low-risk standalone script change.
**Scope**: repair the existing metadata probe and add one standard-library
regression file beside it. No server schema, product status, service, provider,
UI, dependency, capture or deployment change. Legacy Impact: remove the
probe's false-positive classification and stale active instructions; archived
receipts remain history, not a compatibility fallback.

Clarification: current spec §Clarifications/FR-016–019 and the owner contract
now separate API metadata observation from actual P1 acceptance. No unresolved
product-owner decision is delegated to implementation. The response subset,
source projection, category matrix, counter definitions, negative outcomes and
exit codes are explicit in the contract.

Pre-design constitution review: I/II preserve native capture/Stop and do not
launch an app; III/IV preserve server boundaries, GET-only access and
metadata-only evidence with deletion/denial states; VI requires independent
checklist PASS, analyze and existing issue sync before code; VII follows the
approved observable reference with independent code and asset rights. V public
distribution is unchanged and is not implied by local Dev acceptance.

Implementation, only after those gates:

1. In `evidence/test_production_owner_journey_probe.py`, import the script
   without invoking `main`; use synthetic response dictionaries and patched
   request functions/environment. Add small table-driven standard-library
   tests for the contract matrix, request/configuration failures, health,
   aggregate/exit and privacy, including missing/malformed/different response
   UUID and normalized equality. No network, app, real data or new dependency.
2. In `evidence/production-owner-journey-probe.py`, reuse `_get_json`, `_health`,
   `_owner_review`, `main`; validate the observed metadata subset, use nested
   meeting projection, count transcript/lanes/intervals/seek/categories, and
   emit only bounded metadata. Bind response meeting UUID to the requested UUID
   without emitting either. Keep missing/negative evidence negative.
3. Run the offline command in quickstart. Then converge the diff against
   FR-016–019 and the unchanged original T020 acceptance. Record results in
   `evidence/validation-log.md` and `changes/unreleased/F52.yaml`.
4. Use the existing T020/#1819 link; no duplicate feature or issue. Required
   PR checks must pass for the exact final source SHA and current checked base
   through `scripts/validate-pr-checks.py`; review unresolved comments before
   the normal linear merge and verify the result.
5. Real production candidate evidence, Dev/UI proof, release and deployment
   remain separate gates. Do not run them merely to repair this probe, mark
   T020 complete from a mock, or raise `pilot_blocked` from API metadata.

Post-design constitution review: the approach keeps the same boundaries and
adds no generated-content semantics/judge or product state mutation. Safety
checks at runtime input/HTTP boundaries prevent leaking cookies/private
responses; standard-library tests contain only artificial sentinel content.
This is a design assessment, not implementation or live acceptance. Existing
checklist STOP38/8 remains until the independent reviewer records a new result;
read-only analyze and tracker reconciliation also remain required.

Second requirements correction resolves analyze U1/U2: explicit response UUID
binding and preserved speaker-assignment/multi-speaker reference observations,
without implementing editing. The subsequent independent result49/1 also
remains STOP until a new review accepts these corrections. Focused unittest
execution must be recorded against its actual source; generic PR check success
does not establish that this evidence-directory test ran automatically.

All existing task marks and historical validation receipts retain their
original dated meaning. For continuation, active feature routing is the ignored
`.specify/feature.json` and prerequisite output; root `AGENTS.md` stays stable.
Feature authors write only `changes/unreleased/F52.yaml`; root `CHANGELOG.md`
is assembled by the release operator. Release/production execution follows
`docs/agent-guidance/release-and-validation.md` with an immutable candidate,
authoritative exact-SHA evidence and decision, CD dry-run and separate deploy
gate; healthy endpoints alone never authorize it.
