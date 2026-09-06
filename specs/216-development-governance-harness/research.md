# Research: Feature 216

## Decision 1 — Feature ID and umbrella reservation

**Decision**: Use the next collision-free Spec Kit number `216`, reserved in
GitHub umbrella issue #6090. Keep the GitHub issue number separate from the
three-digit Spec Kit Feature ID required by the project issue canon.

**Rationale**: `213`, `214` and `215` are already present in remote feature
branches/issues. GitHub issue numbers are globally atomic but are not
three-digit Spec Kit IDs. The claim record gives atomic reservation while
preserving the existing canon and historical numbering.

**Alternatives considered**:

- Local maximum from `specs/`: rejected because parallel worktrees can select
  the same value and duplicate prefixes already exist.
- GitHub issue number as Feature ID: rejected because it breaks the current
  canon, labels and Spec Kit directory conventions.
- Timestamp-only IDs: rejected because they are harder to read and do not
  preserve the current repository contract.

## Decision 2 — One active Dev promotion

**Decision**: Development remains parallel in worktrees, but the local Dev
environment has exactly one active manifest and one installed
`/Applications/GRAF Dev.app`. `build`, `promote`, `status`, `smoke`,
`rollback` and `reset-data` are separate operations; promotion is lock-protected
and atomic.

**Rationale**: Manual end-to-end QA against multiple mutable SHAs in one app is
not reproducible. A single active manifest makes the tested SHA explicit and
rollback possible. Parallel candidates can be built but cannot be active at
the same time.

**Alternatives considered**:

- One Dev app per worktree: rejected because permissions, ports and user data
  drift and the user explicitly needs one application.
- Mutable containers without a manifest: rejected because a completed test
  could not prove which SHA was running.
- Per-feature permanent environments: deferred; they add cost and do not solve
  the single-app permission requirement.

## Decision 3 — Context isolation

**Decision**: Root `AGENTS.md` contains stable rules only. Active feature/task
state is per worktree in ignored `.specify/feature.json` plus a generated,
bounded context manifest. No resolver may select a plan by file mtime.

**Rationale**: Tracked dynamic pointers and mtime heuristics cause unrelated
agents to load the wrong feature and create merge conflicts. Explicit state is
deterministic and keeps prompts small.

**Alternatives considered**:

- Keep updating the managed plan pointer in root `AGENTS.md`: rejected because
  every feature edits the same tracked file.
- Infer the newest spec by mtime: rejected because worktrees and clocks are not
  an ownership signal.
- Copy all specs into every prompt: rejected because it wastes context and
  increases the chance of cross-feature instructions.

## Decision 4 — Changelog fragments

**Decision**: Feature agents write one owned fragment under
`changes/unreleased/F<feature-id>.yaml` (or the project-configured equivalent).
Only the release operator assembles and edits root `CHANGELOG.md` for a release
candidate.

**Rationale**: Fragment ownership removes the main textual merge-conflict
point while keeping Russian release notes and category metadata structured.

**Alternatives considered**:

- Continue editing `[Unreleased]` in the root file: rejected due to conflicts.
- Generate notes only from commit messages: rejected because messages lack
  compatibility, user impact and known limitations.
- Use an external tracker as changelog source: rejected because releases must
  remain auditable in the repository.

## Decision 5 — CI identity and cancellation

**Decision**: Every run records requested SHA and observed SHA at start and
publication. Fast runs are feedback; a frozen release candidate has one
authoritative Full CI identity. A run whose target SHA changed is stale/cancelled
and cannot be evidence.

**Rationale**: This removes the race where CI completes for an old commit and a
new commit starts another run indefinitely. Immutable candidate metadata makes
the release gate auditable.

**Alternatives considered**:

- Reuse the latest successful run regardless of SHA: rejected as unsafe.
- Run Full CI on every commit: rejected as too slow and contrary to release
  train batching.
- Trust provider job status without local SHA verification: rejected because
  GitHub Actions are currently disabled and any provider can report stale data.

## Decision 6 — Legacy retirement gate

**Decision**: Add a required Legacy Impact section and Definition-of-Done check
to every new feature. New aliases, flags, fallbacks, dependencies, fixtures,
tests and docs that preserve an old path are forbidden unless a bounded
exception names owner, expiry, removal trigger and retirement task. Existing
legacy is retired in separate slices after this feature.

**Rationale**: The project is pre-MVP and can still remove obsolete paths, but
mass deletion of migrations, Temporal history or client compatibility would be
unsafe without cutover evidence.

**Alternatives considered**:

- Delete all legacy immediately: rejected because production/data compatibility
  boundaries are not yet proven.
- Ignore legacy until after MVP: rejected because each new feature would add
  more cleanup cost.
- Allow permanent compatibility flags: rejected because they become
  unowned, untestable legacy.

## Decision 7 — Reusable harness extraction

**Decision**: Keep GRAF-specific product gates in this repository and extract a
  generic harness (rules, validators, templates, scripts, self-tests and
  adapters) into a separate public repository with SemVer, immutable tags and
  migration notes. Provisional name: `graf-development-harness`.

**Rationale**: Other projects need the process without receiving GRAF product
  data or private paths. A generic core plus project adapter avoids copying
  capture/privacy rules that do not apply elsewhere.

**Alternatives considered**:

- Copy GRAF `AGENTS.md` wholesale: rejected because it is product-specific and
  includes paths that cannot be portable.
- Publish only a README: rejected because rules without executable validators
  drift quickly.
- Make the harness a subdirectory of GRAF only: rejected because consumers need
  an independent version and release lifecycle.

## Decision 8 — Hooks and commits

**Decision**: Keep read-only hooks automatic where safe, disable auto-commit
  hooks by default, and require explicit approval for implementation commits
  after validation and convergence.

**Rationale**: Unexpected commits are especially harmful in shared worktrees and
  violate the repository's release safety rule.

**Alternatives considered**:

- Auto-commit every Spec Kit stage: rejected because it obscures ownership and
  creates noisy histories.
- Disable all hooks: rejected because issue-canon and context validation remain
  useful as deterministic gates.
