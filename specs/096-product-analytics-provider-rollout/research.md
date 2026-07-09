# Research: Product Analytics Provider Rollout

**Feature**: `096-product-analytics-provider-rollout`

## Sources Reviewed

- PostHog self-host docs: https://posthog.com/docs/self-host
- PostHog open-source self-host support: https://posthog.com/docs/self-host/open-source/support
- PostHog self-host environment variables: https://posthog.com/docs/self-host/configure/environment-variables
- PostHog session replay storage: https://posthog.com/docs/self-host/configure/session-replay-storage
- Yandex Metrica API authorization: https://yandex.com/dev/metrika/en/intro/authorization
- Yandex Metrica API quick start: https://yandex.com/dev/metrika/en/intro/quick-start
- Yandex Metrica offline conversions: https://yandex.com/dev/metrika/en/management/offline-conv
- Local baseline: `specs/093-public-landing-analytics/contracts/analytics-provider-setup.md`
- Local baseline: `docs/analytics/product-activation-analytics.md`
- Local baseline: `specs/094-product-activation-analytics/validation/implementation-evidence.md`

## Decision: Use Self-Hosted PostHog, Not PostHog Cloud

Self-hosted PostHog is the primary product analytics workspace for 096. PostHog Cloud is excluded.

**Rationale**: The 096 spec requires owner-controlled analytics and broad first-party product learning. Official PostHog docs state that self-hosting means running or purchasing the infrastructure, choosing URLs, and managing scaling risk. That matches the product decision that PostHog is inside the GRAF contour.

**Alternatives considered**:

- PostHog Cloud: rejected by explicit scope.
- Yandex-only product analytics: rejected because Yandex is the parallel ad/web surface, not the primary product workspace.
- Custom analytics store: rejected because 094 already prepared provider wrappers and dashboards.

## Decision: Deploy PostHog On The Same Production Server First, With Separate Domain And Portability

The first rollout places PostHog on the existing production server, exposed through a separate analytics domain such as `analytics.2brain.pro`, with separate service boundaries, TLS routing, secret files, volumes, resource limits, backups, health checks, and rollback.

**Rationale**: This starts quickly without losing operational separation. The PostHog docs also make clear self-hosted instances are the operator's responsibility and PostHog is data-intensive at production scale, so portability and resource isolation are required from day one.

**Alternatives considered**:

- Separate analytics server immediately: cleaner isolation, but slower for the first rollout.
- Same host and same domain/path: rejected because it makes later move-out and rollback harder.
- Staging-only PostHog: rejected because 096 is a production-ready provider rollout.

## Decision: Make PostHog Broad First-Party Analytics With Autocapture Everywhere

PostHog autocapture is enabled everywhere immediately for current browser-rendered GRAF pages and becomes the default for future browser-rendered pages once global credential suppression exists.

**Rationale**: The product clarification explicitly chooses maximum product learning because self-hosted PostHog is owner-controlled. Autocapture helps discover unexpected clicks, paths, drop-offs, and UX friction that explicit events miss.

**Boundaries**:

- This broad allowance is PostHog-only.
- It does not automatically enable PostHog session replay.
- It does not apply to Yandex, Webvisor, click maps, scroll maps, form analytics, paid advertising platforms, committed evidence, logs, screenshots, or raw payload dumps.
- Security credential material must be suppressed everywhere.

**Alternatives considered**:

- Explicit events only: safer but misses product behavior.
- Page-class restricted autocapture: rejected by clarification.
- Replay everywhere: rejected because replay remains a separate capability with stronger proof and storage implications.

## Decision: Keep PostHog Session Replay Separate From Autocapture

PostHog autocapture is broad. PostHog session replay remains a separate feature flag and page-class state.

**Rationale**: Official PostHog self-host replay storage uses blob-backed recordings in current deployments. Replay changes storage volume, retention, masking, and proof requirements more than autocapture. The spec only approved autocapture everywhere, not replay everywhere.

