# Deployment Helper Scripts

Scripts in this directory are operator helpers for 2brain Rec deployment
readiness. They should fail closed, avoid printing secret values, and emit
metadata-only evidence suitable for `docs/deployments/2brain-rec/`.

Scripts must preserve the 021 boundary: first production smoke validates only the
accepted 012 ingest boundary.

Default remote target:

- SSH host: `2brain.dev`
- Deploy path: `/opt/projects/2brain-rec`
- Public endpoint: `https://rec.2brain.pro`

Local execution is for dry-run checks only: tests, compile, compose rendering,
and content scans. Backup, migration, deployment, first production smoke,
cleanup, and final evidence are remote operations on `2brain.dev`.

## Local CI

Run the local CI gate before commits or pushes when GitHub-hosted Actions minutes
are unavailable:

```sh
infra/scripts/ci-local.sh
```

It runs server tests, Ruff, compileall, production Compose rendering, and the
deployment evidence scan. It does not contact production or run remote smoke.

## Manual CD

When GitHub Actions minutes are unavailable, deploy from the workstation through
the remote-first CD gate:

```sh
infra/scripts/cd-remote.sh --dry-run
infra/scripts/cd-remote.sh --execute
```

The execute mode requires a clean local worktree, verifies that the current
branch matches `origin/<branch>`, pins the deployment to that exact commit SHA,
then runs local CI. On `2brain.dev`, it verifies the remote `origin/<branch>`
still resolves to the pinned SHA before reset, then performs backup, restore
rehearsal, production Compose secret-exposure scan, rebuild/up, runtime
secret-environment scan, production smoke, and public health checks.

`--skip-local-ci` is an emergency operator bypass for the local CI step only.
It does not bypass the clean worktree, branch sync, pinned SHA, backup, restore
rehearsal, secret scans, smoke, or public health gates.

Manual CD does not store production secrets in GitHub.
