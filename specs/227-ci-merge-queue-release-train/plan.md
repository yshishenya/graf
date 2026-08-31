# Implementation Plan: CI merge queue и provenance release train

**Branch**: `codex/227-ci-merge-queue-release-train` | **Date**: 2026-08-31

**Spec**: [spec.md](spec.md)

**Umbrella issue**: [#6207](https://github.com/yshishenya/graf/issues/6207)

## Risk / Validation Lane

`significant-feature`: shared CI, GitHub event identity, release provenance and
branch protection. Required path:
`specify → clarify → plan → checklist → tasks → analyze → taskstoissues →
implement → converge → exact-SHA validation`.

## Constitution Check

- Principle VI is preserved through testable requirements, explicit lane,
  checklist, task traceability and exact-SHA gates.
- Principle V is preserved: no signing/notarization or public app release gate
  is weakened; stale evidence is rejected.
- No capture, privacy, auth, storage, Temporal behavior or production data is
  changed.

## Architecture

```text
GitHub event
  ├─ pull_request.head.sha
  ├─ merge_group.head_sha + group/pr mapping
  └─ manual exact SHA
          ↓
event identity resolver + canonical concurrency key
          ↓
exact checkout + target/base verification
          ↓
bounded CI + final cleanliness gate
          ↓
metadata-only CI receipt
          ↓
post-merge train manifest → one authoritative Full CI → immutable decision
```

## Components and Ownership

| Component | Responsibility | Location |
|---|---|---|
| Workflow contract | events, checkout, concurrency, receipt upload | `.github/workflows/governance-fast.yml` |
| Local lane | final cleanliness and receipt metadata | `infra/scripts/ci-local.sh`, `scripts/emit-ci-evidence.py` |
| Validators | event/receipt/train schema and stale checks | `scripts/validate-ci-evidence.py`, `infra/release/` |
| Release integration | train freeze/validate/decide provenance | `infra/scripts/release-candidate.sh` |
| PR contract | required feature/SHA/receipt fields | `.github/pull_request_template.md` |
| Generic extraction | portable schemas/templates/self-tests | `harness/` |
| Documentation | operator and agent runbooks | `docs/agent-guidance/` |

## Phases

1. Contract and schema fixtures.
2. Resolver, exact checkout and unified concurrency.
3. Final cleanliness and stale evidence validation.
4. Release-train manifest and candidate integration.
5. GitHub workflow, artifact receipt and operator documentation.
6. Convergence and exact-SHA validation; enforcement remains operator-owned
   after workflow merge.

## Data and Security Constraints

- Receipts contain metadata only: no logs, secrets, private absolute paths,
  audio, transcript text or signed URLs.
- Unknown event/SHA, missing base, superseded run, changed tree or mismatched
  candidate causes fail-closed `no-go`.
- Synthetic merge SHA and actual post-merge `master` SHA are separate fields.
- Full CI evidence is write-once per candidate; changed candidate means a new
  manifest.
- No production deploy or branch-protection mutation is performed here.

## Verification Strategy

- Unit/contract tests for resolver, schemas, concurrency keys and stale states.
- Workflow static validation and synthetic PR/manual/`merge_group` fixtures.
- Local fast lane on exact SHA.
- Release-candidate rehearsal with at least three synthetic PRs and one Full CI
  receipt.
- Generic harness self-test on supported Python versions.
