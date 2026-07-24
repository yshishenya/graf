# Implementation Plan: Надёжный и безопасный обмен встречами

**Branch**: `125-meeting-sharing`
**Date**: 2026-07-23
**Spec**: [spec.md](spec.md)
**Scenario design**: [scenarios.md](scenarios.md)

**Input**: Feature specification from `/specs/125-meeting-sharing/spec.md`

## Summary

Feature 125 repairs the current Share dead end and turns the modal into a
server-policy-aware access surface. The first implementation fixes internal B2B
summary-only sharing and implements the B2C exact-email invitation path behind
an operator gate: safe metadata email, one-click magic-link acceptance with
automatic personal-account bootstrap, exact invited identity, separate grant
token, bounded expiry and revoke. The controlled
exact-email path is now enabled in production after the delivery, secret,
abuse, deletion and rollback evidence gates; public links stay disabled. The
plan also keeps native address-book, viral onboarding and referral
contracts separate from access delivery. The expanded viral design puts
participant distribution and `Shared with me` first, followed by opt-in owner
auto-share, recurring pre-read, team access and existing-grant channel or
calendar distribution; batch distribution remains a later operation/run slice.

The Ponytail path is deliberately incremental: reuse existing access/grant,
invitation, calendar, audit, deletion, analytics and cabinet UI authorities;
avoid a new storage model or dependency in Phase 0/1; add only the smallest
policy projection and UI behavior needed to remove the observed failure. A
future participant batch may require one narrow bounded operation/idempotency
record; it must not grow into separate outbox, notification and referral
storage models.

## Technical Context

**Language/Version**: Python 3.13; browser JavaScript/CSS; server-rendered Jinja2 cabinet

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy async, Jinja2, native HTML dialog, existing Temporal/email/calendar/access services; no new dependency

**Storage**: Existing PostgreSQL tables `meeting_share_grants`, `meeting_share_invitations`, workspace identity/membership, calendar snapshots/participants and metadata-only egress audit; encrypted invitation fields retain only the short-lived recipient exchange material and separate grant-token material needed for acceptance replay

