# KRISP Reference-Fidelity Matrix

## Boundary

This is a clean-room product study combining black-box interaction with
read-only inspection of installed-package metadata and capability wiring. It is
not authority to copy implementation code or extracted assets. `P` captures the
user job, `G` defines GRAF behavior and product-truth improvements, and `R`
identifies observable Krisp layout/copy/visual treatment that Feature 196 may
faithfully reproduce. A row may explicitly mark a known defect that must not be
preserved. GRAF implementation remains independent; extracted source/assets,
binaries, private APIs/protocols, secrets and private content remain prohibited.

## Reproducible reference metadata

- Audit date: 2026-08-23.
- Installed app: local Krisp desktop installation.
- Bundle/version/build: `ai.krisp.krispMac`, `3.15.6`, `3.15.6`.
- Executable SHA-256: `eb5227e047bd78d9a3416a9d71c5def728f17f2fcfe8fb8c40c351423e441147`.
- Packaged `app.asar` integrity SHA-256:
  `0afb19b7fd7dc0a21a68837724f8872222107f3f2e474af610af43071ff60003`.
- Package observations: Electron 40, React 18 and
  `@krispai/kr-ui-components`; the desktop shell loads `app.krisp.ai`, and the
  preload surface names separate meeting-notes, transcript, copy,
  auto-summarize and WebView event families. These observations constrain
  capability decomposition only. They do not disclose or authorize reuse of
  code, private protocols or assets.
- Method: read-only black-box interaction through the installed UI plus
  metadata/static package inspection. No inference was intentionally triggered
  for this audit. Hidden prompt text, model choice, ranking logic and server-side
  summary pipeline were not observable and are not claimed as Krisp-derived
  facts; GRAF's prompt architecture is independently sourced and evaluated.
- Evidence: exactly 14 JPEG images in one read-only, non-versioned,
  access-restricted outside-git bundle. The files were counted and inspected on
  2026-08-23; no separate 24-screen bundle or 24-screen manifest is available,
  so this document makes no 24-screen claim.
- Repeat validation: a second, separately retained outside-git walkthrough has
  15 frames numbered `00`–`14`. It revisits multiple private recordings and the
  list/detail/type/transcript/player states to challenge the first pass. It is a
  repeat-evidence set, not an extension of the normative 14-image manifest; no
  additional opaque reference IDs or private record names/content are created
  from it. The repeat pass additionally exposed a note-block context menu,
  transcript-row edit/delete affordances and the visible player rate set; those
  control families are assigned explicitly below instead of being treated as
  proof for an unowned interaction.
- Current-state validation: a third read-only outside-git bundle contains
  exactly 11 PNG frames, mapped below to `KRP-183-C01`–`KRP-183-C11` by image
  digest. It reopens the current installed app and captures the Auto template
  shell, one ready/empty-section variant, two-stage feedback entry, persistent
  reformat banner, three assistant-host labels, transcript/audio states, the
  complete visible rate set and the inline selection/block toolbar. The frames
  do not prove the universal empty-section rule or unseen async/accessibility
  combinations. This is a closed current challenge set, not a replacement or
  renumbering of the 14-image baseline.
- Claim limit: static images prove only the visible control/state captured in
  that frame. Keyboard behavior, focus order/trap/restore, VoiceOver output,
  menu actions and async transitions below are target acceptance requirements,
  not claimed observations unless an interaction receipt is named separately.
- Privacy: opaque IDs below replace source filenames because some filenames and
  pixels contain private meeting/contact data. No meeting title, participant,
  transcript or account identifier is copied into git.

### Current installed-package metadata recheck — 2026-08-24

- The installed bundle still reports `ai.krisp.krispMac` version `3.15.6` and
  the executable SHA-256 remains
  `eb5227e047bd78d9a3416a9d71c5def728f17f2fcfe8fb8c40c351423e441147`.
- The current stable `Contents/Resources/app.asar` SHA-256 is
  `d247c922e78ea432779aedc7d1e7378281f08aeec9452a37191cf9a3e24f3ec0`.
  The earlier `0afb19b7fd7dc0a21a68837724f8872222107f3f2e474af610af43071ff60003`
  value remains the hash of the 2026-08-23 captured package and is not
  silently reclassified as the current package.
- This is a metadata/integrity recheck only: it does not change the
  2026-08-23 frame manifests or their stated claim limits. The separate
  current spot-check below is intentionally not part of those manifests and
  records only the visible state it actually captured.

### Current installed-app spot-check — 2026-08-24

- One authenticated meeting-detail screen was read through the macOS
  accessibility tree and saved outside git as the opaque evidence file
  `krisp-current-notes-2026-08-24.jpeg`.
- The screen visibly exposes the split `AI Notes`/`Transcript` control, exact
  revision `Copy`, transcript-language `RU`, persistent `Share` and `Connect`
  header actions, the reformat banner, timestamped action items, `Key Points`,
  section feedback and the `Ask anything...` assistant host. The accessibility
  tree also exposed the action-item timestamp links and `Due date` controls.
- Evidence SHA-256:
  `1772bfb7a6fe6e5d9a74d566856d16815e20bcd33a2ac63bf1ff21d54d8923d4`.
  The screenshot contains private meeting content and remains outside git;
  this spot-check does not claim keyboard, async, mutation or second-record
  behavior.

### Opaque 14-image manifest

`KRP-183-01`–`KRP-183-14` map one-to-one to the bundle's numeric capture order.
The local files remain private research evidence, never product or release
assets.

| Opaque evidence ID | Metadata-only captured surface/state |
|---|---|
| `KRP-183-01` | Meeting list, global navigation, upcoming/history layout and desktop shell |
| `KRP-183-02` | Ready AI Notes detail, action rows and meeting header |
| `KRP-183-03` | Open type menu, contextual reformat prompt, feedback prompt and assistant affordance |
| `KRP-183-04` | Template catalog and settings navigation |
| `KRP-183-05` | Built-in template detail and section structure |
| `KRP-183-06` | Second built-in template detail and richer section structure |
| `KRP-183-07` | Ready AI Notes detail with evidence timestamps and contextual prompt |
| `KRP-183-08` | Transcript, speaker rows/lanes and audio-preparing player state |
| `KRP-183-09` | Transcript-language popover and ready player controls |
| `KRP-183-10` | Share dialog with link-scope menu open |
| `KRP-183-11` | Share dialog with permission menu open |
| `KRP-183-12` | Meeting-list filter menu open |
| `KRP-183-13` | Meeting-list sort menu open |
| `KRP-183-14` | Global search dialog with recent-search rows and per-row removal controls |

### Opaque 11-image current-state manifest

All frames are 1326×768 PNG. Digests identify the private outside-git bytes
without exposing source filenames, meeting titles, participants or transcript
content.

