# Deployment Helper Scripts

Scripts in this directory are operator helpers for GRAF deployment
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

## CI Lanes

Use focused tests first while implementing. Before opening or updating a code
PR, run the fast lane:

```sh
infra/scripts/ci-local.sh --fast
```

It runs the server unit suite, Ruff and Python compile checks. It is the fast
feedback lane, not a release gate.

The **GRAF validation** GitHub workflow runs this fast server lane plus a macOS
build automatically for each PR to `master`. For an early full baseline, start
that workflow manually with `lane=full`, or run:

```sh
infra/scripts/ci-local.sh --full
```

The full lane adds macOS tests and contracts (on macOS), the complete server
suite, RLS validation, production Compose rendering and the deployment evidence
scan. Do not run it after every small edit: `cd-remote.sh --execute` runs this
full lane automatically for the exact commit that will be deployed.

## Manual CD

When GitHub Actions minutes are unavailable, deploy from the workstation through
the remote-first CD gate:

```sh
infra/scripts/cd-remote.sh --dry-run
infra/scripts/cd-remote.sh --execute
```

The execute mode requires a clean local worktree, verifies that the current
branch matches `origin/<branch>`, pins the deployment to that exact commit SHA,
then runs `infra/scripts/ci-local.sh --full`. On `2brain.dev`, it verifies the remote `origin/<branch>`
still resolves to the pinned SHA before reset, then performs backup, restore
rehearsal, production Compose secret-exposure scan, rebuild/up, runtime
secret-environment scan, production smoke, and public health checks.

`--skip-local-ci` is an emergency operator bypass for the full local CI step
only. It requires explicit incident approval and does not bypass the clean
worktree, branch sync, pinned SHA, backup, restore rehearsal, secret scans,
smoke, or public health gates.

Manual CD does not store production secrets in GitHub.
