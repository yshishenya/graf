# Research: Recording Date And Smart Title

## Decision: Use recording start time as the canonical date

**Rationale**: The local manifest already records `startedAt`, `stoppedAt`, and `createdAt`. `createdAt` is generated when the manifest is finalized, while server `created_at` is upload/create time. The user asked for "дата записи, когда она сделана", so `startedAt` is the only truthful primary date. `stoppedAt` and duration remain supporting metadata.

**Alternatives considered**:

- Server `created_at`: rejected because delayed upload would make old recordings look new.
- Manifest `createdAt`: rejected because finalization may happen after recording start.
- Processing/import time: rejected because it describes transcription lifecycle, not recording.

## Decision: Reuse `Meeting.title`, `started_at`, and `ended_at`

**Rationale**: The server already accepts `title`, `started_at`, and `ended_at` in `CreateMeetingRequest`, and the database already stores `meetings.title`, `meetings.started_at`, and `meetings.ended_at`. The desktop client currently sends `title: nil`, `started_at: nil`, and `ended_at: nil`. The smallest useful slice is to populate those existing fields from persisted local metadata before first meeting creation.

**Alternatives considered**:

- Add a new meeting-metadata service/table first: rejected for this slice because the existing create/list/detail path already has the required user-visible fields.
- Derive title/date in cabinet rendering only: rejected because search, sort, retry, and future export need stable metadata before rendering.
- Rename local package directory or object keys: rejected because it would couple user-facing names to upload/deletion/storage identity.

## Decision: Title source order for 059 is app/date, generic date

**Rationale**: Official KRISP help describes richer naming patterns, but Crisp will plan calendar integration separately in feature 060 and window title collection in a later privacy-sensitive slice. For 059, the necessary slice is smaller: use app/platform name plus recording date/time when that context is already available from approved metadata, otherwise a generic date fallback.

**Alternatives considered**:

- Always use app name + date: safe but too weak for real meeting lists.
- Include calendar matching in 059: rejected because calendar permission, matching, and connector scope move to feature 060.
- Include window-title matching in 059: rejected because it collects privacy-sensitive desktop context and is not necessary for the immediate date/title baseline.
- Add a new foreground app/window observer just for naming: rejected because 059 must not introduce a new privacy or permission surface.
- Use transcript/LLM title after processing: rejected for 059 because it introduces content inference and should be a later explicit privacy slice.

## Decision: Calendar titles are deferred to feature 060

**Rationale**: Calendar titles can include customer names, private project names, emails, or ticket numbers. Apple EventKit exposes event title/start/end data only after calendar authorization, and any server/provider calendar connector would be an auth/privacy scope expansion. The user clarified that feature 060 will plan a separate calendar integration, so 059 must not perform calendar lookup or matching.

**Alternatives considered**:

- Silent local calendar lookup: rejected because it surprises users and expands sensitive metadata collection.
- Build a full external calendar connector inside 059: rejected as too broad while the user said the frontend is currently being refactored and 060 will own the integration.
- Leave a calendar-ready contract in 059: rejected because it keeps 059 wider than necessary; 060 should own calendar matching contracts.

## Decision: Browser/window titles are deferred out of 059

**Rationale**: The prior Crisp KRISP/meeting-detection research already says browser detection should be stricter than native-app detection because browser context is noisy. Apple window names/titles are also privacy-sensitive. The user clarified that 059 should keep only the minimum necessary behavior, so browser/window title collection is deferred instead of filtered in this slice.

**Alternatives considered**:

- Store every foreground/window title: rejected because it over-collects private desktop context.
- Use browser app name plus date as `app_context`: accepted as the minimal 059 behavior when that app context is already available; richer browser tab/window titles remain deferred.
- Accept filtered approved window titles in 059: rejected because the feature can meet its immediate goal without collecting window titles.

## Decision: Store title provenance separately from the visible title

**Rationale**: The system needs to know whether a title came from an app/date fallback, generic fallback, or user rename. That distinction matters for policy, support, diagnostics, and future rename behavior. Provenance must remain metadata-only and should not imply calendar/window collection.

**Alternatives considered**:

- Store only the final title: rejected because future agents cannot explain why a title was chosen or suppressed.
- Store all raw candidates: rejected because raw contextual candidates can contain private content and 059 does not need them.
- Store provenance only in committed evidence: rejected because runtime behavior needs it for rename and policy.

## Decision: Safe filename basename is not storage identity

**Rationale**: Local packages already depend on stable required files (`manifest.json`, `mic.wav`, `incoming.wav`) and server upload/deletion depends on stable local recording/media revision ids. A human-readable safe basename should be available for future downloads/exports/local labels, but it must not define storage object keys or required track filenames.

**Alternatives considered**:

- Rename package folder on stop: rejected because upload queue and local purge could break.
- Rename `mic.wav` and `incoming.wav`: rejected because MediaScribe and package validation expect stable roles.
- Use object keys based on title: rejected because title changes, privacy policy, and deletion accounting should not alter storage identity.

## Decision: User rename and export implementation are compatibility constraints, not 059 scope

**Rationale**: The user asked to plan only the necessary minimum while frontend refactoring is active. Feature 059 should preserve title identity boundaries so a user-confirmed title or safe export basename can be used by existing/future paths, but it should not create a new rename UI/API or download/export feature.

**Alternatives considered**:

- Build rename UI/API in 059: rejected because it broadens a date/title metadata slice into a separate interaction feature.
- Build download/export in 059: rejected because the safe basename is enough for this slice and storage identity must remain stable.
- Ignore rename/export compatibility entirely: rejected because the generated title and basename must not paint later implementation into a corner.

## Source Notes

- KRISP public help checked on 2026-06-26:
  - `https://help.krisp.ai/hc/en-us/articles/8326933081116-AI-Meeting-Assistant-FAQ`
  - `https://help.krisp.ai/hc/en-us/articles/18514860919196-Krisp-s-Calendar-Integration`
  - `https://help.krisp.ai/hc/en-us/articles/21499932153244-AI-Meeting-Notes`
- Local KRISP clean-room check on this machine confirmed installed app metadata only: `/Users/yshishenya/Applications/krisp.app`, bundle id `ai.krisp.krispMac`, version `3.12.5`, audio-capture usage copy for transcription/meeting notes. No proprietary source or private meeting content was inspected.
- Apple public docs checked on 2026-06-26:
  - `https://developer.apple.com/documentation/eventkit/ekevent`
  - `https://developer.apple.com/documentation/screencapturekit/scwindow`
  - `https://developer.apple.com/documentation/appkit/nsrunningapplication`
  - `https://developer.apple.com/documentation/coregraphics/1455137-cgwindowlistcopywindowinfo`
- Repo baseline evidence checked before implementation:
  - `LocalRecordingManifest` already has `createdAt`, `startedAt`, and `stoppedAt`.
  - Desktop upload client sent nil title/start/end fields before 059.
  - Server create meeting request already accepts `title`, `started_at`, and `ended_at`.
  - Cabinet list/detail already render meeting title and started-date fallback.
