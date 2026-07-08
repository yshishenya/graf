# 092 Research: Automatic Meeting Detection

**Date**: 2026-07-08

## Decisions

### Server/Admin Before macOS Detector Upload

**Decision**: Implement the server telemetry endpoint, admin review queue,
registry draft/publish flow, and remote registry endpoint before enabling macOS
automatic candidate upload.

**Rationale**: The product needs a safe place to receive, inspect, suppress, and
promote likely VKS candidates before desktop clients send metadata
automatically. Server/admin first also lets forbidden-content rejection,
idempotency, rate limiting, and audit behavior be tested before client rollout.

**Alternatives Considered**:

- Client-only local telemetry first: simpler locally, but leaves no admin review
  loop and encourages ad hoc diagnostic export.
- Hardcoded client allowlist first: fastest prompt path, but forces client
  rebuilds for registry changes and does not learn missing Russian-market apps.

### Remote/Cache/Seed Registry

**Decision**: Use a versioned JSON target registry served by the server, cached
locally by the client, with a packaged seed fallback.

**Rationale**: The target list changes as Russian and global VKS apps are
validated. JSON is small, auditable, versioned, easy to validate, and fits both
server and macOS clients. A packaged seed preserves offline behavior.

**Alternatives Considered**:

- Client-only Swift registry: safer by compilation but too slow to update and
  unsuitable for admin-driven review/publish.
- Client SQLite/CoreData registry: unnecessary for small read-mostly data and
  harder to diff, sign, inspect, and roll back.
- Server database only with no JSON contract: convenient for admin UI but weaker
  as a stable desktop contract.

### Automatic Candidate Upload With Client-Side VKS Filter

**Decision**: Automatically upload bounded metadata-only rollups for known target
health and unknown apps only after the client VKS-candidate filter passes.

**Rationale**: The owner needs to see likely missing VKS apps in admin without
asking every user to export diagnostics, but uploading every mic-using app would
be an app inventory leak. The filter requires stable mic attribution plus VKS
signals, blocks known non-target categories, and rate-limits identity upload.

**Alternatives Considered**:

- Manual export only: privacy-safe but too slow to discover missing apps.
- Upload all mic apps: unacceptable privacy and trust risk.
- Server-side-only filtering: too late because raw app inventory would already
  leave the machine.

### Unknown Apps Never Prompt

**Decision**: Unknown native apps remain non-prompting and non-recording even
when telemetry score is high. They can only become `diagnostic_only` through a
reviewed registry update, and `prompt_enabled` only after target-specific QA.

**Rationale**: A high candidate score is discovery evidence, not product support
evidence. Recording behavior must stay fail-closed.

### Native macOS Detector Rule

**Decision**: First native detector uses Gilb-style Control Center
`sensor-indicators` `mic:<bundle_id>` attribution with a 5 second start debounce
and 15 second end grace.

**Rationale**: Local runtime checks showed Zoom and Yandex Telemost emit stable
bundle-specific mic attribution and removal/end behavior. This is a narrow,
event-driven detector with low overhead and clear false-positive constraints.

**Alternatives Considered**:

- Process launch/process name: too broad and false-positive prone.
- Window title/Accessibility first: more private-data exposure and permission
  complexity.
- Network activity first: useful later, but not enough for MVP and adds raw
  metadata risk if not carefully bucketed.

### Browser Detection Path

**Decision**: Browser meetings use browser metadata plus calendar or join intent,
not browser microphone attribution alone. The first browser Tier A attempt is
Yandex Telemost web in Chromium-family metadata surfaces, with Yandex Browser
included if the metadata path validates.

**Rationale**: Browsers host voice search, media, permissions tests, and many
non-meeting pages. Browser mic use is only supporting evidence.

### Admin Review Queue

**Decision**: Add `/admin/meeting-detection` with queues for VKS candidates,
known target health, and registry drafts. Admin actions are audited and registry
publishing is explicit.

**Rationale**: The owner needs a product surface to review likely apps, mark
non-targets, merge with existing targets, create `diagnostic_only` drafts,
request validation, and publish reviewed registry versions. Audit preserves
change accountability.

### Metadata And Redaction Boundary

**Decision**: Telemetry contains only bounded rollups: target ids, safe labels,
platform/OS major, registry/filter versions, signal families, candidate score,
reason codes, counts, and duration buckets. It excludes raw logs, full URLs,
meeting content, transcript text, audio, attendee emails, raw IPs, secrets, app
paths, and user home paths.

**Rationale**: Meeting detection and discovery are sensitive. Metadata-only
rollups are enough to improve support without content leakage.

## Open Risks For Implementation

- macOS unified log behavior is private and may change; detector must degrade to
  manual recording with health evidence.
- Browser metadata mechanisms vary by browser and permission state; browser
  support may remain detect-only/manual-only for Safari/Firefox in the first
  release.
- Russian enterprise/on-prem products may use branded wrappers or custom bundle
  IDs; admin review must support merging and per-target validation.
- Candidate scoring thresholds may need tuning after dogfood evidence, but
  tuning must not broaden prompt behavior automatically.
