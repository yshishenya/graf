# Research: Calendar Auto Context Match

**Feature**: `098-calendar-auto-context-match`

**Date**: 2026-07-13

## Decision: Resolve automatic context at recording start without blocking capture

**Decision**: Add an authenticated, idempotent recording-start resolve operation. The macOS app calls it after local capture has started and continues recording without waiting. The request carries the stable local recording ID and actual start instant; automatic mode carries no event ID. The server reads only stored calendar snapshots, persists one bounded attempt, and returns an opaque attempt ID plus a coarse outcome. Meeting creation later consumes that attempt in the same transaction as the meeting/context state.

**Rationale**: `POST /api/v1/meetings` currently happens after capture and cannot distinguish a normal online first-party recording from an offline/recovery queue (`apps/server/src/twobrain_rec_server/api/schemas.py`, `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`). A received-time heuristic can misclassify recovery. A successful recording-start attempt is direct evidence that matching ran live against match-time snapshots, while an absent attempt safely degrades to no context. The call cannot block recording because calendar context is optional.

**Alternatives considered**:

- Match every `POST /meetings` request: rejected because old clients and recovered queues are indistinguishable and would create retrospective matches.
- Let the desktop choose from its cached upcoming list: rejected because it duplicates server rules and risks web/macOS divergence.
- Create the meeting synchronously before capture: rejected because calendar/provider availability must never gate local recording.

## Decision: Use a binary deterministic matcher, not a score

**Decision**: Automatic confidence is `high` only when exactly one effective eligible candidate remains. Any second distinct plausible event produces `ambiguous`; there is no medium-score winner.

Candidate timing rules:

- normal candidate: `event.starts_at - 5 minutes <= recording_started_at < event.ends_at`;
- an event satisfying `event.ends_at <= recording_started_at <= event.ends_at + 5 minutes` is never selected alone, but it is a back-to-back boundary blocker when another current/pre-start candidate exists;
- there is no post-end automatic grace;
- a pre-start candidate is provisional until meeting creation proves the recording continued through `event.starts_at`;
- later events during a long recording do not trigger a new decision.

**Rationale**: The feature principle is “no wrong magic.” Five minutes covers an ordinary early start while remaining much narrower than the existing 15-minute desktop lookup window. A symmetric five-minute boundary guard prevents exact and near back-to-back transitions from silently selecting a neighbor. Requiring later overlap prevents a short test recording made before a meeting from inheriting its context.

**Alternatives considered**:

- Rank candidates by title, organizer, link or attendee similarity: rejected because descriptions/titles are sensitive and similarity is not proof.
- Match only when already inside an event: rejected because it misses ordinary early starts explicitly anticipated by the spec.
- Use a post-end grace as a candidate: rejected because it would attach recordings made after a meeting ended.

## Decision: Reuse the 24-hour freshness contract and veto incomplete candidate sets

**Decision**: An active owner source with selected calendars is current only when its last successful sync is no older than 24 hours and no later sync attempt failed. Its sync horizon must cover the recording start. If any relevant selected source is stale, failed, never synced or does not cover the decision window, automatic matching records `skipped_stale_calendar`/`calendar_unavailable`; it does not choose a candidate from only the remaining sources.

**Rationale**: Feature 063 already defines 24 hours and “latest attempt failed” as stale (`apps/server/src/twobrain_rec_server/cabinet/view_models.py`). Ignoring a stale selected source could hide a second event and turn an ambiguous case into a wrong clear match.

**Alternatives considered**:

- Use only current sources when another selected source is stale: rejected because the candidate set is incomplete.
- Perform a provider refresh inside matching: rejected because provider I/O would block or destabilize recording creation.

## Decision: Make automatic eligibility stricter than calendar preview settings

**Decision**: Automatic matching ignores user opt-ins that allow private/all-day preview prompts. Eligible events must be selected, timed with `ends_at > starts_at`, non-all-day, non-private/free-busy/confidential, non-cancelled/deleted, owned by the recording owner in the same workspace, and meeting-like through participants or a meeting link/location boolean. Event descriptions, title similarity and raw link text are never evidence.

