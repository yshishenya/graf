# Implementation Plan: Product Activation Analytics

**Branch**: `094-product-activation-analytics` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/094-product-activation-analytics/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Design product activation analytics for GRAF after the completed `093` public
analytics scope. The plan defines a high-risk analytics architecture, not an
implementation: self-hosted PostHog is the preferred primary product analytics
workspace, Yandex Metrica is a parallel all-web-pages/ad/Webvisor/offline-
conversion surface, and every event/page/replay route is blocked until the
provider, identity, consent, masking, retention, dashboard, smoke, and legal
gates pass.

The planned activation funnel is:

```text
public_installer_download_clicked
-> desktop_first_opened
-> desktop_account_connected
-> desktop_autorecord_enabled
-> first_recording_completed
-> first_result_viewed
-> first_value_session_completed
```

This plan keeps the `093` production boundary intact: live analytics remains
limited to `/` and `/download` until a later implementation slice receives
explicit approval.

## Technical Context

**Language/Version**: Python `>=3.13` for the server, Swift tools `6.0` for the
macOS app, browser JavaScript for web analytics controllers, Markdown/YAML for
contracts and validation evidence.

**Primary Dependencies**: Existing FastAPI/Jinja/Pydantic/SQLAlchemy/Alembic
server stack, existing Swift macOS app (`macOS 14` platform target), Docker
Compose production runtime, current public Yandex Metrica controller from
`093`, future self-hosted PostHog instance if provider gates pass, future
Yandex Metrica all-pages/offline-conversion configuration if legal and masking
gates pass.

**Storage**: Planning only. Future implementation may use PostHog-owned
ClickHouse/object storage, Yandex provider storage, and small GRAF-owned bridge/
delivery-gap records in existing Postgres only after tasks approve exact
schemas. No new storage is created by this plan.

**Testing**: Current plan validation uses `git diff --check` and artifact
review. Future implementation validation must include focused server pytest,
contract tests for event/page/provider configuration, SwiftPM tests for desktop
event emission and telemetry gate behavior, compose/env propagation checks,
rendered-page checks, provider smoke, and `infra/scripts/ci-local.sh` before
implementation closeout.

**Risk / Validation Lane**: `high-risk-feature`. The feature touches product
analytics, authenticated/cabinet pages, desktop behavior, provider egress,
identity linkage, replay/Webvisor, consent/legal copy, retention/deletion
truth, campaign optimization, and production runtime smoke. Full Spec Kit
clarify, plan, checklist, tasks, analyze, task-to-issues, and separate
implementation approval are required.

**Release Gate**: `no deploy`. This pass creates planning artifacts only.
Provider setup, code, production smoke, deploy, and campaign launch remain
blocked until later implementation and release approvals.

**Target Platform**: GRAF production web/server on Docker at `rec.2brain.pro`,
browser-rendered public/auth/cabinet/product web surfaces, embedded desktop
webview surfaces, and native macOS desktop app. Windows and other desktop
platforms remain out of scope.

**Project Type**: Multi-surface product analytics architecture for a FastAPI web
service plus native macOS desktop app.

**Performance Goals**: Analytics must never block normal product workflows.
Provider failure becomes a measurement gap, not a user-facing failure. Future
events must be small bounded payloads; Yandex event parameters must stay below
provider limits; replay/maps/forms may be disabled page-by-page to preserve UX,
privacy, and reliability.

**Constraints**: No raw audio, transcript text, meeting title, participant,
calendar text, email, name, workspace/account name, raw account/user/workspace/
meeting ID, local path, object key, token, signed URL, password, passcode,
device name, or private free-text value may enter analytics. Product telemetry
requires one low-friction personal acceptance before normal product use. Minimum
approved analytics retention baseline is 90 days unless legal/security requires
a shorter category. Direct desktop egress to PostHog/Yandex is permitted only
after explicit legal/security/QA approval and one-time acceptance disclosure.

**Scale/Scope**: One activation funnel, six primary product milestones, six
existing public acquisition events, all browser-rendered page classes in the
inventory, one primary PostHog workspace, one parallel Yandex measurement/ad
surface, and two default Yandex offline conversion milestones:
`desktop_account_connected` and `first_value_session_completed`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: PASS for planning. Implementation remains blocked.

- Capture-first MVP integrity: PASS. This plan does not change capture,
  recording, audio routing, permissions, system audio, microphone behavior, or
  recording acceptance.
- Visible consent and user control: PASS with required gate. The plan requires
  one explicit personal product telemetry acceptance before normal product use
  and prohibits hidden/unbounded collection. Active capture visibility and
  one-action stop are unchanged.
- Data boundary and secret discipline: PASS with required gates. Provider IDs,
  tokens, API keys, live dashboard screenshots, raw payload dumps, signed URLs,
  and private evidence are forbidden in git. Desktop never sends audio to
  MediaScribe and never stores MediaScribe credentials.
