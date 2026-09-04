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

Use focused tests first while implementing. GitHub Actions runs the required
`governance-fast` gate for each PR. Run the local fast lane only when explicit
diagnosis or offline fallback is needed:

```sh
infra/scripts/ci-local.sh --fast
```

The lane argument is mandatory. The fast lane uses the diff from
`origin/master` to run bounded server, macOS, infrastructure/tooling and
documentation checks. Changed server contract/integration files run focused;
calendar performance paths run a focused required proof, while a missing or
renamed proof reports partial coverage without invoking a deleted path.
Deployment evidence also runs its dedicated secret/verdict scanner.
Shared/high-risk, unknown or unavailable diffs report partial coverage and
require full before release, but an explicit `--fast` never changes to `effective=full`.
Release/Spec Kit governance documents also report partial coverage. The common
whitespace check covers the merge-base diff and selected untracked files. It is
the fast feedback lane, not a release gate.

Every local lane emits one metadata-only diagnostic record under the ignored
`.dev/ci-evidence/` directory (or the path in `GRAF_CI_EVIDENCE_PATH`) and
prints `ci_evidence_path=...`. Local evidence is never authoritative for a
release candidate; supplying `GRAF_CI_CANDIDATE_FILE` does not change this.

GitHub Actions runs `governance-fast` automatically for every pull request and
is the authoritative PR gate on the exact PR SHA. The workstation does not run
CI automatically: local `ci-local.sh` is retained only for explicit diagnosis,
offline fallback, or release-operator recovery. For an early full baseline,
run locally only when it is intentionally requested:

```sh
infra/scripts/ci-local.sh --full
```

The local full lane adds macOS tests and contracts (on macOS), the complete server
suite, RLS validation, production Compose rendering and the deployment evidence
scan. Do not run it after every small edit. The normal release path runs one
manual `release-full` workflow in GitHub for the frozen candidate and reuses its
canonical evidence during production execution.

## Local CD

Deploy from the trusted workstation through the remote-first CD gate:

```sh
infra/scripts/cd-remote.sh --dry-run
infra/scripts/cd-remote.sh --execute
```

The execute mode requires a clean tracked-and-untracked local worktree, verifies
that the current branch matches `origin/<branch>`, pins the deployment to that
exact commit SHA, and re-checks the clean worktree plus local/remote SHA before
SSH. Release candidates must carry the immutable authoritative Full CI evidence
from the release workflow; the workstation does not start a local Full CI run.
On `2brain.dev`, it
verifies the remote `origin/<branch>` still resolves to the pinned SHA before reset, then performs backup, restore
rehearsal, production Compose secret-exposure scan, rebuild/up, runtime
secret-environment scan, production smoke, and public health checks.

`--skip-local-ci` is an emergency operator bypass for the full local CI step
only. It requires explicit incident approval and does not bypass the clean
worktree, branch sync, pinned SHA, backup, restore rehearsal, secret scans,
smoke, or public health gates.

Local CD does not store production secrets in GitHub.
