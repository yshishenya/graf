# Meeting-list handoff UI contract

This is an internal browser/native projection contract. It adds no endpoint and
does not change the existing `GRAFLocalRecordings.update(rows, operations,
recoveryRequired)` argument shape.

## State transition

```text
local row (meetingId absent)
  -> native projection receives meetingId
  -> one current-form list request
  -> local alias remains while response is pending
  -> matching server row replaces alias
```

If the authoritative response does not include the meeting in the current
search/filter/visible-result context, the alias is removed after that response
and is not recreated by later progress updates with the same `meetingId`.

A newly loaded WebView may first observe an already completed linked projection;
when its server row is absent, it follows the same one-shot reconciliation.

An authorization failure (`401/403`) is a privacy boundary, not a deletion
signal: private server rows are removed from the browser DOM and the existing
authorization/access recovery state is shown. The native local projection and
local files remain available to the desktop queue. After the user restores the
session or workspace, the next authoritative list response wins; a matching
server row replaces the alias and no duplicate is rendered.

## Required behavior

- Handoff detection is edge-triggered per stable local ID, not progress-triggered.
- Multiple IDs observed in one native publication share one list request.
- The request uses the existing list form, preserving search, filters and sort.
- Existing stale-HTMX-response fencing remains authoritative.
- A matching server row transfers selection and list focus from the alias where
  the existing focus rules allow it.
- Focus in a modal or another user-controlled field is not stolen by the refresh.
- Service/offline failure leaves the local state visible and exposes the existing
  list retry path; a failed request is not treated as deletion.
- `401/403` clears private server-list DOM and preserves native local custody;
  reauthorization reconciles the server row without a local duplicate.
- The contract does not add notifications, a second progress surface, polling,
  server push, credentials, local paths or meeting content.
