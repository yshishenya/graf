# Feature Specification: Automatic Meeting Detection And Record Prompt

**Feature Branch**: `codex/092-automatic-meeting-detection`

**Created**: 2026-07-08

**Status**: Implemented and released foundation; production target promotion and
live admin-browser receipt remain intentionally unclaimed

> Current ownership note (2026-07-23): Feature 092 remains the registry,
> detection, policy-gate, and target-scoped identity foundation. Feature
> `124-restore-automatic-recording` is the current owner of the restored macOS
> prompt UX and runtime wiring: `Автозапись` app list, per-target preference,
> eight-second countdown, automatic start on expiry, immediate start, skip, and
> `Всегда писать это приложение`. Do not replace those behaviors with a generic
> detect-only prompt during later 092/119 maintenance.

**Input**: User description: "091 занят. Давай 092. Новую функцию. Автоматическое
определение, что началась новая встреча, и предлагать ее записывать. Запись
должна подхватываться в приложениях видеоконференций и браузерах. Посмотри как
это реализовано в gilb-ai/gilb-recorder, изучи лучшие практики в сети, GitHub и
Krisp, используй субагентов, подготовь максимально подробную и продуманную
спецификацию, если останутся вопросы - задай их."

## Clarifications

### Session 2026-07-08

- Lane: high-risk product area. This feature touches recording start behavior,
  microphone/system-audio permissions, browser/app detection, tray/widget
  prompts, consent, diagnostics, privacy, and user-facing capture workflow.
- The requested feature number is `092`. `specs/092-*` was free in this
  worktree when this spec was created, but local git already had a separate
  worktree/branch named `codex/092-upload-list-progress`. This specification is
  created without switching branches so that existing local branch is not
  modified. Before planning/implementation, the team should either reserve a
  clean branch for this spec or confirm that reusing `092` with this directory
  is intended.
- This feature supersedes the detection scope of
  `011-assisted-auto-recording` for the current system-audio-first MVP. Feature
  `011` remains useful historical context for detect-and-ask, false-positive
  blocking, naming, and UI authority, but its virtual-device/routed-meeting
  assumptions are no longer the default MVP path after
  `025-system-audio-capture-pivot`.
- Default rollout is **detect-and-ask**, not hidden recording and not broad
  automatic recording. A detected meeting candidate may prompt the user to
  record only after hard gates pass. The first release may also offer an
  explicit prompt checkbox to always record future meetings from this same
  approved app/service, but that rule must be target-scoped, user-controlled,
  reversible in settings, and still gated by visible local capture and Stop.
- Manual `Record`, `Pause`, `Resume`, and `Stop` remain the trusted baseline.
  Meeting detection must help the user avoid missed recordings without making
  active capture invisible or harder to stop.
- Feature `060-calendar-context-ingestion` and
  `063-calendar-settings-ui` already define future calendar context, join
  prompts, at-start record prompts, overlapping-event handling, and the rule
  that calendar prompts do not auto-record. This feature expands from
  calendar-time prompts to real app/browser meeting-start detection.
- Browser detection must be treated as a first-class requirement, not a
  best-effort footnote. However, unsupported browsers, hidden tabs, missing
  adapter permissions, and unknown web meeting services must fail into manual
  recording or detect-only evidence rather than false claims.
- Product priority is the Russian market. The target registry must cover
  Russian VKS systems as first-class candidates, not merely global Zoom/Teams/
  Meet/Webex targets. Every known Russian target may still land in Tier A,
  Tier B, Tier C, or deferred after evidence, but it must be enumerated and
  visible in planning.

### Session 2026-07-08 User Clarifications

- First browser implementation strategy: use macOS browser metadata plus
  calendar/join intent. Do not require a browser extension for the first
  release; keep extension-based browser adapters as a future option.
- First release behavior: detect-and-ask remains the default interaction, but
  the prompt must include an optional checkbox to always record future meetings
  from this app/service automatically.
- Participant notice: do not add per-meeting product prompts, pasteable notice
  steps, calendar notice workflows, or blocking consent acknowledgement. The
  user is responsible for verbally warning meeting participants when needed.
- Default setting: meeting detection prompts are enabled by default, with a
  visible setting to turn detection off or change mode.
- Market coverage: Russian VKS products must be included alongside global
  conferencing products.
- Native/installed app MVP strategy: follow the Gilb approach first. For
  macOS apps, use passive RunningBoard/CoreAudio `AudioHAL` app ownership,
  an allowlist of approved meeting-app bundle IDs, and debounce as the primary
  app-activity detector. Do not require network, window-title, or Accessibility
  joined-state evidence for the first native app prompt path. If this produces
  unacceptable misses or false prompts, later
  planning may add those extra signals.

## Research Summary

### GRAF Product Baseline

- GRAF's MVP recording path is macOS system-audio-first: native microphone
  capture plus Screen/System Audio capture, not a required virtual audio driver.
- Active capture must always have a persistent local visible indicator and a
  one-action Stop path. No user/admin setting may hide active capture.
- Desktop clients must never send audio directly to MediaScribe and must never
  store MediaScribe credentials.
- Diagnostics and evidence are metadata-only by default and must not include
  raw audio, transcript text, meeting content, credentials, signed URLs,
  passwords, live secret paths, or private meeting content.
- Calendar feature `060` already provides current/upcoming event context,
  join prompts, record prompts, overlap handling, descriptive title policy, and
  safe fallback titles. It explicitly excludes auto-record.
- Meeting mute truth feature `022` already establishes product-owned
  `GRAF Pause` / `GRAF Stop` as the proven local privacy controls; third-party
  app mute remains unproven unless future target-specific adapters provide
  fresh evidence.

### gilb-ai/gilb-recorder

Sources inspected:

- https://github.com/gilb-ai/gilb-recorder
- `/tmp/gilb-recorder/crates/gilb-meeting/src/macos.rs`
- `/tmp/gilb-recorder/crates/gilb-meeting/src/allowlist.rs`
- `/tmp/gilb-recorder/crates/gilb-pipeline/src/lib.rs`
- `/tmp/gilb-recorder/docs/ui-design.md`

Useful clean-room findings:

- Gilb separates always-on accessibility activity tracking from event-driven
  meeting recording, with different vocabulary, indicators, and consent models.
  GRAF should similarly keep passive detection, prompt, and active recording
  visually distinct.
- On macOS, Gilb-style detection for GRAF means streaming Apple unified-log
  `AudioHAL` app-ownership changes, parsing bundle ownership, filtering by an
  allowlist of known meeting apps, and debouncing changes before emitting
  `Started`, `AppsChanged`, and `Ended`.
- For GRAF's first native/installed app implementation, this Gilb-style path is
  the intended MVP detector: `AudioHAL` ownership from an approved meeting app,
  after debounce and hard product gates, is enough to ask the user to record or
  honor a previously enabled target-scoped auto-record rule for that target.
- Gilb intentionally omits browsers from its native app allowlist because
  browsers create false positives from voice search and other in-page audio.
  For GRAF, browser meetings need a different path than "browser used mic".
- Gilb uses a start countdown prompt before arming recording and a stop
  countdown after apparent meeting end. That maps well to GRAF's
  detect-and-ask requirement, but GRAF should use its own native trust shell and
  Russian product copy.
- Gilb's broader activity tracking captures keystrokes, focus changes,
  clipboard, and accessibility tree data. That is out of scope for GRAF meeting
  detection and must not be copied as a general data collection model.

### Comparable Open-Source Projects

Sources inspected:

- https://github.com/Ayobamiu/meeting-detection
- https://github.com/Jarus77/meeting-status-py
- https://github.com/pasrom/meeting-transcriber
- https://github.com/yut0takagi/obsidian-meeting-detector
- https://github.com/screenappai/meeting-bot
- https://github.com/Leko/crx-gcal-url-opener
- https://github.com/recallai/chrome-recording-transcription-extension
- https://github.com/prokopsimek/chrome-extension-recording
- https://github.com/screenpipe/screenpipe
- https://github.com/qaid/meeting-minutes-autodetect
- https://github.com/Zackriya-Solutions/meetily/issues/387

Useful clean-room findings:

- `meeting-detection` uses a two-tier model: native meeting apps use
  process + active network connection signals; browser meetings use browser
  tab URLs and meeting URL validation. It treats mic/camera as supporting
  signals rather than the core decision. It requires Accessibility/AppleScript
  access for browser tab URLs and `lsof` for network observations.
- `meeting-detection` validates Google Meet codes and excludes non-meeting
  pages such as landing/new/join. This is an important false-positive pattern.
- `meeting-status-py` is a readable Python port of the same process/network/URL
  strategy. It is useful as pseudocode for detector state changes but should
  not drive production macOS architecture by itself.
- `meeting-transcriber` is a native Swift macOS analogue that combines
  `CGWindowListCopyWindowInfo` owner/title patterns, macOS power assertions,
  watch-loop confirmation counts, cooldowns, end grace periods, max-duration
  limits, and target-specific tests. It is strong evidence that window titles
  and power assertions can raise confidence, but also that Screen Recording and
  Accessibility permissions are product-visible costs.
- `meeting-transcriber` tests explicitly guard against idle/non-call power
  assertions such as generic Teams WebView wake locks. GRAF must treat power
  assertions as target-specific evidence, not as universal meeting truth.