**Testing**: pytest unit, contract and integration suites; static contract checks; synthetic manual browser/embedded matrix; `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: high-risk-feature. The slice changes privacy-sensitive sharing, identity search, invitations, authorization, token-bearing links, deletion/expiry behavior and a user-facing modal. It requires full Spec Kit, security/UX checklists, threat-model gates, focused quickstart and repository CI.

**Release Gate**: PR/closeout requires the focused quickstart and
`infra/scripts/ci-local.sh`. A production deploy is allowed only for the
validated slice after `cd-remote.sh --dry-run`, Russian release notes, rollback
readiness and explicit user approval. Exact-email external delivery is enabled
only for the bounded recipient flow; public links, native Contacts/provider
lookup and referral attribution remain false.

**Target Platform**: browser cabinet and embedded macOS WebKit cabinet backed by the same server routes; native address-book picker is a later macOS client contract, not browser sync

**Project Type**: server-rendered web application embedded in a native macOS capture product

**Performance Goals**: internal recipient search p95 under 1 second for the bounded 20-result query in synthetic fixtures; no network request for disabled capabilities; Share modal remains responsive at the existing cabinet scale

**Constraints**: fail closed; internal and external defaults are summary-only/view-only; external/public flags stay false by default; no raw meeting content, contact records, email delivery secret or bearer token in evidence/logs/analytics; no full address-book sync; 320 CSS px and 200% zoom; browser/embedded parity; no copied competitor UI

**Scale/Scope**: one meeting Share fragment, current workspace/meeting roster candidate search, existing grant/invitation/link lifecycle, existing summary route, exact-email delivery, synthetic security/UX tests; public/contact/referral rollout remains independently gated

## Constitution Check

### Pre-research gate

- **Capture-first integrity**: PASS. The slice does not change recording start/stop,
  system audio, microphone, routing, buffering or upload truth.
- **Visible consent and user control**: PASS. Sharing is an explicit owner action;
  calendar/contact suggestions never create recording consent or access.
- **Data boundary and secret discipline**: PASS with mandatory blockers. Meeting
  content stays behind existing authorization; raw tokens/emails/contact payloads
  are excluded from audit, logs, analytics and committed evidence. Token URL
  hygiene and delivery ambiguity are explicit plan gates.
- **Server authorization and deletion truth**: PASS with mandatory implementation
  checks. Existing access/deletion authorities remain canonical; accepted grants
  inherit bounded invitation expiry; deletion wins share races.
- **External dependency safety**: PASS. Exact-email delivery uses the existing
  Postal provider with a server-only key and a generated HMAC identity secret;
  public links remain gated and no new provider is introduced.
- **Spec-driven delivery**: PASS. Specify, clarification scan, research, plan,
  data model, contracts, checklist, tasks, analyze, issue sync and implementation
  are required.
- **Original design/accessibility**: PASS pending QA. The modal reuses GRAF cabinet
  tokens and native controls, with keyboard/focus/reduced-motion/contrast and
  browser/embedded parity requirements.

### Post-design gate

PASS with conditions:

1. Exact-email external delivery is enabled only after the delivery, abuse,
   token, deletion and rollback evidence recorded in
   [research.md](research.md#обязательные-blockers-перед-rollout); public,
   contact and referral rollout remains disabled.
2. Internal and external rollout remains limited to summary-only view unless a
   later approved slice changes policy.
3. No new persistence is introduced for contacts or referral attribution until
   retention/deletion and analytics contracts are approved.
4. Token/header/log protections and accepted-grant expiry are blocking, not
   optional hardening.

## Design decisions

### Capability authority

Add a small `SharePanelState` capability projection derived from current meeting
authorization and runtime settings. The fragment and JSON review use the same
projection. The client renders available actions and bounded reasons but never
uses the projection as a substitute for mutation authorization.

### Recipient search authority

Bind `share-recipients` to `meeting_id` and the requesting actor. Reuse
`decide_meeting_access` before querying. Search active current-workspace
identity by safe display name and permitted verified email, then merge eligible
calendar matches from the existing linked roster. Escape wildcard input, cap
results and keep suggestions side-effect free.

### Internal grant UX

Separate “Найти” from the explicit result-row “Открыть доступ”. After a successful
grant, render the returned recipient-bound URL as Copy link and add the access
row without inventing a broader link. Revoke removes the row only after a 204;
failure remains visible.

### External/public safety

When external delivery is disabled, no invitation POST is made. The typed value
is preserved and the user sees a policy explanation. When enabled, the endpoint
accepts only exact email + summary-only/view-only scope and remains fail-closed
for stale/hostile clients. Public link creation/resolution keeps the existing
gates and remains disabled in this rollout.

### Viral and contact phases

Use metadata-only value-led CTA and explicit onboarding as a later gated phase.
Do not add a new analytics dependency. Address book is native limited selection
only; browser surfaces do not request Contacts access or sync a full address
book. Calendar presence is a suggestion source, never consent.

Participant distribution is not a loop over the existing single-recipient POST.
Before implementation, select a replay-safe idempotency/run authority, define
per-recipient partial outcomes and keep bearer URLs out of the batch response
when `Shared with me` is sufficient. Retry must never rotate a grant token.

## Validation Plan

1. Run the requirements/security/UX checklists and keep any blocked gated phase
   visibly marked.
2. Run focused unit tests for grant capability, recipient normalization/search,
   invitation expiry transfer, effective policy and problem-code mapping.
3. Run contract tests for the fragment, capability projection, no-disabled-request
   behavior, returned Copy link, source labels, focus and privacy headers.
4. Run integration tests for authorized meeting-bound search, internal grant,
   recipient-bound resolution, revoke/rotation/expiry/deletion and parallel
   duplicate actions.
5. Run synthetic token/log/analytics negative tests, calendar side-effect tests,
   delivery-state tests and provider-disabled external invitation tests.
6. Execute [quickstart.md](quickstart.md), including browser/embedded parity,
   keyboard, VoiceOver, 320 CSS px, 200% zoom, light/dark, reduced motion and
   increased contrast.
7. Run `git diff --check` and `infra/scripts/ci-local.sh` before PR/closeout.
8. Run Ponytail review, product-design audit and code/security review. Production
   deploy is allowed only for the exact-email capability after the recorded
   rollout gate; public/contact/referral deploy remains out of scope.

## Project Structure

### Documentation (this feature)

```text
specs/125-meeting-sharing/
├── spec.md
├── scenarios.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── meeting-sharing.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/cabinet.py
├── api/schemas.py
├── cabinet/access.py
├── cabinet/queries.py
├── cabinet/review_policy_rendering.py
├── cabinet/static/cabinet/cabinet.js
├── cabinet/static/cabinet/cabinet.css
├── cabinet/templates/cabinet/fragments/meeting_share.html
├── cabinet/templates/cabinet/pages/share_invitation_content.html
├── cabinet/rendering.py
├── db/models/meeting_access.py
└── observability/logging.py

