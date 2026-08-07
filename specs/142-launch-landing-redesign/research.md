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