Private/free-busy events in the decision window block auto-selection with a protected skip reason. Recording lists remain generic; only the owner detail can show `Приватное событие пропущено`. All-day events are ignored completely for candidate selection and recorded only as a metadata reason/count where needed.

**Rationale**: Feature 063 preferences govern prompts and previews, while 098 governs durable recording context. The latter has a higher false-positive/privacy cost. Current normalization already exposes safe booleans, privacy state and participant counts without requiring raw provider content.

**Alternatives considered**:

- Reuse `calendar_event_matches_preferences()` directly: rejected because settings may opt into categories explicitly forbidden for 098 automatic matching.
- Treat title alone as meeting evidence: rejected because calendar blocks and reminders are common false positives.

## Decision: Dedupe only with strong stable evidence

**Decision**: Collapse candidates when they share a conference-link hash, or the same source/calendar/provider event identity plus recurrence instance. Equal raw provider IDs from different calendars or sources remain distinct unless a shared link hash proves they are the same meeting. Similar title, organizer and close time never dedupe.

**Rationale**: `dedupe_calendar_events()` intends to use a link hash, but sync currently stores only link presence/provider family in `conference_summary_json`; actual hashes are in `ConferenceLinkCandidate`. The matcher must load those hashes or persist a bounded hash summary. Current tests deliberately treat equal IDs from different sources as ambiguous.

**Alternatives considered**:

- Dedupe equal provider IDs across sources: rejected because provider namespaces are not globally stable.
- Fuzzy title/time dedupe: rejected because it can merge unrelated meetings.

## Decision: Persist a pre-meeting attempt and one authoritative context row

**Decision**: Add `RecordingCalendarMatchAttempt` keyed by workspace, owner and local recording ID, with bounded candidate IDs, safe outcome/reason, matcher version, match-time snapshots, a hashed idempotency key plus normalized-request fingerprint, and consumed/expiry state. The raw idempotency key is never stored. Convert `RecordingCalendarContextLink` into one authoritative row per workspace/meeting: the event FK becomes nullable and the row stores `context_state`, terminal user override state, matcher version, safe reason, immutable title/roster/time/series fields and timestamps. A unique nullable attempt reference prevents one attempt from backing two context rows. Audit events remain the append-only history.

**Rationale**: The existing link cannot represent ambiguous, no-context, private skip or user-cleared states, and lookup-then-insert can create concurrent active duplicates. A single authoritative row makes retries and user choices deterministic. The attempt exists before a server meeting ID and proves live matching; the context row exists for the meeting lifecycle.

**Alternatives considered**:

- Keep many historical link rows plus a separate per-meeting state table: rejected as unnecessary duplication; append-only audit already holds history.
- Store only an audit event for no-context outcomes: rejected because product UI and retry suppression need current durable state.
- Put attempts only in desktop local storage: rejected because the server must validate same-owner/same-workspace match-time evidence.

## Decision: Snapshot safe title, roster and recurrence at match time

**Decision**: On a clear or user-selected match, copy safe title state, event start/end, a bounded roster projection, roster availability, safe source label, source version and a hashed recurring series key into the authoritative context row. The roster projection contains display name only when allowed, participant kind, RSVP, workspace relation, recipient candidate class and `email_present`; it never stores a raw email, description, meeting URL or passcode.

**Rationale**: `upsert_event_snapshot()` mutates event fields and deletes/recreates participants on every sync (`apps/server/src/twobrain_rec_server/calendar/sync.py`). Reading the live event through the existing FK violates stable-history requirements. A small safe snapshot reuses the existing link and avoids versioning the entire provider event model.

**Alternatives considered**:

- Make every provider event update copy-on-write: rejected because it broadens 098 into full event versioning and complicates future-sync cleanup.
- Continue reading live event/participant rows: rejected because later rename/delete/roster changes would rewrite recording history.