- `obsidian-meeting-detector` uses simple process polling plus AppleScript tab
  URL/title checks and prompts the user with Start/Dismiss. It reinforces that
  prompt-and-dismiss is a reasonable low-risk shell, while process-only
  detection remains too weak for recording prompts without other evidence.
- Browser-extension recorders based on `chrome.tabCapture`, offscreen
  documents, MediaRecorder, and content scripts show a possible future browser
  helper path. They also confirm a browser helper is Chrome-family limited,
  permission-heavy, and separate from native app detection.
- `screenpipe` meeting-watcher work and issue evidence show that visible
  meeting controls disappearing is not reliable proof that a meeting ended:
  controls can vanish when switching tabs, minimizing native apps, changing
  Spaces, sharing screen, or when floating toolbars replace normal controls.
- Calendar URL opener extensions show how to extract meeting intent from
  Google Calendar conference data, descriptions, and known URL patterns while
  ignoring declined/cancelled events. This is useful context only; calendar
  intent is not live joined-state evidence.
- `meeting-minutes-autodetect` exposes settings for enable/disable, auto-start,
  auto-stop, notifications, and per-app detection. It uses process monitoring
  for Zoom/Teams and documents Google Meet/browser support as limited. This is
  useful as a lightweight MVP reference but too weak for GRAF's privacy gates.
- The upstream Meetily issue requesting auto detection explicitly calls
  process-name-only monitoring "privacy-preserving", but also asks for fully
  automatic recording. GRAF must be stricter: process names alone can create
  evidence, not a recording prompt.

Practical signal guidance from comparables:

- Native Zoom/Teams/Webex and Russian installed clients should first use the
  Gilb-style target-specific bundle allowlist plus stable macOS `AudioHAL`
  ownership. Known network, window, power-assertion, and Accessibility signals
  are Phase 2 improvement candidates, not first-release blockers.
- The first Gilb-style app detector may prompt for some prejoin/device-test
  situations when an allowlisted app legitimately opens the microphone. That is
  acceptable for the first detect-and-ask rollout because recording still needs
  user confirmation or a prior target-scoped auto-record preference; evidence
  and Skip/Stop suppression must make these cases easy to improve later.
- Browser Google Meet should require validated `meet.google.com` meeting-code
  pages and exclude landing/new/join/settings pages. A URL alone is not enough
  unless paired with joined-state, live activity, or explicit user join intent.
- Browser Zoom/Teams/Webex/Telemost should use service-specific URL patterns
  and active tab/joined-state evidence. Generic browser network activity and
  generic WebRTC activity are too noisy.
- Auto-stop assistance must use a grace period and multiple end signals. It
  must not stop recording merely because a Leave button, tab, window, or
  participant control is no longer visible.

### Krisp Public Behavior

Sources inspected:

- https://krisp.ai/meeting-recording/
- https://krisp.ai/ai-note-taker/
- https://help.krisp.ai/hc/en-us/articles/8214720684956-AI-Meeting-Assistant-overview
- https://help.krisp.ai/hc/en-us/articles/4420114943132-Set-up-Zoom-with-Krisp
- https://help.krisp.ai/hc/en-us/articles/4420146557340-Set-up-Google-Meet-with-Krisp
- https://help.krisp.ai/hc/en-us/articles/4420152310940-Set-up-Microsoft-Teams-with-Krisp
- https://help.krisp.ai/hc/en-us/articles/4420150708380-Set-up-browsers-with-Krisp
- https://help.krisp.ai/hc/en-us/articles/10277892556828-Connecting-your-Calendar-to-Krisp
- https://help.krisp.ai/hc/en-us/articles/10386573495196-Sharing-your-meetings-with-Krisp
- https://help.krisp.ai/hc/en-us/articles/11734566901788-Recording-your-meetings-with-Krisp
- https://help.krisp.ai/hc/en-us/articles/16168004763420-Screen-record-your-meetings-with-Krisp
- https://help.krisp.ai/hc/en-us/articles/8326933081116-AI-Meeting-Assistant-FAQ

Confirmed public facts:

- Krisp markets meeting recording/note taking as bot-free and broadly
  compatible with conferencing apps including Zoom, Google Meet, and Teams.
- Krisp setup guidance relies on selecting Krisp virtual microphone and speaker
  in communication apps. Public docs say missing speaker setup can capture only
  the user's speech, not other participants.
- During calls, Krisp surfaces app/browser usage states such as the app being
  used by Zoom, Teams, Chrome, or another app/browser. This implies a
  virtual-device/activity-centered detection model, but the exact private
  implementation is not public.
- Browser support varies by browser and web-app capability. Safari and Firefox
  have meaningful limitations, especially around virtual speaker selection.
- Krisp uses calendar connection for scheduled/upcoming/past meetings, join
  affordances, menu-bar countdowns, event naming, participant context, and
  auto-share behavior.
- Krisp recording and screen recording controls remain user-facing. Screen
  recording requires explicit OS permission and scope selection.

Clean-room conclusion:

- GRAF should not copy Krisp UI, copy, private behavior, or virtual-driver
  dependence. The useful pattern is product-level: combine app/device activity,
  calendar context, visible controls, and user/admin settings, and remain honest
  when browser/app support is incomplete.

### Platform And Browser Constraints

Sources inspected:

- Apple ScreenCaptureKit overview:
  https://developer.apple.com/documentation/screencapturekit/
- Apple microphone privacy indicator:
  https://support.apple.com/guide/mac-help/control-access-to-the-microphone-on-mac-mchla1b1e1fe/mac
- Recall.ai on macOS capture APIs:
  https://www.recall.ai/blog/macos-screencapture-api
- Recall.ai on Chrome `tabCapture`:
  https://www.recall.ai/blog/how-to-build-a-chrome-recording-extension
- MuteDeck troubleshooting:
  https://mutedeck.com/help/troubleshooting/app-not-detecting/
- Google Meet REST API:
  https://developers.google.com/workspace/meet/api/guides/overview

Findings:

- ScreenCaptureKit captures screen/window/app content and system audio, but it
  does not provide built-in meeting detection. GRAF needs a separate detector
  layer above capture.
- macOS visibly indicates microphone use in Control Center, but public Apple
  docs do not expose a stable meeting-detection API. Unified-log audio ownership
  is a useful but brittle signal and must be treated as adapter evidence with
  health/fallback behavior.
- Chrome extensions can capture a specific tab through `chrome.tabCapture` only
  inside Chrome's extension security model and generally require user gesture
  for microphone/tab capture. Browser extensions can help detect in-meeting DOM
  state, but they are browser-limited and must not be assumed for Safari,
  Firefox, or native apps.
- Chrome tab "audible" signals can be unreliable for WebRTC meetings and should
  not be the sole browser meeting detector.
- Products that control meeting app UI state often require Accessibility,
  browser extensions, visible meeting controls, supported app language, and
  per-app troubleshooting. GRAF should expose adapter health and limitations.
- Google Meet REST APIs can provide meeting spaces, participant/session
  metadata, and events for authorized Workspace contexts. They are not a
  universal local detector for arbitrary browser meetings and should be treated
  as a future rich-provider adapter, not a baseline local signal.

### Russian VKS Market Coverage

Sources inspected:

- https://www.tadviser.ru/index.php/Статья:Крупнейшие_поставщики_систем_видеоконференцсвязи_(ВКС)_в_России
- https://soware.ru/categories/video-conferencing-systems/made-in-rus
- https://catalog.arppsoft.ru/replacement/section_6050213
- https://ucaas.cnews.ru/news/top/2024-06-11_liderom_sredi_vks-servisov
- https://habr.com/ru/news/923634/
- https://kontur.ru/talk/spravka/55579-rossiyskie_servisy_dlya_videokonferenciy

Findings:

- Russian VKS coverage must be treated as a core product requirement for GRAF,
  not a localization afterthought. Public market lists and Russian software
  catalogs repeatedly surface IVA, TrueConf, VK, MTS Link, Yandex Telemost,
  Kontur.Talk, VideoMost, VINTEO, Dion, Pruffme, eXpress, SaluteJazz/Jazz, and
  several enterprise/on-prem products.
- TAdviser market coverage highlights IVA Technologies, TrueConf, and VK Tech
  among leading Russian VKS vendors. Habr/CNews reporting highlights adoption
  and stability comparisons for IVA MCU, TrueConf, VK Calls, Yandex Telemost,
  Dion, MTS Link, Kontur.Talk, and related Russian platforms.
- Russian software catalog data includes enterprise and room-system oriented
  products that may not behave like browser SaaS meetings: IVA MCU/AVES,
  TrueConf Server/Online/Enterprise/MCU, VideoMost Server, VINTEO,
  ВИДЕОСЕЛЕКТОР, ПРОТЕЙ-ВКС, ВКурсе, Волна Цифровой Офис, РОСЧАТ, tada.team,
  Пачка, Р7-Офис communication surfaces, and OS Selector/eClass/EdgeConf
  entries.
- First implementation must not promise prompt-capable support for every
  Russian VKS system. It must instead create a Russian-market target registry,
  classify each target by evidence tier, and show honest support states.
- Russian browser targets need service-specific URL validation and
  calendar/join-intent correlation just like Google Meet/Zoom web. Generic
  Russian browser audio, arbitrary `.ru` domains, and corporate portal pages
  must not become prompt evidence by themselves.

### Consent And Anti-Surprise Patterns

