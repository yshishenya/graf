# Contract: shared meeting egress

## Existing routes

Для принятого внешнего `full_meeting` grant сохраняются существующие relative
routes:

- `GET /api/v1/cabinet/shared-meetings/{meeting_id}/playback`
- `GET /api/v1/cabinet/shared-meetings/{meeting_id}/downloads/audio`
- `GET /api/v1/cabinet/shared-meetings/{meeting_id}/downloads/transcript`
- `GET /api/v1/cabinet/shared-meetings/{meeting_id}/content-exports`
- `POST /api/v1/cabinet/shared-meetings/{meeting_id}/content-exports`

## Authorization contract

1. Route computes the existing recipient proof and authorizes the meeting.
2. The same proof is passed through every egress recheck.
3. Egress independently rechecks active grant, exact recipient, scope,
   expiry/revoke, deletion, policy, revision and storage state.
4. No route returns a storage URL, internal object key, raw upload or workspace
   metadata.

## Output contract

- playback returns the existing inline canonical M4A stream and Range behavior;
- audio/transcript downloads return existing attachment responses;
- content exports return only the existing server-generated formats advertised
  by capabilities;
- unavailable artifacts retain the current safe error/status contract.

`summary_only` remains restricted to summary behavior and cannot use these full
content paths.
