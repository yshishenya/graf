# Implementation Plan: Production Landing Refresh

**Branch**: `codex/179-production-landing-refresh` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/179-production-landing-refresh/spec.md`

## Summary

Replace the server-rendered public landing with the owner-approved local design, adapt the existing `/download` route to the same visual system, keep all legal and authentication routes inside the current FastAPI/Jinja application, and rework public Yandex Metrica goals around the new funnel. Prices are 1,000 RUB/month and 10,000 RUB/year: the tariff is published from an effective database catalog, while any promise of immediate payment remains tied to the existing checkout launch gates. Production checkout must stay disabled until the separate billing canary and four-eyes approvals pass.

## Technical Context

**Language/Version**: Python 3.13+, HTML5, CSS, ES5-compatible browser JavaScript

**Primary Dependencies**: FastAPI, Jinja2, SQLAlchemy async, bundled Onest fonts, local static assets, Yandex Metrica tag

**Storage**: Existing PostgreSQL `billing_plan_versions` and `billing_launch_gates`; no new user-content storage or schema is required for the landing

**Testing**: pytest unit/contract/integration suites, Ruff, JavaScript syntax checks, local CI, Browser desktop/mobile visual and interaction checks, CD dry-run and production smoke

**Risk / Validation Lane**: `release-deploy` and `high-risk-feature` because this changes public brand-distance UX, paid claims, legal copy, external analytics and production deployment

**Release Gate**: `cd dry-run` after implementation validation; `cd execute` only after explicit release authorization. Before a release is considered complete, the exact reviewed SHA also needs a unique application CalVer tag (`vYYYY.MM.DD.N`), a matching GitHub Release and Russian plain-language notes in `docs/releases/`. Billing enablement additionally requires the existing independent finance/legal/security/infrastructure/release gates and provider canary; legal approval for immediate Metrica is a separate gate.

**Target Platform**: Linux/Docker server at `2brain.dev`; public web for modern desktop/mobile browsers; download target macOS 14.5+ universal installer

**Project Type**: Server-rendered web application integrated with a desktop-product distribution route

**Performance Goals**: Meaningful hero content in the initial HTML; no client framework; lazy-load below-fold screenshots; no horizontal overflow at 280-1440 px; no duplicate Yandex initialization or goal delivery

**Constraints**: Preserve the approved composition 1:1 except truth, legal, accessibility and responsive corrections; no user or meeting content in analytics; only `/` and `/download` may load public Metrica; Webvisor, click maps, form analytics and advanced matching remain disabled

**Scale/Scope**: Two public product pages, five legal/discovery routes, one shared CSS bundle, one shared analytics controller, three product screenshots, one universal installer handoff and nine named funnel events

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- Capture-first integrity: pass; desktop capture behavior and packaging are unchanged.
- Visible recording consent/control: pass; public copy must not weaken recording-user responsibility or imply hidden capture.
- Data/secret discipline: pass; counter ID remains runtime configuration, no OAuth token or secret enters Git, and analytics excludes account/meeting surfaces.
- Deletion truth: pass; no new meeting artifacts or deletion promise.
- Public macOS distribution integrity: pass; `/download` keeps the single existing notarized universal `graf.pkg` runtime mount and does not create a new package.
- Spec-driven delivery: pass; specify/clarify/plan/checklist/tasks/analyze precede implementation.
- Brand-distance/accessibility: pass subject to Browser proof at the required viewports and keyboard tab validation.
- Deployment gate: pass subject to backup, exact SHA, dry-run, explicit execute approval, health/smoke and rollback evidence.
- Billing launch: no constitution violation; checkout remains fail-closed until the existing catalog, canary and four-eyes gates are genuinely satisfied.

## Validation Plan

1. Focused static and server tests prove copy, CTA routes, universal installer, pricing truth, legal links, sitemap/robots and safe analytics catalogs.
2. Browser tests at 1440x1000, 1024x768, 768x1024, 390x844, 320x800 and 280x653 verify visual fidelity, tabs, pricing switch, FAQ, links, focus, reduced motion and no overflow.
3. Network inspection proves Yandex loads immediately only on `/` and `/download`, uses explicit safe paths, and never loads on login, cabinet, legal, admin or meeting pages.
4. Goal interception proves each user action maps once to the documented goal and no query/hash, field values, email, account data or meeting content is sent.
5. Billing tests prove 100,000/1,000,000 minor-unit prices, annual saving of 2,000 RUB, seven-day trial, catalog/offer version match and fail-closed checkout when gates/catalog are absent.
6. Full repository CI and CD dry-run run on the exact candidate SHA. Production execute requires explicit approval, backup and the release runbook.

## Project Structure

### Documentation (this feature)

```text
specs/179-production-landing-refresh/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
├── checklists/
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── public/
│   ├── analytics.py
│   ├── templates.py
│   ├── web.py
│   ├── templates/public/
│   └── static/public/
└── billing/catalog.py

apps/server/tests/
├── unit/
├── contract/
└── integration/
```

**Structure Decision**: Reuse the existing FastAPI/Jinja public module and runtime-mounted installer. No standalone static landing, separate deployment or client framework is introduced.

## Complexity Tracking

No constitution violations require justification. The only additional complexity is a server-owned public offer view derived from the same approved billing catalog used by checkout; this prevents the landing from drifting from payable prices.
