# Feature Specification: Expanded Meeting App Registry

**Feature Branch**: `119-expand-meeting-app-registry`

**Created**: 2026-07-21

**Status**: Draft

> Runtime ownership note (2026-07-23): Feature 119 owns the verified native
> target catalog and common settings list. Feature
> `124-restore-automatic-recording` owns the recording behavior consuming that
> list, including per-target opt-in, the eight-second prompt countdown,
> automatic start on expiry, `Записать сейчас`, `Пропустить`, and
> `Всегда писать это приложение`. Registry expansion must not be used as a
> reason to remove those controls.

**Input**: User description: "Проверить и добавить все известные приложения
конференций, перенести и дополнить список проверенных, максимально расширить
поддерживаемые системы, включая Telegram и все возможные его форки; при
необходимости добывать и проверять отпечатки по открытым источникам."

## Clarifications

### Session 2026-07-21

- Lane: high-risk product area. The slice changes the allowlist that influences
  meeting detection and recording prompts, plus a user-facing settings surface.
- "Максимально" means exhaustive coverage of credible current macOS app
  identities and browser meeting families found during this research pass. A
  product is never promoted merely to increase the count: unverifiable or
  obsolete candidates remain explicitly deferred.
- The current MVP remains macOS. Windows-, Linux-, mobile-, and Android-only
  Telegram forks may be documented as out of scope but are not represented as
  supported desktop targets.
- A verified package/source identity is enough to make a native target
  `prompt_enabled`. The user explicitly accepted live verification after
  enablement; failures correct the fingerprint or target behavior in a follow-up.
  Auto-record still requires the user's explicit target selection and the
  existing visible-state, prerequisite, and one-action Stop gates.
- Telegram forks that ship the same macOS bundle ID are one runtime identity
  with documented aliases. They must not become duplicate competing targets.
- Existing prompt-enabled Zoom and Yandex Telemost behavior remains unchanged.
  This slice intentionally enables every native target with a verified bundle
  ID; the expansion is explicit in settings and never changes preferences
  without the user's selection or “Выбрать все” action.
- User clarification: all native applications MUST appear in one common
  applications list alongside Zoom and Yandex Telemost. The UI MUST NOT expose
  an engineering-facing “diagnostic” section. Every native target with a
  verified bundle ID uses the same prompt/auto-record row as Zoom and Telemost.
  Live start/end validation is recorded after enablement as QA evidence.
- Implementation and local validation are in scope. Commit, pull request,
  release, production registry publication, and deployment remain separate
  approval gates.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recognize More Native Meeting Apps (Priority: P1)

As a GRAF user, I want the desktop app to recognize the meeting and calling
applications I actually use, including Telegram clients and regional products,
so that supported activity is not treated as an unknown application.

**Why this priority**: Native app identity is the working meeting-detection path
today. Expanding it provides immediate coverage without adding a new permission
or detector.

**Independent Test**: Feed one synthetic stable audio-ownership event for every
catalogued bundle ID into the existing detector and confirm it resolves to one
known target with the catalogued support mode.

**Acceptance Scenarios**:

1. **Given** a package- or source-verified meeting app is active, **When** its
   bundle ID appears in stable audio-ownership evidence, **Then** GRAF resolves
   it to the correct named target instead of treating it as unknown.
2. **Given** Telegram for macOS, Telegram Desktop, Telegram A, AyuGram, or
   Kotatogram is active, **When** its verified bundle ID appears, **Then** GRAF
   identifies the correct Telegram family target.
3. **Given** Forkgram, 64Gram, or another verified Telegram Desktop derivative
   uses the same bundle ID as Telegram Desktop, **When** it appears, **Then**
   GRAF resolves it once through the shared Telegram Desktop family identity.
4. **Given** a newly catalogued target has a verified native bundle ID, **When**
   it is detected and the user selected it for auto-record, **Then** it follows
   the same prerequisite-gated visible recording flow as Zoom and Telemost.

---

### User Story 2 - Understand What Is Actually Supported (Priority: P1)

As a user reviewing meeting-detection settings, I want one readable list of
recognized applications, so that I can enable auto-record for any or all of
them without a separate engineering-status section.

