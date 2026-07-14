# Calendar Auto Context API Contract

**Feature**: `098-calendar-auto-context-match`

## Purpose

Define the server-owned contract for live recording-time matching, atomic meeting consumption, owner correction/clear and safe list/review projections. This contract extends the existing ingest and calendar APIs; it does not add provider network calls, calendar writes, auto-record or attendee-based permissions.

The canonical OpenAPI document remains `specs/012-server-ingest-foundation/contracts/openapi.yaml`. Implementation must update that document and its drift tests; this file describes the 098 delta.

## Common Rules

- All endpoints are scoped by authenticated user, device and active workspace.
- A foreign workspace/user/local recording/event/attempt is indistinguishable from not found.
- Mutation endpoints preserve existing CSRF rules for cookie-authenticated web calls.
- Responses never include raw event descriptions, raw attendee emails, meeting links/passcodes, provider payloads or credentials.
- Calendar failure never blocks local capture, meeting creation, upload, processing, playback or review.
- Datetimes are timezone-aware ISO 8601 instants.
- Unknown enum values from older/newer clients degrade to safe no-context behavior.

## Recording-Start Resolve

### Endpoint

`POST /api/v1/desktop/recordings/{local_recording_id}/calendar-context/resolve`

Authentication:

- authenticated owner principal;
- registered device;
- active workspace;
- `Idempotency-Key` required.

This endpoint is best-effort and non-blocking from the desktop perspective. The app starts capture first, then calls resolve asynchronously.

### Request

```json
{
  "recording_started_at": "2026-07-13T09:00:00Z",
  "decision_intent": "automatic",
  "event_id": null,
  "contract_version": "calendar_auto_context_v1"
}
```

Fields:

- `recording_started_at`: required actual local recording start.
- `decision_intent`:
  - `automatic`: ordinary manual Record or a single clear prompt; `event_id` must be absent;
  - `user_selected`: explicit overlap/correction choice; `event_id` required;
  - `user_declined`: explicit “record without calendar context”; `event_id` must be absent.
- `event_id`: optional selected safe event UUID, allowed only for `user_selected`.
- `contract_version`: required client/server compatibility marker.

### Response

```json
{
  "attempt_id": "00000000-0000-0000-0000-000000000098",
  "context_state": "matched_auto",
  "reason_code": "single_fresh_candidate",
  "context_confidence": "high",
  "candidate_count": 1,
  "matcher_version": "calendar_auto_match_v1",
  "expires_at": "2026-07-14T09:00:00Z"
}
```

Allowed `context_state` values:

- `matched_auto`;
- `matched_user`;
- `provisional_prestart`;
- `ambiguous`;
- `no_context`;
- `skipped_private`;
- `skipped_all_day`;
- `skipped_stale_calendar`;
- `calendar_unavailable`;
- `declined_by_user`.

Response rules:

- Private/free-busy outcomes return no event ID, title, participant or link detail.
- Private/free-busy outcomes return `candidate_count=0`; the response does not reveal how many hidden events existed.
- Automatic clear matches also return no event ID; the opaque attempt is sufficient.
- `candidate_count` is metadata only and may exceed the later visible candidate cap.
- `expires_at` is exactly 24 hours after the server `evaluated_at`; an attempt at or after expiry cannot be consumed.
- Repeating the same idempotency key and request returns the same attempt.
- Reusing the idempotency key with different input returns `409 calendar_match_idempotency_conflict`.

### Matching Semantics

- The endpoint reads stored snapshots only and performs no provider request.
- Candidate start window is five minutes before event start through event end.
- A recently ended event within five minutes is a boundary blocker only.
- A pre-start result remains provisional until meeting creation proves overlap.
- Any relevant stale/failed selected source vetoes automatic matching.
- Private/free-busy/all-day/cancelled/deleted/weak-signal/cross-owner/cross-workspace events cannot become an automatic match.
- Exactly one strong deduplicated candidate is required for `matched_auto`.

## Meeting Creation Delta

### Existing Endpoint