Sources inspected:

- Zoom recording consent/notification:
  https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0059819
- Zoom consent prompt:
  https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0068228
- Microsoft Teams recording consent:
  https://learn.microsoft.com/en-us/microsoftteams/conferencing-recording-consent
- Microsoft Teams custom recording/transcription notices:
  https://learn.microsoft.com/en-us/microsoftteams/recording-transcription-custom-message
- Google Meet participant consent:
  https://knowledge.workspace.google.com/admin/meet/manage-participant-consent
- Google Meet recording help:
  https://support.google.com/meet/answer/9308681
- Fireflies join settings:
  https://guide.fireflies.ai/articles/3978936124-how-to-set-fireflies-to-join-only-meetings-you-want
- Read AI calendar join settings and opt-out:
  https://support.read.ai/hc/en-us/articles/10568150023059-What-meetings-does-Read-join-when-I-connect-my-calendar
  and https://www.read.ai/articles/how-to-stop-read-ai-from-joining-my-meetings
- Granola consent guidance:
  https://docs.granola.ai/help-center/consent-security-privacy/getting-consent
- Nielsen Norman Group permission request guidance:
  https://www.nngroup.com/articles/permission-requests/
- Apple permission purpose-string guidance:
  https://developer.apple.com/la/videos/play/tech-talks/110152/

Findings:

- Meeting platforms increasingly provide explicit recording/transcription
  notifications, consent prompts, admin policy, or visible bot presence.
- Botless recorders lack participant-list visibility and therefore need
  compensating transparency: visible local capture state, user-facing prompt,
  workspace policy, consent/notice copy, and immediate stop.
- Permission prompts are best requested at the point of need with clear benefit
  and recovery guidance, not as a broad unexplained upfront permission bundle.

## Product Scope Boundary

This feature adds local macOS meeting-start detection that can propose
recording when a user appears to have joined an approved meeting target in a
native conferencing app or browser. It creates candidate evidence, user prompts,
suppression/cooldown behavior, and target support policy for app and browser
meetings.

This feature does **not** implement hidden capture, general automatic recording,
bot auto-join, calendar write behavior, meeting invite mutation, share/send
behavior, MediaScribe egress, new transcription workflows, or new deletion
execution. It may pass trigger metadata to the existing local recording and
upload/review flows, but it must not weaken their gates.

General automatic recording for all meetings remains out of scope. The
verified-target implementation is now restored by Feature 124: its prompt
shows the eight-second countdown, starts on expiry unless skipped, starts
immediately on `Записать сейчас`, and can create a reversible target-scoped
rule through `Всегда писать это приложение`. That preference is not hidden
recording: every automatic start still requires approved target evidence, hard
safety gates, a persistent local indicator, one-action Stop, suppression after
Stop, metadata-only evidence, and settings controls to disable or revoke the
rule.

## Detection Model

### Candidate Confidence Levels

- **Observed signal**: One detector saw something possibly relevant, such as a
  Zoom process, a browser tab URL, audio ownership, a network connection, or a
  current calendar event. This level is for diagnostics/evidence only.
- **Weak candidate**: Signals suggest a possible meeting but may also be media,
  prejoin, settings, app launch, voice search, calendar noise, or generic
  browser activity. No user prompt.
- **Prompt-eligible candidate**: For native/installed apps in the first release,
  stable Gilb-style `AudioHAL` ownership from an approved allowlisted
  meeting app can be enough once hard gates pass. For browsers and non-Gilb
  paths, multiple signals still need to agree that the user is probably in an
  approved meeting target.
- **Blocked candidate**: Meeting-like signals exist, but a hard gate blocks the
  prompt or recording. Record metadata-only blocker evidence and show a
  recoverable state only when useful.
- **Recording candidate**: The user accepted the prompt and the local recording
  controller accepted all prerequisites. Active capture begins visibly.
- **Scoped auto-record candidate**: A future candidate from an approved target
  where the user previously checked "always record meetings from this
  app/service" and every hard gate passes. This is allowed in the first release
  only as target-scoped, visible, reversible behavior.

### Signal Families

The detector may combine these signal families:

- **Target identity**: bundle ID, process name, window owner, browser app,
  tab host/domain, calendar conferencing provider, or approved adapter target.
- **Meeting context**: recognized meeting URL pattern, calendar event match,
  active meeting window/tab state, app-specific in-call process, meeting room
  screen, provider API session, macOS power assertion pattern, or user join
  intent.
- **Live activity**: remote/system audio level, local microphone activity,
  macOS app audio ownership, app network media connection, WebRTC session
  evidence, or meeting adapter state.
- **User/context action**: user clicked a calendar join prompt, opened a meeting
  URL from GRAF, selected a capture scope, or manually armed recording.
- **Safety gates**: workspace policy, user acknowledgement of recording action
  or target-scoped auto-record rule, permissions, visible indicator
  availability, local storage/buffer readiness, active recording state,
  mute-truth limitation copy, and privacy policy. Participant notice is not a
  per-meeting product gate in the first release.

### Hard Decision Rules

- A single generic signal MUST NOT make a candidate prompt-eligible. For the
  first native/installed app MVP, a debounced macOS `AudioHAL bundle ownership`
  event from an approved allowlisted meeting app counts as a combined
  target-identity plus live-activity signal and MAY make the candidate
  prompt-eligible after hard gates pass.
- A running process alone MUST NOT prompt or start recording.
- A browser using microphone/camera alone MUST NOT prompt or start recording.
- System audio activity alone MUST NOT prompt or start recording.
- Calendar event time alone MUST NOT prompt as an app/browser meeting unless it
  is the existing calendar-start prompt from feature `060`; app/browser
  detection still needs live target evidence.
- Browser tab URL alone SHOULD NOT prompt unless the URL is a validated meeting
  URL and at least one additional signal indicates active/joined state or user
  join intent.
- Any prompt or recording start MUST name the approved target and why GRAF
  believes it is a meeting, using safe labels rather than raw private URLs,
  meeting codes, participant names, or agenda text.
- When evidence is ambiguous, stale, contradictory, or unsupported, the system
  MUST prefer detect-only evidence, manual recording availability, or an
  explicit user selection over a confident prompt.
- A target-scoped auto-record rule MUST NOT bypass confidence, permission,
  visible-indicator, storage, policy, or suppression gates. For native apps,
  the first-release confidence gate may be the same debounced Gilb-style mic
  audio ownership used for prompts.

## Target Support Policy

Initial macOS bundle ID seeds, future Windows executable/process seeds, browser
bundle/process seeds, and browser meeting URL families are tracked in
`specs/092-automatic-meeting-detection/fingerprints.md`. That appendix is
research input for `$speckit-plan`, not final support evidence: Tier A promotion
still requires live package/runtime verification, macOS `AudioHAL`
evidence for native apps, and false-positive QA.

### Target Tiers

- **Tier A - prompt-capable after validation**: Targets where GRAF has
  target-specific evidence for app/browser context, live activity, false-positive
  blockers, prompt UX, and recording quality.
- **Tier B - detect-only / prompt-experimental**: Targets where some signals
  are available but false-positive safety or browser/app adapter quality is not
  yet proven.
- **Tier C - manual-only**: Targets where GRAF cannot safely determine meeting
  state. Manual recording remains available when workspace policy permits.

### Initial Candidate Matrix For Planning

Planning should validate and narrow this matrix rather than silently claiming
all apps and browsers:

- Native apps: Zoom, Microsoft Teams, Webex, Slack Huddles/Calls, FaceTime,
  Discord, Skype, WhatsApp.
- Russian native/desktop or installed apps: Yandex Telemost where available,
  Kontur.Talk, TrueConf, MTS Link, VK Calls, VK Teams, SaluteJazz/Jazz,
  eXpress, IVA client surfaces, VideoMost, VINTEO, Dion, Pruffme, РОСЧАТ,
  Пачка, tada.team, and other Russian VKS clients discovered in planning.
- Browser services: Google Meet, Microsoft Teams web, Zoom web, Webex web,
  Yandex Telemost, Kontur.Talk, TrueConf Online/web, MTS Link,
  VK Calls/VK Teams web, SaluteJazz/Jazz, eXpress, Dion, Pruffme, VideoMost
  web, ВКурсе, and Russian VKS services exposed through corporate portals.
- Russian enterprise/on-prem registry candidates: IVA MCU/IVA AVES,
  TrueConf Server/Enterprise/MCU, VideoMost Server, VINTEO, ВИДЕОСЕЛЕКТОР,
  ПРОТЕЙ-ВКС, Волна Цифровой Офис, Р7-Офис communication surfaces,
  OS Selector, eClass, EdgeConf, VirtualRoom/Mirapolis, Bizon 365, and any
  current Russian VKS entries accepted by product during planning.
- Browsers: Chrome, Edge, Opera, Yandex Browser, Safari, Firefox.

The first implementation MUST choose a smaller Tier A set with explicit QA
evidence. Suggested first Tier A candidates are:

- Zoom native on macOS.
- Microsoft Teams native on macOS.
- Google Meet in Chrome or Edge using macOS browser metadata, validated meeting
  URL, calendar/join intent when available, and live activity evidence.
- At least one Russian browser service from Yandex Telemost, MTS Link,
  Kontur.Talk, VK Calls/VK Teams, or TrueConf Online, if current GRAF
  validation infrastructure can reliably exercise it.