**Why this priority**: A large hidden allowlist creates misleading support
claims. The product must expose the complete enabled native list while keeping
post-enable live-call evidence honest in QA documentation.

**Independent Test**: Open meeting-detection settings with the expanded registry
and confirm all verified native applications appear in one scrollable list
alongside Zoom and Telemost, with identical controls and no private meeting data.

**Acceptance Scenarios**:

1. **Given** the registry contains verified native targets, **When** the user
   opens settings, **Then** all applications appear in one common list with the
   same auto-record controls as Zoom and Telemost.
2. **Given** multiple products share one runtime identity, **When** the user
   views its row, **Then** the row names the supported family and its aliases
   without duplicate toggles.
3. **Given** the registry is unavailable and no valid cache exists, **When** the
   user opens settings, **Then** manual recording remains available and the
   support list reports that it is temporarily unavailable.

---

### User Story 3 - Cover Known Browser Meeting Systems Honestly (Priority: P2)

As a user joining meetings in a browser, I want common global and Russian
meeting systems to be recognized by service family when safe metadata exists,
without a generic browser microphone event being treated as a meeting.

**Why this priority**: Browser coverage is important, but the current native
AudioHAL allowlist cannot safely distinguish a meeting tab from voice search,
media, or another microphone-using page.

**Independent Test**: Evaluate catalogued first-party meeting-link examples and
non-meeting examples; known meeting families resolve to a manual/detect-only
target while landing, settings, media, unknown, and generic browser activity
remain manual-only.

**Acceptance Scenarios**:

1. **Given** a calendar or explicit join link uses a catalogued first-party
   meeting domain, **When** GRAF derives metadata-only intent, **Then** it records
   only the service family and never persists the raw URL, room code, title, or
   participant data.
2. **Given** a browser itself owns microphone audio, **When** no safe joined-page
   evidence exists, **Then** no recording prompt or auto-record action occurs.
3. **Given** a discontinued service or an unverifiable domain, **When** it is
   present in the research catalog, **Then** it is labelled historical or
   deferred rather than claimed as supported.

---

### User Story 4 - Publish And Roll Back The Expanded Baseline (Priority: P2)

As an operator, I want the expanded baseline to publish through the existing
versioned registry and roll back to the prior global baseline, so that existing
desktop clients receive new identities safely without a hardcoded client list.

**Why this priority**: Editing the original seed alone does not update already
deployed databases. The new baseline must use the existing publication and
last-good-cache contract.

**Independent Test**: Upgrade a database containing the current global registry,
verify the expanded version is selected while workspace-specific published
registries remain untouched, then downgrade and verify the previous global
version becomes active again.

**Acceptance Scenarios**:

1. **Given** the current global registry is published, **When** the upgrade is
   applied, **Then** exactly one newer global baseline becomes published and the
   prior global baseline becomes superseded.
2. **Given** a workspace has its own published registry, **When** the global
   baseline is upgraded, **Then** workspace-specific precedence is unchanged.
3. **Given** the new baseline is rolled back, **When** downgrade completes,
   **Then** the previous global baseline is restored without deleting workspace
   registry versions or user auto-record preferences.

### Edge Cases

- Bundle IDs are case-insensitive on macOS; case-only variants must resolve to
  one identity and must not bypass duplicate detection.
- Two different target rows claim the same bundle ID, including through a fork
  alias.
- One product ships multiple current bundle IDs or changes identity between a
  classic and current client.
- A Telegram fork changes its bundle ID in a later release or stops shipping a
  macOS build.
- A source repository declares one bundle ID while a downloadable signed package
  contains another; the package identity wins and the discrepancy is recorded.
- A package can be inspected but a live account/call cannot be created.
- An app supports voice messages as well as calls; voice-message recording must
  not be promoted to meeting-prompt evidence without live false-positive review.
- A discontinued product remains present in old installations or calendar data.
- The registry contains enough rows to overflow the current fixed settings
  layout or to make assistive navigation impractical.
- Remote registry validation fails because of one malformed or duplicate new
  target; the desktop must keep the previous valid cache.
- An existing target-scoped auto-record preference references a target that is
  renamed, superseded, or removed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST consolidate every target from the released 092
  baseline into one expanded evidence catalog, preserving it or recording an
  explicit supersession/defer reason.