| Opaque evidence ID | SHA-256 | Metadata-only captured surface/state |
|---|---|---|
| `KRP-183-C01` | `bcf0fcf1c72391eb544a0f0bd85eb9c68cbb67dbad59c8fae0dc03db7ff1f7fc` | Auto template detail with `Action Items` before `Key Points` |
| `KRP-183-C02` | `06c36665aacd26da44461b39895977291e1c5f419759c21670a83b5322384a70` | Current meeting-list shell and row controls |
| `KRP-183-C03` | `57b737b5ef6445dbba587b70a640efb37054aa80c226b2666a04c91c06ff6899` | Ready Auto notes with actions, empty Key Points heading, reformat banner, initial section-feedback chooser and assistant suggestion |
| `KRP-183-C04` | `fb9b5dba25e35a1f8b20f60817ca490ba43e11dc0c86264cf32c0920d4fb5550` | Open quick-type menu and alternate assistant suggestion |
| `KRP-183-C05` | `436c15ae839508e424be54cd26c10ba68ea7ee1a2a964495e7b398838c9ecb57` | Transcript with audio-preparing state and contextual assistant suggestion |
| `KRP-183-C06` | `c432f6270e2f744e23601c40848bc4aa45278ab1ecdc40869b0cde1979ef5ada` | Ready player, timeline, speaker lanes and transport cluster |
| `KRP-183-C07` | `f7e8b136ad896c2aaf73728babc9f924733f62c3d9fb849f71719144514a3412` | Open five-value playback-rate menu and idle assistant host |
| `KRP-183-C08` | `9e5d460d749d3e0367dc15f148f376c4b2b263c818ae418dbb31b21fd19500f2` | Meeting-list return state |
| `KRP-183-C09` | `e27ebe19e197d22f6288021ac99b6d752a1cb3be670184000898c63b06caa82a` | Ready Auto result with Key Points and no rendered Action Items section |
| `KRP-183-C10` | `b7009f5d6246bde3117465de0e283ec2df4a0ad9dd37050cee6aad032d76171d` | Inline text-selection toolbar |
| `KRP-183-C11` | `688cedd86bbc1003993ebf10d601647d70a45f5e76d0eb0f4a90c5844d841127` | Block handle plus inline toolbar state |

`KRP-183-C03` and `KRP-183-C09` expose inconsistent reference behavior for an
empty Auto section: the former leaves an empty `Key Points` heading, while the
latter omits empty `Action Items`. GRAF follows the useful omission behavior
from `C09` for both sections and records the empty heading in `C03` as a
reference defect. If neither section has supported content, the type returns
`no_supported_content` and publishes no empty shell.