`POST /api/v1/meetings`

New request fields:

```json
{
  "title_source": "app_context",
  "calendar_match_attempt_id": "00000000-0000-0000-0000-000000000098"
}
```

- `title_source`: `user_confirmed`, `app_context`, `generic` or `unknown` for desktop creation. Missing/unknown is treated as `legacy_unknown` when a title exists and `generic` when no title exists.
- `calendar_match_attempt_id`: optional opaque resolve result.

Consumption rules:

- The attempt must match workspace, owner, device and `local_recording_id`.
- The attempt must be unexpired and unconsumed.
- Meeting creation and attempt consumption are atomic.
- A consumed `user_declined` attempt creates meeting context state `declined_by_user`; it never creates `cleared_by_user`.
- A provisional pre-start attempt becomes `matched_auto` only if `[meeting.started_at, meeting.ended_at]` overlaps the event start; otherwise it becomes `no_context` with `prestart_not_reached`.
- A missing, invalid, foreign, expired or already-consumed attempt does not trigger a fresh calendar query; the meeting receives `skipped_offline_or_unknown`.
- A repeated idempotent meeting create returns the existing meeting/context and never consumes or creates a second attempt/link.
- Changing `calendar_match_attempt_id` or `title_source` on an idempotent retry is a conflict.
- Manual-media upload does not accept an attempt ID and receives `skipped_manual_upload`.

Meeting response adds a coarse projection:

```json
{
  "calendar_context": {
    "state": "matched_auto",
    "label": "Из календаря",
    "title_source": "calendar"
  }
}
```

Older clients may ignore this field.

## Read Meeting Calendar Context

### Endpoint

`GET /api/v1/meetings/{meeting_id}/calendar-context`

Owner response example:

```json
{
  "meeting_id": "00000000-0000-0000-0000-000000000001",
  "context_state": "ambiguous",
  "context_confidence": "ambiguous",
  "reason_code": "multiple_time_candidates",
  "decision_source": "automatic",
  "title_source": "app_context",
  "matched_title": null,
  "matched_event_starts_at": null,
  "matched_event_ends_at": null,
  "candidate_count": 2,
  "candidates": [
    {
      "event_id": "00000000-0000-0000-0000-000000000011",
      "safe_title": "Планирование",
      "starts_at": "2026-07-13T09:00:00Z",
      "ends_at": "2026-07-13T10:00:00Z",
      "safe_source_label": "Рабочий календарь",
      "roster_state": "available",
      "participant_count": 4
    }
  ],
  "roster": null,
  "previous_recurring_meeting": null,
  "can_change": true,
  "can_clear": true
}
```

Projection rules:

- Only the owner receives candidates, owner-only reason codes and correction actions.
- Matched responses expose only the bounded match-time title and interval snapshot used by review; hidden/unsafe titles and invalid intervals remain `null`.
- Authorized non-owner viewers may receive matched title provenance and safe roster context already permitted by meeting review, but no candidates, private skip reason or mutation capability.
- Private/free-busy candidate details are never returned to any viewer.
- Missing/deleted candidate snapshots are omitted and `candidate_count` remains metadata-only.
- Previous recurring context is returned only after access to that previous meeting is independently authorized.

## Select Or Correct Calendar Context

### Existing Endpoint, Extended

`PUT /api/v1/meetings/{meeting_id}/calendar-context`

Request:

```json
{
  "event_id": "00000000-0000-0000-0000-000000000011",
  "context_reason": "ambiguity_resolution"
}
```

Allowed reasons:

- `manual_selection` (compatibility);
- `ambiguity_resolution`;
- `correction`;
- `current_event_prompt` (compatibility);
- `event_start_prompt` (compatibility).

Rules:

