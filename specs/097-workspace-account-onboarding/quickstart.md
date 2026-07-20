# Quickstart: Workspace Account Onboarding

## Local checks

From `apps/server` run the focused tests named in `tasks.md`, then run:

```sh
infra/scripts/ci-local.sh
```

## Legacy bootstrap classification and no-move operation

Before enabling this release for an installation that used the old configured
browser-login workspace, an operator with the maintenance database role runs:

```sh
cd apps/server
.venv/bin/python -m twobrain_rec_server.cli.workspace_migration_report \
  --database-url "$MAINTENANCE_DATABASE_URL" \
  --bootstrap-workspace-id "$LEGACY_BOOTSTRAP_WORKSPACE_ID"
```

The command is deliberately read-only and prints only aggregate counts: all
legacy bootstrap users (including inactive ones), active/inactive coverage,
personal-space coverage and recording ownership/count coverage.
It never prints email addresses, user/workspace/recording identifiers,
invitation details or recording content. Keep the resulting aggregate receipt
with the release evidence; do not save the connection string or command
history containing credentials.

The report is a release precondition, not a migration tool. It must show a
successful result before any separately approved membership or recording
ownership change. This feature does not move recordings, change existing
memberships or reassign workspace ownership. Take the normal pre-deploy backup
and preserve its restore-rehearsal receipt before deployment. If an unexpected
classification or runtime result appears, stop the rollout, keep all data in
place, revert the deployment to the last release and restore only through the
documented, tested backup procedure. Do not run a schema downgrade against
production as a substitute for a restore plan.

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
