# Quickstart: Running the 072 Audit Checks

This quickstart is for reviewers of the 072 read-only architecture audit. It
does not deploy and does not change product/runtime code.

## 1. Confirm Feature Anchor

```sh
git status --short --branch
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected:

- The branch is a fresh 072 audit branch, currently
  `codex/072-architecture-audit-pass2`.
- The active feature directory is `specs/072-deep-architecture-audit`.
- No product/runtime files are modified for 072 stage one.

## 2. Rebuild Static Inventories

```sh
git ls-files 'apps/server/src/twobrain_rec_server/**/*.py' | wc -l
git ls-files 'apps/macos/**/*.swift' | wc -l
git ls-files '*.sh' | wc -l
rg -n "uvicorn|rec-processing-worker|rec-postgres|rec-minio|rec-temporal" infra
rg -n "MediaScribe|Langfuse|deletion|retention|WebView|capture" docs apps/server apps/macos
```

Use tracked-file inventory commands so generated build/cache files cannot skew
the audit counts.

## 3. Review Required Artifacts

```sh
ls specs/072-deep-architecture-audit
ls specs/072-deep-architecture-audit/audit
ls specs/072-deep-architecture-audit/contracts
```

Required files:

- `spec.md`
- `plan.md`
- `research.md`
- `data-model.md`
- `contracts/architecture-finding-contract.md`
- `contracts/dependency-graph-contract.md`
- `contracts/runtime-flow-contract.md`
- `contracts/refactor-batch-contract.md`
- `audit/architecture-map.md`
- `audit/dependency-graphs.md`
- `audit/runtime-flows.md`
- `audit/findings-register.md`
- `audit/refactor-roadmap.md`
- `tasks.md`

## 4. Check For Template Leftovers

```sh
rg -n "NEEDS CLARIFICATION|\\[FEATURE\\]|\\[###|TODO|TBD|Option 1|Option 2|Option 3" \
  specs/072-deep-architecture-audit AGENTS.md \
  --glob '!specs/072-deep-architecture-audit/quickstart.md' \
  --glob '!specs/072-deep-architecture-audit/tasks.md' \
  --glob '!specs/072-deep-architecture-audit/checklists/**'
```

Expected: no unresolved template placeholders for the 072 deliverables.

## 5. Run Spec Kit Analysis

```sh
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Then review `spec.md`, `plan.md`, `research.md`, `contracts/`,
`quickstart.md`, and `tasks.md` for contradictions. 072 is complete only when
the artifacts agree on:

- read-only first stage;
- no production deploy;
- no code deletion;
- significant architecture / high-risk audit lane;
- Ponytail as form guidance, not as a lower validation lane;
- small future PR batches with focused checks.