- Deletion truth and lifecycle accounting: PASS with required gates. The plan
  requires retention/deletion truth for PostHog, Yandex, offline conversions,
  bridge records, provider-held aggregates, exported dashboards, and delivery
  gaps without promising universal erasure outside GRAF control.
- Spec-driven delivery with testable gates: PASS. Lane is high-risk; clarify is
  complete for this pass; plan artifacts are generated here; checklist, tasks,
  analyze, task-to-issues, and separate implementation approval remain required.
- Deployment/release gates: PASS. No deploy is performed. Future rollout must
  prove host env/secret source, composed service config, live container env,
  rendered HTML/JS, page-class inclusion/exclusion or replay-disabled state,
  provider reachability, and dashboard visibility.

## Validation Plan

Planning validation for this pass:

- `git diff --check`
- Review [research.md](./research.md), [data-model.md](./data-model.md),
  [quickstart.md](./quickstart.md), and all files under [contracts/](./contracts/)
- Confirm no `[NEEDS CLARIFICATION]` remains in the plan artifacts
- Confirm implementation remains explicitly blocked

Future implementation validation, to be expanded by `$speckit-tasks`:

- Server unit and contract tests for event catalog, forbidden fields, telemetry
  gate states, identity/bridge records, retention records, Yandex page
  inventory, replay-disabled page classes, and delivery-gap reporting
- Browser rendered-page tests proving provider snippets appear only on approved
  page classes and replay/maps/forms are disabled where masking proof is absent
- Desktop SwiftPM tests proving event emission is bounded, forbidden fields are
  rejected, direct provider egress is disabled unless approved, and product use
  follows the telemetry gate
- Compose/env tests modeled after the `093` production bug: host env or secret
  source, `docker compose config`, live container env, rendered HTML/JS, and
  provider reachability must all be checked
- Local CI through `infra/scripts/ci-local.sh`
- Production deploy/smoke only after a separate release gate; paid campaign
  optimization only after legal/campaign-readiness approval

## Project Structure

### Documentation (this feature)

```text
specs/094-product-activation-analytics/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── config.py
│   ├── public/analytics.py
│   ├── public/static/public/analytics.js
│   ├── public/templates/public/_analytics.html
│   ├── cabinet/
│   ├── api/
│   └── db/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

apps/macos/
├── Package.swift
├── RecApp/Sources/
│   ├── Cabinet/
│   ├── Capture/
│   └── Upload/
└── Shared/Tests/

infra/
├── docker-compose.yml
├── env/rec.production.env.example
└── scripts/

specs/094-product-activation-analytics/
├── contracts/
├── data-model.md
├── quickstart.md
├── research.md
└── plan.md
```

**Structure Decision**: Future implementation will be a multi-surface slice
touching server-rendered web/cabinet, runtime configuration, macOS desktop
telemetry-gate/event emission, and provider smoke. This planning pass changes
only `specs/094-product-activation-analytics/`.

## Post-Design Constitution Check

**Status**: PASS after Phase 0/Phase 1 artifacts.

- [research.md](./research.md) resolves provider, identity, consent, replay,
  retention, delivery-failure, and runtime-smoke decisions without adding code.
- [data-model.md](./data-model.md) defines logical entities, validation rules,
  and state transitions while preserving forbidden-field and deletion-truth
  boundaries.
- [contracts/parallel-measurement-matrix.md](./contracts/parallel-measurement-matrix.md)
  prevents unbounded event fan-out and keeps Yandex offline conversions limited
  to the approved default subset.
- [contracts/yandex-all-pages-inventory.md](./contracts/yandex-all-pages-inventory.md)
  keeps the `093` production scope intact and requires page-class approval
  before any authenticated/product Yandex expansion.
- [contracts/replay-masking-contract.md](./contracts/replay-masking-contract.md)
  implements staged replay: safe page views/events may launch without replay,
  and unapproved real-user replay is prohibited.
- [contracts/identity-attribution-contract.md](./contracts/identity-attribution-contract.md)
  rejects raw identities and uses stable server-issued pseudonymous identity.
- [contracts/telemetry-gate-contract.md](./contracts/telemetry-gate-contract.md)
  preserves visible, bounded, personal acceptance.
- [contracts/dashboard-rollout-contract.md](./contracts/dashboard-rollout-contract.md)
  requires legal, smoke, dashboard, evidence, and campaign gates before launch.

No constitution violation is introduced. Implementation remains blocked until
`$speckit-checklist`, `$speckit-tasks`, `$speckit-analyze`,
`$speckit-taskstoissues`, and separate implementation approval.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations accepted in this plan. Implementation remains
blocked until later gates pass.
