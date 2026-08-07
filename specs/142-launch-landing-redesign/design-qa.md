# Design QA: Launch Landing Redesign

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

## Final result

visual result: passed

historical release status: blocked — `pkgutil --check-signature` reported `Status: no signature`
for `public/static/public/downloads/graf-local.pkg`; `spctl` acceptance is only
the local `security disabled` override and is not launch evidence.

historical final status: blocked