| Surface | Observed KRISP pattern | P — keep | G — GRAF behavior | R — reference-fidelity target |
|---|---|---|---|---|
| Meeting list | Upcoming is above history; rows show title, duration, participants and date; Later, Filters, Sort and New are nearby. Filters: star/date/contains/company/type/tags/folders. Sort: date/duration/last modified plus newest/oldest | Find the exact meeting and understand readiness before opening | Krisp-faithful list with `Later` in English and localized `Отложенные` in Russian; exact supported facets; AND between facet groups, OR within one group; deterministic date/duration/last-modified ordering and honest empty/no-result states. The former `Сохранённые` wording is not the observed reference and is retired from this target | Sidebar arrangement, iconography, density, palette and locale-correct visible labels |
| Global search | `⌘K` modal starts with recent searches and searches title/content; duplicate same-title rows may show only the same date and remain weakly disambiguated | Reach an exact meeting quickly from anywhere, including duplicate titles | Keep the global/recent pattern but improve identity: stable meeting ID plus date and available duration/participants; permitted metadata/content only; loading/no-result/stale-result/access-loss without leakage | Modal geometry, shortcut presentation and feedback icons; weak duplicate disambiguation is a documented defect, not a fidelity target |
| Meeting detail | AI Notes and Transcript share one compact top strip; AI Notes is a split control whose main target selects notes and whose adjacent icon+chevron opens the format menu | Two primary work modes; type choice stays beside notes; playback context persists | Literal split-control composition: `Итоги`/`AI Notes` main tab, separate adjacent type-menu button, peer `Расшифровка`/`Transcript` tab. Each is an independent focus target; selected type and async state persist without changing the active view | Exact header, split pill, tab spacing, selected/hover/focus states and player geometry |
| Per-meeting continuity | Different meetings reopen their own last AI Notes/Transcript view | Resume where work stopped without global state leakage | Persist last successful view and summary type per user+meeting; browser and embedded macOS use the same behavior | Visible resume behavior; internal route/query/storage mechanisms are not reference targets |
| Main notes | Scannable sections and timestamps; Auto template defines `Action Items` then `Key Points`, while a result may omit an unsupported empty section | Outcome-first hierarchy and evidence jump | Auto uses that ordered two-section vocabulary: actions only in Action Items and every other selected outcome only in Key Points, exactly once. Each empty section is omitted; if both are empty, no result is published. Hidden intent profiles affect selection/priority/safety, never headings. Other formats use their own contracts. Every displayed canonical claim/action with evidence keeps a clickable timestamp | Typography, bullets, timestamp style and labels |
| Type picker | Compact menu opens from the icon+chevron segment next to AI Notes and marks the selected format; quick formats precede All templates/New template | Type choice close to result | Existing saved type opens instantly; selecting a missing type itself starts one idempotent ensure with no second `Generate` confirmation; refresh is separate and ready-only. Menu rows expose ready/preparing/failed/unavailable/retired state without showing another type's content; `Все форматы` remains the full-catalog route | Menu shape, placement, icons, ordering, checkmark and selected/hover/focus colors |
| Notes actions | Copy and `RU` sit on the right of the shared notes/transcript strip; Share stays in the meeting header | Common actions remain visible without crowding content | For a ready selected type, Refresh occupies the right action cluster immediately left of Copy; that same slot stays visible but busy/disabled during updating or blocked work. A missing type has no Refresh control: wait/retry/recovery lives in its type-scoped status panel. Copy follows the active tab and exact painted revision. Feature 196 also owns the observed transcript-language/regeneration surface and an always-present disabled Share host until Feature 203 installs the capability. Async completion never retargets an action | Exact placement, compact icon/text treatment, spacing, hover/focus/disabled/pending feedback |
| Full template library | Built-ins and custom templates discoverable | Quick list + complete catalog + details | Krisp-faithful functional names/descriptions and availability states may match literally; GRAF-specific claims remain truthful | Exact card grid, functional copy and ordering; artwork, logos and trademarks require rights or independent recreation |
| Template details | Purpose and expected sections visible | Explain result before selection | Show sections, exclusions, evidence rules and typical use | KRISP wording, emoji and composition |
| Template management | Settings separates My Templates and built-ins; built-ins are view-only with Duplicate/Set default; custom templates add Delete; Auto is marked default | Built-ins stay safe while custom lifecycle is understandable | Separate built-in/personal collections; built-ins immutable; duplicate creates a personal copy; one explicit default; delete retires future generation but preserves historical results | Names, catalog composition, action menu styling |
| Custom builder | Autosaved draft; name/icon; semantic blocks; custom sections; reorder; duplicate/default/delete | Build from understandable semantic sections without a separate save ceremony | Supported blocks only; explicit autosave state, validation, version/default/permissions/preview, recovery and keyboard reorder | Modal/slash-menu expression and visual hierarchy |
| Inline note editing | Selecting generated note text opens a compact toolbar for bold, italic, underline, strike, left/center/right alignment, color, nest/unnest, link and comment/block actions; a block handle exposes block-level commands | Refine a personal working note without corrupting generated truth | Feature 209 edits a separate versioned note document, never the immutable generated outcome. It reproduces the complete toolbar/handle only with named controls, deterministic selection persistence, autosave status, undo, expected-version conflict/offline recovery and no data loss. Two unlabeled reference buttons are not copied as unlabeled controls; GRAF ships only independently identified, owned actions | Exact toolbar/handle geometry and selected/disabled states; accessible names, keyboard alternatives, autosave/error/undo feedback are mandatory improvements |
| Action items | Inline checkbox, assignee field and due-date calendar; completion strikes through the task; unknown speaker can be mapped to a contact | Operational items are easy to scan and update | Feature 205 canonical mutable task object; each row keeps task, assignee, due-date control and evidence timestamp together; model-proposed owner/due require evidence, while explicit user edits have user provenance; unknown remains unknown; completion/edit persist after reload. Inline controls are required before full public Workspace GA | Exact row/control/timestamp arrangement, contact treatment and calendar styling |
| Evidence | Timestamp near claim opens transcript at the source while player remains available | One action to source and one predictable return | Every displayed canonical claim/action with evidence exposes exact canonical segment seek; return restores type, scroll, focus, player time and play/pause state without auto-play | Timestamp visual treatment |
| Player | Persistent lower player; the evidence set captures audio-preparing and ready states, transport, timeline, speed and speaker lanes/filter affordances | Audio remains available while reading and source checking | Execute `PX-01`–`PX-11` below; preserve time/play state across type/transcript/evidence transitions and keep unavailable/error truth separate | Exact bottom bar/speaker-lane styling where observed; unproven filter behavior is a documented GRAF deviation, not an inferred Krisp contract |
| Failed transcript | Language warning, disabled Copy/Regenerate until a valid change and available player | Explain why summaries cannot exist and prevent unsafe actions | Distinguish transcript failure from summary failure; preserve recording/player; offer only valid recovery | Warning copy and control placement |
| Transcript language | `RU` remains visible beside Copy while AI Notes is selected; it opens `Transcribe in correct language`, requires an explicit `Regenerate` and warns that regeneration may take up to 30 minutes | Make a costly source-reprocessing action explicit | Reproduce one transcript-language control in the observed position. A language choice alone starts nothing; enabled `Regenerate` invokes only Feature 197's authenticated/idempotent expected-source-revision command, whose confirmed success changes the canonical transcript source and marks every old-source active saved type stale. It never acts as a summary `ensure`/`refresh` | Popover wording, placement, language labels, disabled/changed/busy states |
| Notes output language, not observed | No separate summary-only language control was observed; the compact `RU` affordance is transcript regeneration | Do not invent parity from an unsupported inference | Feature 198 may later expose an independent notes-language policy outside the reference strip. Feature 196 does not label `RU` as `Язык итогов` or create a shared summary-language mutation here | No Krisp fidelity target until separately observed and specified |
| Short meeting | Very short valid meetings can have useful Auto notes; source-empty meetings show transcript failure/no content | Do not use duration alone to decide usefulness | Decide from canonical source quality and profile support, not minute count; never fabricate notes | KRISP CTA wording and assistant bubble |
| Regeneration | Missing-format generation temporarily opens a blank canvas; on `400` it restores Auto | Preserve the previous useful result and make update discoverable | Never blank same-type current content; missing-type work keeps prior ready type one switch away and restores it on failure only while that request owns the latest presentation intent; no accept dialog or raw provider error | Selector/loading geometry and previous-type restoration; blank same-type content and raw errors are documented defects, not fidelity targets |
| Reformat suggestion | Ready Auto notes visibly show `Reformat AI notes to Meeting Minutes?`, `Try it out` and dismiss directly below the primary strip in all three current ready-note checks | Discover another useful saved format without a confirmation ceremony | Required when Auto is ready, Meeting Minutes is available and no current Meeting Minutes result exists, unless dismissed for the exact user+meeting+target-template-version. It is derived from local catalog/result state, starts no inference on paint, and `Try it out` is the single explicit idempotent ensure+selection intent. It never displaces status/error or silently changes Auto | Exact banner geometry, copy, CTA/close order, focus and dismissed state |
| Feedback | Initial `How were the:` chooser offers `Key Points` and `Action Items`; choosing one expands that section's five-point emoji scale | Capture low-friction, version-bound quality signal without asking for acceptance | Reproduce the two-stage flow. Stage 1 selects the exact visible section and starts no write; stage 2 is one text-labelled radio group tied to the exact result+section. Ratings 1–3 reveal optional closed diagnostic reasons, later selection updates the same record, and explicit remove clears it. Pending/error/conflict/retry preserve the prior value. Feedback is optional, never blocks reading and never mutates/promotes a prompt automatically. Feature 201 is required before full public Workspace GA, not before initial calibration | Exact chooser/scale placement and wording; text labels, arrow-key group behavior, focus and error recovery are mandatory |
| Assistant host | The same bottom-right capsule is observed as `Summarize unresolved topics`, `Write down weekly recap` and `Ask anything...` | Keep query help discoverable without hidden inference | Feature 210 owns three explicit host states: idle composer `Ask anything…`; deterministic unresolved-topic suggestion only when unresolved canonical questions exist; weekly-recap suggestion only for the eligible weekly intent. Opening idle starts no call. Activating a suggestion or submitting typed text is one explicit request; responses are evidence-backed drafts and never mutate notes/actions/source automatically | Exact capsule position/shape and visible strings; named control/input, focus, submit/busy/real-cancel/ambiguous/error and source-return states |
| Share | Invite by email; permissions: edit, comment, view notes+transcript+recording, or notes-only. Link scopes: invite-only, personal workspace, team, anyone with link | Make recipient, access and exact shared result clear before egress | Feature 203 capability matrix starts fail-closed at invite-only; expose only scopes allowed by workspace policy; invocation freezes the exact displayed type/revision/language for the open dialog, and later refresh only announces that a newer version exists. Pending/ambiguous/success/failure are explicit; an existing artifact never follows refresh | Header placement, modal composition, permission wording and `Personal` naming |
| Global actions | Action items can be aggregated; Personal Free shows a paywall | Cross-meeting follow-through is valuable | Feature 206 projects Feature 205 canonical actions with completion/owner/due consistency; unavailable plans show a truthful non-blocking state | Exact navigation/category names and paywall art |
| Automation settings | Auto-start note taker, open meeting page, summarize notes and generate title are separate toggles; exclusions are separate; recap audience and default link permission are separate sharing defaults | Independent controls prevent accidental coupling | Keep existing capture auto-start/exclusions under capture policy; Feature 197 owns auto-summary/open/title policy; Feature 203 owns recap audience/link defaults. No toggle silently enables another | Settings layout, copy and plan gating |

## Executable player and transcript parity matrix

Feature 196 owns browser/embedded presentation parity and reuses the existing
GRAF transcript/playback runtime. Feature 197 owns transcript regeneration, not
ordinary playback. Every browser and embedded acceptance below uses synthetic
fixtures and the same authorized media/transcript identity; no private capture
is test data. `KRP-183-08`/`09` ground visible geometry only.

