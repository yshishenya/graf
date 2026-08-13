# Design QA: Launch Landing Redesign

## Final legal, consent and responsive hardening — 2026-08-12

- Replaced the five public draft notices with dated plain-Russian editions
  covering the site and product, the current processors and the actual
  Langfuse Cloud EU content boundary. Payment text remains explicitly
  non-operative until checkout publishes the price and essential terms.
- Added query-safe consent-gated Yandex loading, independent attribution and
  replay categories, provider disable-on-revoke, canonical/social metadata,
  discovery routes, public HTML security headers and fingerprint-aware cache
  policy.
- Browser QA passed for the landing at 1440, 390, 320 and 280 CSS px and for
  download/legal routes at 280 CSS px. The only discovered overflow was a long
  localStorage identifier on `/cookies`; the shared legal code style now wraps
  it and the repeated result is `scrollWidth = clientWidth = 280`.
- Live consent QA passed: necessary-only disables Yandex; analytics-only does
  not enable attribution or replay; revocation records `revoked` and sets the
  Yandex disable flag. Server-rendered content remains available without the
  analytics runtime, and reduced-motion behavior remains covered by the
  existing CSS and contract checks.
- Focused public contracts: `39 passed, 2 warnings`. Full server suite before
  the final CSS-only overflow fix: `1207 passed, 2 warnings`. Web: 114 tests,
  lint and production build passed. The published package reports Apple arm64,
  macOS 14.5 minimum and a valid Apple Developer ID Installer chain.

visual result: passed

release result: blocked — production release still requires confirmed Russian
primary-storage location, Roskomnadzor processing/cross-border formalities and
processor/DPA/retention evidence. Billing publication additionally requires
the final catalog, YooKassa/receipt configuration and effective checkout terms.

## Marketing-proof crop refresh — 2026-08-08

The desktop hero pair was re-composed from the current GRAF runtime screens.
The product UI, synthetic meeting content, speaker lanes, timestamps and
player remain intact; only the crop and density were refined to remove unused
lower space and keep the transcript/outcome pair visually balanced.

| Asset | Pixels | SHA-256 | Provenance |
|---|---:|---|---|
| `landing-transcript-proof.png` | 1487 × 1058 | `cb089e669c3e6d943f732a9117861956183da583cf314cd09d56b4f90f0065d9` | Edited from the current real GRAF transcript runtime with synthetic product, sales and support dialogue. |
| `landing-outcome-proof.png` | 1487 × 1058 | `1d90003066d83a452408f3903fde0f290ba2ab370f35ce3307c4641b3fce9576` | Edited from the matching accepted-outcome runtime for the same synthetic meeting. |

- The mobile source pair remains the privacy-cleared runtime capture so small
  screens retain exact product truth and readable native controls.
- No personal data, real names or external meeting content were introduced.

## Product-proof depth and application breadth — 2026-08-07

The final proof sequence uses one 18-minute synthetic pilot meeting with three
role-based participants. Its transcript, summary, actions, decisions and source
timestamps agree. Chapter 01 now combines the current native auto-record settings
with the current registry breadth instead of a generic stepper.

| Asset | Pixels | SHA-256 | Provenance |
|---|---:|---|---|
| `landing-transcript-proof.png` | 1440 × 1300 | `7b17676e432d31ff59dd2cfd74a4b563ccbc3261529d0dea3433f1b3e1d757ac` | Current Feature 139 meeting runtime; synthetic product, sales and support dialogue. |
| `landing-transcript-proof-mobile.png` | 390 × 1100 | `ed9bd8e673907f0b015e3fd37b7cf52ad0c82c7083e03795ee935b30d6f7ef6d` | Current responsive transcript state for the same meeting. |
| `landing-outcome-proof.png` | 1440 × 1300 | `99ed7d32ce823864f382ce7ccd98dd3aaa82f57bb12e97aca1829732464abbcd` | Current accepted-outcome runtime; ImageGen text-localization changed only `Template` to the valid built-in format label `Авто`. |
| `landing-outcome-proof-mobile.png` | 390 × 1100 | `10deedc39d41a2437484323898517c4c247b5c80b7b566714ea9ce8e935da045` | Current mobile outcome state with the same single text-localization correction. |
| `landing-autorecord-proof-focus.png` | 3040 × 2000 | `b97fb4d65e3917bbb28d22788dea0ddeaa4b91ff73962d3ee23c50d45c65fdf9` | Current `MeetingDetectionSettingsView` rendered in dark appearance from the native macOS target registry. |
| `landing-autorecord-proof-control-mobile.png` | 1120 × 300 | `fcb47dc3e8c2571e813a9c63ea5b4e9b09092263915f1ff7504993af0b70903f` | Deterministic crop of the current native auto-record control. |
| `landing-autorecord-proof-toggle-mobile.png` | 480 × 240 | `7c0255001f2200143be9789d833848b57f1158c6d934fa8ed85b9a64b4edff71` | Deterministic crop of the enabled native toggle. |

