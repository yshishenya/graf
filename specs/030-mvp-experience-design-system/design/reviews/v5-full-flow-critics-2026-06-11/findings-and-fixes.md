# V5 Full Flow Critics Review

Date: 2026-06-11

Superseded note: this review is historical evidence only. The 2026-06-13
Krisp/code/Figma re-audit found live v5 blockers in button styling, duplicate
toolbar controls, technical-copy leakage, and speaker-assignment emphasis. Use
`../v6-krisp-code-audit-2026-06-13/` for current handoff status.

## Input

- Current accepted prototype before this review: Figma v4.1, 14 primary frames.
- User concern: 14 screens may not cover a complete MVP design.
- Required target: full flow from auth to export/share, useful meeting review,
  speaker/timeline/assignment, light and dark themes, desktop/web/embedded
  feasibility, and a clickable preview.

## Verdict

Fourteen frames are not enough for the full MVP design. They are enough only
for an executive walkthrough. The complete MVP design needs primary flow
screens plus state/detail screens that cover auth, permission recovery, upload
errors, processing failures, speaker work, action-item assignment, sharing,
export, deletion, browser handoff, empty states, and light theme.

## Five Critics

- Product critic: Does every screen create launch value and avoid future
  product debt?
- UX critic: Can a real owner complete the journey without guessing?
- IA/content critic: Are routes, status names, actions, and copy placed where
  users expect them?
- UI/visual critic: Is the interface dense, centered, modern, calm, and
  visually durable for 2027?
- Implementation/trust critic: Can macOS, web, and embedded web implement this
  safely without moving native capture authority into server UI?

## Round 1 Findings

- The v4.1 desktop ready screen was useful but still did not prove sign-in,
  local-only policy, permissions, or onboarding.
- The web review screen lacked a real playback timeline, speaker distribution,
  speaker assignment, transcript search, and segment-linked interaction model.
- Share/export/delete were only implied, not designed as actual states.
- Light theme existed only as tokens/docs, not visible screens.
- Desktop and browser route boundaries were documented but not visible enough in
  the clickable flow.

Fix in v5:

- Add auth/local policy, permissions, settings, browser handoff, share, export,
  deletion, speaker/timeline, and light-theme frames.

## Round 2 Findings

- Meeting list needs dense rows with status, source, owner, updated time, and
  next action. Cards waste space.
- Search and filters should be browser-rich but desktop-simple.
- Upload must explain audio-first processing and show metadata/language/source
  choices before upload.
- Processing must show stage history and what already exists, not an empty
  transcript shell.

Fix in v5:

- Add full web list, search/filter palette, upload page, upload error board,
  processing page, and degraded processing page.

## Round 3 Findings

- Action items are not useful unless assignee, due date, priority, status, and
  source segment are visible.
- Speaker assignment is useful after transcript, but must be server-owned and
  explicit because it changes downstream notes/action items.
- AI must be scoped: this meeting by default, all meetings as browser-only or
  policy-gated.
- Timeline should show talk time and active segments, not only a decorative
  audio bar.

Fix in v5:

- Add speaker/talk-time frame, notes/action assignment frame, action edit
  drawer, and scoped AI drawer.

## Round 4 Findings

- The design must not age by leaning on decorative glass or gradients.
- The modern pattern should be calm operational density, progressive
  disclosure, contextual AI, and semantic status color.
- Buttons must be fixed-height, centered, and text-safe.
- Product screens should not include UI-kit artifacts that look like broken
  components.

Fix in v5:

- Use solid surfaces, restrained translucent chrome only for macOS title areas,
  dense rows, semantic accents, and visible focus/status cues.

## Round 5 Findings

- The prototype must be reviewable by clicking from start to result, not just
  viewing a board.
- Desktop active capture must stay native and pinned above embedded content.
- Browser-only actions should be visible as handoff/confirmation flows.
- Repo docs must call v5 the current accepted target only after screenshot and
  metadata QA.

