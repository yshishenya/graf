# Contract: Owner Journey Proof

## Required P1 Gates

052 closeout must classify each gate as `pass`, `fail`, `blocked`,
`unproven`, or `out_of_scope`.

| Gate ID | Surface | Required Evidence |
|---|---|---|
| `release-deployed` | production_infra | GitHub Release, deployed SHA, production health ready |
| `installed-app-current` | macos_native | single `/Applications/GRAF Dev.app` identity/version, source SHA, signing, availability and occupancy; public distribution acceptance remains separate |
| `fresh-record-stop-upload` | macos_native | Current installed-app record, stop, upload, or exact blocker |
| `finalize-processing` | server_backend | Accepted finalization and processing start/reuse for the same candidate |
| `transcript-diarization` | web_cabinet | Production candidate has transcript and diarization/speaker state |
| `playback-seek-timeline` | web_cabinet | Playback, timestamp seek, and speaker timeline visible and usable |
| `stored-outcomes-production` | web_cabinet | Stored outcome category states and counts on current production candidate |
| `embedded-parity` | desktop_embedded_web | macOS embedded review matches web review state for the same candidate |
| `processing-time-target` | server_backend | Representative timing measured against 180 seconds per one hour audio |
| `interface-quality` | web_cabinet, desktop_embedded_web, macos_native | No P1 overlap, overflow, false-ready, or hidden-control finding |
| `truth-docs-current` | docs_status | Status, readiness docs, changelog, and release notes share one claim |
| `forbidden-content-scan` | security | Evidence contains no forbidden private content |

## Claim Rules

- `internal_pilot_candidate` requires all P1 gates to pass.
- `pilot_blocked` is required if any P1 gate fails, is blocked, or is
  unproven.
- `production_ready` and broad `user_rollout_ready` are out of scope for 052.

## Evidence Safety

Committed evidence must not contain raw audio, transcript text, generated
private outcome text, private meeting titles, account identifiers, cookies,
tokens, credentials, signed URLs, storage object keys, or local private paths.

## T020 Metadata Probe Contract — 2026-11-17

Scope: one read-only observation of the existing
`GET /api/v1/cabinet/meetings/{meeting_id}` response, plus live/ready health.
This contract changes neither the server response nor product readiness policy.
The authoritative response is `MeetingReviewResponse`; meeting status is
`meeting.status` (the user-facing projection, not the raw ORM state).

### Inputs and safety

- `OWNER_SESSION_COOKIE` and `OWNER_MEETING_ID` are runtime-only inputs; do not
  print their values. Missing either yields `blocked / owner_context_missing`.
  Validate the meeting reference as a UUID before constructing the request.
- `PUBLIC_URL` is an explicitly selected HTTPS origin, with no userinfo, query,
  fragment or path beyond `/`. Invalid configuration and non-positive/non-finite
  timeout yield `fail / invalid_configuration` without echoing input values.
- Never forward cookies through a redirect. A redirect is a failed request.
  Requests are GET-only; no login, capture, upload, generation or data mutation.
- Emit only fixed reason codes, known enum values, booleans, counts, HTTP codes
  and the fixed redacted candidate reference. Never emit response bodies,
  exception messages, private labels, IDs, titles, text, paths, URLs, protocol
  content or source references. Unknown values become a fixed schema error.
- Unused response fields may exist. This is a strict check of the documented
  metadata subset, not a second implementation of the full server schema.

### Type and source rules

Objects below must be JSON objects, arrays must be arrays of objects, readiness
flags must be actual JSON booleans (no string/number coercion). Missing required
metadata, nulls where a type is required, unknown enums or wrong types yield
`fail / schema_mismatch`; missing arrays are never substituted with empty ones.
Category `items` arrays may be empty. Content inside them is never printed or
semantically evaluated. Check structure, not the quality of generated prose.

| Observation | Source and positive API condition |
|---|---|
| owner access | top-level `access.state=owner`, `can_view=true`, `can_view_full_meeting=true`, `content_scope=full_meeting`; allowed access states: `owner`, `team`, `shared`, `denied`, `unavailable`, `deleted`; scopes: `full_meeting`, `summary_only`; optional nested `meeting.access`, when non-null, must agree on the owner conditions |
| candidate identity | `meeting.meeting_id` must be a JSON string containing a valid UUID and equal the requested `OWNER_MEETING_ID` after UUID normalization; no ID is emitted |
| meeting | `meeting.status=ready`; known non-ready values are `local_only`, `uploading`, `submitted`, `processing`, `partial`, `blocked`, `failed`, `unavailable`, `deleted_future` |
| transcript | `transcript.available=true`, nonempty `transcript.segments`; segment objects have finite numeric `start_seconds/end_seconds`, `0 <= start <= end`; `seekable` is boolean, `seek_seconds` null or finite nonnegative number |
| speaker timeline | `speakers.available=true`, nonempty `speakers.speakers`; each lane has a `segments` array; interval objects have finite numeric `start_seconds/end_seconds`, `0 <= start <= end`; at least one positive-length interval overall |
| playback | `playback.available=true`, `can_play=true`, `state=available`, `source_mode=stored_review_m4a`, positive integer `duration_seconds`; allowed playback states: `preparing`, `available`, `unavailable`, `deleting`, `deleted`; source modes: `none`, `stored_review_m4a` |
| seek metadata | at least one transcript segment has `seekable=true` and numeric `seek_seconds` within `[0, playback.duration_seconds]`; this counts API targets only, not working UI seek |
| stored outcomes | `notes_action_truth.source_basis=stored_output`; all eight category objects have known `state`, `readiness_impact` and `items`; category rules below |

