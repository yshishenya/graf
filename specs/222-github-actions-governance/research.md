# Research: Feature 222

## Decisions

1. **Use `pull_request` plus explicit `workflow_dispatch`** — PR events provide
   the authoritative head SHA; manual runs are bounded audits and require a
   caller-supplied SHA.
2. **Use per-PR concurrency with cancellation** — this is the native GitHub
   mechanism for stopping obsolete runs and prevents a new commit from waiting
   behind an old one.
3. **Reuse local fast lane** — the repository already owns scope detection,
   stale-SHA evidence and metadata-only output in `ci-local.sh`; duplicating the
   test graph in YAML would drift.
4. **Keep Full CI outside PR workflow** — release candidates need one immutable
   authoritative run, not repeated full runs for every feature commit.
5. **Enable branch protection last** — required check names are immutable only
   after the workflow has produced a real successful PR run.

## Rejected Alternatives

- Running Full CI on every PR: too slow and recreates the user's race.
- Deploying a shared Dev environment from GitHub Actions: unsafe and outside
  the local single-manifest operator boundary.
- Uploading raw logs: violates metadata-only evidence and can expose secrets or
  meeting data.