- At least one Russian native or installed client, if available on macOS and
  able to produce enough target-specific evidence.

Unsupported targets MUST remain manual-only or detect-only until their own
adapter evidence is accepted.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect And Ask For A New Meeting (Priority: P1)

As a macOS user, I want GRAF to notice when I have likely joined a new approved
meeting and ask whether to record, so that I do not forget important calls while
still deciding when capture begins.

**Why this priority**: This is the core value. It reduces missed recordings
without hidden auto-start or broad capture from weak signals.

**Independent Test**: Enable meeting detection in detect-and-ask mode, join one
validated Tier A target, and verify GRAF shows a local prompt with record, skip,
and suppression actions only after multi-signal candidate confidence and hard
gates pass.

**Acceptance Scenarios**:

1. **Given** meeting detection is enabled, workspace policy permits recording,
   required permissions are granted, and no recording is active, **When** the
   user joins a validated Tier A meeting and the candidate remains stable for
   the configured window, **Then** GRAF shows a visible prompt offering to
   record that meeting.
2. **Given** a record prompt is shown, **When** the user chooses Record,
   **Then** local recording starts with persistent local indicator,
   one-action Stop, and trigger evidence `meeting_detection_prompt`.
3. **Given** a record prompt is shown, **When** the user chooses Record and
   checks "always record meetings from this app/service", **Then** GRAF starts
   the current recording and stores a reversible target-scoped auto-record
   preference for future prompt-eligible candidates from that same target.
4. **Given** a record prompt is shown, **When** the user chooses Skip,
   **Then** GRAF does not prompt again for the same candidate until the
   candidate ends or a cooldown expires.
5. **Given** the user manually starts recording while a candidate exists,
   **When** detector state changes, **Then** GRAF does not show a second prompt
   or create a second recording for the same meeting.
6. **Given** required safety gates do not pass, **When** a meeting-like
   candidate appears, **Then** GRAF records blocked evidence and does not offer
   a misleading record action.

---

### User Story 2 - Detect Native Apps With Gilb-Style Mic Attribution (Priority: P1)

As a user who joins meetings in native apps, I want GRAF to distinguish an
actual Zoom/Teams/Webex-style meeting from the app merely being open, so that I
am not interrupted by false prompts.

**Why this priority**: Native conferencing apps often run background helpers,
launch screens and updaters. Treating process existence as a meeting would be
noisy and unsafe, while Gilb-style audio ownership gives a practical
first signal that the app is actively using call hardware.

**Independent Test**: Run native-app scenarios covering app launch, sign-in,
idle state, stable `AudioHAL` ownership, ownership changes,
ownership end, unsupported app, and target-scoped auto-record. Verify
allowlisted audio ownership after debounce becomes prompt-eligible while process
existence alone does not.

**Acceptance Scenarios**:

1. **Given** Zoom or Teams is launched but no meeting is active, **When** the
   detector observes the process, **Then** it records at most a weak candidate
   and shows no recording prompt.
2. **Given** macOS reports `AudioHAL bundle ownership` for an allowlisted native meeting
   app, **When** the ownership remains stable for the configured debounce
   window and hard gates pass, **Then** the candidate becomes prompt-eligible.
3. **Given** an allowlisted native app briefly opens the microphone for less
   than the debounce window, **When** the ownership disappears, **Then** GRAF
   records metadata-only evidence and does not prompt.
4. **Given** a prejoin or device-test screen in an allowlisted app uses the
   microphone long enough to pass the Gilb-style detector, **When** the prompt
   appears, **Then** the user can Skip/Dismiss and GRAF records this as evidence
   for future detector improvement rather than treating it as a privacy failure.
5. **Given** a meeting app keeps helper processes alive after the call ends,
   **When** macOS audio ownership for the allowlisted app ends, **Then** GRAF
   clears or downgrades the candidate and does not keep prompting.
6. **Given** a native target's adapter health is degraded or unsupported,
   **When** the user joins a meeting, **Then** manual recording remains
   available but GRAF does not claim automatic detection support for that target.

---

### User Story 3 - Detect Browser Meetings Safely (Priority: P1)

As a user who joins meetings in browsers, I want GRAF to detect Google Meet,
Teams web, Zoom web, Telemost web, and similar browser meetings without treating
ordinary browser audio, voice search, streaming video, or landing pages as
recordable meetings.

**Why this priority**: Browser meetings are strategically important and
especially false-positive prone. Browser process or microphone activity is too
broad because one browser hosts many unrelated tasks.

**Independent Test**: Run browser scenarios across the planned browser matrix:
valid meeting URL joined, meeting URL prejoin, landing/new/join pages, browser
settings, YouTube/media playback, voice search, notification sounds, tab reload,
tab close, multiple tabs, and unsupported browser. Verify prompt behavior and
blocked evidence.

**Acceptance Scenarios**:

1. **Given** a browser tab is on a recognized meeting service landing, new, join,
   settings, or permission page, **When** the detector sees the URL or title,
   **Then** the candidate remains blocked and no record prompt appears.
2. **Given** a browser tab has a validated meeting URL and joined-state/live
   activity evidence, **When** all gates pass, **Then** GRAF can show a record
   prompt naming the browser and meeting service.
3. **Given** a browser plays music/video or a notification sound, **When**
   system audio is active but no approved meeting context exists, **Then** GRAF
   records `non_meeting_media` or equivalent metadata and shows no prompt.
4. **Given** browser tab URL access or extension/adapter permission is missing,
   **When** browser meeting signals are otherwise ambiguous, **Then** GRAF
   explains the detector limitation only in settings/health surfaces and keeps
   manual recording available.
5. **Given** multiple browser tabs look like meetings, **When** only one has
   active joined-state evidence, **Then** GRAF prompts for that candidate only;
   if more than one remains ambiguous, it asks the user to choose or remains
   detect-only.
6. **Given** the first release does not install a browser extension, **When** a
   browser meeting is evaluated, **Then** GRAF uses macOS browser metadata,
   validated service URL classes, calendar/join intent where available, and
   live activity evidence; extension-only joined-state evidence is deferred.

---

### User Story 4 - Cover Russian VKS Targets (Priority: P1)

As a user in the Russian market, I want GRAF to understand Russian VKS products
as first-class meeting targets, so that automatic detection is useful in the
services my team actually uses.

**Why this priority**: GRAF is being built for the Russian market. Support that
only focuses on global Zoom/Teams/Meet/Webex targets would miss important user
workflows and QA evidence.

**Independent Test**: Build the target registry from the Russian-market matrix,
then classify each product as prompt-capable, detect-only, manual-only, or
deferred with reason codes. Verify at least one Russian browser service and at
least one Russian native/installed client are evaluated for Tier A.

**Acceptance Scenarios**:

1. **Given** a Russian VKS target appears in the planning registry, **When** it
   lacks enough evidence for prompting, **Then** GRAF marks it detect-only,
   manual-only, or deferred instead of pretending it is supported.
2. **Given** Yandex Telemost, MTS Link, Kontur.Talk, VK Calls/VK Teams, or
   TrueConf Online runs in a supported browser, **When** the detector sees a
   validated meeting URL plus live/join-intent evidence, **Then** it can become
   prompt-eligible after target-specific QA passes.
3. **Given** IVA, TrueConf, VideoMost, VINTEO, Dion, eXpress, SaluteJazz/Jazz,
   or another Russian native/installed target has a macOS client or wrapper,
   **When** only process/app launch is visible, **Then** the candidate remains
   weak until stable allowlisted audio ownership appears.
4. **Given** a Russian VKS is accessed through a private corporate portal,
   **When** GRAF cannot validate the service-specific meeting pattern safely,
   **Then** it records metadata-only evidence and keeps manual recording
   available.

---

### User Story 5 - Block False Positives From Non-Meeting Activity (Priority: P1)

As a privacy-conscious user, I want GRAF to avoid recording for media playback,
app launches, prejoin tests, background browser activity, calendar noise, and
arbitrary system audio, and to avoid prompts whenever the Gilb-style detector
has no stable approved app audio ownership.

**Why this priority**: False positives are the primary trust risk for a botless
recorder. A recorder that prompts from ordinary audio will lose user trust even
if it does not auto-start.

**Independent Test**: Run the false-positive matrix with detection enabled and
verify zero recording starts. Verify zero prompts for non-meeting activity that
does not produce stable allowlisted app audio ownership; track
mic-using native-app prejoin/device-test prompts as prompt-quality evidence.

**Acceptance Scenarios**:

1. **Given** system audio is playing from music, video, notification, podcast,
   game, or arbitrary browser media, **When** no approved meeting context is
   present, **Then** GRAF does not prompt and does not record.
2. **Given** a calendar event starts but the user never opens or joins the
   meeting target, **When** app/browser live evidence is absent, **Then** this
   feature does not create an app/browser detection prompt beyond the existing
   calendar prompt rules.
3. **Given** a meeting app opens settings, device test, waiting room, or prejoin
   audio test, **When** no stable allowlisted audio ownership appears,
   **Then** the candidate is blocked.
4. **Given** an allowlisted native app opens the microphone in prejoin or device
   test long enough to match the Gilb-style detector, **When** a prompt appears,
   **Then** no recording starts without user action or a prior target-scoped
   auto-record rule, and the prompt result is stored as evidence for improving
   later detection.
