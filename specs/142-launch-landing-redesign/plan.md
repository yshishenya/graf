# Implementation Plan: Launch Landing Redesign

**Branch**: `codex/146-public-legal-hardening` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/142-launch-landing-redesign/spec.md`

## Summary

Пересобрать существующие server-rendered `/` и `/download` в выбранном тёмном редакционном направлении 3, сохранив текущий публичный runtime, consent-аналитику и CTA-маршруты. Использовать крупный ритм `hero → 01 → 02 → 03 → final CTA`, реальный GRAF UI с синтетическими данными и truth-safe copy. Неподтверждённые AI/egress, billing, YooKassa и universal-capture claims остаются release-gated и не публикуются как текущая возможность.

## Technical Context

**Language/Version**: Python 3.13 runtime, Jinja/server-rendered HTML, modern CSS

**Primary Dependencies**: existing FastAPI public router, Jinja templates, local packaged static assets, existing consent-aware public analytics

**Storage**: existing browser consent state only; no database schema, catalog data, payment state or migrations

**Testing**: focused pytest public landing/analytics contracts, HTML/CSS static checks, local browser desktop/mobile/accessibility interaction matrix, Product Design visual comparison

**Risk / Validation Lane**: `high-risk-feature`; public launch positioning touches brand-distance UX, privacy/AI claims, capture wording, download truth and payment expectations

**Release Gate**: public rollout remains blocked until the published policy matches the active processors and cross-border notification posture; paid checkout remains disabled until a catalog, fiscal flow and effective payment terms exist.

**Target Platform**: responsive public web at 320–1440+ CSS px; current downloadable client remains macOS-first

**Project Type**: monorepo web service with a native macOS product and server-rendered public site

**Performance Goals**: critical landing content and first product proof render without client JavaScript; static images have explicit dimensions and responsive sources; no new font, framework or runtime dependency

**Constraints**: no fake product assets, no personal data, no hardcoded price, no specific model names, no false universal capture/egress claim, no public local/self-signed installer claim, WCAG-oriented keyboard/focus/contrast/reduced-motion behavior

**Scale/Scope**: landing, download, five legal templates and the legal notice in login/signup; consent-copy version defaults in settings/Compose/env example; one shared stylesheet and analytics controller; public response helpers/routes and focused contracts; no auth/session behavior, billing, checkout, capture behavior, app UI or database change

## Constitution Check

*GATE: PASS before Phase 0 and after Phase 1 design.*

- PASS — capture implementation, automatic recording policy, permissions and one-action Stop behavior are not changed; copy explicitly distinguishes manual system-audio recording from approved-target auto-recording.
- PASS — public copy does not claim arbitrary audio auto-start or hide active capture; the visible recording proof retains Pause and Stop.
- PASS — current plaintext Langfuse/Temporal and LiteLLM architecture is not misrepresented as fully local or Russia-only; stronger wording remains blocked by a separate egress gate.
- PASS — no real meeting content, secrets, raw audio or private screenshots are committed; product proofs use synthetic demo data.
- PASS — public download is not represented as Developer ID/notarized while origin/master still points to a local installer; production rollout stays blocked.
- PASS — clean-room GRAF design evolves the selected original mock and current GRAF tokens without copying competitor assets or identity.
- PASS — Ponytail: reuse the current templates, CSS delivery, analytics attributes, routes and real product evidence; no SPA, component framework, carousel, CMS, price service or new dependency.

Post-Phase-1 re-check: PASS. The UI contract below narrows claims and does not expand capture, privacy, payment, release or data boundaries.

## Design and Implementation

1. Replace the current teal/grid/3D landing presentation with the selected near-black, violet-accent editorial rhythm while preserving semantic HTML, skip link, anchors and existing analytics attributes.
2. Use the official GRAF wordmark image and actual product UI captures. The current generated direction remains a design target only; it is never shipped as product evidence.
3. Keep the hero platform-neutral. The proof chapters use current public truth: familiar services/manual system-audio recording, verifiable meeting outcomes, and visible user control.
4. Keep the model-origin claim separate from data-residency claims and link to the factual processor disclosure. Reserve ruble/YooKassa conversion copy until the billing gate passes; do not add feature flags or parallel pricing logic in this slice.
5. Redesign `/download` as a platform availability surface: macOS is the only actionable platform; Windows and Linux are non-interactive planned statuses. The existing runtime-mounted package URL remains, while release/deploy validation—not a git file-presence check—proves public readiness.
6. Replace internal legal drafts with plain-Russian public editions that identify the operator, processing purposes and bases, recipients, retention limits, user rights and the actual Langfuse Cloud EU content boundary.
7. Make Yandex Metrica truly category-scoped: defer the automatic pageview, send an allowlisted path, omit attribution without its category and disable the counter after revocation.
8. Harden public HTML responses, add canonical/social discovery surfaces and cache only fingerprinted public assets as immutable.
9. Extend focused contracts for legal completeness, consent categories, CTA routes, platform truth, product assets, security headers and 280–1440 px responsive safety.
10. Validate visually at desktop and mobile against `design/selected-direction-3.png`, then fix P0–P2 differences that do not conflict with product truth.
11. Link the login/signup legal notice to the published product terms and privacy notice, and make the analytics opt-out instructions truthful when optional public analytics is disabled.
12. Bump the consent-copy version with the changed legal edition so a future analytics rollout cannot reuse a browser choice made for the previous text.

## Validation Plan

1. Run the focused public landing and analytics contracts named in `quickstart.md`.
2. Run template/source checks for forbidden claims, personal data, fake prices, disabled platform links, external CDNs and missing focus/reduced-motion rules.
3. Start the existing server locally and inspect `/`, `/download` and every legal route at 1440×1000, 1024×768, 768×1024, 390×844, 320×800 and 280×800.
4. Test header anchors, CTA destinations, keyboard order, visible focus, skip link, image fallback meaning, consent accept/custom/reject/revoke and reduced-motion mode.
5. Compare the 1440 landing capture with the selected direction in one visual QA input. Record findings in `design-qa.md`; fix P0/P1/P2 until `final result: passed`.
6. Run `infra/scripts/ci-local.sh --fast` before implementation closeout because public UX/QA expectations and shared server assets change. Full CI and deploy smoke remain release-gate work.

## Project Structure

### Documentation (this feature)

```text
specs/142-launch-landing-redesign/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── design-qa.md
├── design/selected-direction-3.png
├── contracts/public-launch-experience.md
├── checklists/
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/public/
├── templates/public/
│   ├── landing.html
│   ├── download.html
│   ├── privacy.html
│   ├── cookies.html
│   ├── terms.html
│   ├── offer.html
│   └── analytics_consent.html
└── static/public/
    ├── landing.css
    ├── analytics.js
    └── landing-*.png

apps/server/src/twobrain_rec_server/cabinet/static/cabinet/
└── graf-wordmark-light@2x.png

apps/server/tests/
├── unit/test_public_landing.py
└── contract/
    ├── test_public_landing_contract.py
    └── test_public_analytics_contract.py

apps/server/src/twobrain_rec_server/public/templates.py
apps/server/src/twobrain_rec_server/public/web.py
apps/server/src/twobrain_rec_server/main.py
CHANGELOG.md
```

**Structure Decision**: modify the existing server-rendered public surface only. Product screenshots are copied as local immutable static evidence; no new web application or build system is introduced.

## Complexity Tracking

No constitution violations. Skipped SPA/framework, custom icon set, animation library, pricing subsystem, billing API, CMS, new route family and duplicated analytics code.