Fix in v5:

- Add a prototype click map, create main-path reactions, run metadata/screenshot
  QA, and update handoff docs after validation.

## Post-Review V5.1 Shell/Product Boundary Fix

Follow-up critique found one important architecture gap: variable product UI
was still too easy to interpret as native macOS UI, and speaker assignment was
not visibly available inside desktop. The accepted product rule is now:

- Platform desktop shells for macOS, Windows, and Linux own only
  platform-critical native work: capture start/stop, visible recording
  indicator, permissions, local buffer/artifact/queue truth, tray/menu,
  diagnostics, native bridge, and route guard.
- Server/web owns variable product UI: meeting list, processing status, review,
  transcript, notes, actions, speaker assignment, account/workspace status,
  upload metadata, settings copy, policies, and route evolution.
- Speaker assignment is available in desktop only as an embedded server-owned
  route. Native desktop code hosts it but does not implement diarization,
  speaker naming, merge, save, or conflict logic.

Fix in v5.1:

- Added `V5 34 - Desktop embedded speaker assignment`.
- Added `V5 35 - Active recording with embedded review`.
- Added desktop-ready row/status-pill click reactions so `Проверить` opens the
  embedded speaker assignment route.
- Added V5 34/V5 35 button reactions for Stop, speakers, actions, web handoff,
  record/upload, and return-to-review.
- Added `contracts/embedded-product-ui-contract.md` for route allowlist, auth,
  CSP/WebView policy, bridge events, offline fallback, and speaker assignment
  ownership.
- Updated route visibility, status, terminology, localization, component,
  screen, prototype, QA, plan, status, and changelog artifacts.

## Post-Review V5.2 Speaker Lane And Button Polish

Stakeholder visual QA found two concrete defects:

- affected speaker screens had uneven button widths that felt accidental;
- speaker separation used a single combined color strip, while the reference
  interaction should read as one separate horizontal lane per speaker.

Fix in v5.2:

- `V5 16` and `V5 34` now render speaker separation as individual lanes:
  speaker label, speaker-specific segments, and talk-time percentage per row.
- Desktop speaker action buttons were normalized to a compact fixed row-action
  width, with long merge copy shortened to `Объединить`.
- Top capture buttons in the affected desktop speaker screen were normalized to
  equal widths.
- The `V5 34` status chip and `Назад к обзору` button were separated so they no
  longer overlap.
- Fresh screenshots were saved for `v5-speakers-final.png` and
  `v5-desktop-speakers-embedded-final.png`.
- Repeated same-row button groups across the Figma page were normalized; final
  audit reports `varyingSameRowGroups=0`.

## Final V5.2 QA Result

- Figma page: `030 MVP Experience v5 - Full MVP Flow`, page id `17:2`.
- Frame count: 36 top-level frames.
- Prototype reaction count: 82 button `ON_CLICK` reactions, 130 sidebar/nav
  `ON_CLICK` reactions, and 8 meeting-row/status-pill reactions.
- Total click reactions: 220.
- Button layer count: 106 button frames across primary and supporting screens.
- Sidebar/menu coverage: 130 of 135 sidebar nav items are reactive; the five
  non-reactive items are current-section self links, which Figma correctly
  rejects as same-frame navigation.
- Programmatic layout audit: `appOverflowCount=0`.
- Final live Figma polish audit: `mixedTextHitCount=0` in V5 34/V5 35,
  `appOverflowCount=0`.
- Speaker-lane audit: `V5 16` and `V5 34` contain separate per-speaker track
  rows.
- Button-size audit: `varyingSameRowGroups=0`.
- Programmatic visible-copy audit: no unresolved English CTA/control copy after
  translating `Share`/`Export`, replacing `AI-помощник` with `ИИ-помощник`,
  shortening one export audit pill, and converting visible frame captions to
  Russian. Remaining Latin strings are intentional product/technical tokens
  such as `2brain Rec`, `MVP`, `API`, `macOS`, URLs, file formats, and service
  names.