- Evidence: `evidence/screenshot-refinement-v8/`.
- IA: removed the redundant three-step strip; setup, manual-control safety,
  calendar context and application breadth now read as one causal sequence.
- Registry truth: the public `79` count is checked against current macOS
  `prompt_enabled` entries in `0030_meeting_target_registry.json`.
- Both visual rows and the accessible list contain all 79 current registry
  values. Familiar Russian-market services lead the presentation; the remaining
  names retain stable case-insensitive alphabetical order without a popularity
  ranking claim.
- Responsive browser review passed at 1440 CSS px and the available 625 CSS px
  mobile breakpoint; document width matched viewport width in both cases.
- Mobile exposes both manually scrollable application rows; desktop animates the
  same complete rows and provides a visible pause control.
- Screenshots remain real product UI with synthetic, role-based content and no
  personal data.
- Focused public landing and asset contracts: `19 passed, 2 warnings`.
- Independent conversion/IA and visual/code review: `PASS`, no P0–P2 findings.

visual result: passed

final result: passed

## Linked transcript/outcomes and auto-record closeout — 2026-08-07

The hero now proves one complete conversation: a role-based transcript switches
to matching outcomes without JavaScript, and the action/decision sources resolve
to the exact `00:27` and `00:57` turns. Chapter 01 now uses the current native
auto-record settings rather than the unrelated blue/green recording strip.

| Asset | Pixels | SHA-256 | Provenance |
|---|---:|---|---|
| `landing-transcript-proof.png` | 1440 × 1000 | `7d8a501748c8ab3488308840dc8c0c7a7628b00290cddf79480566952674d518` | Current Feature 139 meeting runtime; synthetic product/sales dialogue and no personal data. |
| `landing-transcript-proof-mobile.png` | 390 × 844 | `9c23fbb7b66c9f6ef4fd00cc33b8ce41027b2a4de0b4b69f6c4b66123b0996ab` | Current responsive transcript state for the same dialogue. |
| `landing-outcome-proof.png` | 1440 × 1000 | `dc9724f62a0b8f2dde676f751885b5260357c41d63d1d9a2ade2d5ef6e42ddc6` | Current accepted-outcome runtime; summary, action at `00:27` and decision at `00:57`. |
| `landing-outcome-proof-mobile.png` | 390 × 844 | `9e42281dd991044af57ef632443d9611c5169b44b1b9a14dadd946566f793a51` | Current mobile outcome scroll-state with summary, action, decision and exact sources. |
| `landing-autorecord-proof-focus.png` | 1166 × 820 | `e186eaa64ec77f69d40d6287e60c857364f60e92d747f69d38afea64d6ea12dc` | Current `MeetingDetectionSettingsView` rendered in dark appearance with synthetic Zoom/Telemost selections and the product violet accent token. |

- Source/current/final evidence: `evidence/screenshot-refinement-v7/`.
- Combined source/implementation review: `evidence/screenshot-refinement-v7/comparison.jpg`.
- Hero proof carousel: automatic CSS slide, no JavaScript or manual controls
  disabled under reduced motion.
- IA: transcript and outcomes share one case; auto-record precedes calendar
  context; calendar copy explicitly avoids a calendar-driven start claim.
- Responsive matrix: 1440, 1024, 768, 390, 320 and 280 CSS px; document width
  matched viewport width at every breakpoint.
- Focused public landing/asset contracts: `18 passed, 2 warnings`.
- Canonical fast CI: `885 passed, 2 warnings`; server lint and Python compile
  passed.

visual result: passed

final result: passed

## Product screenshot refinement closeout — 2026-08-07