5. **Given** the microphone is used by dictation, voice search, another
   recorder, a browser permission test, or a non-approved app, **When** the
   detector evaluates activity, **Then** it does not prompt.
6. **Given** a target adapter emits contradictory signals, **When** confidence
   cannot be resolved, **Then** GRAF records `contradictory_signals` evidence
   and remains silent or shows a non-recording health warning.

---

### User Story 6 - Preserve Visible Capture Control (Priority: P1)

As a user, I want every detector-assisted recording to be visibly distinguishable
and immediately stoppable, so that I always know whether GRAF is recording.

**Why this priority**: Visible consent and one-action Stop are constitutional
requirements and the most important compensating controls for botless capture.

**Independent Test**: Accept a detector prompt, then inspect the menu bar/tray,
main native surface, compact window, embedded cabinet boundary, and keyboard
navigation. Verify active capture state and Stop are present before capture is
accepted.

**Acceptance Scenarios**:

1. **Given** the user accepts a detector prompt, **When** recording begins,
   **Then** the local indicator changes to a detector-assisted recording state
   before the recording is considered accepted.
2. **Given** detector-assisted recording is active, **When** the user presses
   Stop from any required local control surface, **Then** recording stops in one
   action and the detector suppresses restart for that candidate.
3. **Given** the visible indicator cannot be shown or becomes unavailable,
   **When** a detector-assisted recording would start or is active, **Then**
   start is blocked or recording fails closed with a truthful reason.
4. **Given** the embedded web cabinet is offline, signed out, loading, or
   displaying settings/review, **When** detector-assisted recording is active,
   **Then** native recording truth and Stop remain outside the web content and
   usable.
5. **Given** `GRAF Pause` is used during detector-assisted recording, **When**
   local speech occurs, **Then** existing product-owned pause semantics and
   metadata-only privacy segments still apply.

---

### User Story 7 - Let Users And Admins Control Detection (Priority: P1)

As a user or workspace owner, I want clear controls for meeting detection,
prompts, targets, suppression, and consent policy, so that detection behavior
matches my workflow and legal expectations.

**Why this priority**: Detection changes when and why users are interrupted
about recording. It is enabled by default for the first release, but it must be
explainable, suppressible, and easy to turn off or narrow.

**Independent Test**: Configure detect-only, detect-and-ask,
target allowlists, target-scoped auto-record preferences, browser adapter
health, prompt suppression, and workspace policy constraints. Verify runtime
behavior matches settings.

**Acceptance Scenarios**:

1. **Given** a user completes onboarding or upgrades into the first release,
   **When** workspace policy permits recording, **Then** meeting detection
   prompts are enabled by default in detect-and-ask mode and can be turned off or
   changed in settings.
2. **Given** detect-only mode is enabled, **When** meeting candidates appear,
   **Then** GRAF records metadata-only candidate decisions without prompting or
   recording.
3. **Given** detect-and-ask mode is enabled, **When** prompt-eligible candidates
   appear, **Then** GRAF prompts according to target and cooldown policy.
4. **Given** a user chooses "do not ask again" for a specific event, target, or
   service, **When** matching candidates recur, **Then** GRAF respects the
   suppression scope without disabling manual recording.
6. **Given** a user has enabled "always record meetings from this app/service",
   **When** a future candidate from that same target becomes prompt-eligible,
   **Then** GRAF starts recording without another prompt only after all hard
   gates pass and the visible local indicator/Stop are available.
7. **Given** the user revokes a target-scoped auto-record preference in
   settings, **When** future meetings from that target occur, **Then** GRAF
   returns to detect-and-ask or the configured mode.
8. **Given** workspace policy disables recording, **When** a meeting candidate
   appears, **Then** controls and prompts reflect the policy and do not offer
   unsafe actions.
9. **Given** a meeting recording starts from prompt or target-scoped auto-record,
   **When** participant notice is considered, **Then** GRAF does not show a
   per-meeting notice/consent prompt or blocking notice step; the user remains
   responsible for verbally warning participants when needed.

---

### User Story 8 - Use Calendar Context Without Overclaiming (Priority: P2)

As a meeting owner, I want detection to use calendar context for better prompts,
naming, and confidence while avoiding wrong matches and private event leaks.

**Why this priority**: Calendar context improves precision and titles, but
calendar data can be stale, private, overlapping, or unrelated to actual app
activity.

**Independent Test**: Run detection with current event match, selected event
join prompt, multiple overlapping events, private/free-busy events, stale sync,
no calendar context, and manually renamed meetings. Verify candidate confidence
and title/roster behavior.

**Acceptance Scenarios**:

1. **Given** the user opens a meeting from a GRAF calendar join prompt, **When**
   app/browser live evidence appears, **Then** detector confidence can include
   the selected calendar event.
2. **Given** one current calendar event matches the meeting target and policy
   allows descriptive names, **When** recording starts from a detector prompt,
   **Then** the recording can use calendar title context with source confidence.
3. **Given** multiple current events overlap, **When** app/browser evidence does
   not disambiguate them, **Then** GRAF avoids automatic calendar assignment and
   asks the user or records without calendar context.
4. **Given** a private/free-busy event overlaps a detected meeting, **When** a
   prompt is shown, **Then** private title, agenda, participant emails, meeting
   URL, and passcode are not exposed in the prompt or diagnostics.
5. **Given** calendar sync is stale or unavailable, **When** a meeting is
   detected, **Then** GRAF can still prompt from app/browser evidence but marks
   calendar context as unavailable/stale.

---

### User Story 9 - Record Metadata-Only Detector Evidence (Priority: P2)

As QA and product owners, we need metadata-only evidence for detected,
prompted, skipped, blocked, suppressed, recorded, and missed candidates so that
we can improve detection and prove false-positive safety.

**Why this priority**: Automatic detection quality cannot be asserted from
anecdotes. The team needs privacy-safe evidence before enabling broader prompt
or auto-record behavior.

**Independent Test**: Run a scripted and manual QA matrix, export detector
evidence, and verify every decision has safe reason codes without raw meeting
content, transcript text, full private URLs, meeting codes, participant emails,
IP addresses, credentials, or signed URLs.

**Acceptance Scenarios**:

1. **Given** detect-only mode is enabled, **When** candidates are observed,
   **Then** evidence records signal families, target family, confidence, hard
   blockers, decision, and adapter health without prompting or recording.
2. **Given** a candidate is prompted, skipped, suppressed, blocked, or recorded,
   **When** evidence is exported, **Then** it includes the decision path and
   reason codes.
3. **Given** browser URL evidence contributes to detection, **When** evidence is
   stored, **Then** it uses service family, host category, validated pattern
   class, and redacted/hashing where needed instead of raw private meeting URLs.
4. **Given** network evidence contributes to detection, **When** evidence is
   stored, **Then** it avoids raw remote IP addresses and records only safe
   domain/port/service-family categories needed for QA.
5. **Given** detector health degrades, **When** required adapters fail, **Then**
   evidence records the adapter state and the product does not silently claim
   target support.

---

### User Story 10 - End Or Suppress Recordings Safely (Priority: P2)

As a user, I want GRAF to avoid nagging after I skip or stop, and to avoid
ending recordings too aggressively when a meeting briefly changes state.

**Why this priority**: Meeting apps reconnect, switch devices, change tabs, and
briefly lose network/audio. Over-eager stop or re-prompt behavior can lose
important content or annoy the user.

**Independent Test**: Exercise meeting end, leave/rejoin, tab reload, network
drop, audio silence, app crash, manual Stop, Skip, and suppression states.

**Acceptance Scenarios**:

1. **Given** the user skips a prompt, **When** the same candidate remains
   active, **Then** GRAF does not re-prompt during the suppression window.
2. **Given** the user stops detector-assisted recording, **When** the same
   meeting remains active or reconnects shortly after, **Then** GRAF does not
   auto-restart or immediately re-prompt.
3. **Given** meeting activity temporarily drops due to network, tab reload, or
   app reconnection, **When** the drop is shorter than the end grace period,
   **Then** GRAF preserves candidate continuity.
4. **Given** the meeting appears ended and recording is active, **When** auto
   stop assistance is enabled, **Then** GRAF may offer a stop prompt or apply a
   configured safe stop policy only if it preserves visible Stop and reason
   evidence.
5. **Given** a different meeting starts while one recording is active, **When**
   detection sees the second candidate, **Then** GRAF does not switch recording
   context without explicit user action.

---

### User Story 11 - Target-Scoped Auto-Record After User Opt-In (Priority: P1)

As a user who repeatedly records meetings from the same app or service, I want
to check a box in the prompt so future meetings from that target are recorded
automatically, so that routine calls are captured without repeated prompts.

**Why this priority**: The first release should reduce repeated interruptions
for trusted apps/services, while still preventing hidden capture and broad
automatic recording.

**Independent Test**: Accept a prompt with the auto-record checkbox for one
approved target, then join future meetings from the same target and from other
targets. Verify only same-target candidates can auto-start, every hard gate is
enforced, active capture is visible, Stop suppresses restart, and settings can
revoke the rule.

**Acceptance Scenarios**:

1. **Given** the user has not checked the target-scoped auto-record checkbox,
   **When** a prompt-eligible meeting appears, **Then** GRAF asks before
   recording.
2. **Given** the user checks "always record meetings from this app/service" in
   a prompt, **When** a later candidate from the same approved target qualifies,
   **Then** recording starts with visible detector-assisted-auto state and
   one-action Stop.
