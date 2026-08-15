# Quickstart: Remove Workspace Legacy

## Focused checks

From `apps/server`:

```bash
bash scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_workspace_onboarding.py \
  tests/contract/test_auth_contracts.py \
  tests/contract/test_provider_link_settings_contract.py \
  tests/contract/test_billing_ui.py \
  tests/integration/test_tenant_authorization.py \
  tests/integration/test_web_owner_session_context.py \
  tests/integration/test_billing_webhooks.py \
  tests/unit/test_billing_observation.py \
  tests/unit/test_billing_renewal_workflow.py \
  tests/unit/test_renewal_charge.py -q
```

## Obsolete surface check

```bash
test ! -e apps/server/src/twobrain_rec_server/cli/workspace_migration_report.py
test ! -e apps/server/tests/unit/test_workspace_migration_report.py
! rg -n 'workspace_migration_report|legacy_bootstrap_classification|pre-097 bootstrap' \
  apps/server/src apps/server/tests
! rg -n 'completeAdminInvitation|InvitationCompleteRequest|complete_workspace_invitation' \
  apps/server/src apps/server/tests
```

## Product scenarios

1. Complete signup twice and concurrently; assert one personal workspace/owner membership and zero internal memberships.
2. Seed a stale internal membership/session/device; assert login selects personal, list omits internal, activation and protected tenant/billing requests reject internal.
3. Create corporate invitation; assert no membership before explicit accept and one after accept.
4. Revoke corporate membership; assert personal remains accessible and queued work is not retargeted.
5. Assert canonical Russian selector labels and no internal ID/name in public HTML/JSON.

## PostgreSQL/RLS

```bash
bash scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_rls_postgres_policies.py -q
```

Expected: pass after removal of legacy report assertions; `auth_bootstrap` remains bounded for policy/callback operations.

## Repository gate

```bash
infra/scripts/ci-local.sh --fast
```

## Validation evidence — 2026-08-15

- Disposable PostgreSQL auth/workspace/billing/RLS matrix: `202 passed, 2 warnings`;
  the isolated container was removed by the wrapper.
- Fast repository gate: `1086 passed, 2 warnings`; lint and compile checks passed,
  and its isolated PostgreSQL container was removed by the wrapper.
- Post-review auth/workspace regression matrix: `116 passed, 2 warnings`; the
  isolated PostgreSQL container was removed by the wrapper.
- Obsolete workspace surface and removed admin invitation-completion endpoint checks passed.
- Browser review at 1280 × 720 confirmed the workspace hierarchy, contextual
  accessible names and empty console on synthetic data only.
- Final bypass-oriented security review found no remaining auth, tenant or billing
  blocker; `git diff --check` and the metadata-only secret-pattern scan passed.
- Deletion-focused Ponytail review removed formatter-only noise from the billing
  route, leaving its behavioral change as a two-line owner redirect guard; no new
  dependency or abstraction was retained.
- Production cleanup, commit and deployment were not executed as part of this validation.

## Pre-launch production cleanup (not executed here)

1. Standard remote backup and exact SHA receipt.
2. Resolve internal anchor from server config without printing it in evidence.
3. One-shot aggregate inventory across memberships, sessions, devices, invitations/offers, meetings/uploads/recordings, usage, referrals, subscriptions, invoices and payments.
4. Stop on any customer/financial residue.
5. With explicit approval, delete only synthetic internal-workspace memberships and dependent test sessions/devices; retain auth policy anchor.
6. Re-register test account and verify exactly one visible personal workspace and personal billing.

No cleanup execution, commit or deploy belongs to this implementation handoff.