The public proof sequence now uses three distinct current GRAF states: transcript
in the hero, native recording control in chapter 01 and accepted outcomes in
chapter 02. Synthetic role-based content replaces person-like names, and the
mobile proof treatment keeps the original interface visible while adding
intentional real-image close-ups for readable status, Pause and Stop labels.

| Asset | Pixels | SHA-256 | Provenance |
|---|---:|---|---|
| `landing-transcript-proof.png` | 1440 × 1000 | `b418ee6945e62835686993a38a62d1958f6af89d287fa696a5b3878d6f581fab` | Fresh current feature 139 transcript runtime with synthetic launch-planning content. |
| `landing-transcript-proof-mobile.png` | 390 × 844 | `103699f0df0c64f771f7743a9e4b02a62ec9d1b978884d4fcbabf5ebd488e280` | Current responsive transcript state with role labels only. |
| `landing-outcome-proof.png` | 1440 × 1000 | `a3fcbcdb1aeeb0d4a0d0ca1f2a45d4c11cb4d411bf7ed6c972bd28d197b94270` | Fresh accepted-outcome runtime with summary, action, decision and sources. |
| `landing-outcome-proof-mobile.png` | 390 × 844 | `1e69fe33758d2ce5144d69ba24480b3960d688a3baa4ec12d56a370706149ecd` | Real mobile scroll-state exposing summary, action, decision and source timestamps. |

- Before/current/final evidence: `evidence/screenshot-refinement-v6/`.
- Combined source/implementation review: `evidence/screenshot-refinement-v6/comparison.jpg`.
- Final states: `21-final-desktop-hero.jpg` through `25-final-mobile-outcome.jpg`.
- Document width matched the viewport at 1440, 1024, 768, 390, 320 and 280 CSS
  px; no horizontal overflow.
- Hero copy and CTA are visible immediately; only the product proof retains a
  restrained entry animation, disabled under reduced motion.
- Reduced motion reported `animation-name: none` for the hero and platform rail,
  hid the duplicate rail and restored `scroll-behavior: auto`.
- Final browser console: no warnings or errors.
- Three independent UX, visual and art-direction reviewers reported no remaining
  P0, P1 or P2 findings for the screenshot-refinement scope.
- Focused public landing/analytics contracts: `31 passed, 2 warnings`.
- Canonical fast CI: `885 passed, 2 warnings`; lint and Python compile passed.

visual result: passed

final result: passed

## Atmospheric refinement closeout after product-owner review — 2026-08-07

The reopened visual findings are closed. One quiet local raster supplies optical
depth, native CSS supplies transform/opacity motion, and the hero now composes
the real outcome and recording states as one product scene. Headline punctuation,
manual wraps, line lengths and responsive type scales were reviewed again.

- Final evidence: `evidence/refinement-v5/`.
- Combined source/implementation review: `evidence/refinement-v5/comparison-hero.png`.
- Responsive states: 1440, 1024, 768, 390, 320 and 280 CSS px; no horizontal overflow.
- Motion: hero entry, quiet recording float, scroll reveal and VKS rail use native
  CSS only; the pause control pauses and resumes immediately.
- Reduced motion: smooth scrolling, decorative motion and the duplicate rail are
  disabled; the service list remains horizontally readable.
- Product proof: every visible UI image is current GRAF evidence with synthetic,
  privacy-cleared content; the generated atmospheric image contains no product UI.
- Browser console: no warnings or errors.
- Focused landing/analytics tests: `43 passed, 2 warnings`.
- Canonical fast CI: `885 passed, 2 warnings`; lint and Python compile passed.

visual result: passed

release result: passed — the worktree is synced to `v2026.08.07.2` release
truth and the active local package matches the published SHA-256, Developer ID,
Apple notarization, staple and Gatekeeper evidence. The download page exposes
the bounded user-facing trust copy `Подписано разработчиком и проверено Apple`.

final result: passed

The earlier refinement closeout below remains historical evidence.

## Previous refinement closeout after product-owner review — 2026-08-07

The visual refinement is complete. The type system, controlled wrapping,
spacing, product-proof crops, CTA hierarchy, VKS rail, responsive composition
and managed Russian/local model chapter were rebuilt and checked again by an
independent reviewer.

