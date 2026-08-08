# Feature 142: Launch Landing Redesign

> Refined again 2026-08-07 after product-owner review. Earlier passes are
> superseded by the current visual audit in
> `specs/142-launch-landing-redesign/design-qa.md`.

visual result: passed

release result: passed — the active macOS package is Developer ID signed,
notarized, stapled and accepted by Gatekeeper

final result: passed

---

**Source Visual Truth**

- Selected direction: `specs/142-launch-landing-redesign/design/selected-direction-3.png`, 863 × 1823, SHA-256 `89a90f0a1f09c261f2ba0b42409b9d0a92b9bcbf5fa5d64dec890db34e5189fd`.

**Implementation Evidence**

- Landing matrix and chapter evidence: `specs/142-launch-landing-redesign/evidence/refinement-v5/` at 1440, 1024, 768, 390, 320 and 280 CSS px.
- Combined comparison: `specs/142-launch-landing-redesign/evidence/refinement-v5/comparison-hero.png`.
- State: dark public landing and download flow, unauthenticated.

**Findings**

- No actionable visual P0/P1/P2 findings remain after the final typography, IA, product-proof and responsive refinement.
- The selected typography, spacing, near-black/violet palette, real-product screenshots and CTA hierarchy pass the combined comparison.
- Intentional differences from the selected mock remove unsupported universal-capture, foreign-transfer and payment claims; the implementation preserves current product truth.
- VKS rail pause/resume, reduced motion, mobile overflow, download platform states and browser console were checked. Focus semantics are additionally covered by contract tests.

Full receipt: `specs/142-launch-landing-redesign/design-qa.md`. The active
`graf-local.pkg` is the checksum-matched public `v2026.08.07.2` artifact and
the download page now carries the bounded Apple trust copy.

---

**Source Visual Truth**

> Historical QA receipt. The local signing identity mentioned in this file is
> preserved as past evidence only; current public macOS publication uses the
> Feature 130 Developer ID-only path.
- User-provided Krisp login screenshot in the current chat, state: desktop login screen at app.krisp.ai.
- Local source file path: not available; the reference was supplied as an in-chat screenshot.

**Implementation Evidence**
- Desktop screenshot: `/tmp/2brain-rec-login-preview.png`
- Code screenshot: `/tmp/2brain-rec-code-preview.png`
- Mobile screenshot: `/tmp/2brain-rec-login-preview-mobile.png`
- Viewports: 1328x768 desktop, 390x844 mobile.
- State: unauthenticated browser login, Russian copy, 2brain Rec brand, provider placeholders, email-code flow.
- Full-view comparison evidence: compared the supplied Krisp login screenshot against the rendered 2brain Rec preview at matching desktop scale.
- Focused region comparison evidence: focused on auth card, provider buttons, email form, legal copy, and mobile wrapping. No additional crop was needed because the card text and controls were readable in the full screenshots.

**Findings**
- No actionable P0/P1/P2 findings remain.

**Required Fidelity Surfaces**
- Fonts and typography: system sans stack matches the clean desktop-app feel; headings and buttons use stronger weights similar to the reference without negative letter spacing.
- Spacing and layout rhythm: centered auth card, narrow width, compact provider stack, divider, email form, SSO link, signup link, and legal copy match the reference structure.
- Colors and visual tokens: dark surface, subdued borders, purple accent, and right-side purple background glow align with the reference while preserving 2brain brand distance.
- Image quality and asset fidelity: no external raster assets are required for this server-rendered screen; provider marks are textual product labels, not copied third-party logos.
- Copy and content: Russian UI copy matches the intended flow and avoids exposing internal workspace identifiers.

**Patches Made Since Previous QA Pass**
- Removed visible and hidden `workspace_id` fields from the browser login and code forms.
- Added Krisp-like centered auth scene with 2brain Rec brand, provider buttons, email entry, SSO placeholder, signup placeholder, and legal copy.
- Changed auth primary button from blue to purple to better match the reference.
- Added tests that fail if workspace UUIDs reappear in the login UI.