3. **Given** any hard gate fails, **When** a future auto-record candidate
   appears, **Then** recording does not start and evidence records the blocker.
4. **Given** the user manually stops an auto-recorded meeting, **When** the
   same candidate remains active, **Then** GRAF suppresses restart for that
   candidate.
5. **Given** a different app/service becomes prompt-eligible, **When** the user
   only enabled auto-record for another target, **Then** GRAF does not reuse the
   preference across targets.

## Edge Cases

- A native meeting app is open but no meeting is active.
- A native meeting app is on sign-in, update, waiting room, settings, device
  test, or prejoin screen.
- A browser is open to a meeting landing/new/join/settings page.
- A browser has a valid meeting URL in an inactive background tab.
- Multiple browser tabs contain valid meeting URLs.
- The user joins one meeting in a browser while another native meeting app is
  still open.
- The user is in two simultaneous meetings.
- Calendar shows a meeting but the user joins a different ad hoc meeting.
- Calendar has overlapping meetings and app/browser signals do not
  disambiguate.
- Calendar sync is stale, disconnected, rate-limited, or private/free-busy.
- User opened a meeting through a calendar join prompt but then did not join.
- User joins from a forwarded link not present in the calendar.
- User starts manual recording before detector prompt appears.
- User skips, dismisses, snoozes, or stops while candidate remains active.
- User changes microphone, output, display, capture scope, or meeting app
  permissions during detection.
- Screen/system-audio or microphone permission is missing, revoked, stale, or
  restricted.
- The visible indicator cannot render because the app is hidden, crashed,
  signed out, offline, or in embedded web-only state.
- The app loses storage/buffer readiness while candidate is prompt-eligible.
- System audio is active from media playback, notifications, music, games, or
  web video.
- A browser uses microphone for voice search, dictation, browser permission
  tests, or non-meeting WebRTC pages.
- Google Meet/Teams/Zoom UI changes break DOM/title/URL assumptions.
- Browser extension is missing, disabled, outdated, or denied host permission.
- AppleScript/Accessibility access is denied or returns stale browser tabs.
- macOS unified-log audio ownership changes or becomes unavailable.
- Network evidence is unavailable due to permissions, VPN, proxy, firewall, or
  encrypted/private relay behavior.
- Meeting service domains/ports change.
- A target adapter reports stale, delayed, or contradictory state.
- The meeting is silent for several minutes but still active.
- Remote participants join late; meeting starts before remote audio exists.
- Visible meeting controls disappear because the user switches tabs, minimizes
  the app, changes macOS Spaces, shares a screen, moves focus, or the provider
  swaps to a floating toolbar.
- Native app power assertions remain active after meeting end or are present
  while the app is idle.
- User mutes inside the meeting app; GRAF product Pause remains the only proven
  local privacy control unless a target-specific mute adapter exists.
- The user records in transcript-only mode, audio+transcript mode, or future
  policy-limited mode.
- Localization: Russian prompt copy is long and must fit compact native
  surfaces.
- Accessibility: prompt must be keyboard and screen-reader usable while another
  app is focused.
- Evidence screenshots must not include raw meeting titles, participant emails,
  meeting URLs, passcodes, transcript text, or raw audio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a macOS local meeting detector that can
  observe approved app and browser meeting candidates without starting capture.
- **FR-002**: The detector MUST support two runtime modes: `detect_only` and
  `detect_and_ask`.
- **FR-003**: `detect_and_ask` MUST be the first product rollout mode for this
  feature. Broad automatic recording MUST remain unavailable, but a
  target-scoped auto-record preference MAY be created when the user explicitly
  checks "always record meetings from this app/service" in a record prompt.
- **FR-004**: Manual Record/Stop/Pause/Resume MUST remain available whenever
  workspace policy permits recording, regardless of detector state.
- **FR-005**: A candidate MUST NOT become prompt-eligible from a single weak
  signal such as process running, browser mic use, system audio activity,
  calendar time, or a generic browser tab URL. For native/installed apps,
  debounced macOS audio ownership from an approved allowlisted bundle is
  not considered a weak generic signal in the first release.
- **FR-006**: A prompt-eligible candidate MUST include at least one approved
  meeting context signal and at least one live activity or user join-intent
  signal, plus all hard safety gates. For native/installed apps, a stable
  `AudioHAL` ownership event from an approved allowlisted app satisfies both
  target identity and live app activity for the first Gilb-style MVP.
  Non-allowlisted audio ownership events MUST be ignored by the detector
  decision input.
- **FR-007**: Hard safety gates MUST include workspace recording policy, user
  acknowledgement, required permissions, visible local indicator availability,
  one-action Stop availability, local storage/buffer readiness, and no active
  conflicting recording.
- **FR-008**: The target registry MUST distinguish Tier A prompt-capable
  targets, Tier B detect-only/experimental targets, and Tier C manual-only
  targets.
- **FR-009**: The target registry MUST record target family, native bundle or
  browser/service identity, support tier, required permissions/adapters,
  confidence rules, false-positive blockers, QA status, and user-facing support
  label.
- **FR-010**: Native-app detection MUST distinguish app/process launch from
  app activity by using Gilb-style macOS `AudioHAL` app ownership for
  allowlisted bundle IDs; generic process existence alone MUST remain
  insufficient.
- **FR-011**: Browser detection MUST distinguish meeting pages from landing,
  new, join, settings, help, account, permission, device-test, and post-meeting
  pages.
- **FR-012**: Browser detection MUST NOT treat browser process existence,
  browser microphone/camera use, tab audible state, or arbitrary WebRTC
  activity as sufficient prompt evidence.
- **FR-013**: Browser URL evidence MUST use validated service-specific meeting
  patterns and must redact or hash private meeting codes/URLs outside
  authorized product surfaces.
- **FR-014**: Browser adapters MAY use public browser extension APIs,
  AppleScript/Accessibility, browser tab metadata, or provider APIs only after
  their permission, privacy, and failure behavior is documented in planning.
  The first release MUST rely on macOS browser metadata plus calendar/join
  intent and MUST NOT require a browser extension.
- **FR-015**: The detector MUST fail closed to detect-only or manual-only when
  browser adapter permissions are missing, denied, stale, unsupported, or
  health-degraded.
- **FR-016**: Calendar context MAY improve candidate confidence, title, and
  roster context only when feature `060` confidence and privacy rules pass.
- **FR-017**: Calendar context MUST NOT overwrite user-renamed titles, silently
  choose among overlapping events, expose private/free-busy details, or create
  recipient/share/send behavior.
- **FR-018**: System audio level/activity MAY be used as live activity evidence
  only when paired with approved meeting context; it MUST NOT prompt from
  arbitrary background audio.
- **FR-019**: Microphone/camera attribution MAY be used as live activity
  evidence. For allowlisted native/installed apps in the first release, stable
  macOS audio ownership is the primary app-activity detector; browser
  mic/camera attribution alone MUST remain weak because browsers host
  non-meeting activity.
- **FR-020**: Network evidence MAY be used for native-app or browser-service
  confidence only when recorded as metadata-only service-family/port/state
  categories and not as raw private IP evidence in diagnostics. Network
  evidence is optional Phase 2 improvement for native apps, not a first-release
  blocker.
- **FR-021**: The detector MUST define stable debounce windows for meeting
  start, candidate update, and meeting end so brief app/network/audio changes
  do not produce prompt churn.
- **FR-022**: The prompt MUST identify the safe target label, capture mode,
  capture sources, workspace policy state, and user choices without exposing
  raw meeting URLs, passcodes, attendee emails, or agenda text.
- **FR-023**: The prompt MUST provide Record, Skip/Dismiss, and at least one
  scoped suppression path such as "do not ask for this event/target/service"
  where policy permits.
- **FR-024**: Accepting a prompt MUST start recording only through the existing
  local recording prerequisite gate; detector code MUST NOT bypass recording
  start blockers.
- **FR-025**: Active detector-assisted recording MUST show a persistent local
  indicator and one-action Stop before it can be considered accepted.
- **FR-026**: If the local visible indicator cannot be shown, detector-assisted
  recording MUST be blocked or fail closed.
- **FR-027**: Stopping a detector-assisted recording MUST suppress immediate
  restart or re-prompt for the same candidate for a configured window.
- **FR-028**: Skipping/dismissing a prompt MUST suppress repeat prompts for the
  same candidate until the candidate ends or the suppression window expires.
- **FR-029**: The detector MUST record metadata-only evidence for observed,
  weak, prompt-eligible, blocked, suppressed, skipped, recorded, ended,
  missed, and health-degraded candidates.
- **FR-030**: Detector evidence MUST include signal family presence, safe target
  label, confidence level, decision outcome, reason codes, blocker codes,
  adapter health, policy state, and prompt/recording result.
- **FR-031**: Detector evidence MUST NOT include raw audio, transcript text,
  meeting content, full private URLs, passcodes, participant emails, raw agenda
  text, credentials, tokens, signed URLs, passwords, live secret paths, or raw
  remote IP addresses.
- **FR-032**: Diagnostics MUST be metadata-only by default and must pass the
  existing diagnostic redaction discipline before any evidence is committed or
  exported.
- **FR-033**: The detector MUST provide a user-visible health/settings surface
  for detect-only, auto-record off, monitoring, prompt-capable, degraded,
  permission needed, unsupported target, and adapter unavailable states.
