# Research: Быстрый и доказуемый CI/CD

## Decision 1 — Explicit lanes, no implicit full

**Decision**: `ci-local.sh` exits with usage code when no lane is supplied. Focused commands remain feature-specific; the shared runner accepts explicit `--fast` or `--full` only.

**Rationale**: The repository already documents focused → fast → full, but the executable default silently converts copied bare commands into the most expensive lane. Making cost explicit fixes the root cause without another scheduler or CI service.

**Alternatives considered**: Keep `full` default (preserves the problem); default to `fast` (silently weakens old release instructions); infer every lane automatically (hides evidence strength).

## Decision 2 — Conservative component-aware fast lane

**Decision**: Derive changed tracked/untracked paths from the merge base with `origin/master`. Server source/unit-only changes select server fast checks; macOS changes select macOS validation; documentation selects consistency checks. Shared infrastructure, dependency, migration, contract/integration-test, unknown, or unresolvable paths escalate to full.

**Rationale**: Known independent components can safely avoid unrelated work. Ambiguous paths must not trade speed for a false green result.

**Alternatives considered**: Always run the current server unit suite (not component-aware); maintain a complete dependency graph (high upkeep and drift risk); use only filename extensions (unsafe at shared boundaries).

## Decision 3 — Local exact-input receipt

**Decision**: A clean successful full run writes a versioned JSON receipt beneath `git rev-parse --git-path`, using atomic replacement and restrictive permissions. It binds result/times to commit, tree, runner files, lockfiles, test surface, local toolchain and the exact ordered list of platform-required full stages from a private temporary runner journal. Default validity is 24 hours.

**Rationale**: The deploy begins on the same trusted workstation/worktree, so a local receipt removes the duplicate run without introducing a remote service. Input recomputation makes copied or stale evidence fail closed; requiring the complete mode-`0600` stage journal prevents a direct `create` call with only invented collection metadata. A compromised same-user workstation remains outside this local optimization's trust boundary and still requires credential/host incident handling.

**Alternatives considered**: Commit the receipt (self-invalidating/noisy); store in the worktree (breaks clean-tree gate); sign remotely (unneeded infrastructure for a local workflow); trust only SHA (misses runner/toolchain drift).

## Decision 4 — Deploy fallback, not receipt hard dependency

**Decision**: `cd-remote.sh --execute` validates the receipt after clean-tree, branch and remote-SHA checks. Valid means reuse; missing/invalid means run `ci-local.sh --full`, then require the newly created receipt. `--skip-local-ci` remains an explicit incident-only bypass.

**Rationale**: Operators keep one robust command. Receipt bugs or cleanup cannot strand a release, while no invalid evidence can silently weaken validation.

**Alternatives considered**: Block deploy when receipt is missing (less resilient); always repeat full (current waste); accept a manual `--receipt` path (copy/paste and provenance risk).

## Decision 5 — Isolate noisy timing proof

**Decision**: Keep functional tests hard. Mark the existing serial performance phase report-only on ordinary shared-host full runs, but hard-required when calendar matching/performance paths change or the operator selects the controlled performance gate.

**Rationale**: The 50 ms database timing proof has repeatedly failed only under host load and passed alone. It should measure performance, not randomly block unrelated releases.

**Alternatives considered**: Raise the threshold without evidence (weakens the requirement); delete the test (loses regression proof); keep universal hard blocking (known false negatives).

## Decision 6 — No image-registry migration in this slice

**Decision**: Keep current production build/runtime behavior. Measure it separately and design build-once/deploy-by-digest only after registry, secret custody and rollback contracts are approved.

**Rationale**: Immutable images are valuable but do not need to exist to remove duplicate full tests. Bundling them would enlarge the trust boundary and delay the requested improvement.

**Alternatives considered**: Add a registry now (unresolved provider/custody); export images over SSH (large artifacts and a new failure surface); leave as an explicit follow-up (chosen).
