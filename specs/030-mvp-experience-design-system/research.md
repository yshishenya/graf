# Research: MVP Product Experience And Design System

## Decision: Hybrid Product Experience Model

Use a native macOS desktop trust shell for capture-critical behavior, a full
browser web cabinet for the broad product, and an allowlisted embedded desktop
cabinet subset for non-capture account, upload, processing, meeting review, and
basic settings workflows.

**Rationale**: ADR `001` and the constitution require active recording truth,
visible indicator, Stop, permission recovery, local artifact truth, and local
queue truth to remain local/native. A full browser cabinet avoids duplicating
review/admin/product screens across platforms. The embedded subset gives the
desktop app useful server-connected value without making it a full web browser
or giving remote content control over recording.

**Alternatives considered**:

- Fully native cabinet in every desktop app: strongest native feel, but too slow
  and duplicative for web review/admin surfaces.
- Full web app inside desktop: faster, but unsafe for capture-critical trust and
  too easy to show irrelevant browser-only product areas inside the recorder.
- Server-driven native schema for all screens: useful later for non-critical
  forms, but unnecessary complexity for this design-readiness slice.

## Decision: Owner Value Loop Is The Prototype v1 Boundary

The first prototype proves the launch-critical owner journey: record in the
app or upload owned media, see current status consistently in app and web, wait
through transcription, and receive a complete meeting review.

**Rationale**: This creates a finished reviewable value artifact rather than a
large but shallow screen gallery. It validates the already implemented `014`
desktop upload and `015` processing behavior from a product-experience angle,
then maps remaining work to `016` dashboard review, `017` access/sharing, `018`
retention/deletion, design-system, and desktop/web polish slices while avoiding
premature admin/billing/team scope.

**Alternatives considered**:

- Happy-path-only prototype: fast but misses the states that make the product
  trustworthy.
- Full product prototype with admin, billing, sharing, audit, help/legal, and
  full video UX: broader but likely to delay the MVP and weaken the launch
  value loop.
- Desktop-only prototype: avoids web complexity but does not prove the product
  promise after upload/transcription.

## Decision: Figma Preferred, StitchFlow Fallback

Use Figma as the preferred source for the visual pack and clickable prototype
when access and free-plan limits allow. Use StitchFlow as a documented fallback
when Figma access, file limits, connector availability, or workflow friction
blocks delivery.

**Rationale**: Figma is better for review, manual refinement, collaboration,
and design-system discussions. StitchFlow is a practical fallback because it
can generate multi-screen projects, `DESIGN.md`, variants, screenshots, HTML/
code checkpoints, and local handoff evidence. Repo artifacts remain the
product source of truth regardless of visual tool.

**Alternatives considered**:

- Repo-only Markdown design: durable but insufficient for UI review.
- StitchFlow as primary source: useful for generation and fallback, but less
  ideal as the primary collaborative design canvas.
- Disposable coded prototype as primary artifact: too close to implementation
  and likely to distract from product/design decisions.

## Decision: Route Visibility Matrix Required

Every cabinet route and navigation element must be classified as embedded
desktop, browser-only, hidden in desktop, disabled in desktop, or hand off to
browser.

**Rationale**: Without an explicit matrix, the embedded desktop cabinet can
accidentally become the full web cabinet. The matrix makes app/web boundaries
testable and gives future Windows/native shells a reusable contract.

**Alternatives considered**:

- Decide visibility per screen during implementation: faster now, but likely
  to create inconsistent app/web behavior.
- Embed all cabinet routes and hide only capture controls: rejected because the
  recorder app would inherit broad admin/billing/legal complexity.

## Decision: Cross-Surface Status Model Required

Define shared user-facing states for local recording saved, local only, queued,
uploading, uploaded, audio extraction, transcription, transcript ready, notes
ready, partial/degraded, failed, deleted, and access denied.

**Rationale**: The core user value depends on app and web not contradicting
each other while upload/transcription/review evolves asynchronously. Status
truth also protects deletion, retention, and support copy.

**Alternatives considered**:

- Surface-specific status labels: gives each UI freedom but creates trust risk.
- Only backend technical states: too implementation-oriented and not clear to
  users.

## Decision: Manual Upload Is Audio-First With Common Video Containers

Manual upload may accept user-owned audio files and common video/meeting files,
but the MVP promise is usable audio extraction and meeting intelligence, not a
full video product.

**Rationale**: Users often have Zoom/Meet/Teams-style recordings in video
containers. Accepting them increases usefulness, but full video playback,
timeline review, video-native annotations, and collaboration are too large for
the MVP design promise.

**Alternatives considered**:

- Audio-only: simpler but rejects common real-world meeting files.
- Full video review: valuable later but expands design, processing, playback,
  storage, and accessibility requirements.

## Decision: Clean-Room Krisp Benchmark

Use Krisp only for category-level learning: compact recorder controls, meeting
assistant navigation patterns, status clarity, settings grouping, and trust
copy patterns. Do not copy Krisp UI expression, copy, icons, assets, proprietary
flows, screenshots, binaries, or model behavior.

**Rationale**: Krisp is a useful category reference, but the constitution and
PRD require original `2brain Rec` design and brand-distance review.

**Alternatives considered**:

- Direct UI imitation: rejected for legal/product differentiation risk.
- No benchmark: safe legally but loses category learnings for UX ergonomics.

## Decision: Planning Produces Contracts, Not Production Code

This slice creates design and handoff contracts. Production implementation is
deferred to follow-up Spec Kit features, except where it documents and validates
already implemented behavior from `014` desktop upload and `015` processing.

**Rationale**: The current feature is explicitly design/product readiness. It
must align with implemented `014/015`, guide `016-018` and later UI
implementation, and avoid silently broadening scope into production code.

**Alternatives considered**:

- Implement prototype in repo as production UI: rejected because the spec does
  not authorize implementation and design choices are still under review.
- Stop at narrative docs: rejected because downstream teams need route/status/
  prototype contracts and validation steps.