| ID | Capability and GRAF contract | Keyboard and VoiceOver contract | Browser executable acceptance | Embedded macOS executable acceptance | Evidence / disposition |
|---|---|---|---|---|---|
| `PX-01` | `Расшифровка` is the peer tab; speaker label, timestamp and text keep deterministic reading order. Switching tabs preserves player time and play/pause state. | Tab follows the two-tab arrow/Home/End model; transcript landmarks, speaker labels and timestamp buttons have useful names and order. | Select with pointer and keyboard; assert selected tab/panel, unchanged `currentTime`/paused state and no model/generation request. | Run the same route assertions in the shared WebView test; native Record/Stop and shell shortcuts remain untouched. | `KRP-183-08`, `09` · reproduce |
| `PX-02` | Ready audio exposes bounded backward-step, one play/pause and bounded forward-step controls in that order. One activation changes time/state once; tab/type changes do not restart playback. Preparing, unavailable, error, access-loss and deleting never fake transport. | Each button has a visible/focused text alternative; Enter/Space invokes once; Play/Pause changes its accessible action and announces state once. No undocumented global shortcut is required. | Prove backward clamp, paused→playing→paused, forward clamp, one command per activation and clock advance only while playing. Step size is one versioned GRAF media constant and is included in the accessible name; it is not guessed from an unlabeled reference icon. | Assert the same media state through the WebView boundary and that the bridge neither duplicates nor consumes focused activation. | `KRP-183-09`, `KRP-183-C06`; reference icons are visible but unlabeled · reproduce with accessible GRAF semantics |
| `PX-03` | Timeline scrub and evidence timestamp seek use one bounded seek path. Seek never starts playback implicitly and clamps to available duration. | Slider exposes min/max/current value and human-readable elapsed/total time; arrows adjust, Home/End reach bounds, and focus stays on the slider. | Pointer scrub plus keyboard seek update the fixture to the requested time within media tolerance, emit one seek, preserve paused/playing state and keep elapsed text synchronized. | The identical checks pass inside WebView; arrow keys reach the slider rather than the native shell. | `KRP-183-09`; source-jump target also appears in `02`, `07`–`09` · reproduce |
| `PX-04` | Speed control shows the current rate and changes only among the observed `0.75×`, `1×`, `1.25×`, `1.5×`, `2×` rates; selection persists across Notes/Transcript and evidence round-trips for the meeting. | Named menu button exposes selected rate; arrow navigation plus Enter/Space selects; Escape closes and restores trigger focus. | Iterate all five rates and assert visible label, `playbackRate`, menu selection and persistence without changing time or play state. | Repeat through the embedded route and prove the WebView bridge does not swallow menu keys. | `KRP-183-09`, repeat frame `14`, `KRP-183-C07` · reproduce |
| `PX-05` | Speaker rows and timeline lanes share stable speaker identity. GRAF's filter is explicitly non-destructive: it changes transcript/lane emphasis only, never source, time, current revision or media bytes; reset restores all speakers. | Each filter is a text-labelled pressed/unpressed control; speaker identity is not color-only; the lane list exposes name and share without reading every decorative mark. | Select one/multiple/reset filters and assert transcript/lane agreement, unchanged player time/state and zero generation/source mutation. | Repeat the same state assertions with VoiceOver names/states and keyboard-only operation in WebView. | `KRP-183-08`, `09` show lanes/filter affordances; exact reference effect unobserved · deviate to explicit GRAF semantics |
| `PX-06` | `audio_preparing` keeps transcript and eligible notes readable, shows one bounded preparing status and disables transport/seek/speed without pretending duration/progress. | Status is associated with the player and announced politely once; disabled controls expose a concise reason and are not focus traps. | Delayed-ready fixture starts in preparing, issues no play/seek command, then enables the same controls without focus theft or duplicate announcement. | Same transition and focus behavior in WebView; native capture state is not conflated with post-meeting audio preparation. | `KRP-183-08` · reproduce |
| `PX-07` | `audio_unavailable` removes unusable transport and gives a truthful bounded reason/next action while authorized transcript/notes remain usable; it never renders an empty timeline. | Reason is programmatically associated with the player region; reading can continue without traversing dead controls. | No-media fixture exposes unavailable state, zero media requests and the permitted transcript path. | Same state and no private path/identity leakage in embedded route. | Not captured in the 14 images · GRAF target-only deviation, no visual parity claim |
| `PX-08` | `audio_error` preserves transcript/notes and last stable player context. Retry appears only when the media contract says it is safe; access/deletion failures never expose retry or cached private detail. | Error is associated, announced once and followed by the safe action; retry keeps focus and cannot submit twice. | Failed-load and safe-retry fixtures prove one request, stable context and distinct terminal/access-loss behavior. | Same lifecycle through WebView, including navigation away/back and no duplicate native/web submission. | Not captured in the 14 images · GRAF target-only deviation, no visual parity claim |
| `PX-09` | Evidence jump pins outcome item/kind/segment, seeks without auto-play, and `Вернуться к итогам` restores type, result scroll, originating focus, time and play/pause state; refresh fallback follows the documented deterministic chain. | Timestamp names include time/category; return focuses the original control or deterministic fallback heading and announces fallback once. | Execute exact-item, refreshed-same-segment, section-fallback and no-current cases while asserting focus, scroll, time and play state. | Run identical route fixtures in WebView and prove native shell focus/shortcuts are restored after leaving the embedded surface. | `KRP-183-02`, `07`–`09`; round-trip behavior unobserved · reproduce with executable proof |
| `PX-10` | Browser and embedded routes project the same ready/preparing/unavailable/error/access/deleting state, transcript identity, duration, rate, speaker filters and persisted player context. Access loss clears private painted content before any next interaction. | Equivalent names, roles, states, focus order and live announcements; WebView adds no duplicate landmark or shortcut. | Serialize the authoritative fixture state and assert the rendered role/state snapshot plus media commands. | Feed the same fixture to the shared embedded test target and compare the allowed platform-only differences; any semantic/state mismatch fails. | Program acceptance · reproduce |
| `PX-11` | Closed ready-player control order is: transcript/list utility host, `Listen To` speaker filter, clip/trim host, timestamped comment, backward step, play/pause, forward step, follow/current-segment host, speed; then elapsed/total slider and speaker lanes. Only `Listen To` and comment behavior were black-box confirmed. GRAF renders an unconfirmed host only after an owner and executable behavior exist; otherwise it is absent, never an inert icon. | No unnamed button is legal. Every rendered control has an accessible name/state, logical Tab order, Enter/Space behavior, tooltip that is not the only label, visible focus and a deterministic return target; disabled clip/trim explains why. | Enumerate the exact rendered control list in ready/preparing/view-only/error/access-loss fixtures; activate each owned control once and prove the documented media/comment/filter effect, with zero request for absent hosts. | Run the identical inventory/command assertions in WebView and prove no native-shell collision or duplicate action. | `KRP-183-C06`, live accessibility pass; four reference icon buttons and two inline-editor actions lacked useful names, documented as reference defects · reproduce owned behavior / deviate from unnamed controls |

## Closed opaque control/state inventory

This inventory closes the observed 14-image baseline, 15-frame repeat and
11-image current-state set. Every row has one owner and
one disposition: `reproduce`, `deviate` or `out-of-scope`. A static frame does
not prove the interaction contract in the accessibility column; those clauses
are executable requirements. Rows marked “not captured” are included only to
close a named program state and carry no reference-fidelity claim.

