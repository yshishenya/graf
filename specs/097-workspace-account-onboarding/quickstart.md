# Quickstart: Workspace Account Onboarding

## Local checks

From `apps/server` run the focused tests named in `tasks.md`, then run:

```sh
infra/scripts/ci-local.sh
```

## Required scenarios

1. Register a new email without a workspace ID. Verify one user, one personal
   workspace, an owner membership and a session scoped to that personal space.
   Repeat verification and confirm no duplicates.
   For a legacy user, first run the metadata-only classification report, then
   verify that sign-in may add an empty personal fallback without moving any
   existing record or membership.
2. Create a corporate invitation for a verified email. Register or log in with
   that email. Verify the person remains in the personal space until explicitly
   accepting the offer; reject and replay paths create no membership.
3. Accept one of multiple offers. Verify only that corporate membership is
   created, personal records remain isolated, and the active space does not
   change until explicit selection.
4. Revoke a corporate membership. Verify its session can no longer read,
   upload, record, delete or audit there; the personal space remains usable.
5. Run migration upgrade/downgrade and PostgreSQL RLS receipts. Run the legacy
   report and confirm it contains only counts/classifications.
6. Browser smoke: `/sign-up`, `/login`, settings spaces and join offers work
   without rendering or requesting a raw workspace ID. Do not use real codes,
   invitations, user data or credentials in evidence.

## Production gate

After the approved release candidate passes local CI, run the documented
deploy dry-run. Production smoke uses a disposable test identity and cleans it
up, records only metadata, verifies the public health endpoint and retains the
pre-deploy backup/rollback receipt.