- Owner-only mutation.
- Event must belong to an owner source and selected calendar in the same workspace.
- Private/free-busy/all-day/cancelled/deleted events cannot be selected in 098.
- The service updates the one authoritative context row; it does not insert a second active row.
- Automatic and explicit mutations are serialized against the authoritative row; an automatic result never overwrites an explicit user state.
- If two explicit owner mutations race, the last successfully committed owner action is authoritative and both attempts receive metadata-only audit history; the database still contains one context row.
- Selected state becomes `matched_user` and is terminal against automatic overwrite.
- If the meeting title source is `calendar`, the chosen safe title may replace it.
- User/upload/file/legacy titles remain unchanged.
- Match-time title/roster/time/series fields are recopied from the selected snapshot.

Response uses the same shape as GET.

## Clear Or Continue Without Context

Start-time “continue without calendar context” is represented by the consumed resolve state `declined_by_user`. The endpoint below is only for a later owner action on an already created meeting and therefore uses `cleared_by_user`.

### Existing Endpoint, Extended

`DELETE /api/v1/meetings/{meeting_id}/calendar-context`

Rules:

- Owner-only mutation.
- The operation is idempotent even when no active event is linked.
- It creates or updates the authoritative row to `cleared_by_user`.
- It clears event FK, candidate choices and roster snapshot.
- It records a safe audit reason and prevents later automatic reattachment.
- It does not silently rename the meeting; a calendar-derived visible title remains stable until an explicit title change.

Response uses the GET shape with `context_state=cleared_by_user`, no candidates and no roster.

## Meeting List Projection

`MeetingListItem` adds:

```json
{
  "calendar_context": {
    "state": "matched_auto",
    "label": "Из календаря",
    "needs_owner_action": false
  }
}
```

Allowed coarse list states:

- `matched_auto` -> `Из календаря`;
- `matched_user` -> `Выбрано вами`;
- `ambiguous` -> `Нужно выбрать встречу` for owner, generic no-context for non-owner;
- all other non-match/skip/clear states -> `Без календарного контекста`.

Private skip reason is never present in list JSON or accessible labels.

## Meeting Review Projection

`MeetingReviewResponse` adds `calendar_context` with:

- safe context state/provenance;
- owner-safe reason;
- safe candidate choices for owner only;
- immutable roster snapshot;
- optional authorized previous recurring meeting;
- correction/clear capabilities.

The existing `calendar_roster` field remains during compatibility migration and must be derived from the immutable snapshot once available. Transcript and speaker schemas remain unchanged.

## Safe Reason Codes

Allowed examples:

- `single_fresh_candidate`;
- `multiple_time_candidates`;
- `back_to_back_boundary`;
- `no_matching_event`;
- `weak_event_signal`;
- `private_free_busy_skipped`;
- `all_day_skipped`;
- `selected_source_stale`;
- `latest_sync_failed`;
- `calendar_not_connected`;
- `calendar_not_selected`;
- `calendar_unavailable`;
- `manual_upload_skipped`;
- `offline_or_unknown_skipped`;
- `prestart_not_reached`;
- `user_selected`;
- `user_cleared`;
- `meeting_deleted`.

Reason codes are not provider error strings and must map to localized product copy outside the API.

## Error Contract

- `400 invalid_calendar_match_intent`;
- `400 calendar_event_not_selectable`;
- `404 calendar_match_attempt_not_found` only for direct attempt management; meeting creation degrades safely instead of exposing attempt existence;
- `404 meeting_not_found`;
- `404 calendar_event_not_found`;
- `409 calendar_match_idempotency_conflict`;
- `409 calendar_match_attempt_consumed`;
- `409 idempotency_conflict` for meeting retry drift;
- `422 request_validation_failed` for field-shape violations.

Provider unavailability during resolve is normally a `200 calendar_unavailable` outcome because recording must continue. Authentication, tenant and malformed-request failures retain normal HTTP errors.

## Side-Effect Prohibitions

Calendar matching and every endpoint above MUST NOT:

- mutate an external calendar or RSVP;
- join or start recording;
- grant meeting access or shares;
- add recipients or send messages/reports/summaries;
- rename transcript speakers;
- fetch event descriptions/attachments for matching;
- call a provider during resolve/consumption;
- scan old meetings retrospectively.
