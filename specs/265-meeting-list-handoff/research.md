# Research: immediate meeting-list handoff

## Decision 1: refresh the existing list from the shared local-recording projection

- **Decision**: Detect the first `meetingId` transition in
  `GRAFLocalRecordings.update` and call the existing
  `requestMeetingListRefresh` path once.
- **Rationale**: The native upload callback already publishes every server-truth
  update through this function. The cabinet already has one authoritative HTMX
  request path that preserves the current form state, stale-response fencing,
  loading state, result announcements and focus recovery.
- **Alternatives considered**: A new Swift-to-WebView message would duplicate
  the existing projection boundary; a new API or push channel is unnecessary for
  a state that is already committed before `POST /api/v1/meetings` returns.

  A newly created WebView can first receive an already completed linked
  projection. It uses the same one-shot reconciliation when that `meetingId` is
  missing from the current server DOM, so the result does not depend on whether
  the native update arrived during or before page navigation.

## Decision 2: retain a temporary local alias until the authoritative response

- **Decision**: Keep a newly handed-off local row only while its `meetingId` is in
  an in-memory pending-handoff set. Resolve that set on the next list swap: a
  matching server row replaces the alias, and a missing row removes it.
- **Rationale**: The current code filters every row with `meetingId` out before
  the browser has asked for the server list. Removing the alias immediately
  creates the observed empty interval. Keeping all historical aliases forever
  would violate the existing rule that a server identity belongs to the current
  result set and could resurrect rows excluded by filters or the visible result
  boundary.
- **Alternatives considered**: Always rendering a local alias for every known
  `meetingId` risks duplicates and stale resurrection; removing the alias only
  after upload finalization still leaves a gap because server identity arrives
  before finalization.

## Decision 3: one-shot, coalesced refresh instead of permanent polling

- **Decision**: One publication can submit one list form request containing all
  newly observed handoff IDs. Repeated progress publications do not submit again.
- **Rationale**: Native upload progress is frequent. Existing server polling is
  intentionally conditional on rows the browser already knows about, so it
  cannot discover this new meeting. A transition-triggered request discovers it
  without turning every cabinet into a one-second list poll.
- **Alternatives considered**: Enabling polling unconditionally adds network and
  server load and changes a broad product behavior; refreshing on every progress
  fragment creates request races and HTMX churn.

## Decision 4: preserve current query and interaction state

- **Decision**: Use the current `.cabinet-list-controls` submission and existing
  focus recovery. Ask for focus restoration only when focus started inside the
  meeting list; do not move focus out of a modal or active form input.
- **Rationale**: The form already serializes the current search, filters and sort.
  Existing `listRefreshFocusMeetingIds` and server-row identity mapping can move
  selection/focus from a local alias to the authoritative row.
- **Alternatives considered**: A direct `window.location.reload()` discards
  interaction state and was the user-visible workaround; a new notification or
  toast adds a second path without improving list truth.

## Decision 5: preserve local visibility on refresh failure

- **Decision**: When the existing list recovery state is shown for an ordinary
  service/offline failure, include pending local rows in that state and retain
  the existing retry button. For `401/403`, keep the existing privacy recovery:
  clear private server-list DOM, retain native local custody, and reconcile from
  the next authorized server response.
- **Rationale**: A failed list request is not evidence that the recording failed
  or was deleted. The user must continue to see that the local recording exists
  while the server list is temporarily unavailable.
- **Alternatives considered**: Replacing the entire region with only an error
  hides the only visible recording state; treating a failed request as deletion
  would violate local custody and data-loss safeguards.

## Decision 6: no server, Swift, or data-model changes

- **Decision**: Keep the implementation in the shared cabinet JavaScript and
  browser coverage. Do not change meeting creation, upload finalization,
  processing, retention, deletion, authorization, or the native bridge payload.
- **Rationale**: The source trace shows the meeting is committed before the
  client receives the identity. The defect is a missing browser refresh and an
  overly early local-row projection removal, not a server persistence failure.
- **Alternatives considered**: Changing server commit timing or adding a new
  event stream would expand scope and introduce failure modes without fixing the
  existing DOM handoff contract.
