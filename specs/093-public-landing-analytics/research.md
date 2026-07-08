# Research: Public Landing Analytics

**Feature**: 093-public-landing-analytics

## Decision: Use Yandex Metrica only for Phase 1

**Rationale**: The user wants ready-made analytics while keeping the first
legal/compliance surface simple for Russia-first traffic. Yandex Metrica covers
the Russian advertising and landing-behavior side: a counter snippet, goals,
UTM reports, Yandex Direct reports, scroll maps, and Session Replay. GA4,
Google Analytics, Google Ads tags, and Google Tag Manager are deferred until a
separate legal-approved slice because they add cross-border and consent-review
work that is not needed for the first Yandex-focused launch.

Official sources:

- Yandex Metrica starts from a counter snippet:
  https://yandex.com/support/metrica/en/general/how-it-works
- Yandex JavaScript goals use `reachGoal` for custom actions:
  https://yandex.com/support/metrica/en/objects/reachgoal
- Yandex Metrica UTM reports group campaign traffic:
  https://yandex.com/support/metrica/en/reports/tags-utm
- Yandex Direct reports require linking the Metrica tag to Direct campaigns:
  https://yandex.com/support/metrica/en/general/direct
- Yandex Metrica cookie/storage behavior must be disclosed in consent and
  cookie-policy copy:
  https://yandex.com/support/metrica/en/general/cookie-usage

**Alternatives considered**:

- Yandex Metrica plus GA4 in Phase 1: rejected after clarification because
  Google adds cross-border/legal-review scope before the Yandex-first funnel is
  validated.
- GA4 only: rejected because it misses Yandex Direct-native reports and
  Metrica's landing behavior tooling.
- Build a custom analytics pipeline: rejected by user direction and privacy
  risk; Phase 1 should use proven tools.

## Decision: Use direct Yandex snippet loading, not GTM, for Phase 1

**Rationale**: The first release has exactly one approved provider and a
strict consent/replay scope. Direct snippets loaded by a small local controller
are easier to reason about, test, and constrain than a general tag manager
container that can later load unreviewed tags outside the repository.

Google Tag Manager may be reconsidered only in a later legal-approved
marketing-stack slice. It is not required for the first release.

**Alternatives considered**:

- Google Tag Manager from day one: rejected because it adds Google scope and a
  broad external tag-control surface before the team has a tag governance
  process.
- Server-side tag manager: rejected because it is a larger infrastructure and
  data-boundary project, not needed for two public pages.

## Decision: Use strict consent gating and load no provider tags before consent

**Rationale**: Phase 1 should be privacy-first and easy to explain. Yandex
Metrica, Webvisor/behavior tools, and advertising attribution load only after
the visitor accepts analytics/behavior cookies. This sacrifices some
pre-consent visit measurement, but it avoids ambiguous pre-consent egress and
keeps the consent copy straightforward.

**Alternatives considered**:

- Provider-supported pre-consent or consent-denied pings: rejected for Phase 1
  because they are harder to explain and validate under the Russia-first legal
  posture.
- Load Yandex Metrica before consent but disable replay: rejected because it
  still expands third-party egress before a clear user choice.
- No consent UI: rejected because analytics cookies, advertising identifiers,
  and session observation are not strictly necessary for using the public
  landing.

## Decision: Use one free self-hosted consent control and separate legal pages

**Rationale**: The landing should not interrupt visitors with repeated legal
prompts. Phase 1 uses self-hosted CookieConsent v3.1.0 for one non-blocking
Russian consent control with `accept all`, `necessary only`, and `customize`
choices. The choice is remembered per consent-copy version, and public
footer/settings links let the visitor change it later. Public cookie/analytics
consent is separate from product Terms acceptance, which belongs to
registration, installer, desktop app, or first product use.

CookieConsent v3 is a free open-source vanilla JavaScript consent manager
released under the MIT License. Its public documentation says it blocks scripts
until explicit consent is given and provides opt-out options:
https://cookieconsent.orestbida.com/

Version and runtime decision:

- Pin local static assets to CookieConsent v3.1.0.
- Keep MIT attribution with the vendored assets.
- Do not load CookieConsent from a CDN or third-party runtime host.
- Any CookieConsent version change requires an implementation note and focused
  consent/no-CDN regression validation.

Required public legal surfaces before paid campaign launch:

- privacy policy
- cookie policy
- terms
- analytics-consent text
- cookie settings entry

Russia-first legal readiness references:

- The personal-data portal says operators must notify Roskomnadzor about the
  start or performance of personal-data processing except for statutory
  exceptions:
  https://pd.rkn.gov.ru/operators-registry/notification/
- The personal-data portal says operators must notify Roskomnadzor before
  cross-border transfer of personal data:
  https://pd.rkn.gov.ru/cross-border-transmission/form2/
- The official legal-information portal publishes Federal Law No. 152-FZ:
  https://pravo.gov.ru/proxy/ips/?docbody=&nd=102108261