**Implementation Checklist**
- [x] Desktop login card matches reference structure.
- [x] Mobile login card wraps without overflow.
- [x] Email-code page uses the same visual system.
- [x] Workspace ID remains server-side and hidden from users.
- [x] Auth-flow tests pass.

**Follow-up Polish**
- Replace textual provider marks with official provider logos when we add the actual OAuth integrations and have approved brand assets.

final result: passed

---

# Feature 118: Interactive Playback Timeline

**Source Visual Truth**
- User-supplied playback and speaker-assignment references in the current chat: `CleanShot 2026-07-21 at 02.07.39@2x.png`, `CleanShot 2026-07-21 at 02.11.32@2x.png`, `CleanShot 2026-07-21 at 02.11.41@2x.png`, `CleanShot 2026-07-21 at 02.11.48@2x.png`, `CleanShot 2026-07-21 at 02.12.16@2x.png`, and `CleanShot 2026-07-21 at 02.12.26@2x.png`.
- Production follow-up references: `CleanShot 2026-07-21 at 09.53.57@2x.png` exposed the remaining scale offset and missing inline rename control; `CleanShot 2026-07-21 at 10.02.40@2x.png` and `CleanShot 2026-07-21 at 10.02.52@2x.png` establish that the speaker caption belongs above the lane rather than inside a narrow left column.
- Final density reference: `CleanShot 2026-07-21 at 13.56.58@2x.png` and the paired Krisp app screenshot establish the compact spacing between speaker lanes and the central-content width boundary.
- The references define interaction behavior, density, aligned playhead semantics, active-speaker state, and manual naming. GRAF keeps its existing clean-room visual system instead of copying Krisp styling.

**Implementation Evidence**
- Desktop screenshot: `/tmp/graf-feature118-desktop-final.jpg` at 1280x720.
- Desktop-embedded screenshot: `/tmp/graf-feature118-embedded.jpg` at 900x720.
- Combined source-versus-implementation timeline comparison: `/tmp/graf-feature118-timeline-comparison.jpg`.
- Synthetic fixture only; no real meeting audio, transcript, participant identity, or credential is present.

**Measured Results**
- Native range bounds: 853.61 px; speaker-track bounds: 837.61 px; both lane edges are inset exactly 8 px to match the 16 px native thumb center.
- A pointer click intended for 9.00 seconds resolved to 8.97 seconds, within the 0.25-second requirement.
- At 8.97 seconds both overlapping speaker lanes were active and the transcript turn beginning at 8.00 seconds was current.
- A click in the 18-20 second gap resolved to 18.92 seconds, produced zero active lanes, and centered the deterministic previous transcript turn within 0.22 px of the viewport center.
- At 900 px embedded width the dock occupied the full viewport, kept 10 px symmetric range-to-track insets, exposed all three rename forms, and produced no horizontal overflow.
- Reduced-motion emulation selected the non-animated transcript-follow path and preserved seek/current-turn behavior.
- Renaming `speaker_00` to a synthetic `Алексей` value persisted through reload and appeared in the input, timeline, and transcript.
- Browser console warnings/errors: none.

**Visual Review**
- The main range thumb and every lane playhead share the same horizontal time truth.
- Active lanes have a non-color-only outline/weight treatment; overlap remains legible.
- Speaker labels, percentages, controls, and editor stay compact within the existing GRAF cabinet hierarchy.
- Transcript current state remains visible without moving keyboard focus.
- No P0, P1, or P2 visual or interaction findings remain.

