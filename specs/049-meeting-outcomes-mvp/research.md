# Research: Meeting Outcomes MVP

## Decision: Store outcomes as first-class meeting content

Outcome data will live in dedicated tables instead of only extending
`ProcessingResult.summary_status`.

**Rationale**: The MVP blocker is not whether a provider says a summary exists;
it is whether 2brain Rec stores launch-safe, reviewable, deletion-accounted
meeting outcomes. Dedicated tables let the system track category-level state,
source evidence, provider/template provenance, retry attempts, lifecycle state,
and deletion participation.

**Alternatives considered**:

- Reuse `summary_status` only: rejected because it cannot store content,
  category state, evidence, deletion accounting, or readiness proof.
- Store one JSON blob on `processing_results`: rejected because it weakens
  queryability, RLS/accounting clarity, category-level rendering, and future
  version history.

## Decision: Generate outcomes server-side after transcript import

The server will create or reuse an outcome set after a latest processing result
has an available transcript. The generation service is idempotent for the
workspace, meeting, media revision, processing result, and generator version.

**Rationale**: The PRD requires server-owned notes generation and forbids
desktop-to-provider egress. Running after transcript import keeps the workflow
near existing MediaScribe processing while allowing transcript/playback review
to become visible immediately.

**Alternatives considered**:

- Generate inside the desktop app: rejected by data-boundary and secret rules.
- Block `ProcessingStatus.PROCESSED` until outcomes finish: rejected because it
  delays transcript/playback review and violates FR-016.
- Generate only on page render: rejected because it risks duplicate work,
  request latency, and less durable failure truth.

## Decision: MVP generator is deterministic, extractive, and safe-by-default

The first implementation should produce launchable stored outcomes using a
server-owned deterministic/extractive generator over transcript segments:
summary/key points from bounded transcript excerpts, decisions/actions/followups
only when supported by strong textual cues, and explicit "not found/not
inferable" category states otherwise. The same service interface can later
delegate to an approved LLM provider.

**Rationale**: There is no existing configured 2brain LLM provider in the repo,
while the MVP still needs stored outcomes now. A deterministic generator can be
tested, kept within 30 seconds for a one-hour transcript, and made
non-fabricating by design. It closes the stored-output blocker more honestly
than pretending provider summary availability is enough.

**Alternatives considered**:

- Enable MediaScribe `summarize=true` only: rejected because it may provide a
  summary but not full category truth, action items, decisions, provenance,
  deletion accounting, or 2brain-owned storage.
- Add an unconfigured LLM provider immediately: rejected because it would add
  secrets, admin provider policy, content-bearing prompt handling, deletion
  obligations, and production risk beyond this slice.
- Keep placeholders and defer: rejected because the objective is to move toward
  full MVP and the current readiness blocker is exactly placeholders.

## Decision: MediaScribe summary is optional source material, not a blocker

If imported MediaScribe payloads include summary content in the future, the
outcome service may store it as a summary source, with provenance and deletion
accounting. Current 049 implementation must not rely on provider-reported
summary availability alone.

**Rationale**: The PRD says MediaScribe summary should be used when available,
but the current code normalizes only `summary_status` and intentionally blocks
that state as not launch-safe. 049 can add a place to persist summary content
later without requiring a live MediaScribe contract change in the MVP slice.

**Alternatives considered**:

- Change `TWOBRAIN_MEDIASCRIBE_SUMMARIZE=true` in production now: rejected
  until result content persistence, deletion accounting, and privacy evidence
  are in place.

## Decision: Category-level truth drives UI and readiness

Each category has a stored state: `available`, `not_found`, `not_inferable`,
`processing`, `blocked`, or `unsafe`. The review UI renders the category state
and, for available categories, the stored items and transcript evidence.

**Rationale**: The transcript often will not contain decisions, owners, due
dates, or risks. Category truth prevents hallucination and gives users a useful
review page even when some categories are empty.

**Alternatives considered**:

- One global "notes available" flag: rejected because partial output and
  no-inferable categories are expected MVP cases.

## Decision: Outcomes participate in access, deletion, retention, and egress

Outcomes are derived meeting content. They should be hidden for denied viewers,
blocked for deleting/deleted meetings, included in deletion artifact accounting,
and kept out of downloads/export unless an existing policy explicitly allows
the relevant artifact.

**Rationale**: Outcome text can be as sensitive as transcript text. Treating it
as metadata would violate constitution deletion and data-boundary gates.

**Alternatives considered**:

- Show outcome state to denied users: rejected because outcome existence can
  leak meeting state.
- Leave deletion reports unchanged: rejected because outcomes would survive in
  the product truth model without an accounting row.

## Decision: Browser runtime proof is required

049 needs a browser/runtime verifier that checks ordinary web, mobile-width
web, and desktop embedded review with stored outcomes, partial/blocked states,
bottom playback bar coexistence, no horizontal overflow, and no download-link
coupling.

**Rationale**: The product uses server-owned HTML for both web and macOS
embedded review. The MVP objective explicitly requires rechecking both
interfaces and the recent 046/048 work proved that code tests alone can miss
visibility/layout issues.

**Alternatives considered**:

- Rely on unit tests only: rejected because overlap/overflow/parity are UI
  runtime behaviors.

## Decision: Readiness remains honest unless stored outcomes are proven

`notes-action-output` closes only after stored outcomes are visible, access
controlled, deletion-accounted, and validated in web plus embedded review. If
any category remains intentionally limited, docs and release notes must say so
in simple Russian.

**Rationale**: The goal is a full MVP, not a green-looking status page. The
readiness model must not overclaim AI assistant completeness.

**Alternatives considered**:

- Close readiness from implementation intent: rejected because current project
  guidance requires evidence-backed truth.