**Alternatives considered**:

- Multiple separate banners for cookies, analytics, replay, and terms:
  rejected because it would create consent fatigue and reduce trust.
- Treat cookie consent as Terms acceptance: rejected because public analytics
  consent and product contractual acceptance have different scope and timing.
- Use a paid hosted CMP: rejected because the user requested a free solution
  and Phase 1 can stay self-hosted.

## Decision: Enable behavior recording only through Yandex Metrica and only on public pages

**Rationale**: Yandex Metrica Session Replay, scroll map, and form analysis are
first-party capabilities inside the selected Metrica provider, so adding
Microsoft Clarity would duplicate replay/heatmap behavior and introduce a
second observation provider. Yandex documents Session Replay setup and replay
requirements separately:

- https://yandex.com/support/metrica/en/general/counter-webvisor
- https://yandex.com/support/metrica/en/webvisor/settings
- https://yandex.com/support/metrica/en/webvisor/requirements
- https://yandex.com/support/metrica/en/behavior/scroll-map

The code must load the tag only on `/` and `/download`; replay must not appear
on login, cabinet, meeting, upload, playback, deletion, admin, or desktop
embedded surfaces.

**Alternatives considered**:

- Add Clarity: rejected for Phase 1 because Metrica already covers landing
  replay/scroll behavior and Clarity would increase consent and egress surface.
- Record authenticated product sessions: rejected because that would touch
  meeting/account content and requires a separate privacy spec.

## Decision: Treat installer download as the primary web conversion

**Rationale**: Current public product flow is install-first:
`landing -> download -> installer -> login/cabinet -> first use`. The
business can optimize public landing and paid traffic against installer
download intent immediately. It must not claim product activation until the
desktop/app path is instrumented in a later slice.

**Alternatives considered**:

- Optimize to landing CTA click: rejected because CTA click is a weaker signal
  than installer download intent.
- Optimize to login intent: rejected because login can happen without install
  and is a separate secondary path.
- Claim first meeting result attribution now: rejected because Phase 1 does
  not instrument authenticated product or desktop activation.

## Decision: Define PostHog as Phase 2 product activation analytics

**Rationale**: PostHog is better suited than public web analytics tools for product funnels,
cohorts, user paths, and activation journeys after the public click. Its docs
cover UTM segmentation, funnels, web analytics, product analytics, session
replay privacy controls, and self-hosting:

- https://posthog.com/docs/data/utm-segmentation
- https://posthog.com/docs/product-analytics/funnels
- https://posthog.com/docs/web-analytics/getting-started
- https://posthog.com/docs/product-analytics/start-here
- https://posthog.com/docs/session-replay/privacy
- https://posthog.com/docs/self-host

However, adding PostHog now would require identity linkage, desktop/app event
semantics, consent/notice across product surfaces, and deletion/retention
decisions. Those are out of Phase 1.

**Alternatives considered**:

- Add PostHog together with Metrica: rejected because it turns a public
  landing slice into a product-wide analytics and identity project.
- Use GA4 for product activation: rejected for Phase 1 because Google is out
  of scope and GRAF's product surfaces include desktop/native behavior and
  privacy-sensitive meeting workflows where a dedicated product analytics
  contract is needed first.

## Decision: Store consent locally and do not create a server consent table

**Rationale**: Phase 1 measures public anonymous pages only. A browser-local
consent preference keyed by consent-copy version is enough to drive public
provider loading. Persisting it server-side would create a new visitor data
store and increase scope without enabling authenticated product analytics.

**Alternatives considered**:

- Server-stored public consent: rejected because it creates a new data store
  and identity problem for anonymous public visits.
- No persistence: rejected because visitors need a stable choice across public
  page views and a way to change it.

## Decision: Use a strict event allowlist and UTM canon

**Rationale**: All public events must be metadata-only. Event and UTM fields
need fixed names and bounded values so provider dashboards can be interpreted
and tests can catch unsafe leakage. Yandex depends on correctly configured UTM
tags for traffic/campaign reporting, and Yandex's ad-expense docs call out
standardized UTM values as a prerequisite for cost reports:
https://yandex.com/support/metrica/en/sources/ad-expenses.

**Alternatives considered**:

- Send visible section text or CTA copy: rejected because labels change and may
  include marketing or example text that should not become analytics payload.
- Let ad platforms define arbitrary UTM values: rejected because mixed naming
  creates fragmented reports.

## Decision: Validate locally without contacting live providers

**Rationale**: Most correctness can be proven through rendered HTML, static JS,
event catalog tests, route-scope tests, and forbidden-content scans. Live
provider dashboards require real IDs and external accounts, so they belong to a
separate production/campaign readiness smoke with metadata-only evidence.

**Alternatives considered**:

- Use real provider IDs in automated tests: rejected because it risks live
  egress, unstable tests, and committed account identifiers.
- Skip provider dashboard validation entirely: rejected because campaign launch
  requires proof that dashboards and conversion imports are configured.