## Decision: Persist server-side meeting title provenance

**Decision**: Add `Meeting.title_source`, `title_updated_at` and a nullable
`create_request_fingerprint_sha256`. Accepted sources are `user_confirmed`,
`calendar`, `app_context`, `generic`, `upload_provided`, `file_name_derived` and
`legacy_unknown`. The desktop sends its existing
`RecordingDisplayMetadata.titleSource`; manual upload assigns upload/file-name
provenance server-side. The canonical create fingerprint covers the original
title/provenance, media and timing identity plus the requested opaque calendar
attempt ID, so a safe calendar rename cannot break identical create retries.
Existing titled rows backfill to `legacy_unknown`; existing fingerprints remain
nullable and use the legacy comparison path.

A safe calendar title may replace `app_context` or `generic`, but never `user_confirmed`, `upload_provided`, `file_name_derived` or `legacy_unknown`. A user-selected correction may replace a prior calendar title. Clearing calendar context removes roster/relationship state but keeps the already visible title stable; the owner can rename it through a title workflow later.

**Rationale**: The desktop already knows title provenance, but omits it from the create payload. The server currently treats every non-empty generated title as user-owned, so 098 cannot apply calendar titles correctly. Keeping the title after clear follows the stable-history principle and avoids inventing a previous fallback value.

**Alternatives considered**:

- Treat any existing title as manual: rejected because all normal desktop recordings already send generated titles.
- Clear or regenerate title when context is removed: rejected because the previous source is not reliably reconstructable and would silently rename history.

## Decision: Model explicit selection and no-context as terminal user decisions

**Decision**: Recording-start resolve accepts `automatic`, `user_selected` with an event ID, or `user_declined`. Single-event prompts and ordinary manual Record use `automatic`; overlap selection uses `user_selected`; “Начать без календаря” uses `user_declined` and persists `declined_by_user`. Existing meeting PUT/DELETE endpoints remain correction paths; only DELETE on an already created meeting persists `cleared_by_user`. `matched_user`, `declined_by_user` and `cleared_by_user` cannot be overwritten automatically; a later explicit owner selection may replace any of them.

**Rationale**: The current desktop sends a single prompt event as `manual_selection`, so normal matches would be mislabeled. Passing `nil` cannot distinguish ordinary automatic mode from an explicit “without calendar” choice. A distinct durable decline tombstone preserves what the user did at recording start, while a clear tombstone truthfully records later removal of existing context.

**Alternatives considered**:

- Infer explicit no-context from an absent event ID: rejected because absence is also the normal automatic path.
- Allow retries to reattach after clear: rejected because it violates the user's explicit correction.

## Decision: Exclude manual uploads and offline recovery by construction

**Decision**: The manual-media endpoint never accepts a calendar attempt ID and records `skipped_manual_upload`. A desktop meeting without a valid same-owner/same-workspace recording-start attempt records `skipped_offline_or_unknown` and does not evaluate current calendar data. Recovery scanning never fabricates an attempt ID. Old clients therefore remain backward-safe and unmatched unless the owner chooses context explicitly later.

**Rationale**: `MediaRevisionSourceKind.MANUAL_UPLOAD` already distinguishes manual uploads. There is no authoritative server marker for offline recovery, so the live attempt is the conservative discriminator.

**Alternatives considered**:

- Use upload/meeting receive time: rejected because a short offline period can look live and a normal retry can look delayed.
- Auto-match old-client recordings: rejected because they cannot prove match-time calendar state.

## Decision: Recurring continuity is an authorized pointer, not copied content

**Decision**: Derive a series key from workspace/source plus provider recurring ID, falling back to iCalendar UID, and hash the key before storing it on context rows. For a matched occurrence, query the latest earlier matched meeting in the same workspace/series. Return a pointer with meeting ID, safe title/date and readiness only after the existing meeting access decision authorizes the viewer. Deleted, inaccessible or cross-space predecessors produce no placeholder and no existence signal.