- **FR-002**: Every catalog item MUST record a stable target identity, display
  name, product aliases, platform, market, support mode, evidence level,
  evidence source, verification date, and either a verified fingerprint or a
  concrete reason why no safe fingerprint is available.
- **FR-003**: The catalog MUST include current macOS-capable Telegram families
  found in this research pass, including Telegram for macOS, Telegram Desktop,
  Telegram A, AyuGram, Kotatogram, Forkgram, and 64Gram.
- **FR-004**: Telegram products sharing one verified bundle ID MUST map to one
  runtime target with aliases; distinct verified bundle IDs MUST remain distinct
  targets so the operator can validate and promote them independently.
- **FR-005**: Mobile-only, Windows-only, Linux-only, abandoned, unverifiable, or
  non-call Telegram forks MUST NOT be represented as current macOS-supported
  targets; their exclusion reason MUST be documented when they were considered.
- **FR-006**: The expanded catalog MUST cover credible current native meeting,
  calling, enterprise collaboration, and Russian VKS applications discovered
  from official packages, vendor documentation, maintained source repositories,
  or corroborated deployment metadata.
- **FR-007**: Every current native target with a verified macOS bundle ID MUST be
  `prompt_enabled` in the expanded baseline; targets without a safe bundle ID
  remain blocked.
- **FR-008**: Package-, installed-, source-, or maintained detector-verified
  identity evidence MAY authorize `prompt_enabled`; this mode MUST NOT bypass
  explicit user target selection, capture prerequisites, visible recording
  state, workspace policy, or one-action Stop.
- **FR-009**: Registry validation MUST reject duplicate target IDs and duplicate
  native bundle IDs across targets using macOS case-insensitive identity rules.
- **FR-010**: Native target matching MUST use the same case-insensitive identity
  rule as registry validation.
- **FR-011**: Every catalogued native bundle MUST resolve as a known target and
  MUST NOT become an unknown-app candidate. Auto-record requires that target to
  be explicitly selected by the user.
- **FR-012**: The desktop settings surface MUST show every verified native target
  in one common applications list using the same enabled auto-record row as Zoom
  and Yandex Telemost; it MUST NOT expose a section named “diagnostic”.
- **FR-013**: The expanded settings list MUST remain usable at the complete
  catalog size through scrolling, keyboard navigation, VoiceOver labels,
  increased text size, narrow-window behavior, and non-color-only status text.
- **FR-014**: Manual Record, Pause, Resume, Stop, the persistent local recording
  indicator, and one-action Stop MUST remain unchanged and available according
  to existing workspace policy.
- **FR-015**: Browser meeting families MUST remain separate from the native app
  allowlist and MUST require service-specific metadata plus calendar or explicit
  join intent before any target classification.
- **FR-016**: A generic browser bundle, generic microphone ownership, raw WebRTC
  activity, landing page, settings page, device test, media page, voice search,
  or unknown page MUST NOT produce a recording prompt or auto-record action.
- **FR-017**: Browser and calendar evidence MUST store only bounded service-family
  metadata; raw URLs, room codes, passwords, attendee data, titles, agenda text,
  audio, transcript text, and meeting content MUST remain excluded.
- **FR-018**: The expanded baseline MUST publish as a new version through the
  existing server registry, ETag, last-good cache, and fail-closed validation
  path; it MUST NOT add a client-only hardcoded allowlist.
- **FR-019**: Publishing the new global baseline MUST supersede only the previous
  global baseline and MUST preserve workspace-specific registries, admin review
  history, telemetry rollups, and user target-scoped preferences.
- **FR-020**: Downgrade MUST remove only the new migration-owned global baseline
  and restore the most recent prior global baseline.
- **FR-021**: Registry validation failure or network unavailability MUST retain
  the previous valid registry cache and manual recording path.
- **FR-022**: Diagnostics, tests, fixtures, and evidence MUST remain metadata-only
  and MUST NOT contain credentials, signed URLs, private local paths, raw log
  lines, meeting URLs, room codes, audio, transcripts, or private meeting data.
