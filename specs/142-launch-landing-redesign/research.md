# Research: Launch Landing Redesign

## Decision 1: Preserve the selected visual system, replace unsupported meaning

**Decision**: Keep direction 3's dark editorial composition and numbered chapters, but use release-safe chapter meaning: familiar services, verifiable outcomes and visible control.

**Rationale**: The mock's hierarchy is strong, but current origin/master does not prove Russia-only processing, YooKassa checkout, a public billing catalog or universal auto-recording.

**Alternatives considered**:

- Ship the mock copy unchanged — rejected because it overstates current product truth.
- Remove numbered proof chapters — rejected because they are the defining, user-selected visual structure.
- Add runtime flags for future claims — rejected as speculative complexity owned by separate AI/billing slices.

## Decision 2: Real UI captures, never the generated UI panels

**Decision**: Use current GRAF runtime screenshots with synthetic content. The generated option is used only for layout comparison.

**Rationale**: The user explicitly requires screenshots to prove value. Generated product panels, obsolete `2brain Rec` captures and the current 3D hero illustration are not launch evidence.

**Alternatives considered**:

- Keep `landing-hero-product.png` — rejected because it depicts a fictional device and invented interface.
- Recreate product windows in HTML/CSS — rejected because that would be a fake visible asset.
- Use old full-window recording screenshots — rejected for obsolete branding and technical noise; only a newly captured or carefully focused real state is acceptable.

## Decision 3: No public price or checkout UI in this slice

**Decision**: Do not show a price, tariff card or payment CTA. Document the future ruble/YooKassa copy but defer its publication to the billing source of truth.

**Rationale**: Feature 140 is not current origin/master product truth. YooKassa executes a payment; the approved versioned catalog must remain the price authority.

**Alternatives considered**:

- Hardcode a launch hypothesis — rejected because the user will provide pricing later.
- Show a placeholder or blurred price — rejected because it creates false certainty and poor accessibility.
- Build a landing-only catalog endpoint — rejected because it duplicates the billing boundary.

## Decision 4: Platform-neutral landing, honest download page

**Decision**: Keep operating systems out of the hero. On `/download`, macOS is the only potentially actionable platform; Windows and Linux are labelled `Планируется` without buttons or dates.

**Rationale**: macOS is the MVP, but GRAF's product positioning is broader. The current repository has no approved Windows/Linux release slices.

**Alternatives considered**:

- Put “for Mac” in the hero — rejected because it narrows the product promise.
- Use disabled download buttons — rejected because a non-action should not look or behave like an action.
- Say “скоро” — deferred until the product owner intentionally accepts that roadmap commitment.

## Decision 5: Existing delivery stack and analytics remain authoritative

**Decision**: Reuse Jinja, local CSS/assets, existing CTA URLs, analytics attributes and cookie consent. Add no JavaScript for core content.

**Rationale**: The current public surface already supports fingerprinted local assets, consent-aware analytics and no-client-toolchain operation.

**Alternatives considered**:

- Introduce a component framework — rejected as unnecessary for two static public templates.
- Add scroll animation JavaScript — rejected because spacing and typography carry the design; reduced-motion and no-JS behavior are stronger.

## Decision 6: Preserve the useful service rail, narrow its meaning

**Decision**: Keep one text-only service rail inside chapter 01. Populate it with a curated subset of current native registry targets and describe browser meetings separately as manual-start.

**Rationale**: The existing rail answers the high-intent question “will this fit how we meet?” faster than prose. Keeping it inside the first proof chapter preserves direction 3's whitespace and avoids a separate dense platform card.

**Alternatives considered**:

- Remove the rail — rejected because it discards one of the strongest comprehension devices in the current landing.
- Preserve two animated rows and all historical labels — rejected because it creates a noisy, misleading compatibility matrix.
- Use service logos — rejected because they imply partnership/integration and add external brand assets.
- Use only generic labels — rejected because verified current target names provide stronger, evidence-backed reassurance.

## Decision 7: Keep current conversion and trust infrastructure

**Decision**: Preserve repeated download CTAs, the separate login path, stable section analytics, skip link, consent-aware local analytics assets, legal footer and reduced-motion behavior.

**Rationale**: These are successful parts of the current implementation and do not conflict with the selected visual direction. The redesign changes hierarchy and evidence, not the proven public funnel mechanics.

## Decision 8: Public installer claim stays release-gated

**Decision**: Keep the existing runtime-mounted macOS package URL and current public Developer ID/notarization wording. Release validation remains responsible for ensuring the mounted artifact matches that claim before deployment.