**Rationale**: A pointer satisfies the preparation/review value without copying transcript or summary content into calendar state. Access must be evaluated against the previous recording, not inferred from current calendar roster.

**Alternatives considered**:

- Embed previous summary excerpts: rejected because it expands content handling and may leak stale/private meeting content.
- Use raw recurrence identifiers in diagnostics: rejected because hashes are sufficient for correlation.

## Decision: Reuse server-owned cabinet UI for web and macOS parity

**Decision**: Add a compact text state to the existing meeting row metadata and a `Контекст встречи` block to owner review. Ambiguous choices use existing calendar conflict/panel/radio patterns in the main column; roster and recurring pointer use the right-side detail panel. The embedded macOS cabinet renders the same routes. Native Swift changes are limited to resolve/selection intent and existing capture prompts; no native review screen is added.

List labels:

- `Из календаря`
- `Выбрано вами`
- `Нужно выбрать встречу`
- `Без календарного контекста`

Owner-only detail reasons distinguish automatic, user-selected, ambiguous, calendar unavailable, private skipped and user-cleared states. Roster copy states that invitees are not confirmed speakers. Candidate choices show only safe title, localized time and safe source label; no roster, description or link appears before selection.

**Rationale**: The macOS app already embeds the server meeting list/detail routes. Current calendar settings provide conflict, preview, state and accessibility patterns. One server read model prevents divergent context truth.

**Alternatives considered**:

- Add a native Swift review implementation: rejected because it duplicates the cabinet and expands scope.
- Put the ambiguous chooser in the narrow inspector only: rejected because it cannot present multiple accessible choices clearly.

## Decision: Extend lifecycle, RLS and metadata-only audit coverage

**Decision**: Treat match attempts, authoritative context state, title/roster snapshots and recurring keys as GRAF-controlled calendar artifacts. Every attempt sets `expires_at = evaluated_at + 24 hours`; an unconsumed attempt at or after that instant is rejected from consumption and becomes eligible for purge. Meeting deletion scrubs the context snapshot and accounts for it in deletion reports. Source disconnect removes unresolved candidate references from attempts/context while retaining matched safe snapshots only under the meeting lifecycle. New workspace-scoped tables receive RLS policies and validation inventory entries.

Audit events contain only matcher version, outcome, safe reason, candidate count, freshness class, decision source and booleans. They do not contain event titles, participant values, raw event IDs in metadata, URLs or provider payloads.

**Rationale**: Current deletion only unlinks the active link and current source disconnect only protects linked events. New derived artifacts must participate in the same lifecycle truth and tenant isolation as 060.

**Alternatives considered**:

- Leave expired attempts indefinitely: rejected because they are unmatched future calendar data.
- Report context deletion only through the generic meeting row: rejected because the constitution requires explicit artifact accounting.

## Decision: Use one portable migration and no new dependency

**Decision**: Create `0021_calendar_auto_context_match.py` from `0020_user_scoped_recording_ids`. Use `batch_alter_table` for existing tables, portable unique constraints for attempt/local identity and workspace/meeting context identity, and explicit PostgreSQL/SQLite partial-index clauses only where an active-row index remains necessary. Update RLS policy creation, `db/rls_validation.py`, RLS fixtures and calendar contract tests.

**Rationale**: Production is PostgreSQL while most integration tests use SQLite. The repository already has batch-alter and dual partial-index precedents. A single migration keeps title provenance and context state transition atomic for rollout/rollback.

**Alternatives considered**:

- Add a queue/worker or external cache: rejected because matching is a bounded local database decision.
- Use PostgreSQL-only JSON/index features: rejected because they would weaken local migration evidence.

## Validation Boundary

The user deferred the standalone Codex Security scan for this feature chain. Implementation still must pass the feature's normal authorization, privacy, redaction, lifecycle and forbidden-content acceptance tests because they define product behavior. Those checks must be reported as acceptance evidence, not as completion of the deferred security audit.
