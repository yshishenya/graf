# Calendar disconnect contract

## Request and confirmation

Disconnect is an authenticated, owner-authorized, CSRF-protected destructive
operation. The confirmation must say:

> Отключить календарь? Новые встречи перестанут появляться в GRAF.
> Уже созданные встречи останутся.

Cancel is a no-op and closes the confirmation without a request.

## Transactional sequence

1. Lock/claim source and reject a second disconnect as idempotent success.
2. Mark source disconnecting and prevent new sync-job claims/decryption.
3. Do not call a provider revoke endpoint. Mark the credential payload locally
   purged and permanently unavailable to runtime.
4. Retain only content-free lifecycle metadata for 30 days.
5. Clear selections and mark catalog rows disconnected.
6. Delete future event snapshots and dependent participants/link/reminder rows;
   detach audit references safely.
7. Delete unconsumed match attempts; scrub consumed attempts.
8. Detach matched context snapshot/provider references and mark
   `calendar_unavailable` when its source was the only candidate. Preserve
   safe meeting-retention copy only as explicitly approved.
9. Set source `disconnected`, `failed_closed`, zero selected count and commit.
10. Return cleanup summary and refresh source projection.

## Response

```json
{
  "source_id": "opaque UUID",
  "connection_state": "disconnected",
  "sync_state": "failed_closed",
  "credentials_purged": true,
  "future_cache_purged": true,
  "matched_context": "retained_safe_snapshot|detached|deleted_by_policy",
  "idempotent": false
}
```

No secret, provider error body or event content is returned.
The successful UI result is exactly «Календарь отключён от GRAF.» and
does not include provider-side revoke guidance.

## Postconditions

- Reload does not show the disconnected source as active.
- Manual sync cannot contact provider and returns `failed_closed`.
- Worker cannot decrypt/read credential envelope for the source.
- Upcoming/desktop endpoints exclude future data from that source.
- Reconnect creates a new validated operation; it cannot resurrect old cache.
- Other tenant/user cannot observe source existence or cleanup details.
