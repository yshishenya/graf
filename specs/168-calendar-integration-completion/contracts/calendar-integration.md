# Calendar integration contract

## Authoritative source projection

```json
{
  "source_id": "opaque UUID",
  "provider_family": "allow-listed provider",
  "connection_state": "connecting|needs_action|connected_selection_needed|connected|disconnected|error",
  "credential_state": "pending|sealed|revoked|purged|failed_closed",
  "sync_state": "never_synced|queued|syncing|synced|stale|credential_failed|provider_unavailable|rate_limited|failed_closed",
  "selected_calendar_count": 0,
  "readable_calendar_count": 0,
  "last_successful_sync_at": null,
  "last_safe_error_code": null,
  "safe_next_action": "select_calendars|sync|reconnect|wait|none"
}
```

No credential, raw provider response, event body, participant email or raw
meeting URL may appear in this projection.

## Operations

| Operation | Request | Success | Safe failure |
|---|---|---|---|
| Connect | provider/auth input or provider OAuth start | validated source + catalog/pending state | no source or `needs_action`/`failed` |
| List catalog | source ID | readable/hidden/unavailable catalog | source state unchanged + safe error |
| Select | source ID + deduplicated IDs | committed count and server projection | last committed selection retained |
| Sync | source ID + idempotency | accepted/running then synced/stale/failure | no duplicate job/call |
| Disconnect | source ID + CSRF | disconnected + cleanup summary | retry-safe partial/failed cleanup |

## Event normalization contract

Adapter output must contain stable provider/event/calendar identity, source
version/etag, start/end or all-day date, IANA timezone where known, recurrence
series/instance identity, cancellation/status, privacy class, safe title state,
bounded participant classifications and hashed/classified conference links.
Provider-specific extras are allow-listed and bounded.

## Failure mapping

`invalid_credentials`, `revoked_access`, `provider_timeout`,
`provider_unavailable`, `rate_limited`, `invalid_payload`,
`provider_policy_denied`, `calendar_catalog_empty`, `cursor_invalid` and
`credential_encryption_unavailable` are the only public-safe classes. Provider
HTTP bodies and tokens stay server-side.

## Compatibility

Existing `/api/v1/calendar/*`, browser cabinet and `/desktop` aliases remain
compatible unless a response adds fields. Existing 060/063/098 fields and
states remain readable. A legacy source created by synthetic/local flow must be
marked unverified until provider validation is performed.