apps/server/tests/
├── unit/test_recording_workflow_access.py
├── unit/test_meeting_sharing.py
├── contract/test_recording_share_ui_contract.py
├── contract/test_recording_share_invitation_contract.py
├── contract/test_meeting_sharing_contract.py
└── integration/test_meeting_share_links.py
```

**Structure Decision**: Keep the existing server-rendered cabinet architecture
and extend the current access and calendar helpers. Do not introduce a React
share component, a second permission service, a contact-sync subsystem, a new
email provider or a new database table in this slice.

## Implementation phases

### Phase 12 — Magic-link acceptance and account-created notification

- replace the invitation-only email-code handoff with an explicit, CSRF-bound
  magic-link POST that consumes the existing invitation continuation exactly once;
- retain the invited address only as encrypted delivery material until acceptance,
  revoke or expiry so the link can bootstrap the exact recipient without putting
  email in the URL or client state;
- create/reuse the recipient personal account, issue the browser session and open
  the summary in the same response; do not add workspace membership;
- queue an idempotent account-created email after commit with links to `/meetings`
  and `/settings`, and keep notification delivery state separate from access;
- simplify the Share modal around recipient, default summary-only scope, explicit
  one-step invite confirmation and understandable delivery states while preserving
  existing GRAF cabinet tokens, focus management and browser/embedded parity;
- keep standard non-invitation email login code-based, and keep public links,
  Contacts/provider lookup and referral attribution gated.

### Phase 0 — Repair and hard safety invariants

- capability projection and explicit disabled state;
- meeting-bound recipient search and escaped query;
- domain-level scope/audience validation;
- accepted invitation expiry propagation;
- token/header/log/autocapture protections where existing shell allows;
- focused negative tests.

### Phase 1 — Internal Share UX

- workspace/email/calendar candidate projection;
- explicit result-row grant action;
- returned recipient-bound Copy link;
- active grant list, revoke, rotation and bounded status/error copy;
- browser/embedded and accessibility parity.

### Phase 2 — B2C gated delivery and later extensions

- B2C external invitation delivery state, exact-email onboarding and CTA behind
  the operator gate; the exact-email capability is enabled in the current
  controlled production rollout, while broader viral extensions remain gated;
- explicit share-to-eligible-participants action and `Shared with me` adoption
  loop, after idempotent distribution/run design;
- owner opt-in auto-share, recurring pre-read and bounded action-item delivery;
- admin-gated summary-only team access with no retroactive grant by default;
- calendar pointer and Slack/Teams distribution that reuse existing grants;
- public links and edge/app abuse gates;
- native Contacts picker and provider-specific least-privilege lookup;
- opaque referral attribution and aggregate funnel measurement.

## Complexity Tracking

No constitution exception is requested. The high-risk complexity is handled by
reuse of existing authorities and by keeping Phase 2 capabilities disabled until
their independent gates have evidence.

Ponytail review (2026-07-23): Lean already. No new dependency, storage model,
permission service or contact-sync layer was introduced; the remaining gated
phases are intentionally design/contract-only.