- visual result: passed
- historical release status: blocked — the repository's active `graf-local.pkg` had no
  Developer ID signature, notarization ticket or stapling evidence
- historical final status: blocked until a verified production package replaced the local
  unsigned artifact (or the public download CTA is disabled)

Final evidence: `evidence/refinement-v4/`. Earlier findings and screenshots in
`evidence/ux-audit-v2/` remain as before-state history.

## Source visual truth

- Path: `specs/142-launch-landing-redesign/design/selected-direction-3.png`
- Pixels: 863 × 1823
- SHA-256: `89a90f0a1f09c261f2ba0b42409b9d0a92b9bcbf5fa5d64dec890db34e5189fd`
- State: selected dark editorial direction 3; generated product panels are layout references only.

## Product proof inventory

| Asset | Pixels | SHA-256 | Provenance |
|---|---:|---|---|
| `landing-recording-proof.png` | 992 × 260 | `88e47a270e89071917e60009679329108b9721ed815968a9c595fd18e9c693da` | Current `CaptureStatusItem` rendered from the macOS product target with a synthetic active session; no audio or personal data. |
| `landing-outcome-proof.png` | 1280 × 720 | `e2c55f1ffb4ae947ce1ea92689121eb17ecc86106e9c5c494a38920a7e2ec51c` | Accepted feature 139 browser runtime evidence with synthetic meeting content. |
| `landing-outcome-proof-mobile.png` | 390 × 844 | `961c1b3d95e3b7c6f265ba727d0375ae6a9db1fce95d06204b6ec4b645b86cf8` | Accepted feature 139 mobile browser runtime evidence with synthetic meeting content. |
| `landing-outcome-proof-focus.png` | 1040 × 320 | `53c628763b6f1d2336f2ff5eeb2284efdb021d078159fbf6a76ce7a4624cefb4` | Privacy-cleared crop of accepted feature 139 evidence; shows only concise outcomes, actions and sources, without internal template controls. |
| `landing-outcome-proof-focus-mobile.png` | 390 × 320 | `a37073e748f12c481d8958d1acf17b4345e7821351ce259719471137e9bea2f1` | Mobile value crop from the same accepted synthetic state. |
| `landing-recording-proof-focus.png` | 880 × 180 | `fdf300fe6bae56370846923b9310ac766b44f7693ac6559011811af0881ac60c` | Focused current `CaptureStatusItem` state with visible Pause and Stop. |

## Implementation evidence

- Landing hero matrix: `evidence/refinement-v4/landing-{1440,1024,768,390,320,280}-hero.png`.
- Product proof and chapters: `evidence/refinement-v4/landing-1440-outcome-proof.png`, `landing-390-outcome-proof.png`, `landing-1440-how.png`, `landing-1440-trust.png` and final CTA captures.
- Download: `evidence/refinement-v4/download-1440.png` and `download-390.png`.
- Combined source/implementation comparison: `evidence/refinement-v4/comparison-hero.png`.
- Required viewports: 1440 × 1000, 1024 × 900, 768 × 900, 390 × 844, 320 × 800 and 280 × 720; CSS pixel scale 1 where supported by the browser harness.
- State: `/` and `/download`, dark theme, unauthenticated public visitor.
- Layout: no horizontal overflow at 1440, 1024, 768, 390, 320 or 280 CSS px.
- Console: no warnings or errors in the verified browser session.
- Primary interactions: download/login links resolve; the VKS rail pauses and resumes through its native checkbox/label control; reduced motion disables the animation and duplicate rail; Windows and Linux expose no focusable download action.

## Findings

- No actionable P0, P1 or P2 UX/UI/IA findings remain after the final independent review.
- Typography: local Onest Variable provides real Cyrillic outlines, controlled desktop line breaks and dedicated tablet/mobile scales.
- Spacing: hero, proof chapters and final CTA remain visually distinct at desktop and mobile widths; no screenshot is present without an adjacent product promise.
- Colors: near-black and violet tokens stay consistent across landing and download pages; the wordmark has sufficient contrast.
- Image quality: product proofs are current GRAF runtime evidence with synthetic, privacy-cleared content. Focused crops remove the internal `Template` control and keep the visible evidence tied to the adjacent USP.
- Copy: the implementation intentionally replaces the selected mock's unapproved universal-capture and payment claims with current product truth. Browser meetings use manual start, price/YooKassa are absent until billing is live, and model wording is limited to the managed GRAF contour.
- Current-landing patterns retained after review: compact header, three anchors, repeated CTA, dedicated download route, visible recording control, consent/legal shell and the VKS-service rail. The rail now supports pause, manual mobile scrolling and reduced motion.
- Keyboard focus traversal could not be exercised reliably through the in-app browser's Tab simulation. Semantic HTML, visible focus CSS and focused contract tests passed; this is a tooling gap, not an observed product defect.