| Opaque evidence | Observed control/state | Owner | GRAF behavior/states | Accessibility / executable acceptance | Disposition |
|---|---|---|---|---|---|
| `KRP-183-01`, `12`–`14`; `KRP-183-C02`, `C08` | Workspace/account switcher, plan badge, profile, invite/reactivate/upgrade controls | Existing account/billing/workspace owners outside 183–211 | Preserve current GRAF account and billing truth; Feature 196 creates no copied plan, invite or reactivation action. | Existing controls keep names, state and keyboard order; no inert copied CTA. | out-of-scope |
| `KRP-183-01`, `03`, `07`–`09`, `12`–`14` | Primary `Search` and `My Meetings` navigation | Feature 196 | Canonical list/search routes, selected state, loading and access-safe failure. | `nav` landmark, current-page state, text labels, visible focus and 390px collapse without losing access. | reproduce |
| `KRP-183-01`, `03`, `07`–`09`, `12`–`14` | `Shared with me` navigation | Feature 203 | Expose only after an authorized share projection exists; never imply shared content through an empty copied route. | Current/unavailable state is named and does not leak inaccessible meeting existence. | deviate |
| `KRP-183-01`, `03`, `07`–`09`, `12`–`14` | `Action Items` navigation | Feature 206 over Feature 205 | Canonical cross-meeting projection with truthful unavailable/paywall/empty/error states; no second extraction. | Current-page state, keyboard/VoiceOver, 390px/200% and exact source return. | reproduce |
| `KRP-183-01`, `03`, `07`–`09`, `12`–`14`; `KRP-183-C02`–`C11` | Activity, Contacts, folder/teamspace creation and developer links | Existing/future owners outside the 183–211 summary program | Do not add dead destinations to achieve visual parity. | Any existing destination retains its own accessibility contract. | out-of-scope |
| `KRP-183-04`, `KRP-183-05`, `KRP-183-06` | Settings navigation and selected Templates route | Features 198–199 | Built-in and personal catalog routes with deterministic selected state. | Landmark/list semantics, text labels and visible focus; route selection announced. | reproduce |
| `KRP-183-02`–`04`, `07`–`09`; `KRP-183-C03`–`C07`, `C09`–`C11` | Header `Connect` and Settings `Integrations` entry/badge | Separate integration owner outside 183–211 | No active or badged integration control until GRAF has an authorized capability and lifecycle. | Hidden rather than focusable-dead; later capability needs named status/error. | out-of-scope |
| `KRP-183-01`, `12`–`14` | Native side rail for capture/noise/device controls | Existing macOS capture/noise shell | Remains native and outside the server-owned post-meeting workspace; Feature 196 must not duplicate or intercept it. | Native labels, state, focus and one-action Stop remain independently testable. | out-of-scope |
| `KRP-183-01`, `12`–`14` | Trial/paywall banner and upgrade CTA | Commercial policy owner plus Feature 196 unavailable-state presentation | Use truthful GRAF plan/policy copy and capability reason; do not copy Krisp plan language or artwork. | Banner is a named region, CTA is keyboard reachable, and dismissal/timing never blocks meeting access. | deviate |
| `KRP-183-01`, `12`–`14` | Upcoming block, meeting history rows and row metadata/status icons | Feature 196 | Stable meeting identity, readiness, duration/participants/date, pagination and access-safe empty/loading/error states. | List/table semantics as appropriate; icon status has text; duplicate titles have non-private disambiguation. | reproduce |
| `KRP-183-01`, `12`, `13` | Later/bookmark toolbar control | Feature 196 | Reversible add/remove from Later without changing meeting content or identity. | Text-labelled toggle with pressed state, visible focus and stable row focus after mutation. | reproduce |
| `KRP-183-01`, `12`, `13` | `New` toolbar control | Existing capture/upload owner outside Feature 196 | Feature 196 does not wire a copied creation action; show only when an existing GRAF command and truthful lifecycle are available. | Absent rather than focusable-dead until owned. | out-of-scope |
| `KRP-183-12` | Filter menu and seven visible facet entries | Feature 196 | Star/date/contains/company/type/tags/folders; AND between facets, OR within one facet; applied count/clear and deterministic results. | Named menu/dialog, logical focus, selected values not color-only, Escape/close restores trigger. | reproduce |
| `KRP-183-13` | Sort field and direction menus | Feature 196 | Date/duration/last-modified plus newest/oldest and stable meeting-ID tie-break. | Two labelled radio groups or equivalent; current values announced; no focus loss on apply. | reproduce |
| `KRP-183-14` | Search dialog, search field, visible Escape affordance | Feature 196 | Opens from Search/`⌘K`, autofocuses the query, keeps background inert, closes on Escape and restores the exact invoker. | Accessible dialog name, initial focus, logical trap, close semantics and no WebView shortcut conflict. Static evidence proves only the visible shell. | reproduce |
| `KRP-183-14` | Recent-search rows, history icons and per-row remove buttons | Feature 196 | Activate reruns only that permitted query; remove deletes only that recent entry; empty recent state is truthful. | Each remove button names its row without exposing hidden content; after removal focus moves to the next row, previous row or field. | reproduce |
| Not captured in `KRP-183-01`–`14` | Search loading, results, no-results, stale-result and access-loss states | Feature 196 | Delayed progress, exact canonical meeting result, duplicate-title disambiguation and fail-closed access loss; no nearest-title fallback. | Results use listbox/list semantics, active result is announced, status is polite and close restores the invoker. | deviate |
| `KRP-183-02`, `03`, `07`–`09` | Back, meeting title/date/participant metadata and small metadata actions | Feature 196 | One canonical meeting identity and authorized metadata only; cached private labels clear on access loss/deletion. | Header hierarchy, text alternatives for icon actions, deterministic back focus/route. | reproduce |
| `KRP-183-02`, `03`, `07`–`09` | Meeting-header Share host | Feature 196 host; Feature 203 capability | Always positioned for an accessible meeting, disabled with reason until authorized; hidden on access loss/deleting/no-existence-leak. | Named button, programmatic disabled reason, stable focus; no fake pending. | reproduce |
| `KRP-183-10`, `KRP-183-11` | Share dialog, invite field/action, participant row, link scope, permissions, copy link and close | Feature 203 | Pin displayed type/revision/language; policy exposes only supported scopes/capabilities and complete pending/ambiguous/success/failure lifecycle. | Labelled title/description, initial/logical/trapped/restored focus, grouped scope/permission semantics, Escape/close and 390px/200% reflow. | deviate |
| `KRP-183-02`, `03`, `05`–`09` | Header/template overflow triggers | Feature 196/198/199 plus each command owner | Render only when at least one authorized GRAF action exists. Menu contents and behavior were not captured; no inert ellipsis. | Named menu button, menu roles, disabled reasons, Escape and trigger-focus restore. | deviate |
| `KRP-183-02`, `03`, `07`–`09` | Split AI Notes/type button/Transcript strip | Feature 196 | Separate tabs and menu button; exact selected type/state; no type/content mismatch or implicit inference on ready switch. | Executable tab/menu keyboard model, separate focus stops, named selected/busy/error states. | reproduce |
| `KRP-183-02`, `03`, `07`–`09`; `KRP-183-C03`–`C07`, `C09`–`C11` | Copy and compact transcript-language control | Feature 196; Feature 197 owns regeneration command | Copy follows the active tab: exact painted outcome on AI Notes, exact authorized current transcript revision on Transcript; it never copies hidden notes. Language selection starts nothing and explicit Regenerate follows the source contract. | Exact action/layer names include active content kind; disabled reasons, menu/popover focus restore and one status announcement. | reproduce |
| `KRP-183-02`, `03` | Action checkbox, due-date and assignee controls | Feature 205 state/commands; Feature 196 composition | Read-only evidence-backed rows before Feature 205; afterward one canonical idempotent edit path with conflict recovery. | Keyboard-only edit, text labels, busy/error state, target size and focus preservation. | reproduce |
| `KRP-183-02`, `07`–`09` | Notes/transcript evidence timestamps | Feature 196 | Exact canonical seek and deterministic return; no implicit play. | Descriptive time/category name and `PX-03`/`PX-09` acceptance. | reproduce |
| `KRP-183-03`, `KRP-183-07`–`KRP-183-09`; `KRP-183-C03`–`C07`, `C09`–`C11` | Persistent contextual reformat banner, CTA and dismiss control | Feature 196 presentation; 198 catalog; 195 runtime | Required for ready Auto when Meeting Minutes is available and unsaved, unless dismissed for the exact user+meeting+target-template-version. Paint is deterministic and creates no call; `Try it out` is the one ensure+selection intent. It never displaces status/error. | Banner/status relation, named CTA/close, focus remains stable; dismissal persistence and target-version reset are executable. | reproduce |
| `KRP-183-03`; `KRP-183-C03` | Initial `How were the:` section chooser and dismiss control | Feature 201 | Stage 1 selects Key Points or Action Items without a write; stage 2 creates/updates one optional exact-result+section five-point record with remove/error/conflict recovery; never approval or prompt promotion. | Two named chooser buttons, then a text-labelled radio group with arrow keys, scope label, saved/error association and focus preservation. | reproduce |
| `KRP-183-02`, `03`, `07`–`09`; repeat frames `01`, `06`, `08`–`14`; `KRP-183-C03`–`C07`, `C09`–`C11` | Bottom-right assistant host: `Summarize unresolved topics`, `Write down weekly recap`, `Ask anything...` | Feature 210 grounded meeting assistant | Keep absent until Feature 210. Then install one compact host with exactly those three states: idle composer; deterministic unresolved-question suggestion; eligible weekly-intent suggestion. Paint/open starts no call; suggestion activation or typed submit is one explicit pinned request with evidence and its own receipt/session lifecycle. | Before 210, absent. After 210, named input/suggestion, keyboard submission, busy/real-cancel/ambiguous/error, focus preservation and evidence navigation. | reproduce in Feature 210 |
| Repeat frame `12`; `KRP-183-C10`, `C11` | Inline selection toolbar and block handle: bold/italic/underline/strike, left/center/right alignment, colors, nest/unnest, link and comment/block actions; block context menu color/copy/duplicate/comment/delete | Feature 209 editable meeting-note document | Generated `outcome_set_id` remains immutable. Feature 209 creates a separately versioned human-editable document with stable block IDs/provenance and reproduces only identified commands it can persist safely. Selection, block order and formatting autosave; offline/conflict/error never loses the last acknowledged document; undo restores the exact prior version. Two unlabeled Krisp buttons are evidence of an accessibility defect, not names to copy. | Complete named toolbar/menu/handle, toggle/disabled/selection states, keyboard shortcuts and menu keys, focus restore, autosave/pending/saved/error, expected-version recovery, undo and described destructive action. | reproduce in Feature 209 |
| Repeat frame `08` | Transcript-row hover edit/delete controls | Feature 211 transcript correction revisions | Keep absent until Feature 211 owns non-destructive transcript revision, authorization, audit and summary invalidation. A correction creates a new canonical source revision and follows the same stale/fan-out boundary as an authorized source replacement; it never mutates accepted source bytes or an old summary in place. | Controls are named and keyboard-reachable without hover; edit has expected-version conflict recovery; destructive exclusion is confirmed, reversible/audited as specified and cannot leave stale private paint. | reproduce in Feature 211 |
| `KRP-183-04` | Template cards, new-template card, default/view-only badges and card overflow | Feature 198 built-ins; Feature 199 personal lifecycle | Deterministic catalog; built-ins immutable; personal duplicate/default/delete/version rules; rights/provenance gate on visible material. | Card/action names, badge meaning not color-only, keyboard menu and stable order/reflow. | reproduce |
| `KRP-183-05`, `06` | Template breadcrumb/header, origin/view-only state, overflow and section preview | Features 198–199 | Explain purpose/sections/exclusions without generating; only authorized commands appear. | Heading hierarchy, breadcrumb, read-only status and menu-focus restore. | reproduce |
| `KRP-183-08`, `09` | Transcript speaker rows, timestamps and colored identity marks | Feature 196 over existing transcript runtime | Stable speaker identity and canonical timestamps; no content/source mutation from presentation controls. | Speaker name is text, color is supplemental, timestamps are operable, reading order is deterministic. | reproduce |
| `KRP-183-08` | Player `Preparing audio recording` state and visible speaker lanes | Existing playback runtime; Feature 196 parity | `PX-06`: transcript remains usable, transport is unavailable truthfully and readiness transition cannot steal focus. | Polite associated status and no focusable dead controls. | reproduce |
| `KRP-183-09`; repeat frame `14` | Ready transport, scrubber, speed and speaker lanes | Existing playback runtime; Feature 196 parity | `PX-02`–`PX-04`: one media state, bounded seek, the observed `0.75×`, `1×`, `1.25×`, `1.5×`, `2×` rate set and stable speaker-lane identity. | Named controls, slider/menu semantics, visible focus, non-color speaker identity and WebView parity. | reproduce |
| `KRP-183-09` | Speaker filter affordances | Feature 196 | `PX-05`: explicit non-destructive GRAF filter semantics; exact Krisp effect remains unproven and is not inferred from the frame. | Text-labelled pressed state, keyboard/VoiceOver operation, reset and no color-only meaning. | deviate |
| Not captured in `KRP-183-01`–`14` | Player unavailable/error/access-loss/deleting states | Existing playback/access runtime; Feature 196 parity | `PX-07`, `PX-08`, `PX-10`; preserve authorized text context, expose only safe recovery and clear private paint on access loss. | Associated status/error, no repeated announcement, no dead transport and deterministic focus. | deviate |