Counters: `transcript_segment_count=len(transcript.segments)`,
`speaker_count=len(speakers.speakers)`,
`speaker_interval_count=sum(len(lane.segments))`,
`seek_target_count` as defined above, and eight `outcome_item_counts` from the
category arrays. Zero is a measured empty array, not an unavailable value.
Never rename lane count as raw diarization row count or claim UI visibility.
The probe does not prove matching persisted transcript revisions, capture
lineage, candidate freshness or semantic correctness from these counters.

### Outcome state matrix

Categories: summary, key_points, decisions, action_items, followups, risks,
questions, evidence. Allowed states are `available`, `not_found`,
`not_inferable`, `processing`, `blocked`, `unavailable`, `deferred`, `unsafe`;
allowed readiness impacts are `closes_gap`, `keeps_gap_open`, `non_blocking`.
Known source bases are `stored_output`, `processing_status`, `transcript_only`,
`policy_deferral`, `not_supported`, `blocked`.

| Current stored projection | Category API result |
|---|---|
| state `available`, impact `closes_gap`, nonempty items | pass |
| state `not_found` or `not_inferable`, impact `closes_gap`, empty items | pass; zero stays zero |
| risks only: state `unavailable`, impact `non_blocking`, empty items, `protocol` is an object | pass for this current projection; protocol content is neither printed nor semantically revalidated |
| known state/impact but any other combination, including `available` with zero items | blocked; record the state/count without inventing content |
| missing/unknown/wrongly typed state, impact, items, source basis; protocol neither null nor object | fail / schema_mismatch |

All category passes also require `source_basis=stored_output`. Other known
bases keep stored-outcomes proof blocked. The special risks case follows
`stored_outcome_truth_state`; it must not become a blanket non-blocking bypass.
A negative category is an honest observation, not a successful P1 launch gate.

### Decision order, aggregate and process result

| Priority / condition | owner_review.status / reason |
|---|---|
| invalid configuration | fail / invalid_configuration |
| missing owner context | blocked / owner_context_missing |
| HTTP non-2xx (including redirects), timeout/network, decode/JSON error | fail / request_failed |
| malformed required subset or unknown enum | fail / schema_mismatch |
| well-typed response UUID differs from requested UUID | fail / candidate_mismatch |
| known access state team/shared/denied/unavailable/deleted, limited scope, view denied, or conflicting nested access | blocked / owner_access_unproven |
| known non-ready meeting state | blocked / meeting_not_ready |
| valid ready owner response with a false availability flag, zero required transcript/lane/interval/seek count, unavailable playback or blocking outcome combination | blocked / review_metadata_incomplete |
| all positive API conditions | pass / review_metadata_available |

Type/source validation precedes availability evaluation for a successful
response; failure cannot hide malformed required fields. HTTP failure and
missing input do not try to parse a nonexistent response. Conditions have the
priority shown above; incomplete positive-looking data never overrides a
negative access or meeting state.
Missing, null, non-string or invalid response UUID is `schema_mismatch`;
comparison occurs only after subset validation and before access/readiness.

Health passes only if both requests succeed with HTTP 2xx, object bodies and
exact statuses `ok`/`ready` respectively. Wrong types, JSON errors, network,
redirects, HTTP failures and other status values cannot pass. Do not echo
unknown health strings. `overall_status=pass` iff health and owner metadata both
pass; otherwise `fail` if either health observation fails or the owner result is `fail`, else `blocked`.
Process exit is 0 only for that scoped overall pass, 1 otherwise, including
missing owner inputs. This intentionally removes the former healthy-but-no-owner
zero exit code: a health-only invocation no longer looks like T020 success.

Every output includes `proof_scope=owner_review_api_metadata` and
`owner_journey_status=unproven`, including a positive observation. The P1 gate
table at the start of this contract is filled separately from direct evidence.
No full-journey gate, T019/T020 checkbox, launch claim, release or deployment is
completed automatically by this probe. T020 acceptance still requires running it
on a real current production candidate and recording the resulting states and
counts; source changes and offline tests cannot substitute for that step.

### Required offline regressions

Cover the complete positive subset; missing/null/non-string/invalid/different
response UUID and equivalent normalized UUID spelling; all projected meeting states; owner,
team/shared/denied/limited/conflicting access; empty and nested-ready incomplete
HTTP 200 responses; malformed JSON, null/scalar/list objects, wrong boolean and
array types, unknown enums; every category's empty/blocking/state/source cases
and the bounded protocol-risks exception; zero timeline and seek counters;
transport/HTTP/redirect/health errors; absent owner inputs; aggregate/exit codes;
private sentinel values excluded from stdout and errors. No network, real
cookies, real candidate, server, app, database or mail is needed for these tests.
