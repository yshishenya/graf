# Contract: campaign provisioning

- `apps/server/scripts/manage_promo_campaign.py create` is an internal
  maintenance command, dry-run by default and explicit `--execute` for writes.
- Raw code is read from a hidden prompt or stdin, normalized and hashed in
  memory. It never appears in command arguments, output, logs or persisted rows.
- Create requires a version, `personal` scope, one optional cycle, percentage
  1-99, positive redemption cap and a UTC window where `ends_at > starts_at`.
- Existing code hashes fail closed. Disable is idempotent for an existing row;
  missing rows fail closed. No command mutates invoices or redemptions.
- The command uses the existing `twobrain_rec_maintenance`/maintenance RLS
  boundary configured for billing reconciliation and emits metadata-only JSON.
