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

The lane argument is mandatory. The fast lane uses the diff from
`origin/master` to run known server, macOS and documentation components only;
shared infrastructure, dependencies, migrations, contract/integration tests,
unknown paths or an unavailable diff expand to full. It is the fast feedback
lane, not a release gate.

GitHub Actions are disabled. No pull-request validation runs remotely. For an
early full baseline, run locally:

```sh
infra/scripts/ci-local.sh --full
```

The full lane adds macOS tests and contracts (on macOS), the complete server
suite, RLS validation, production Compose rendering and the deployment evidence
scan. A clean successful run writes a 24-hour exact-input receipt beneath the
Git metadata directory. Do not run it after every small edit.

## Local CD

Deploy from the trusted workstation through the remote-first CD gate:

```sh
infra/scripts/cd-remote.sh --dry-run
infra/scripts/cd-remote.sh --execute
```

The execute mode requires a clean tracked-and-untracked local worktree, verifies
that the current branch matches `origin/<branch>`, pins the deployment to that
exact commit SHA, then reuses a matching full-CI receipt or runs
`infra/scripts/ci-local.sh --full` as a safe fallback. On `2brain.dev`, it
verifies the remote `origin/<branch>` still resolves to the pinned SHA before reset, then performs backup, restore
rehearsal, production Compose secret-exposure scan, rebuild/up, runtime
secret-environment scan, production smoke, and public health checks.

`--skip-local-ci` is an emergency operator bypass for the full local CI step
only. It requires explicit incident approval and does not bypass the clean
worktree, branch sync, pinned SHA, backup, restore rehearsal, secret scans,
smoke, or public health gates.

Local CD does not store production secrets in GitHub.
