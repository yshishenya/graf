# V8 Five-Critic Screen Audit

Date: 2026-06-15
Feature: `030-mvp-experience-design-system`
Figma page: `030 MVP Experience v8 - Clean RU` (`341:2`)

## Purpose

This audit checks the active V8 design against the stakeholder blockers that
rejected the earlier V5-V7 directions: uneven controls, fragmented flows,
underdesigned settings, technical copy, empty layouts, missing provider sign-in,
weak permissions onboarding, weak web meeting list, standalone upload/status
screens, missing dark/light proof, and speaker assignment not feeling primary.

The five critic lenses are:

- Product flow: can a user complete the MVP owner value loop?
- IA: does the screen belong in the right surface and avoid fake destinations?
- Visual/UI: does density, hierarchy, spacing, and control size feel coherent?
- Platform: does native macOS stay native and variable product UI stay cabinet/web-owned?
- Content/trust: is copy Russian, non-technical, privacy-aware, and truthful?

## Requirement Trace

| Stakeholder blocker | V8 evidence | Verdict |
|---|---|---|
| Buttons looked different sizes | Figma audit: button heights only `36/40`, bad button heights `0`; chips `28`, bad chips `0` | PASS |
| Flow was fragmented | V8 has 98 valid `ON_CLICK` reactions, invalid destinations `0`, self-links `0`, superseded-page destinations `0`, and required owner-value-loop coverage PASS | PASS |
| Settings were not thought through | `V8 09` covers recording behavior, selected app detection, sources, theme, language, access/upload/notifications/diagnostics, and web handoff | PASS |
| Technical elements leaked into UI | Post-copy visible text sweep: `forbiddenTextCount=0` after fixing `Stop` and local wording leaks | PASS |
| "Server online" took too much space | V8 uses compact sync/status chips and menu-bar/header state, not a standalone server screen | PASS |
| Sign-in was too large and lacked providers | `V8 01` is compact and provider-first: Google, Apple, Microsoft, Yandex, почта | PASS |
| "Continue locally" was confusing | Removed as a primary auth route; copy says recording starts after sign-in and explicit start | PASS |
| Permissions route felt unexplained | `V8 02` is a first-open guided macOS permissions screen with visual System Settings guide | PASS |
| Ready cabinet lacked date/time | Desktop and web meeting rows include date/time/duration/status/source context | PASS |
| Active recording felt like a strange window | `V8 05` makes recording a menu-bar/header state with Stop and compact popover | PASS |
| Auto-detected meeting prompt/policy missing | `V8 04` prompt plus `V8 09` policy choices cover ask/auto/manual behavior | PASS |
| Saved/upload queue copy was too vague | `V8 06` models upload and transcription as concrete meeting rows/statuses | PASS |
| Upload should be integrated | Desktop and web upload are list/sheet states, not standalone MVP destinations | PASS |
| Web list composition was weak | `V8 10` includes inline search, filters, sort, upload, source, status, date/time, actions | PASS |
| Search/filter as separate screen was wrong | V8 search/filter live on the meetings list; no separate filter route is needed | PASS |
| Web upload/metadata should match app upload | Upload routes converge into the same processing/list state model | PASS |
| Validation/processing screens felt standalone | Error/status are represented as row states and expandable detail patterns | PASS |
| Light/dark theme missing | `V8 09` has system/dark/light settings; `V8 13` is the light-theme proof | PASS |
| Speaker assignment must be primary and lane-based | `V8 08` uses separate speaker rows/lanes with percentages and assignment actions | PASS |

## Screen-by-Screen Critic Matrix