**Rationale**: Current product status records the public release as Developer ID signed and notarized, while the package itself is mounted outside git. The landing must not regress to the obsolete local-signing bypass copy.

**Alternatives considered**:

- Preserve “Открыть всё равно” — rejected because it conflicts with the public distribution policy.
- Add new release configuration to the landing — rejected as duplicate release authority; the existing deploy gate owns the artifact.

## Decision 9: Use the owner-approved undated roadmap status

**Decision**: Show Windows and Linux as static `Скоро` rows on `/download`, with no link, date or disabled button.

**Rationale**: The product owner explicitly asked for these future platforms to be visible without making macOS the product position.

**Alternatives considered**:

- Hide future platforms — rejected because it makes the MVP look permanently macOS-only.
- Add waitlist controls — rejected because no approved capture or CRM path exists in this slice.
- Publish dates — rejected because there is no release slice or evidence for them.

## Decision 10: Add atmospheric depth with one raster and native CSS motion

**Decision**: Use one optimized local atmospheric raster behind the editorial
canvas, recompose existing real GRAF proof images with layered perspective and
add restrained opacity/transform motion. Keep all core content and navigation
functional without JavaScript and disable decorative movement for reduced
motion.

**Rationale**: Product-owner review found the technically correct composition
flat and inexpensive. A single reusable raster supplies optical texture that
CSS should not imitate, while native CSS motion keeps the public surface light,
interruptible and dependency-free.

**Alternatives considered**:

- Add an animation framework — rejected because two server-rendered templates
  do not justify a client runtime.
- Build decorative light shapes in HTML/CSS — rejected because the atmosphere
  is a visual asset, not product UI.
- Animate every section continuously — rejected because motion must guide
  attention rather than compete with reading.

## Decision 11: One real product state per promise

**Decision**: Use a current transcript state in the hero, the current native
recording control in chapter 01 and a separate accepted-outcome state in chapter
02. Keep the full recording strip for context, add real-image close-up crops on
small screens, and use a mobile outcome scroll-state that visibly includes
`Кратко`, `Действия`, `Решения` and source timestamps.

**Rationale**: Current Granola, Notion AI Meeting Notes and Linear product pages
use large, legible interface evidence tied to one adjacent benefit. Repeating one
technical crop weakens the product story; distinct current states create the
sequence `записал → получил расшифровку → понял следующий шаг` without inventing
marketing UI. All captured content is synthetic and role-based.

**Alternatives considered**:

- Reuse the accepted-outcome image in hero and chapter 02 — rejected because it
  makes the journey feel templated and repeats the same proof.
- Build a decorative fake dashboard — rejected because public product evidence
  must come from the current GRAF runtime.
- Keep the full recording strip only on mobile — rejected because native labels
  become too small; intentional real-image close-ups preserve both context and
  legibility.

## Decision 12: Link transcript, outcomes, auto-record and calendar truth

**Decision**: Make the hero a no-JavaScript radio switch between a current
transcript and current outcomes screen for the same synthetic launch-pilot
conversation. Replace the generic active-recording strip with a focused render
of the current `MeetingDetectionSettingsView`, showing target-scoped auto-record
selection. Place calendar context after the three-step recording flow and before
the service rail.

**Rationale**: A matched conversation proves that GRAF turns speech into usable
decisions instead of displaying unrelated screenshots. Current Feature 124 truth
supports automatic recording for user-selected native targets; current calendar
truth supports upcoming-meeting context and title matching, but does not make the
calendar an auto-start trigger. The chosen IA keeps the primary promise clear:
select an app once, let GRAF detect the meeting, then retain manual control.

**Alternatives considered**:

- Keep the green/blue active-recording strip — rejected because it proves only
  controls, conflicts with the landing palette and does not explain detection.
- Claim that a calendar event starts recording — rejected because the current
  calendar feature supplies context and matching, not the capture trigger.
- Build a bespoke marketing dashboard — rejected because visible product proof
  must remain current GRAF runtime with synthetic, privacy-cleared data.
- Add a slider library — rejected because two native radio controls and CSS
  provide the complete accessible interaction without a client dependency.

## Decision 13: Prove depth with one meeting and breadth with the registry

**Decision**: Show one coherent 18-minute synthetic meeting with three role-based
participants across the transcript and outcome states. Replace the generic
three-step strip and four benefit columns with the current native auto-record
settings, the exact current count of `prompt_enabled` macOS targets, two
restrained rows containing the full current registry and three meeting-specific
outcome rows with source timestamps.

