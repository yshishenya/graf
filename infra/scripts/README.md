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

Every lane emits one metadata-only evidence record under the ignored
`.dev/ci-evidence/` directory (or the path in `GRAF_CI_EVIDENCE_PATH`) and
prints `ci_evidence_path=...`. Set `GRAF_CI_CANDIDATE_FILE` for the single
authoritative Full CI run so its evidence is bound to the frozen candidate.

GitHub Actions are disabled. No pull-request validation runs remotely. For an
early full baseline, run locally:

```sh
infra/scripts/ci-local.sh --full
```

The full lane adds macOS tests and contracts (on macOS), the complete server
suite, RLS validation, production Compose rendering and the deployment evidence
scan. Do not run it after every small edit; the normal production path runs the
authoritative full inside execute.

## Local CD

Deploy from the trusted workstation through the remote-first CD gate:

```sh
infra/scripts/cd-remote.sh --dry-run
infra/scripts/cd-remote.sh --execute
```

The execute mode requires a clean tracked-and-untracked local worktree, verifies
that the current branch matches `origin/<branch>`, pins the deployment to that
exact commit SHA, runs one `infra/scripts/ci-local.sh --full`, and re-checks the
clean worktree plus local/remote SHA before SSH. On `2brain.dev`, it
verifies the remote `origin/<branch>` still resolves to the pinned SHA before reset, then performs backup, restore
rehearsal, production Compose secret-exposure scan, rebuild/up, runtime
secret-environment scan, production smoke, and public health checks.

`--skip-local-ci` is an emergency operator bypass for the full local CI step
only. It requires explicit incident approval and does not bypass the clean
worktree, branch sync, pinned SHA, backup, restore rehearsal, secret scans,
smoke, or public health gates.

Local CD does not store production secrets in GitHub.