- **FR-023**: The feature MUST update the current product status and changelog
  with exact counts by support mode, Telegram coverage, known limitations, and
  the distinction between enabled native, blocked-without-fingerprint, and
  browser/manual targets.
- **FR-024**: The feature MUST NOT claim a production rollout, target promotion,
  or live-call verification that was not actually completed.
- **FR-025**: Post-enable live QA MUST record, per target and current app build,
  AudioHAL ownership start, ownership end, idle/prejoin behavior, voice-message
  or non-meeting audio false-positive behavior where applicable, prompt display,
  visible recording state, and one-action Stop as post-enable QA.
- **FR-026**: A target that passes FR-025 MUST update its evidence to
  `runtime_verified`; a failed target MUST be corrected or disabled without
  weakening manual recording or existing capture safety gates.

### Key Entities

- **Meeting Target Catalog Item**: One researched product or product family with
  aliases, platform/market scope, evidence provenance, current support mode, and
  either verified fingerprints or an explicit defer/exclusion reason.
- **Native App Identity**: A case-insensitive macOS bundle identifier belonging
  to exactly one runtime target, optionally shared by documented product aliases.
- **Browser Service Family**: A bounded name for a meeting provider derived from
  first-party host/path evidence without retaining the raw meeting link.
- **Registry Baseline Version**: The immutable global document that exports
  runtime targets to desktops and can supersede or restore another global
  version without overriding workspace-specific versions.
- **Support Status**: One of prompt-enabled, diagnostic-only, browser/manual,
  blocked pending fingerprint, disabled/historical, or excluded from current
  macOS scope.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the 31 released baseline targets are present in the new
  catalog or have an explicit, reviewable supersession/defer mapping.
- **SC-002**: The new runtime registry contains at least 50 distinct verified
  macOS bundle IDs across at least 40 named target families, with zero duplicate
  case-insensitive identities.
- **SC-003**: Every current macOS-capable Telegram family identified in FR-003 is
  either matched by a verified bundle ID or explicitly excluded with evidence;
  no reviewed Telegram candidate remains silently unclassified.
- **SC-004**: 100% of the 87 verified native bundle IDs are prompt-capable and
  visible in the common applications list; none auto-record until the user
  explicitly selects its target or uses “Выбрать все”.
- **SC-005**: Synthetic ownership events for every catalogued native bundle ID
  resolve to exactly one expected target and support mode after the existing
  debounce window.
- **SC-006**: Case-only identity variants resolve to the same target, and a
  registry containing duplicate case-insensitive bundle IDs is rejected before
  it can replace the last-good registry.
- **SC-007**: A user can locate an application's support status in meeting-
  detection settings within 15 seconds in the full catalog, using pointer,
  keyboard, or VoiceOver navigation.
- **SC-008**: The complete expanded registry remains below 100 KB and validation,
  lookup, rendering, and cache fallback complete without user-visible delay on
  the supported Mac baseline.
- **SC-009**: Upgrade, workspace precedence, and downgrade tests prove no loss of
  workspace registry versions, review history, telemetry rollups, or existing
  user auto-record preferences.
- **SC-010**: Focused registry, detector, migration, settings/accessibility, and
  metadata-safety checks pass, followed by the repository local CI gate with no
  new secret/content findings.

## Assumptions

- GRAF's supported client in this slice is the current Apple Silicon macOS app;
  a future Windows detector may reuse documented process names but is not
  enabled or claimed here.
- Public package metadata, maintained source declarations, and maintained
  detector allowlists are acceptable identity evidence for prompt support. Live
  account/call access produces post-enable QA evidence.
- A messaging or collaboration app is in scope only when it offers live voice,
  video, huddles, or conferencing on macOS; text-only clients are excluded.
- Browser catalog breadth is useful for intent classification, but the absence
  of a safe active-tab adapter remains manual-only rather than a reason to use
  generic browser audio ownership.
- The server-published registry, desktop last-good cache, detector state machine,
  capture prerequisite gate, prompt shell, and target-scoped preferences from
  feature 092 are reused rather than redesigned.
- No new dependency, browser extension, Accessibility permission, Screen
  Recording permission, network observer, window-title scraper, or virtual audio
  device is required for this slice.