**Alternatives considered**:

- Enable replay everywhere with autocapture: rejected because it would exceed clarification and add recording storage risk.
- Disable replay forever: rejected because future approved replay may be valuable.

## Decision: Use Existing 093 Yandex Production Counter As Expandable Surface

096 reuses the existing production Yandex counter from 093 for public pages, future all-pages measurement, Yandex Direct linkage, and approved offline conversions.

**Rationale**: This preserves attribution continuity from public acquisition to product milestones. A single counter is better for Yandex Direct and offline conversion linkage than a separate product counter.

**Alternatives considered**:

- Separate product counter: cleaner separation but weaker attribution continuity.
- Existing counter only for offline conversions: too narrow for the requested expandable all-pages Yandex surface.
- Planning blocker: unnecessary after clarification.

## Decision: Yandex All-Pages Uses Inventory Gates, Unlike PostHog Autocapture

Yandex collection remains gated by an all-pages inventory. Future pages are blocked for Yandex until the inventory approves them. Public `/` and `/download` remain the live approved baseline from 093.

**Rationale**: Yandex is an external/ad-facing provider and does not inherit PostHog's first-party allowance. Yandex Webvisor/maps/forms require page-class proof and legal/QA status.

**Alternatives considered**:

- Yandex everywhere immediately: rejected because it conflicts with the external provider boundary.
- Yandex public only forever: rejected because 096 requires an expandable all-pages surface.

## Decision: Enable Live Yandex Offline Conversion Upload For Two Milestones

Yandex offline conversion live upload is in scope for exactly:

- `desktop_account_connected`
- `first_value_session_completed`

**Rationale**: The Yandex docs require an OAuth token and counter/tag ID for the offline conversion upload endpoint. They also support identity linkage through owner `UserId`, Yandex `ClientId`, or `Yclid`. This matches 094 attribution bridging and the 096 goal of feeding real product activation signals into the existing Yandex counter.

**Alternatives considered**:

- Dry-run only: safer but not a real provider rollout.
- Only `desktop_account_connected` live: partial and harder to explain.
- More product milestones: rejected by explicit scope.

## Decision: Keep Provider Secrets In Runtime Secret Files Only

PostHog project key, PostHog internal service secrets, Yandex OAuth token, and any live runtime IDs are not committed. Runtime file paths may be documented only as placeholders.

**Rationale**: The constitution and product gates prohibit committing credentials, tokens, signed URLs, live credential paths, raw payloads, or private evidence. Yandex docs also state OAuth tokens must be stored securely and are required in the Authorization header.

**Alternatives considered**:

- Plain environment values: rejected for secrets.
- Committed test values resembling live IDs: rejected because 093/094 already found provider config evidence must avoid live values.

## Decision: Use Metadata-Only Smoke And Evidence

Provider smoke proves runtime propagation, reachability, delivery status, dashboard/goal visibility, duplicate handling, and rollback readiness. Evidence records statuses and redacted metadata only.

**Rationale**: GRAF evidence must not contain raw audio, transcript text, meeting content, tokens, signed URLs, cookies, visitor/account IDs, screenshots with account data, or raw provider payloads.

**Alternatives considered**:

- Raw network payload evidence: rejected.
- Provider screenshots with live data: rejected.
- Manual dashboard inspection with no artifact: rejected because rollout evidence must be reviewable.

## Decision: Paid Campaign Launch Remains Blocked

096 may enable provider infrastructure and live Yandex offline conversions, but paid campaign launch is a separate legal/campaign readiness decision.

**Rationale**: 093 closeout already kept paid campaign launch blocked. 096 adds product/provider capability but does not replace legal, operator notice, campaign naming, or interpretation approval.

**Alternatives considered**:

- Treat technical provider smoke as campaign readiness: rejected.
- Block all provider setup until campaign approval: rejected because 096 is provider rollout, not campaign launch.