## Current GRAF baseline observed on synthetic fixtures

Read-only browser audit on 2026-08-23 confirmed the current interaction gap that Features 183 and 196 must close:

- the format picker names types but does not distinguish saved, missing, generating, failed or stale results before selection;
- `Обновить итоги` does not explain that the current same-type result will remain safe while a replacement is prepared;
- a ready short synthetic meeting renders several repeated empty categories as the main result instead of one concise no-useful-content state;
- the deferred state says that generation was postponed by policy but does not give a user-meaningful next step;
- transcript/player remain available, which is a useful continuity pattern to preserve.

Synthetic-only screenshots remain in a non-versioned local evidence bundle.
The installed-reference screenshots and metadata-only notes are kept separately.
They may guide implementation locally but are never committed, published or
shipped as assets.

## Target information architecture

```text
Встречи
└── Встреча
    ├── Header: title / participants / Share / overflow
    ├── Primary strip
    │   ├── Split AI Notes / Итоги tab + type-menu button
    │   ├── Transcript / Расшифровка tab
    │   ├── Copy exact displayed revision
    │   └── Transcript language `RU` / explicit Regenerate
    ├── Итоги
    │   ├── Type switcher
    │   │   ├── Saved types
    │   │   ├── Select missing type → ensure once
    │   │   └── All types
    │   ├── Current type result
    │   │   ├── Selected type's contract sections
    │   │   ├── Auto: Action Items
    │   │   ├── Auto: Key Points
    │   │   └── Evidence links
    │   ├── Editable note document / comments (Feature 209)
    │   └── Update current type
    ├── Grounded meeting assistant (Feature 210)
    └── Расшифровка + persistent player
        └── Transcript correction revisions (Feature 211)

Поиск встреч
├── Recent
├── Search results / no results / loading
└── Exact meeting open

Форматы итогов
├── Built-in catalog
├── Type details
└── Personal formats
    ├── Create from blocks
    ├── Edit/version
    ├── Set default
    └── Delete
```

## Executable top-control contract

The visible composition follows Krisp exactly where observed, but each target has
one unambiguous product responsibility:

- The `Итоги`/`AI Notes` main segment and `Расшифровка`/`Transcript` are tabs.
  Left/Right and Home/End move only between those two tabs. The adjacent type
  icon+chevron is not part of arrow-tab movement; it is a separate Tab stop and
  menu button. Enter/Space/ArrowDown opens the type menu, arrows move rows,
  Enter/Space selects, and Escape closes and restores focus without selection.
- The type button's accessible name includes the exact selected type and state,
  even when the literal Krisp-faithful visual surface shows only icon+chevron.
  Menu selection never changes the main tab away from `Итоги`.
- Copy reads the exact currently painted, authorized `outcome_set_id`; the
  clipboard payload and success announcement remain bound to that revision even
  if background refresh finishes first. It never copies a candidate, a hidden
  newer revision or another type.
- The single observed `RU` control is always `Язык расшифровки`, including while
  the `Итоги` tab is active. It opens `Transcribe in correct language`, selection
  alone starts nothing, and explicit `Regenerate` is enabled only after a valid
  change. The popover warns `Regeneration might take up to 30 min.` and never
  emits a summary `ensure`/`refresh` event. Notes output-language policy, if
  later exposed by Feature 198, lives outside this reference control.
- Share freezes the displayed type/revision/language when its dialog opens.
  Background completion may show `Доступна новая версия`, but cannot retarget the
  open dialog. Closing and reopening is the only way to choose the newer current
  revision. For every accessible meeting, Feature 196 owns the
  reference-faithful always-present header host: it is disabled with a concise
  reason until Feature 203 supplies the capability or while policy blocks it,
  and is hidden only for access-loss/deleting/no-existence-leak states. The
  action, dialog, command and full lifecycle do not exist until Feature 203.
- The contextual reformat suggestion is required exactly when Auto is ready,
  Meeting Minutes is available and that meeting has no saved result for the
  target template version. Dismissal is scoped to the exact
  user+meeting+target-template-version, so a later target version may be offered
  once. Paint performs no inference; `Try it out` is one idempotent
  ensure+selection intent. The banner cannot displace status/error copy.

The Share column below is the complete-program Feature 203 contract. Feature 196
implements only the column's placement and capability-driven unavailable state;
it cannot synthesize any pending/success/failure behavior before Feature 203.

Selecting a missing type is the one explicit generation intent and immediately
starts one idempotent `ensure`; there is no second `Generate` confirmation.
`Refresh` exists only for a ready type. A retry appears only when a terminal
attempt has typed `next_action=retry_safe` and derived `retryable=true`. Active
work coalesces on the exact meeting/type/source/root/control dispatch identity,
so selection, reload or another device creates no duplicate inference.

For every ready row below, Refresh is in the right action cluster immediately
left of Copy. Updating/blocked/deferred/ambiguous keeps that physical slot
busy/disabled so controls do not jump. Every missing-type row omits Refresh;
typed wait, safe retry or transcript recovery appears only in the status panel.

| Result state | Type button | Refresh / retry | Copy | Share |
|---|---|---|---|---|
| Ready | enabled; selected check; selection performs no inference | `Refresh` enabled only with refresh permission and ready source; one click starts same-type replacement without confirmation; otherwise disabled with reason | enabled for displayed revision | host always visible; enabled for displayed revision only when Feature 203/policy allows, otherwise disabled with reason |
| Same type updating | enabled; `Обновляем` status | busy and disabled; exact owned attempt is coalesced and its typed `next_action` is shown | enabled for old displayed revision | enabled for old displayed revision when Feature 203/policy allows; dialog pins it |
| Ready + refresh blocked/deferred | enabled; old result stays primary and bounded dependency/capacity status follows typed `next_action` | disabled while the owned attempt is non-terminal; named wait/recovery action; no retry or duplicate | enabled for old displayed revision | visible; enabled for the old revision when its own source/access/deletion policy remains valid, otherwise disabled with reason |
| Ready + refresh ambiguous | enabled; old result stays primary, status says to wait and never offers unsafe retry | disabled, wait-only until authoritative terminal proof | enabled for old displayed revision | visible; enabled for the old revision when eligible and any open dialog remains pinned |
| Ready + newer attempt `no_supported_content` | enabled; old result remains current with a calm type-scoped notice | retry only after a new eligible source/profile condition and typed safe-retry action | enabled for old displayed revision | visible; enabled for the old displayed revision when eligible; the empty attempt never replaces it |
| Missing type preparing/no result | enabled to switch away; selection already started one coalesced ensure | no separate action; reload/device joins the exact attempt | disabled with named reason | visible and disabled: no published revision exists |
| Missing type blocked/deferred | enabled to switch away; exact wait/recovery status | disabled with named dependency/capacity reason and typed `next_action`; duplicate ensure blocked | disabled | visible and disabled: no artifact exists to pin |
| Missing type ambiguous | enabled to switch away; wait-only status | disabled until reconciliation proves a safe terminal state | disabled | visible and disabled; no candidate/latest fallback |
| Missing type `no_supported_content` | enabled; type-scoped empty state and only declared switch/transcript recovery | `Повторить` only after source/profile eligibility changes and typed safe-retry | disabled | visible and disabled; another saved type is never shared as this type |
| Failed update with old result | enabled; bounded error badge | `Refresh` returns only for terminal safe-retry; otherwise disabled with exact reason/action | enabled for old displayed revision | visible; enabled for old displayed revision when eligible |
| Failed missing type | failed row plus safe retry only when proven | `Повторить` only for terminal `next_action=retry_safe` and `retryable=true` | disabled for failed type | visible and disabled for failed type |
| Source stale | enabled; stale state visible | disabled until current source is ready, then exact-source replacement intents coalesce per saved active type | disabled as new egress | visible and disabled for new artifact; existing pinned artifacts unchanged |
| Retired type with saved result | read-only selected row | absent or disabled with `Формат больше недоступен`; no ensure/refresh | enabled only when policy permits historical copy | visible and disabled for every new artifact; previously created pinned artifacts remain unchanged and separately access-controlled |
| Access lost / deleting | no private labels or cached content | hidden/disabled; no request is sent | disabled and clipboard unchanged | hidden; any open dialog fails closed and clears private details |
| Feature/policy unavailable | visible disabled control with concise reason | disabled/absent with plan, permission or policy reason; never fake pending or retry | depends only on readable exact result | visible and disabled with plan/policy reason |

Transcript language is orthogonal to every result row above:

| Transcript/source state | `RU` behavior |
|---|---|
| Ready and editable | visible; opens `Transcribe in correct language`; `Regenerate` stays disabled until a valid different language is selected |
| Ready and view-only | visible read-only language label; no regeneration command |
| Regenerating | visible busy/disabled with the up-to-30-minute impact; old transcript-backed results remain readable until source replacement |
| Successful source replacement | every active saved old-source type becomes stale; one bounded coalesced replacement intent per active saved available type, default/current first; unsaved and retired types are not generated |
| Transcript failed | visible only when the typed recovery permits language correction or safe transcript retry; summary controls remain unavailable without source |
| Access lost / deleting | hidden or fail-closed without private source/language leakage |

Hover, pressed, focus-visible, selected, disabled, busy and error appearance must
be captured side by side against the reference at desktop width and reflowed at
390px/200%. Async completion never moves focus, changes tabs, opens a menu,
copies, shares or announces more than once.

## Interaction states