- **FR-034**: Prompt UX MUST be keyboard operable, screen-reader labeled,
  reduced-motion safe, compact-width safe, and localized for Russian product
  surfaces without overlapping text or controls.
- **FR-035**: Detection MUST NOT create uploads, start MediaScribe, send
  transcript/summary/report messages, mutate calendar events, invite bots, or
  grant meeting access.
- **FR-036**: Target-scoped auto-record MUST be blocked unless planning defines
  evidence thresholds, allowed target classes, visible auto-start state,
  suppression behavior, rollback controls, and settings UI for revocation.
- **FR-037**: The feature MUST define a false-positive QA matrix covering media
  playback, notifications, app launch, prejoin, settings, device tests, browser
  landing pages, voice search, inactive tabs, calendar-only events, and
  unsupported targets. For the first Gilb-style native-app MVP, mic-using
  prejoin/device-test prompts MUST be tracked as prompt-quality evidence rather
  than as recording-start failures.
- **FR-038**: The feature MUST define a positive detection QA matrix covering
  each Tier A native app and browser service in realistic joined-meeting states
  with remote audio, local speech, silence, tab/app switching, and meeting end.
- **FR-039**: The feature MUST define detector resource gates for idle and
  monitoring states so detection cannot cause noticeable CPU, memory, or
  battery drain.
- **FR-040**: The feature MUST maintain clean-room and brand-distance
  requirements: no Krisp assets, copy, icons, private behavior, binaries, or
  proprietary model behavior may be copied.
- **FR-041**: Auto-stop assistance MUST NOT end recording solely because a
  meeting control, participant panel, browser tab, window, or app focus is no
  longer visible; it MUST use a configured end grace period and multiple
  target-specific end signals.
- **FR-042**: Window title, Accessibility, browser URL, browser extension,
  provider API, power assertion, and network observations MUST be scoped to the
  minimum metadata needed for detection and evidence, with permission and
  redaction behavior documented before implementation.
- **FR-043**: Native-app confidence rules MAY use macOS power assertions,
  window owner/title classes, audio ownership, and media network categories,
  but the first release SHOULD use Gilb-style audio ownership as the primary
  native-app rule. Power/window/network signals are later improvements and MUST
  be validated per target before affecting decisions.
- **FR-044**: Meeting detection prompts MUST be enabled by default for the
  first release when workspace policy permits recording, while settings MUST
  allow users/admins to disable detection or switch to detect-only.
- **FR-045**: The target registry MUST treat Russian VKS systems as
  first-class targets and MUST include global targets plus Russian-market
  candidates such as Yandex Telemost, VK Calls/VK Teams, MTS Link,
  Kontur.Talk, TrueConf, IVA, VideoMost, VINTEO, Dion, SaluteJazz/Jazz,
  eXpress, Pruffme, ВКурсе, РОСЧАТ, Пачка, and enterprise/on-prem products
  discovered during planning.
- **FR-046**: The first release MUST NOT show a per-meeting participant-notice
  prompt, pasteable notice step, calendar notice workflow, or blocking consent
  acknowledgement. User-facing settings/onboarding copy MAY state that the
  user is responsible for warning participants verbally when required.
- **FR-047**: The first-release prompt MUST provide an optional checkbox to
  always record future meetings from this app/service. The checkbox MUST be
  unchecked by default in each prompt until the user enables the preference,
  and the resulting rule MUST be target-scoped and reversible in settings.
- **FR-048**: The native-app detector MUST emit health-degraded evidence and
  fall back to manual recording if `/usr/bin/log stream` cannot start, the
  `AudioHAL` predicate stops producing parseable ownership events, or macOS
  changes the private unified-log behavior.
- **FR-049**: The target registry MUST be deliverable as a versioned remote JSON
  document with a last-good local cache, so adding or changing target support
  state does not require rebuilding the macOS client.
- **FR-050**: The client MUST validate registry schema version, target modes,
  target identifiers, adapter types, platform fields, and safety constraints
  before applying a remote registry. Invalid or unsafe registries MUST fail
  closed to the previous good registry cache or to no automatic detection when
  no valid cache exists.
- **FR-051**: The remote registry MUST NOT be able to disable compiled safety
  gates such as prompt requirements, target-scoped auto-record opt-in, visible
  local recording state, one-action Stop, metadata-only diagnostics, or
  forbidden-content redaction.
- **FR-052**: The detector MUST maintain lightweight local telemetry rollups for
  known target health, blocked/missed candidates, prompt outcomes, adapter
  health, resource overhead, and unknown native-app discovery candidates.
- **FR-053**: Unknown native apps observed through stable audio ownership
  MUST remain non-prompting and non-recording until a reviewed registry update
  and target-specific QA promote them to a supported mode.
- **FR-054**: Unknown app identifiers such as raw bundle IDs, display names,
  signing team IDs, and versions MUST NOT be uploaded for every microphone-using
  app. They MAY be uploaded automatically only when the app passes a client-side
  VKS-candidate filter and does not match an explicit non-target category.
- **FR-055**: Automatic telemetry upload, when enabled, MUST send bounded
  metadata-only aggregates rather than raw event logs and MUST respect rate
  limits, local retention caps, backoff, and the resource gates.
- **FR-056**: Registry fetch and telemetry upload MUST be optional for detection
  safety. Network failure MUST NOT block manual recording; automatic detection
  may use a last-good registry cache and otherwise must fail closed.
- **FR-057**: The registry and telemetry design MUST follow
  `specs/092-automatic-meeting-detection/registry-telemetry.md`.
- **FR-058**: The first server implementation MUST provide an authenticated
  desktop telemetry endpoint for meeting-detection rollups and VKS-candidate
  uploads, with schema validation, idempotency, rate limiting, and
  forbidden-content rejection.
- **FR-059**: The admin surface MUST provide a meeting-detection review queue
  where admins can inspect VKS candidates, known-target health, and registry
  drafts; mark candidates as non-target; merge candidates; add candidates as
  `diagnostic_only`; request validation; and publish reviewed registry changes.
- **FR-060**: Telemetry, candidate score, or admin queue presence MUST NOT
  automatically promote an unknown target to `prompt_enabled`. Prompt-capable
  support requires explicit reviewed registry change plus target-specific QA
  evidence.

### Key Entities *(include if feature involves data)*

- **Meeting Detection Policy**: User/workspace settings for default-enabled
  detect-and-ask, detect-only, target tiers, suppression defaults,
  prompt controls, and target-scoped auto-record eligibility.
- **Approved Meeting Target**: A native app, browser service, browser family,
  or provider target with support tier, safe display label, required adapter
  permissions, confidence rules, QA status, and fallback behavior.
- **Meeting Target Registry Document**: Versioned remote or packaged JSON
  document listing known targets, platform identities, support modes, evidence
  state, required signals, labels, and safety metadata.
- **Registry Cache**: Last valid applied remote registry stored locally so the
  detector can continue with known-good behavior when the server or network is
  unavailable.
- **Detection Signal**: A metadata-only observation from one signal family,
  including timestamp, source adapter, safe target family, freshness, strength,
  and redaction state.
- **Meeting Candidate**: A time-bounded aggregation of detection signals that
  may represent one real meeting, including confidence, target identity,
  calendar link candidates, lifecycle state, and suppression identity.
- **Candidate Decision**: The detector's current decision for a candidate:
  observed, weak, prompt-eligible, blocked, prompted, skipped, suppressed,
  recorded, ended, expired, or health-degraded.
- **Record Prompt**: A local/native user prompt tied to one candidate, with
  safe target label, capture explanation, action set, policy state,
  accessibility metadata, and result.
- **Prompt Suppression**: User or policy state that suppresses prompts for a
  candidate, event, target, service, browser, time window, or workspace scope.
- **Target-Scoped Auto-Record Preference**: A user-enabled rule created from a
  record prompt checkbox that lets future prompt-eligible meetings from the
  same approved app/service start recording automatically after all hard gates
  pass.
- **Target Adapter Health**: Status for an app/browser/provider adapter,
  including permissions, last successful observation, degraded reason, and
  user-facing recovery action.
- **Browser Meeting Adapter**: A browser-specific observation path such as
  extension, AppleScript/Accessibility tab metadata, provider API, or safe
  native browser integration.
- **Calendar Detection Link**: Optional link between a candidate and one or
  more calendar event snapshots, with confidence, privacy/title policy,
  overlap state, and user selection state.
- **Detector Evidence Record**: Metadata-only evidence row or local diagnostic
  entry proving why a detector decision happened and what was excluded.
- **Telemetry Rollup**: Bounded local aggregate of detector outcomes, target
  health, unknown discovery candidates, and resource metrics after redaction and
  classification.
- **Unknown Native App Discovery Candidate**: A non-prompting local observation
  of stable `AudioHAL` ownership from a non-registry native app that may
  guide future research, registry updates, or QA.
- **VKS-Candidate Filter**: Client-side scoring and denylist policy that decides
  whether an unknown microphone-using app is likely enough to be a meeting/VKS
  app to upload safe app identity for admin review.
- **Meeting Detection Admin Review Item**: Server-side aggregated candidate or
  known-target health item visible in admin review, with safe identifiers, score,
  reason codes, review state, and audited admin actions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the accepted Tier A positive QA matrix, GRAF shows a record
  prompt within 20 seconds of stable joined-meeting evidence in at least 95% of
  validated runs, with zero hidden recording starts.
