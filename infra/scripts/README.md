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
