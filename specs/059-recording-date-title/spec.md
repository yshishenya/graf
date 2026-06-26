# Feature Specification: Recording Date And Smart Title

**Feature Branch**: `codex/059-recording-date-title`

**Created**: 2026-06-26

**Status**: Implemented locally with full CI pass; pending PR review, release,
deploy, and app bundle evidence

**Input**: User description: "берем номер 059 для фичи. Пока только планируем ее детально. Так-как у нас щас идет процес рефакторинга фронта. Нужно проставлять дату записи, когда она сделана. Нужно проставлять имя файла и продумать откуда его брать: KRISP берет из приложения плюс дату; для браузера - название окна, из которого писали звук; если есть календарное мероприятие на эту дату/время - название из встречи в календаре. Посмотреть KRISP, интернет, полный анализ."

## Clarifications

### Session 2026-06-26

- Q: Should 059 include calendar title lookup, or defer calendar integration? → A: Defer all calendar integration and matching to feature 060; 059 keeps only the minimum needed date/title/basename behavior without calendar access.
- Q: Should 059 collect window titles, or keep only the minimum title/date fallback? → A: Keep 059 to recording date plus app/date/generic title and safe basename; defer window title collection to a later privacy-sensitive slice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Show The Real Recording Date (Priority: P1)

As a meeting owner, I want every recording in the desktop and web review surfaces to show when the recording was actually made, so that delayed upload, processing, or UI refresh does not make old meetings look new.

**Why this priority**: Date truth is the least risky and highest-value part of the feature. The repository already records local `startedAt` and `stoppedAt`; the gap is carrying that truth into meeting creation and list/detail display consistently.

**Independent Test**: Create a recording, delay upload or processing, then verify the meeting list and detail page show the recording start date/time rather than server upload or processing time.

**Acceptance Scenarios**:

1. **Given** a local recording starts at 2026-06-26 14:30 local time and uploads later, **When** the owner opens the meeting list, **Then** the visible date/time is based on the recording start instant.
2. **Given** a recording has a start and stop time, **When** the meeting detail page is shown, **Then** the page can distinguish recording start, recording end, duration, and processing/upload state without implying the upload time is the recording time.
3. **Given** a legacy meeting has no recording start time, **When** it appears in the list, **Then** the UI shows a truthful fallback such as "Без даты" rather than inventing a date.

---

### User Story 2 - Generate A Minimal Recording Title (Priority: P1)

As a meeting owner, I want new recordings to receive a minimal useful title automatically, so that the meeting list is readable without collecting calendar or window titles.

**Why this priority**: The product already has uploaded recordings, transcripts, playback, notes, and list deletion. A small app/date fallback closes the immediate list readability gap without adding a new privacy-sensitive metadata collector.

**Independent Test**: Create recordings with an approved app context and unknown context, then verify each meeting receives the expected app/date or generic fallback without calendar or window-title access.

**Acceptance Scenarios**:

1. **Given** the approved capture app or platform name is known, **When** the recording is created, **Then** the title uses the app/platform name plus recording date/time.
2. **Given** no reliable app/platform name exists, **When** the recording is created, **Then** the title falls back to a generic date/time title such as `Meeting - 2026-06-26 14:30`.

---

### User Story 3 - Keep A Safe Filename Basename (Priority: P2)

As a meeting owner, I want future downloads, exports, and local record labels to have safe filenames derived from the meeting title and date, so that files are recognizable without leaking unsafe strings or breaking storage identity.

**Why this priority**: The user asked for "имя файла", but the product must not couple human titles to internal object keys or required track names. A safe basename gives user value while preserving upload, deletion, and retry invariants.

**Independent Test**: Generate titles from app/platform and generic fallback sources; verify the derived basename is stable, filesystem-safe, includes date/time, and does not rename required track files.

**Acceptance Scenarios**:

1. **Given** a recording title is `Weekly Product Sync`, **When** a safe basename is generated, **Then** it follows a date/title/suffix pattern such as `2026-06-26_14-30_weekly-product-sync_ab12cd`.
2. **Given** a title contains slashes, control characters, URLs, email addresses, meeting codes, or excessive length, **When** the basename is generated, **Then** unsafe content is removed or replaced and a stable suffix prevents collisions.
3. **Given** local package files exist as `manifest.json`, `mic.wav`, and `incoming.wav`, **When** the safe basename is generated, **Then** those required files and storage object identities are not renamed.

---

### User Story 4 - Preserve Privacy And Rename Control (Priority: P2)

As a privacy-conscious owner or admin, I want title source and policy behavior to be explicit, so that 059 does not silently collect calendar or window context.

**Why this priority**: Calendar and window titles can contain customer names, emails, URLs, ticket numbers, or private project names. This slice should not cross that trust boundary.

**Independent Test**: Run the naming resolver without calendar/window inputs; verify it chooses conservative app/date or generic titles, records metadata-only provenance, and remains compatible with an explicit user-confirmed title replacement without changing stable identities.

**Acceptance Scenarios**:

1. **Given** calendar or window-title data may exist outside 059, **When** a 059 title is generated, **Then** the visible title ignores those sources and uses only app/date or generic fallback.
2. **Given** an existing or future explicit rename path marks a title as user-confirmed, **When** the list, detail, export, and deletion surfaces render later, **Then** the user title takes precedence without changing local recording identity, upload identity, media revision identity, storage object keys, or deletion accounting.
3. **Given** title provenance is included in diagnostics or evidence, **When** evidence is committed or exported, **Then** it remains metadata-only and does not include raw private meeting content, raw URLs, tokens, credentials, transcript text, or audio.

### Edge Cases

- Upload happens hours or days after recording.
- User changes system timezone between recording and upload.
- The recording starts before midnight and stops after midnight.
- Local manifest exists but has missing or invalid start/stop time.
- Server already has a meeting for the same local recording because the upload is retrying.
- Existing meeting was created by an older client with no title or start time.
- Two recordings start in the same minute and produce the same sanitized title.
- Calendar access, calendar event matching, and calendar event titles are deferred to feature `060-calendar-integration`.
- Browser/window title collection and filtering are deferred to a later privacy-sensitive slice.
- Native app title is unavailable and only the app bundle/name is known.
- Approved app/platform context changes during the recording.
- An explicit user-confirmed title replacement arrives while upload or processing is still in progress.
- Deletion or export reports need to refer to the meeting after title changes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST use the local recording start instant as the canonical recording date for new recordings.
- **FR-002**: The desktop upload path MUST pass recording start and stop instants to meeting creation when local manifest data is available.
- **FR-003**: Web and desktop review surfaces MUST display recording date/time from the recording start instant, with truthful fallback copy when the date is unavailable.
- **FR-004**: The product MUST generate an initial meeting title before first meeting creation using this source order: user-confirmed title, already-available approved app/platform name plus recording date/time, generic recording date/time fallback.
- **FR-005**: Calendar access, calendar event matching, and calendar-derived titles MUST be out of scope for feature 059 and deferred to feature 060.
- **FR-006**: Browser/window title collection, filtering, and window-derived titles MUST be out of scope for feature 059 and deferred to a later privacy-sensitive slice.
- **FR-007**: Title sanitization MUST remove control characters and reject or suppress raw URLs, credentials, invite links, email addresses, and other unsafe strings before they become visible meeting titles or filenames.
- **FR-008**: Feature 059 MUST NOT introduce a new rename UI/API; when an explicit existing or future rename path provides a user-confirmed title, that title MUST take precedence over generated titles and MUST NOT change stable local recording identity, upload identity, media revision identity, object storage keys, or deletion lifecycle accounting.
- **FR-009**: The product MUST record title source and confidence in persisted local manifest/upload metadata separately from the visible title; server-side title provenance is optional in 059 and may be added only when an existing metadata-only API path already supports it.
- **FR-010**: The product MUST derive a safe filename basename from recording date/time, sanitized title, and a short stable suffix for future exports/downloads/local labels.
- **FR-011**: The product MUST NOT rename required local package files (`manifest.json`, `mic.wav`, `incoming.wav`) or server storage object keys based on the visible title.
- **FR-012**: Upload retries MUST be idempotent: the same local recording must not conflict merely because upload happened later, processing completed later, or the generated title/date is recomputed from the same persisted metadata.
- **FR-013**: Existing meetings without title/date metadata MUST remain viewable and searchable; the UI must use truthful fallbacks without mutating old data silently.
- **FR-014**: Search and sort behavior MUST continue to support title search and recording-date sort for meetings that have the new metadata.
- **FR-015**: Evidence committed to the repository for this feature MUST be metadata-only and MUST NOT include raw audio, transcript text, participant emails, raw browser URLs, tokens, signed URLs, or private meeting content.
- **FR-016**: The product MUST preserve canonical recording instants across timezone changes; display labels may use existing user/workspace display timezone behavior, but upload, retry, and sort logic must not replace the recording start instant.
- **FR-017**: Feature 059 MUST NOT add a new app/window observer or permission prompt only to discover a title source; if approved app/platform context is absent, ambiguous, or changes during recording, the resolver must use persisted deterministic metadata or the generic fallback.