- Delete safety polish: the confirmation input now appears before the
  destructive `Удалить` button.
- Final screenshot evidence:
  - `screenshots/v5-desktop-ready-final.png`
  - `screenshots/v5-web-meetings-final.png`
  - `screenshots/v5-review-final.png`
  - `screenshots/v5-speakers-final.png`
  - `screenshots/v5-share-final.png`
  - `screenshots/v5-export-final.png`
  - `screenshots/v5-delete-final.png`
  - `screenshots/v5-desktop-speakers-embedded-final.png`
  - `screenshots/v5-active-embedded-review-final.png`

## Completion Audit Against Goal

| Requirement | Evidence | Result |
|---|---|---|
| 14 screens are not enough for full MVP design | V5.1 expanded coverage from 14 v4.1 frames to 36 top-level frames | HISTORICAL PASS; superseded for handoff by v6 audit |
| Every launch-critical screen is represented | V5 screen backlog below is fully checked | PASS |
| Full flow from auth to export/share exists | `design/prototype/clickable-paths.md`, v5 page `17:2` | PASS |
| Desktop app shows a real cabinet, not diagnostics-only shell | `screenshots/v5-desktop-ready-final.png` | PASS |
| Web cabinet shows useful statuses and meeting value | `screenshots/v5-web-meetings-final.png` | PASS |
| Meeting review includes transcript, timeline, notes, actions | `screenshots/v5-review-final.png` | PASS |
| Speaker assignment, naming, merge, and evidence fragments exist | `screenshots/v5-speakers-final.png`, `screenshots/v5-desktop-speakers-embedded-final.png` | PASS |
| Speaker separation uses per-speaker lanes | `V5 16`, `V5 34`, updated screenshots | PASS |
| Speaker buttons use consistent sizing by context | Updated Figma audit and screenshots | PASS |
| Repeated same-row buttons are not randomly sized | `varyingSameRowGroups=0` | PASS |
| Speaker assignment is available in desktop but server-owned | `V5 34`, embedded product UI contract, route visibility matrix | PASS |
| Active recording remains native while embedded web is open | `V5 35`, `screenshots/v5-active-embedded-review-final.png` | PASS |
| Share, export, and deletion truth are designed | `screenshots/v5-share-final.png`, `v5-export-final.png`, `v5-delete-final.png` | PASS |
| Russian-first interface | Visible-copy audit has no unresolved English CTA/control copy after final Russian-copy polish | PASS |
| Dark and light themes are represented | V5 dark primary screens plus `V5 26`-`V5 29` light proof frames | PASS |
| Desktop/web/embedded boundaries are implementable | `V5 24`, `V5 31`, `V5 34`, `V5 35`, route matrix and embedded product UI contract | PASS |
| Prototype is reviewable by clicking key routes and menus | 82 button reactions, 130 sidebar/nav reactions, 8 row/status reactions | PASS |
| Non-clicking controls are intentionally local-state, not forgotten | `Скачать`, `Изменить`, `Назначить`, `Отозвать ссылку` are local controls whose states are visible in-frame | PASS |
| Krisp was studied without copying | `evidence/krisp-v5-live-audit-2026-06-11.md`, brand-distance review, no Krisp assets in asset inventory | PASS |
| Free UI kits/templates were selected as references | `visual/asset-inventory.md`, Figma kit shortlist page `16:2` | PASS |

## Ten Expert Acceptance Criteria