## Comparison history

- Pass 1: direction 3 matched in hierarchy and tone, but the header used the light-background wordmark and failed contrast on the dark canvas (P2).
- Patch: switched both public templates to the official dark-background wordmark asset and recaptured desktop/mobile evidence.
- Pass 2: full-view and focused hero comparisons passed. Intentional drift is limited to product-truth corrections and additional whitespace requested by the product owner.

## Validation

- Focused public landing/analytics suite after the final proof change: `43 passed, 2 warnings`.
- Static contract subset: `7 passed`.
- Canonical fast CI: `885 passed, 2 warnings`; server lint and Python compile passed.
- Independent final visual review: passed; no remaining visual P0, P1 or P2.
- Browser states: landing 1440/1024/768/390/320/280, download 1440/390, VKS pause/reduced-motion states, and console.

## Compact hero carousel refinement — 2026-08-07

- The first viewport now uses a side-by-side product viewport instead of a
  full-width screenshot wall. The real transcript and outcome screens share one
  synthetic 18-minute meeting and slide once automatically from
  `Расшифровка` to `Итоги`.
- Manual hero tabs were removed. A non-interactive two-segment progress rail
  explains the sequence; the animation stops on outcomes so the value remains
  visible instead of looping indefinitely.
- `prefers-reduced-motion` keeps the outcome screen static and removes the
  progress animation. The product screenshots remain ordinary images with
  meaningful alternative text and no client runtime dependency.
- Evidence: `evidence/hero-carousel-v1/hero-{1440,390}.png` and
  `hero-1440-outcome.png`; the desktop proof was recaptured after constraining
  the atmospheric layer to the product side so it cannot overlap the hero copy.
- Focused public landing/analytics contracts: `32 passed, 2 warnings`.
- Fast local CI: `885 passed, 2 warnings`; lint and Python compile passed.
- Evidence: `evidence/hero-carousel-v1/hero-1440.png`,
  `evidence/hero-carousel-v1/hero-1440-outcome.png` and
  `evidence/hero-carousel-v1/hero-390.png`.
- Browser check: local server at `127.0.0.1:8780`, 1440×1000 and 390×844;
  assets loaded with no console errors, the transcript state rendered first,
  the outcome state rendered after the slide, and the focused public suite
  passed `32 tests`.

## Final result

### Legal trust UX closeout — 2026-08-13

- Login and registration now expose keyboard-accessible `/terms` and `/privacy`
  links beside the legal explanation. Login does not claim a new acceptance;
  registration identifies account creation as the acceptance action.
- Cookies and analytics-consent instructions now point to the main/download
  controls only when optional public analytics is active and explain that a
  missing control means the optional public provider is disabled.
- Browser QA passed at 1440×1000 and 390×844: no horizontal overflow, no console
  warnings/errors, visible keyboard focus on the terms link, successful
  registration-to-privacy navigation, and readable mobile legal sections.
- Focused public/auth matrix: `44 passed, 2 warnings`.
- Consent-version settings/Compose/env contracts: `3 passed, 2 warnings`.
- Canonical fast CI: `1046 passed, 2 warnings`; server lint, Python compile and
  the no-legacy-audio-driver guard passed. The warnings are existing pytest
  rewrite and Starlette/httpx deprecation warnings.
- Spec Kit analyze found no new critical, high or constitutional inconsistency
  in FR-032/FR-033 and T060–T064. External release gates T058/T059 remain open.
- Ponytail review: lean already; no dependency, abstraction or runtime code was
  added.

visual result: passed

historical release status: blocked — `pkgutil --check-signature` reported `Status: no signature`
for `public/static/public/downloads/graf-local.pkg`; `spctl` acceptance is only
the local `security disabled` override and is not launch evidence.

historical final status: blocked