### Key Entities

- **Recording Time Metadata**: The recording start instant, stop instant, display timezone, duration, and fallback state used to answer "when was this recorded?"
- **Meeting Title**: The user-visible name of the meeting, generated at creation or later renamed by the user.
- **Title Source Candidate**: A candidate title from app/platform or generic fallback, with source, confidence, suppression reason, and sanitized value.
- **Title Provenance**: Metadata-only record explaining which source won, which sources were suppressed, and why.
- **Safe Filename Basename**: A filesystem-safe, collision-resistant basename for future downloads/exports/local labels that is derived from date/time and sanitized title but does not define storage identity.
- **Stable Recording Identity**: Existing local recording directory/session/media revision identifiers that remain independent from display titles and filenames.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of new recordings with valid local manifest start time show a recording date based on the start instant in both list and detail surfaces.
- **SC-002**: A delayed-upload validation where upload happens at least 24 hours after recording still displays the original recording date/time, not the upload date/time.
- **SC-003**: The naming QA matrix covers approved app/platform fallback, generic fallback, source-unavailable fallback, duplicate-title cases, calendar-deferred behavior, and window-title-deferred behavior with all expected title-source outcomes recorded.
- **SC-004**: No generated visible title or safe basename in the QA matrix contains control characters, raw URLs, email addresses, credentials, invite links, or reserved filesystem separators.
- **SC-005**: Title identity validation proves generated titles and explicit user-confirmed title replacements do not change local recording id, media revision id, upload idempotency, playback, transcript, outcomes, or deletion accounting.
- **SC-006**: Existing legacy meetings without title/date metadata remain readable and do not fail list/detail rendering.

## Assumptions

- Feature `059` is implemented locally after the post-057/058 merge basis and
  has passed full local CI; PR, release, deployment, and app bundle evidence
  remain separate closeout gates.
- Selected lane is `high-risk-feature` because the feature touches user-facing workflow, local recording metadata, server review surfaces, and explicit deferral of privacy-sensitive calendar/window metadata.
- The current frontend refactor should consume existing meeting fields where possible; this feature should not introduce a new frontend architecture or design system.
- Feature 059 does not implement a new rename UI/API, download/export feature, calendar connector, window observer, or app-observer permission flow.
- Calendar title use is out of scope for 059 and deferred to feature 060, which will own calendar permission, matching, source confidence, and connector scope.
- Transcript-derived or LLM-generated titles are out of scope for this feature.
- Auto-record/detect-and-ask behavior remains governed by `011-assisted-auto-recording`; this feature only supplies recording metadata and naming behavior that can be reused by manual or assisted recordings later.
- Download/export implementation may use the safe basename in future slices; feature `059` only defines and persists it where needed so later export code has a safe value.
