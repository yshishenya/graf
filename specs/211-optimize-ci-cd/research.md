# Research: Быстрый и доказуемый CI/CD

## Decision 1 — Explicit lanes, no implicit full

**Decision**: `ci-local.sh` exits with usage code when no lane is supplied. Focused commands remain feature-specific; the shared runner accepts explicit `--fast` or `--full` only.

**Rationale**: The repository already documents focused → fast → full, but the executable default silently converts copied bare commands into the most expensive lane. Making cost explicit fixes the root cause without another scheduler or CI service.

**Alternatives considered**: Keep `full` default (preserves the problem); default to `fast` (silently weakens old release instructions); infer every lane automatically (hides evidence strength).

## Decision 2 — Conservative component-aware fast lane

**Decision**: Derive changed tracked/untracked paths from the merge base with `origin/master`, disabling rename detection so both endpoints are classified. Server unit tests plus reviewed domain source select server fast checks; macOS changes select macOS validation; ordinary documentation selects consistency checks. Calendar performance paths, high-risk backend/API source, deployment evidence, shared infrastructure, dependency, migration, contract/integration-test, unknown, or unresolvable paths escalate to full.

**Rationale**: Known independent components can safely avoid unrelated work. Ambiguous paths must not trade speed for a false green result.

**Alternatives considered**: Always run the current server unit suite (not component-aware); maintain a complete dependency graph (high upkeep and drift risk); use only filename extensions (unsafe at shared boundaries).

## Decision 3 — One authoritative full inside deploy

**Decision**: `cd-remote.sh --execute` proves clean `master` and exact `origin/master` SHA, then runs `ci-local.sh --full` once before any remote production action.

**Rationale**: A local receipt has no independent provenance against another process running as the same user. Executing full at the exact deployment boundary is simpler and gives one clear source of truth without pretending to provide attestation.

**Alternatives considered**: Local JSON receipt (false trust boundary and more code); remote signed attestation (unneeded infrastructure for the current workstation flow); always run preflight plus deploy full (current duplication).

## Decision 4 — Preflight full is diagnostic only

**Decision**: The normal release path does not run full before execute. An operator may run a diagnostic preflight full, but execute intentionally repeats it after synchronization because no independently verified reuse artifact exists. `--skip-local-ci` remains an explicit incident-only bypass.

**Rationale**: Operators get one robust production command and one authoritative gate. Diagnostic work is not mislabeled as deployment evidence.

**Alternatives considered**: Trust local receipt reuse (unproven); make preflight mandatory (duplicates work); move full after remote mutation (unsafe ordering).

## Decision 5 — Isolate noisy timing proof

**Decision**: Keep the performance test's setup, database operations and functional assertions hard. Only its final load-sensitive p95 threshold becomes an expected report-only xfail on ordinary shared-host runs. The threshold is hard-required when calendar matching/performance paths change, the operator selects the controlled gate, or a synchronized-master full has no diff from which to recover relatedness.

**Rationale**: The 50 ms database timing proof has repeatedly failed only under host load and passed alone. It should measure performance, not randomly block unrelated releases.

**Alternatives considered**: Raise the threshold without evidence (weakens the requirement); delete the test (loses regression proof); keep universal hard blocking (known false negatives).

## Decision 6 — No image-registry migration in this slice

**Decision**: Keep current production build/runtime behavior. Measure it separately and design build-once/deploy-by-digest only after registry, secret custody and rollback contracts are approved.

**Rationale**: Immutable images are valuable but do not need to exist to remove duplicate full tests. Bundling them would enlarge the trust boundary and delay the requested improvement.

**Alternatives considered**: Add a registry now (unresolved provider/custody); export images over SSH (large artifacts and a new failure surface); leave as an explicit follow-up (chosen).
