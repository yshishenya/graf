# Research: Meeting Dashboard Review

Feature: `016-meeting-dashboard-review`
Date: 2026-06-16

## Decision: Server-Owned FastAPI Cabinet For 016

Use the existing FastAPI server to serve both content-safe JSON endpoints and a
server-owned HTML/CSS/vanilla-JS cabinet shell. Do not introduce a separate
frontend package or build toolchain in this slice.

**Rationale**: The repository currently has a mature FastAPI backend and no
frontend app scaffold. The immediate launch need is an authorized owner review
surface over accepted ingest/processing/RLS data. A small server-owned cabinet
keeps implementation close to existing auth/session/RLS boundaries and can be
embedded in desktop routes later.

**Alternatives considered**:

- New React/Vite app: better long-term UI ergonomics, but adds build, routing,
  packaging, auth, and deployment surface before the first product review value.
- Native-only macOS review UI: duplicates product workflows across platforms
  and violates the web-owned post-meeting surface direction in ADR 001/030.
- API-only implementation: validates data but does not satisfy user-facing
  launch/readiness or reference-matched UI goals.

## Decision: Reuse Existing Meeting And Processing Tables

Build meeting list/detail view models from existing `meetings`,
`processing_workflows`, `mediascribe_jobs`, `processing_results`,
`transcript_segments`, `diarization_segments`, and
`processing_dependency_states` tables. Do not add duplicate summary/review
tables in 016.

**Rationale**: Features 012/015/031/032 already established owner-controlled
ingest, processing import, content-safe status, and RLS table coverage. 016 is
a read/review slice over those accepted sources.

**Alternatives considered**:

- New denormalized dashboard table: faster queries later, but creates lifecycle
  and deletion/accounting duplication before the first UI needs it.
- Store generated notes/action items: not accepted yet; summary generation and
  AI assistant behavior require a separate egress and observability slice.

## Decision: View State Is Explicit And Truthful

Represent ready, processing, pending, blocked, failed, partial, unavailable,
local-only, deleted-future, and access-denied states as explicit UI/API states.
Never render fake notes/transcripts while content is unavailable.

**Rationale**: Live Krisp web/desktop references show pending detail as a
first-class waiting state, and the 2brain Rec constitution requires truthful
availability and no unavailable content claims.

**Alternatives considered**:

- Hide unavailable meetings from the list: makes upload/processing failures
  invisible and undermines recovery.
- Render disabled-looking transcript with placeholder text: risks users reading
  placeholder as real content.

## Decision: Governance Actions Are Reserved, Not Executed

Reserve stable UI locations for share, export, download, retention, deletion,
assistant, templates, action items, tags, saved/starred state, and speaker
correction, but make out-of-scope actions disabled, planned, policy-controlled,
or no-op with clear copy.

**Rationale**: Crisp references show these affordances early, and 030 requires
route stability. However 017/018 own access/downloads/retention/deletion, and
assistant/template execution requires explicit content egress policy.

**Alternatives considered**:

- Remove all future actions: simpler, but would force redesign when 017/018
  land.
- Implement share/download/delete now: violates 016 out-of-scope boundaries and
  product deletion/access gates.

## Decision: Desktop Embedding Is A Route Contract, Not Native UI Work

016 validates embeddable `/desktop/meetings` and `/desktop/meetings/{id}`
semantics in documentation/contracts and web route behavior. It does not modify
the macOS shell or add WebView embedding code.

**Rationale**: ADR 001 and 030 already define the native-vs-web boundary. The
next practical step is to make the web surface safe and embeddable; native
integration can be a later platform slice.

**Alternatives considered**:

- Implement macOS embedding immediately: broadens scope into native UI, auth
  handoff, route guard, and WebView policy before the web surface exists.
- Ignore desktop embedding: risks building browser-only IA that cannot later fit
  the native capture shell.

## Decision: Raw Reference Screenshots Stay Outside Git

Save raw authenticated Krisp screenshots outside the repository and keep
tracked artifacts metadata-only.

**Rationale**: Live references contain private meeting titles, transcript text,
email addresses, and account identifiers. The spec requires saved references,
but the constitution forbids leaking real customer/private content into tracked
evidence.

**Alternatives considered**:

- Commit raw screenshots: violates privacy/content evidence rules.
- Discard screenshots entirely: loses implementation reference quality and
  contradicts the user request.

## Decision: Content-Safe Evidence And Tests Are Required

Validation must include tests or scans proving problem responses, logs,
diagnostics, tracked screenshots, and validation artifacts do not contain
secrets, signed URLs, raw audio, live paths, or real private meeting content.

**Rationale**: 016 is the first slice that deliberately exposes transcript text
to authorized users. The boundary between authorized product content and
metadata-only diagnostics must be tested.

**Alternatives considered**:

- Rely on existing redaction helpers only: useful but insufficient because new
  product routes add new response and evidence surfaces.