**Patches Made During QA**
- Replaced browser-dependent range geometry with one explicit inner scale shared by the custom 16 px visual thumb and every lane playhead.
- Preserved one responsive three-column grid for current time, progress, duration, lane marker, lane track, and share while moving each caption above its lane in the full-width track column.
- Made the caption itself the inline rename control and placed its authorized form directly beneath the matching lane; the existing summary editor remains only as a non-playable fallback.
- Confirmed the synthetic QA server supports byte-range audio so browser seek evidence measures the implementation rather than a fixture limitation.

**Production Follow-up Validation**
- A long synthetic caption is rendered in the full-width track column and covered by a server-rendering regression test.
- Focused cabinet, playback-contract, and PostgreSQL speaker-name persistence checks pass; the complete server suite passed with 1954 normal and 34 strict-RLS tests in the memory-safe one-worker lane.
- Installed GRAF `2026.07.21.9` was inspected against the production meeting-detail route after an in-app Sparkle update from `2026.07.21.8`; private meeting screenshots remained temporary and were not committed.
- The dock starts after the left navigation and ends before the native recording inspector. Three speaker lanes remain compact, keep labels above full-width tracks, and use the same speaker colors as transcript markers.
- The manager is exposed as an ordinary accessible button rather than a browser disclosure. Opening it exposed three `Изменить` actions; opening one editor exposed the expected name field, `Сохранить`, and `Отмена`. The editor was cancelled without submitting or changing production data.
- Pressing the `SPEAKER_02` lane changed the accessible playback position from `393.9` to `242.4` seconds, centered the matching transcript turn, and applied the non-color white outline to the active lane. Playback was paused after the check.
- The public update feed, downloaded ZIP and pkg matched the reviewed local artifacts byte-for-byte. The installed bundle kept identifier `pro.2brain.graf`, the existing feed URL, the `GRAF Local Code Signing` identity, and granted microphone/system-audio permissions.
- Final release boundary: [v2026.07.21.9](https://github.com/yshishenya/crisp/releases/tag/v2026.07.21.9), implementation [PR #4008](https://github.com/yshishenya/crisp/pull/4008), release [PR #4009](https://github.com/yshishenya/crisp/pull/4009). No P0, P1, or P2 finding remains.

final result: passed

---

# Feature 123: меню «Ещё»

Подробный feature-specific отчёт находится в
[`specs/123-meeting-actions-menu/design-qa.md`](specs/123-meeting-actions-menu/design-qa.md).

## Evidence

- Source visual truth: выбранный пользователем первый вариант ImageGen;
  исходный артефакт находится вне репозитория и не поставляется в продукт.
- Implementation screenshot:
  `specs/123-meeting-actions-menu/design-qa-open-menu.png`.
- Combined comparison:
  `specs/123-meeting-actions-menu/design-qa-comparison.png`.
- Source and implementation pixels: 1488 × 1058; CSS viewport: 1488 × 1058;
  density 1; downsampling не применялся.
- State: тёмная тема, detail встречи, меню открыто, первый пункт в фокусе;
  fixture синтетический и metadata-safe.

## Review

- Full-view comparison: композиция, плотность и расположение меню совпадают с
  выбранным направлением; отличие безопасного fixture в теле встречи не
  относится к этой UI-поверхности.
- Focused comparison: проверена область меню; 280px ширина, 48px строки,
  helper hierarchy, divider перед удалением, focus ring и существующие иконки.
- Fidelity surfaces: сохранены шрифт и иерархия GRAF, spacing/tokens, цвета
  темы и контраста, vector icon source и русские пользовательские подписи.
- Tested interactions: click/Enter/Space/ArrowUp/ArrowDown/Home/End/Escape,
  outside click, details dialog close/backdrop/focus return; desktop 1488×1058
  и mobile 390×844 без clipping; console без error/warn.

## Findings and history

No actionable P0/P1/P2 findings remain. Initial review found only brittle
contract assertions and a destination-trigger focus race; contracts were
updated to the semantic markup, focus restoration was made visible-target
aware, and the desktop/mobile states were captured again.

## Result

final result: passed
