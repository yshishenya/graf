# Data model: meeting-list handoff

This feature adds no persisted entity and no server schema change. The following
objects describe the existing data and the one ephemeral browser state required
to bridge them.

## Local recording projection

- Stable key: `id` (native local recording identifier).
- Server link: optional `meetingId`; absent means the server meeting has not yet
  been confirmed to the cabinet projection.
- Display data: title, start/update time, duration, status, playback/send/delete
  capabilities, and deletion flags.
- Authority: the native upload queue owns local custody; the browser must not
  infer server readiness or access from local data.

## Server meeting row

- Stable key: `meetingId`.
- Display data: the server-rendered meeting row and its processing/access state.
- Authority: the current meeting-list response owns visibility when a server
  identity exists.
- Boundary: search, status/access filters, sorting and the current visible result
  set apply to this row.

## Pending local recording handoff

- Shape: an in-memory `Set` of `meetingId` values.
- Created when: the same local `id` changes from no `meetingId` to a confirmed
  `meetingId`, or a newly loaded WebView first observes a linked projection; in
  both cases the ID must not already be a server row in the current DOM.
- While pending: the local row may remain visible as a temporary alias and one
  existing list refresh may be requested.
- Resolved when: the next authoritative list swap contains the ID or completes
  without it. It is also pruned when its native local item disappears.
- Persistence: none; a new document obtains its truth from the server list and
  native projection again.

## Invariants

1. At most one local alias and one server row for a `meetingId` are visible; once
   the server row is present, the alias is removed.
2. A non-pending local item with a `meetingId` is never rendered as a new local
   recording when the server row is absent.
3. A failed list request does not clear the pending set or delete local data.
4. Selection and focus identify the server row after a successful handoff when
   the user did not move focus during the request.
5. An authorization failure may clear private server rows from the DOM but never
   deletes the native local item or its files; the next authorized server response
   resolves the pending alias and remains the only rendered row.