**Rationale**: The user's long current settings list proves breadth but is not a
useful landing-page composition. The current registry contains 79 macOS targets
eligible for prompt-enabled auto-recording, while the native settings screen
shows how the user controls them. Two complete rows lead with familiar
Russian-market services and keep the remainder alphabetic, without claiming an
unsupported popularity ranking. The outcome rows
now repeat facts visible in the screenshot, so the product proof and adjacent
copy form one story instead of two unrelated abstractions.

**Alternatives considered**:

- Publish the full 79-item settings screenshot — rejected because it is too tall
  to scan and turns a product benefit into a configuration catalogue.
- Sort the rail by an asserted Russian popularity ranking — rejected because no
  stable product-owned ranking exists and an external ranking would add a claim
  that must be continuously maintained.
- Keep the three-step strip — rejected because the native settings screenshot
  already explains setup and the safety line preserves manual control.
- Keep generic `Кратко / Действия / Решения / Источник` columns — rejected because
  they describe output types but do not demonstrate the value of this meeting.

## Decision 14: Publish one product-wide privacy notice

**Decision**: Replace the site-only draft with one notice covering the public
site, account, desktop application, meeting content, integrations, support and
future billing. Identify the operator and describe categories, purposes, legal
bases, operations, recipients, retention boundaries, rights and contact route.

**Rationale**: Article 18.1 of Federal Law No. 152-FZ requires the operator's
policy to be publicly available on the resources used to collect personal data.
The current page expressly excludes the main product and therefore does not
inform meeting participants or account holders about the actual processing.

**Alternatives considered**:

- Keep separate unspecified product terms — rejected because no linked public
  product privacy notice exists.
- Publish an exhaustive vendor register without verified facts — rejected;
  named processors are limited to confirmed current boundaries and provider
  categories are used where the configured route can change.

## Decision 15: Disclose the current content-bearing EU trace boundary

**Decision**: State that current AI observability can send the complete compiled
request, transcript, model response and validated result to private Langfuse
Cloud EU infrastructure in Ireland. State that per-meeting deletion in GRAF does
not automatically erase retained Langfuse traces, Temporal history, provider
logs or backups outside the same deletion boundary.

**Rationale**: The constitution, product gates and baseline PRD record this as
current architecture. Langfuse documents `cloud.langfuse.com` as AWS
`eu-west-1` in Ireland. A Russia-only or zero-egress statement would be false.

**Alternatives considered**:

- Preserve “Российские и локальные модели” as a privacy guarantee — rejected
  because model origin does not prove data residency.
- Hide processor details behind “managed contour” — rejected because it prevents
  informed consent and creates a misleading absolute claim.

## Decision 16: Make analytics consent enforceable, not descriptive

**Decision**: Initialize Yandex Metrica with `defer: true`, send the configured
allowlisted page path without query/hash/title, include campaign attribution
only when its separate category is granted, enable replay only with its category
at first initialization, and set `disableYaCounter<ID>` when analytics is
revoked.

**Rationale**: Yandex documents that `defer` disables the automatic initial hit,
that `hit` accepts an explicit URL and that `disableYaCounter<ID> = true` blocks
cookies and collection. The previous controller allowed an automatic full-URL
hit, sent UTM values with analytics-only consent and did not stop an initialized
counter after revocation.

**Alternatives considered**:

- Rely only on safe custom goal payloads — rejected because the provider's
  automatic pageview still observes the full browser URL.
- Attempt to switch Webvisor in place — rejected because the provider does not
  expose a reliable category toggle after initialization; a changed replay
  choice disables the counter and takes effect on a reload.

## Decision 17: Keep payment terms conditional until checkout is real

**Decision**: Keep `/offer` as discoverable payment and refund information, but
do not present it as an active priced public offer. Paid terms take effect only
when a checkout names the plan, price, period, recurring-payment choice and
acceptance action.

**Rationale**: Civil Code Articles 437 and 438 require sufficiently definite
offer terms and acceptance. The current product has no approved public catalog
or active checkout, so publishing invented price or acceptance mechanics would
mislead users.

## Sources reviewed

- Federal Law No. 152-FZ, including Articles 6, 9, 12, 18.1 and 19.
- Law of the Russian Federation No. 2300-1, including Articles 8–10 and 16.
- Civil Code of the Russian Federation, Articles 437, 438, 1235 and 1286.
- Yandex Metrica documentation for initialization, manual hits and visitor opt-out.
- Langfuse privacy, security FAQ and EU data-region documentation.
