# Contract: Shared with me cabinet routes

## Browser collection

`GET /shared-with-me`

Authentication is required. Returns the cabinet HTML page with a recipient-only
list of meetings that the current user can open now. It returns an empty state
when no such meeting exists.

## Embedded collection

`GET /desktop/shared-with-me`

Same authorization and data as the browser route. Uses the embedded cabinet
shell and links to the existing shared-meeting egress route.

## Card target

`GET /shared-meetings/{meeting_id}?workspace_id={source_workspace_id}`

Existing contract. The collection must use this route rather than an owner
workspace meeting route. Target authorization remains authoritative and may
deny an access changed since the list render.

## Data and error rules

- Collection eligibility is active, unexpired, direct user grant plus the
  existing authoritative recipient access decision.
- A source meeting that cannot be revalidated is omitted rather than disclosed
  as an error detail.
- Pending invitations, inactive grants, expired grants, deleted meetings and
  owner/workspace metadata never appear in the collection response.
- No mutation is available through either route.