| Expert lens | Criterion | Evidence |
|---|---|---|
| Product | A user can get value after recording or uploading one file | Auth/upload/status/review/share/export flow in v5 |
| UX | Primary actions stay predictable and fixed-size | Screenshot QA plus `appOverflowCount=0` |
| IA | Desktop, embedded web, browser-only, and future routes are not mixed | `V5 24`, `V5 31`, route visibility contract |
| UI | Dark theme is calm, dense, modern, and not decorative-only | `visual-qa.md`, v5 screenshots |
| Implementation | Capture authority remains native while variable product UI comes from web/backend | desktop ready/active frames, V5 34/V5 35, route matrix, embedded product UI contract |
| Accessibility | Status is text-backed and not color-only | `system/accessibility.md`, semantic status rows |
| Localization | Russian is launch language and English is future localization | visible-copy audit after final Russian-copy polish and localization matrix |
| Privacy/security | Delete/share/export copy does not overpromise | `v5-share-final.png`, `v5-export-final.png`, `v5-delete-final.png` |
| Future scale | macOS/Windows/Linux can reuse server-owned product UI while each keeps native capture shell | `V5 34`, `V5 35`, embedded product UI contract |
| Handoff QA | Implementation team has specs, screenshots, click paths, and audit numbers | `figma-handoff.md`, `validation-evidence.md`, this review |

## V5.2 Critic Re-Review Status

After the speaker-lane, button-sizing, and web/native copy fixes:

- Product Value critic: `100% satisfied`; no remaining product-value blockers.
- UX Flow critic: `100% satisfied`; no remaining flow blockers.
- IA/Content critic: `100% satisfied`; the old browser-record handoff copy was
  fixed as `Open desktop app to record` / `Открыть приложение для записи`.
- UI/Pixel QA critic: `100% satisfied`; speaker lanes, button widths, native
  Stop proof, and embedded boundary are visually acceptable.
- Implementation/Trust critic: `100% satisfied`; ownership split, route
  manifest, and evidence consistency blockers are closed.

Implementation/Trust blocker fixes applied:

- Native/web ownership was tightened so native shells own only capture,
  permission, local queue/artifact truth, tray/menu, diagnostics, route guard,
  and a minimal connection/session/policy badge. Account/workspace and recent
  meeting summaries are embedded server-owned product UI.
- `embedded-product-ui-contract.md` now contains a canonical embedded route
  manifest with every required field populated per route, including
  `/desktop/meetings/:id/speakers`.
- Final validation evidence and changelog now claim `T001-T085` only after T085
  was closed and all five critics were satisfied.

## V5 Screen Backlog

- [x] V5 00 - Full flow cover and acceptance map.
- [x] V5 01 - Auth sign-in and local policy.
- [x] V5 02 - Workspace/server connection.
- [x] V5 03 - macOS permissions onboarding.
- [x] V5 04 - Desktop ready cabinet.
- [x] V5 05 - Desktop active recording.
- [x] V5 06 - Menu bar controller.
- [x] V5 07 - Desktop saved/upload queue.
- [x] V5 08 - Desktop embedded upload.
- [x] V5 09 - Web meetings list.
- [x] V5 10 - Search and filters.
- [x] V5 11 - Web upload and metadata.
- [x] V5 12 - Upload validation errors.
- [x] V5 13 - Processing status.
- [x] V5 14 - Degraded processing.
- [x] V5 15 - Meeting review with transcript and timeline.
- [x] V5 16 - Speaker assignment and talk time.
- [x] V5 17 - Notes, decisions, and assigned actions.
- [x] V5 18 - Action item edit drawer.
- [x] V5 19 - Scoped AI drawer.
- [x] V5 20 - Share and access.
- [x] V5 21 - Export and download.
- [x] V5 22 - Delete and retention truth.
- [x] V5 23 - Account, security, and settings.
- [x] V5 24 - Browser-only handoff.
- [x] V5 25 - Empty states.
- [x] V5 26 - Light desktop ready.
- [x] V5 27 - Light web meetings.
- [x] V5 28 - Light upload.
- [x] V5 29 - Light review.
- [x] V5 30 - Tokens and components.
- [x] V5 31 - Native/web route matrix.
- [x] V5 32 - Critics fixes board.
- [x] V5 33 - Prototype click map.
- [x] V5 34 - Desktop embedded speaker assignment.
- [x] V5 35 - Active recording with embedded review.
