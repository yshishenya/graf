# Quickstart: validation

## Prerequisites

- Start the local server with the repository's existing development command.
- Use disposable PostgreSQL data and the existing auth fixtures; never use
  production identities or meeting content.
- For local email auth use the existing development code echo/test harness.

## Focused scenarios

### Policy v1 and evidence mapping

`MERGE_POLICY_VERSION=1` is the active policy. A verified current session plus
the second verified method is required; empty duplicates may be auto-linked,
while any user-owned data requires an explicit preview confirmation. Meetings
and workspace IDs are preserved, role/billing/calendar/deletion conflicts block
the operation, and every terminal mutation is one-use and idempotent.

The focused integration suite covers dataful preservation, empty-duplicate
auto-link, completed replay, cancellation and expiry. Contract/unit checks cover
blocker fingerprints, browser/desktop route parity, CSRF and safe rendering.

1. **Email → OAuth link**: authenticate by email code, start provider link from
   settings, complete a verified OAuth callback, confirm, and verify that the
   same `user_identities.id` and meetings are visible.
2. **OAuth → email link**: authenticate by OAuth, confirm the email code, and
   verify no password prompt and no duplicate user.
3. **Empty duplicate**: create two users with one verified identity each and no
   user-owned data; prove both identities end on the survivor and no content
   rows are copied.
4. **Both accounts have data**: create meetings in separate workspaces, inspect
   preview, confirm, and verify all meetings remain with stable IDs and source
   workspaces.
5. **Role/billing/deletion blocker**: seed each blocker, verify a localized
   reason, no session issuance, and zero changed rows.
6. **Cancel, expiry, replay and concurrent confirm**: verify no partial merge,
   one completed operation at most, and deterministic idempotent retry.
7. **Ambiguous email regression**: start and verify email login for an email
   linked to multiple users; expect a recovery page/problem, never HTTP 500 or
   an arbitrary session.
8. **Settings parity**: render browser and `/desktop` account-security pages;
   verify the same method labels, actions, CSRF, accessible status and safe
   error copy.
9. **WebView boundary**: during active auth return to the original local or
   production route; outside auth, external navigation remains blocked.

## Commands

```sh
cd /Users/yshishenya/Documents/crisp
uv run pytest apps/server/tests/unit/test_provider_links.py \
  apps/server/tests/contract/test_provider_link_settings_contract.py \
  apps/server/tests/contract/test_account_routes.py
infra/scripts/ci-local.sh --fast
```

Before PR, run the full repository gate from
`docs/agent-guidance/release-and-validation.md`. Production deployment is not
part of this feature plan; if requested later, run `cd-remote.sh --dry-run`
and obtain explicit approval before execute.