- **SC-002**: In the required false-positive matrix, GRAF starts zero recordings
  and shows zero record prompts for media playback, notifications, app launch
  without stable allowlisted audio ownership, browser landing pages, voice
  search, inactive tabs, calendar-only events, and unsupported targets. Native
  prejoin/device-test cases that open the microphone long enough to match the
  Gilb-style detector are tracked as known prompt-quality evidence for Phase 2
  rather than as hidden recording failures.
- **SC-003**: 100% of detector-assisted recordings begin only after either a
  user Record action or a previously enabled target-scoped auto-record
  preference, and show persistent local indicator plus one-action Stop before
  accepted capture.
- **SC-004**: 100% of blocked candidates produce a reason code that maps to a
  user-recoverable state, detect-only state, or manual-only state without raw
  private content.
- **SC-005**: Browser validation covers at least one Chromium-based browser and
  one non-Chromium browser decision: prompt-capable, detect-only, or
  manual-only with explicit evidence. Unsupported browsers are not silently
  claimed.
- **SC-006**: Native-app validation covers at least Zoom and Microsoft Teams
  through Gilb-style macOS audio ownership, and planning must either
  validate or explicitly defer Webex, Slack/Discord, and each enumerated
  Russian meeting target with a reason code.
- **SC-007**: Diagnostic/evidence forbidden-content scans find zero raw audio,
  transcript text, private meeting content, full private URLs, passcodes,
  participant emails, credentials, tokens, signed URLs, passwords, live secret
  paths, or raw remote IP addresses.
- **SC-008**: Stopping or skipping a detector prompt suppresses repeat prompt or
  restart for the same candidate in 100% of tested same-meeting continuation
  scenarios.
- **SC-009**: Detector idle/monitoring overhead stays within the resource gate
  selected during planning and does not regress existing local recording CPU
  gates.
- **SC-010**: Calendar-overlap, private/free-busy, stale-sync, no-calendar, and
  manually selected calendar contexts produce deterministic prompt/title
  outcomes without exposing private calendar content.
- **SC-011**: Feature closeout can report per-target support state as
  prompt-capable, detect-only, manual-only, or deferred; no target is described
  as supported without evidence.
- **SC-012**: At least one Russian browser service and one Russian native or
  installed target are evaluated for Tier A; the native/installed target is
  evaluated first by allowlisted bundle ID plus stable macOS audio ownership.
  If either cannot be Tier A, the closeout records why and keeps the target in
  detect-only, manual-only, or deferred state.
- **SC-013**: Target-scoped auto-record starts only for the exact app/service
  preference selected by the user, never for unrelated targets, and Stop or
  settings revocation suppresses future auto-starts in 100% of tested cases.
- **SC-014**: No first-release prompt contains a participant-notice blocking
  step or mandatory consent checkbox; any participant-warning copy is confined
  to non-blocking onboarding/settings guidance.
- **SC-015**: Registry validation tests prove malformed, incompatible, unsafe,
  expired, or downgraded remote registries are rejected and the client keeps the
  previous good registry cache or fails closed when no valid cache exists.
- **SC-016**: Telemetry forbidden-content scans find zero raw unified-log lines,
  raw audio, transcript text, private meeting content, full private URLs,
  passcodes, participant emails, raw remote IP addresses, credentials, tokens,
  signed URLs, passwords, secret paths, or full local app paths.
- **SC-017**: Unknown-app discovery tests prove stable unknown native audio
  ownership that fails the VKS-candidate filter creates only local aggregate
  evidence, uploads no raw app identity, and never creates a prompt, recording,
  or target-scoped auto-record rule.
- **SC-018**: Resource validation shows registry refresh, event parsing,
  rollup persistence, and automatic candidate telemetry upload remain within the
  selected CPU, memory, disk-write, retention, and network gates.
- **SC-019**: Candidate upload tests prove only apps that pass the VKS-candidate
  filter are sent to the server, while browsers, Krisp/audio utilities, system
  services, media players, audio editors, games, screen recorders, short tests,
  and low-score unknown apps are suppressed before upload.
- **SC-020**: Admin review tests prove a candidate can be inspected, marked
  non-target, merged, added as `diagnostic_only`, moved to validation-needed, and
  published through a reviewed registry draft without enabling prompt behavior
  before QA evidence exists.

## Assumptions

- The first implementation remains macOS-only and native-first.
- GRAF already has accepted local manual recording, visible local recording
  state, product-owned Pause/Stop, local artifact truth, upload/sync/review
  foundations, and calendar context primitives.
- Meeting detection prompts are enabled by default when policy permits, but
  broad automatic recording is not. The only first-release automatic recording
  path is a user-enabled target-scoped preference created from a prompt.
- For native/installed apps, the first release intentionally follows Gilb's
  macOS unified-log audio ownership model before adding network,
  window-title, power-assertion, or Accessibility joined-state signals.
- Calendar connection, if present, is useful for context and confidence but is
  not required for manual recording or all prompt-eligible detections.
- First browser detection uses macOS browser metadata plus calendar/join intent;
  a browser extension remains a future adapter option for richer joined-state
  evidence.
- Some meeting apps and browser services will remain manual-only until their
  false-positive safety is proven.
- Participant/legal notice requirements vary by workspace and jurisdiction.
  The first release does not interrupt recording with participant-notice
  prompts; users are responsible for verbally warning participants where needed.
- Implementation will reuse existing local recording prerequisite gates and
  metadata redaction helpers rather than building a parallel recording path.

## Explicitly Out Of Scope

- Hidden recording or invisible active capture.
- Broad automatic recording in the first rollout. Target-scoped auto-record
  after an explicit prompt checkbox is in scope.
- Mandatory per-meeting participant-notice prompts, pasteable notice text,
  calendar notices, or consent-blocking workflows in the first release.
- Bot auto-join or bot participant behavior.
- Calendar write/mutation or invite updates.
- Summary/transcript/report sending or auto-share.
- Granting meeting access based on calendar participants.
- MediaScribe submission changes.
- New transcript/outcome generation workflows.
- Windows/Linux/iOS/Android detector support.
- Future virtual audio driver routing as a detection requirement.
- Perfect first-release distinction between a true joined meeting and every
  mic-using native-app prejoin/device-test state. The MVP handles this through
  prompt/Skip/Stop, evidence, and later detector improvements.
- Raw accessibility activity logging, keystroke logging, clipboard logging, or
  general browsing history capture.
- Copying Krisp's brand, UI, assets, copy, proprietary behavior, binaries, or
  model behavior.

## Clarification Questions For Next Step

Resolved in the 2026-07-08 clarification session:

1. Russian market coverage is mandatory. Planning must enumerate Russian VKS
   targets and classify each by support tier.
2. First browser release uses macOS browser metadata plus calendar/join intent;
   browser extension support is future optional work.
3. First release is detect-and-ask with a prompt checkbox for target-scoped
   future auto-record from the same app/service.
4. First release does not include per-meeting participant-notice or
   consent-blocking product prompts. The user warns participants verbally.
5. Detection prompts are enabled by default and can be changed in settings.
6. Native/installed app detection should initially match Gilb: macOS
   `AudioHAL` app ownership, approved app allowlist, debounce, health-degraded
   fallback, and prompt/auto-rule only after hard gates.
7. The target list should be maintained as a broad server-published registry
   with a last-good client cache, while client telemetry should use lightweight
   metadata-only rollups to identify working, failing, and missing targets
   without broadening recording behavior.
8. Meeting-detection telemetry should be uploaded automatically to the server for
   admin review only after client-side VKS-candidate filtering; the product must
   not upload all microphone apps or the user's app inventory.

Resolved for `$speckit-plan` on 2026-07-08:

1. First Tier A native validation targets are Zoom and Yandex Telemost native.
   Yandex Telemost is the first Russian native/installed Tier A attempt because
   local runtime start/end audio ownership is already verified. Microsoft Teams
   stays required for global validation but is not the first Russian target.
2. First Russian browser Tier A attempt is Yandex Telemost web in Chromium-family
   metadata surfaces, with Yandex Browser included in the browser matrix if the
   metadata mechanism can be validated. Safari and Firefox may remain
   manual-only or detect-only if the first macOS metadata path cannot safely
   identify active joined meeting tabs without an extension.
3. Target-scoped auto-record identity granularity is target-specific:
   native/installed apps use `targetId + nativeBundleId`; browser meetings use
   `serviceFamily + browserFamily` for the first release. Workspace domain may
   become a later narrowing key for enterprise/custom domains, but it is not the
   default first-release scope.
4. The first native detector parser contract is the Gilb-style `AudioHAL`
   ownership stream. Start debounce is 5 seconds of stable bundle ownership,
   end grace is 15 seconds after ownership removal or an inactive ownership
   event, and sub-5-second observations are telemetry short tests rather than
   prompt triggers. CI uses synthetic ndjson fixtures for ownership start,
   update, unknown app, non-target app, parser failure, and end events; live
   macOS log streaming remains manual QA evidence.
5. The first implementation slice is server/admin/registry telemetry foundation:
   telemetry endpoint, VKS-candidate review queue, registry draft/publish path,
   and remote registry endpoint. macOS detector and prompt integration follow
   only after the server/admin safety surface exists.
