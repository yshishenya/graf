# Contract: desktop storage status

**Route**: `GET /api/v1/desktop/storage/status`

**Auth**: principal + device + tenant-scoped database session. `Cache-Control: no-store`.

## Response

```json
{
  "billing_role": "owner",
  "access_mode": "manage",
  "plan_code": "personal",
  "used_bytes": 123456789,
  "reserved_bytes": 0,
  "capacity_bytes": 5368709120,
  "available_bytes": 5245252331,
  "threshold": "normal",
  "action": "none",
  "action_path": null,
  "meeting_retention_days": 365,
  "source_audio_retention_days": null,
  "retention_policy_state": "active",
  "observed_at": "2026-11-16T10:00:00Z"
}
```

## Role matrix

| Role | access_mode | amounts | threshold | action | action_path |
|---|---|---|---|---|---|
| Personal owner with payer rights | `manage` | visible | exact | `open_billing_storage` when over threshold, else `none` | `/billing/storage` only when actionable |
| Corporate owner/admin | `read_only` | visible if the existing billing projection allows | exact | `contact_owner` when over threshold, else `none` | `null` |
| Member | `read_only` | `null` | `unknown` | `none` | `null` |
| Unknown role | `read_only` | `null` | `unknown` | `none` | `null` |

`read_only` does not automatically mean null amounts; only member/unknown hide them. Corporate owners are `admin` in auth, not `owner`.

## Thresholds

Exactly `normal`, `80%`, `95%`, `full`, `unknown`. Reuse `classify_storage_threshold`. Do not invent `over_capacity`.

## Failure behavior

- Missing database session: `503 cabinet_store_unavailable` (the request cannot be scoped).
- Projection failure after a valid session: HTTP 200 with `threshold=unknown`, role-appropriate visibility and `retention_policy_state` as known; never 5xx for a dependency failure.
- Unknown role/plan: fail closed with `read_only`, `threshold=unknown`, `action=none`.

## RLS

The route must use the request tenant context (`get_request_db_session` / `apply_tenant_scope(context_kind="request")`); billing tables are forced-RLS.