| Frame | Product flow | IA | Visual/UI | Platform | Content/trust | Verdict |
|---|---|---|---|---|---|---|
| `V8 00` flow map | Shows reset owner loop | States boundaries upfront | Dense but readable overview | Defines native vs cabinet ownership | No implementation labels in visible copy | PASS |
| `V8 01` sign-in | Starts MVP with account | Provider-first, no local bypass | Compact window, no oversized slogan | Fits first-run native shell | Russian copy and explicit start truth | PASS |
| `V8 02` permissions | Explains why app needs access | First-open route is clear | Visual guide reduces guesswork | macOS permissions stay native | No silent recording promise | PASS |
| `V8 03` desktop workspace | Default daily cockpit | Meetings first, upload inline | Rows include useful density | Native shell owns capture/status | Readiness, transcript, upload, and next-action copy are clear | PASS |
| `V8 04` detected prompt | Lets user choose before capture | Prompt is inline, not a new product area | Compact choices with policy chip | Detection remains native shell logic | Ask/auto/manual wording is user-facing | PASS |
| `V8 05` active recording | One-action Stop, clear state | Recording is chrome/popover, not route | Latest copy fix removes `Stop`/local leaks | Menu bar/header behavior is native | After-stop queue copy is truthful | PASS |
| `V8 06` upload/processing | File becomes a meeting row | Upload/status stay in workspace | Progress and rows are compact | Desktop uses shell plus embedded state | Avoids vague "saved locally" headline | PASS |
| `V8 07` transcript review | Shows transcript and outcomes | Review is a cockpit, not a dashboard | Speaker action and panes fit | Cabinet-owned variable review UI | Source/status copy is non-technical | PASS |
| `V8 08` speaker lanes | Enables speaker correction | Primary review mode, not secondary afterthought | Separate lanes and percentages are visible | Embedded cabinet owns variable speaker UI | Labels/actions are understandable | PASS |
| `V8 09` settings | Covers policies needed for MVP | List-detail settings console | Controls are dense and grouped | Native shell links to web where needed | Theme/language/sources are explicit | PASS |
| `V8 10` web list | Web mirrors current statuses | Search/filter/upload inline | Table/list density matches meeting work | Browser cabinet owns broad meeting list | Date/source/status/action are visible | PASS |
| `V8 11` web detail | Review complete meeting in web | Detail owns share/export/speaker paths | Transcript, playback, outcomes coexist | Browser cabinet owns collaboration actions | No deletion overpromise here | PASS |
| `V8 12` governance | Share/export/delete in one place | Risky actions live in browser cabinet | Three panels reduce hidden danger | Browser-owned access/deletion handoff | Deletion truth is bounded | PASS |
| `V8 13` light proof | Proves theme switch result | Same cockpit semantics as dark | Light state does not change layout model | Cross-theme shell proof | Status/date/source still visible | PASS |
| `V8 14` QA rules | Locks component rules for build | Defines ownership boundaries | Button/chip/control sizes explicit | Separates native and cabinet responsibilities | Forbids user-facing technical copy | PASS |

## Machine Evidence

- Current V8 frame count: `15`.
- Current V8 clickable reactions: `65`.
- Reaction graph issues: `0`.
- Required owner-value-loop coverage: PASS.
- Frame-bound overflow: `0`.
- Bad button heights: `0`.
- Bad chip heights: `0`.
- Visible forbidden implementation copy: `0`.
- Placeholder artifacts: `0`.

## Krisp Reference Recheck

After the stakeholder challenged whether enough Krisp product practice was
actually used, V8 received an explicit clean-room Krisp reference matrix:
`krisp-reference-matrix.md`.

The matrix turned the Krisp observations into product gates instead of broad
inspiration. It then triggered a first-path correction pass:

- `V8 01`: visible `email` wording was replaced with `почта`, and the bottom
  note now talks about explicit recording start instead of file creation.
- `V8 02`: the simulated System Settings heading is Russian, and permission
  copy explains the user-visible access path.
- `V8 03`: the default desktop cockpit now says `Готовность к записи`, uses
  `Расшифровка` for processing rows, uses `Подробнее` for processing-row
  actions, and turns the upload rail into `Добавить запись` instead of a
  queue-first destination.
- `V8 04`: the detected-meeting policy row reads as a saved preference preview:
  `Спрашивать`, `Всегда писать`, `Вручную`.
- `V8 05`: the legacy `Видимый индикатор` chip is hidden, recording details are
  short, and the popover explains that the meeting appears in the list after
  stop.
- `V8 06`: uploaded media appears as a meeting-style row first, with file/progress
  secondary and `Подробнее` as the next action.

Targeted Figma API re-audit across `V8 01` through `V8 06` returned
`missingFrames=0`, `forbiddenHits=0`, and `badControls=[]`. Required first-path
copy gates are present: `Войти по почте`,
`Конфиденциальность и безопасность`, `Готовность к записи`, `Добавить запись`,
`Всегда писать`, `После остановки встреча появится в списке.`,
`Звонок с клиентом`, `Подробнее`, and `Расшифровка`.

Decision: V8 remains the active review candidate. The first-path
Krisp-alignment correction queue is complete, but final implementation handoff
still requires stakeholder visual approval.

## Remaining Value-Surface Recheck

After the first-path recheck, the remaining screens `V8 07` through `V8 14`
received a separate deep pass documented in
`v8-remaining-screens-deep-pass.md`.

This pass found and fixed:

- `V8 10`: technical browser hint, overlapping web-list copy, file-name primary
  title, vague `Статус` row action, and bottom filter chip overlap.
- `V8 11`: technical browser hint and playback metadata overlap.
- `V8 12`: technical browser hint, export-row overlap, and weak deletion
  outside-control wording.
- `V8 13`: light-theme drift where a file name and vague row action remained.
- `V8 14`: QA-board ownership overlap, generic status sample, and missing Krisp
  matrix gate.

Post-fix Figma API audit for `V8 07` through `V8 14` returned
`missingFrames=0`, `badControls=[]`, `textOverlap=[]`, and
`forbiddenHits=[]`. Screen-specific gates passed for transcript review, speaker
lanes, settings, web list, web detail, share/export/delete, light theme proof,
and component QA rules.

## Remaining Gate

V8 is ready for stakeholder visual review, but not final implementation handoff
until visual acceptance is recorded. The remaining risk is taste/product fit
under live human review, not missing coverage in the current Spec Kit/Figma
evidence.