| State | What remains primary | Background/status | Main action |
|---|---|---|---|
| Default type preparing, no result yet | Transcript/player | «Итоги готовятся» | Continue using meeting |
| Saved type ready | Saved result | None | Read/use/share |
| Missing type generating | Honest empty/preparing state for that selected type | Progress on target type; other saved types remain one switch away | Return to saved type or continue with transcript |
| Same type updating | Old current revision | «Обновляем» | Continue reading |
| Update failed/invalid | Old current revision | «Предыдущая версия сохранена»; safe recovery is automatic | Continue reading or switch type |
| Missing type failed with a prior ready type | Prior ready type is restored without changing its revision only if the failed request still owns the latest presentation intent; newer intent remains untouched | «Не удалось создать выбранный формат · текущие итоги сохранены» | Continue reading; explicit retry only when safe |
| Missing type failed without any ready type | Transcript/player | Calm type-scoped failure and safe retry/background recovery | Continue with transcript |
| Source changed | Old revision labelled from earlier source if still allowed | New generation scheduled/available | Open latest transcript |
| No useful source content | Single honest meeting-level state | Why no result | Open transcript |
| Selected type has no supported content | The selected type stays selected; its own type-scoped empty state is primary, or Transcript/player is primary when the typed recovery contract explicitly chooses it | Other ready types remain switch targets only; none is painted as the selected type | Switch type/open transcript |
| External AI outage | All saved types remain usable | «Итоги временно недоступны · обновим позже» | No destructive action |
| Failed transcript | Recording/player if available | Language/source recovery; summary actions unavailable | Correct language or retry transcript only when valid |
| Search/list loading | Stable frame or previous result set | Delayed progress after 300 ms; no flicker or duplicate navigation | Continue/clear query |
| Type generation longer than 5 s | Previous ready result or stable preparing state | Explain that work continues in background; completion is announced once | Leave the page safely |
| Type unavailable/paywalled | Other saved types | Reason and scope; no fake generation | Choose an available type |
| Retired custom type with a saved result | Read-only saved result | `Формат удалён`; generation/update/default controls absent | Read/copy permitted by access policy; choose/duplicate an available type for future generation |
| Retired custom type without a saved result | Transcript/player or last ready type | `absent + retired`; no generation and no substitution under the retired name | Choose/duplicate an available type |
| Meeting deleting/access lost | No cached private content | Truthful access/deletion state | Leave meeting |

## Interaction timing and duplicate-action contract

- Selecting a saved ready type changes presentation immediately and creates zero generation intents/model calls. Selecting a missing available type creates exactly one idempotent `ensure`. Clicking the explicit ready-only `Refresh` creates exactly one same-type refresh intent. No other select/read action may infer.
- Do not flash a spinner for operations completed within 300 ms. After 300 ms show a stable type-scoped preparing state; after 5 s explain that work continues in the background.
- Repeated clicks while the same intent is active are coalesced and do not create another model call, toast stack or navigation.
- Navigating away does not cancel a durable generation. Do not offer a Cancel button unless cancellation is real, durable and cannot leave ambiguous provider egress.
- Reload/close while a missing type prepares does not create a second intent. On return, the last successful type is primary and the preparing type remains visible in availability/status; if no successful type exists or an explicit deep link requests the preparing type, its honest preparing state is primary.
- Async completion never steals focus, resets scroll or starts playback. It produces one bounded live announcement.
- Every visible type selection increments a presentation-intent version. A later background success may make its type available but cannot change the visible or remembered type after a newer selection/navigation. Failure auto-restore runs only while the failed request still owns the current intent; otherwise it reports status without moving the user.

## Program route and persistence matrix

Feature 196 owns meeting/list/type/evidence presentation parity and always renders the inert, accessible Share header host for every accessible meeting. Feature 203 later supplies that existing host with share commands/dialog/lifecycle states, and Feature 205 supplies mutable action commands; neither downstream owner is required for Feature 196 to render the truthful disabled host.

| Behavior | Browser cabinet | Embedded macOS cabinet |
|---|---|---|
| Open meeting from list/search | Same canonical meeting route and access checks | Same server-owned route inside the native shell |
| Last AI Notes/Transcript view | Per user+meeting; reload-safe | Same value after closing/reopening the embedded surface |
| Last successful summary type | Per user+meeting; failures do not overwrite it | Same contract; no device-global mutation |
| Evidence jump/return | Restore type, result scroll, focus and player position | Same, while native Record/Stop shell remains unaffected |
| Saved type switch | No inference and no dependency on LiteLLM/Langfuse/Temporal | Identical server response and visible state |
| Accessibility | Keyboard, focus, live region, 200% zoom, 390px | VoiceOver plus keyboard/focus; WebView bridge must not consume shortcuts unexpectedly |
| Action edits and share lifecycle | Same canonical commands, pending/error/success states and exact result identity | Identical commands and states; native shell must not duplicate or swallow submission |

## Reference-fidelity acceptance for Feature 196

Approval requires a side-by-side state-by-state review of navigation,
type-selector composition, content geometry, player, colors/tokens, typography,
icons, copy and interaction timing. The reviewer records reference screen/state,
measured fidelity and every deliberate deviation. First-glance difference is
not required. Private screenshots stay outside git; extracted assets do not
ship. Approved functional UI labels and interaction microcopy may match
literally. Every third-party asset, logo or trademark has documented rights or
an independently created substitute. Accessibility and truthful GRAF states
take precedence over copying a reference defect.

Every reference-derived visible element carries one closed release state:
`not_applicable | cleared | replacement_required | blocked`.
`not_applicable` means independently implemented GRAF material with no
third-party asset/content dependency; `cleared` points to the owner-controlled
rights evidence; `replacement_required` may remain in an internal comparison
build but cannot ship; `blocked` is absent from the release capability snapshot.
The state is server/release metadata, never inferred or downgraded by the UI.

## Program accessibility contract

Feature 196 owns the meeting/list/type/evidence requirements below. Feature 199 owns the keyboard alternative for personal-format reorder; Features 203/205 own accessibility of their share/action commands even when rendered in the Feature 196 workspace.

- Target WCAG 2.2 AA for the browser content and equivalent VoiceOver/keyboard operability in the embedded macOS surface.
- Real tabs/listbox/menu semantics: tabs use Left/Right (and Home/End), listboxes/menus use arrow navigation, Enter/Space selects, and Escape closes without committing.
- Focus returns to the invoker; async updates never steal focus. Evidence return restores the originating control when it still exists, otherwise the nearest current section heading.
- Non-urgent progress/success uses a deduplicated polite live region; actionable errors are associated with the affected control and are not announced repeatedly. No summary transition requires an assertive announcement.
- 390px and 200% zoom reflow to one column without horizontal scrolling.
- Text/essential UI contrast meets 4.5:1/3:1 as applicable; focus indicators meet WCAG 2.2 focus appearance expectations.
- Pointer targets are at least 24×24 CSS px with spacing; primary touch actions target 44×44 where layout permits.
- Status does not rely on color or motion; reduced-motion supported.
- Drag/reorder has keyboard alternative.
- Evidence controls have descriptive time/category labels.

## Governance decision resolved

Constitution 5.0.0 explicitly authorizes literal reproduction of observable
Krisp UX/UI/IA for Features 196 and 209–211. The remaining release gates are independent
implementation, accessibility, GRAF privacy/security/deletion truth, documented
deviations from known defects and usage rights/provenance for third-party
assets, logos and trademarks. Functional reference labels and interaction
microcopy may be reproduced literally.
