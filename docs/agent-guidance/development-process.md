# GRAF Development Process

This is the short operator runbook. Detailed product gates remain in the
constitution and linked guidance; this file only routes a feature through them.

## Roles and ownership

| Role | Owns | Must not do |
|---|---|---|
| Product owner | goal, priority, acceptance and release approval | silently change a running candidate |
| Feature agent | one worktree, branch, Feature ID, owned source/spec/fragment | edit another feature's context or root changelog |
| Reviewer | requirements, checklist state, risk acceptance and evidence | let implementation mark reviewer checkboxes |
| Dev operator | single Dev manifest, promote/rollback/status/smoke | activate two SHAs or touch production |
| Release operator | candidate freeze, one Full CI, CalVer/tag/Release/notes | release a floating branch or stale evidence |

## Start a feature

1. Start from `/Users/yshishenya/Documents/crisp` or a disposable Codex
   worktree based on `origin/master`.
2. Check `git status --short --branch`, exact `HEAD`, remote and
   `.specify/feature.json`.
3. Reserve a collision-free Feature ID and umbrella GitHub issue before branch
   or spec creation. Check local specs, visible refs, issues and PRs. Never use
   only the local maximum.
4. Run the full significant/high-risk sequence:
   `specify → clarify → plan → checklist → tasks → analyze → taskstoissues →
   implement → converge → quickstart → fast validation`.
5. Keep root `AGENTS.md` stable. Active feature/task context is per-worktree in
   ignored `.specify/feature.json`; no mtime fallback is allowed.

## Agent context budget

- Load root rules, then only the active feature's `spec.md`, `plan.md`,
  `tasks.md`, `quickstart.md`, relevant contracts and risk guidance.
- Do not load all historical specs, all worktrees or complete CI logs into the
  prompt. Use bounded summaries and links.
- Every state-changing command prints Feature ID, task and exact SHA in
  metadata-only output.
- If the active pointer is missing, malformed or points outside the current
  worktree, stop rather than guessing.
- A stacked feature may set an explicit full-hex `base_sha` in
  `.specify/feature.json`; ownership is checked only against
  `base_sha...HEAD`. Without it, validators use `origin/master...HEAD` for
  backwards compatibility. Never widen `owned_paths` just to hide an inherited
  diff.

Codex instruction discovery follows the official OpenAI contract: global
guidance is loaded first, then project and nested-directory guidance; the
closest non-empty file wins, and `AGENTS.override.md` replaces `AGENTS.md` at
the same directory level. Keep this file and the root `AGENTS.md` concise: the
default combined instruction budget is 32 KiB. Put task-specific procedures in
one scoped guidance file and verify the active chain from a fresh Codex run;
never copy the whole repository history into always-on instructions. See the
[official AGENTS.md guidance](https://developers.openai.com/codex/guides/agents-md).

## Parallel development and Dev testing

Development is parallel; manual end-to-end verification is serialized:

```text
feature worktrees (parallel) → focused checks / fast CI
        → one selected exact SHA
        → build → promote (lock) → status → smoke
        → one /Applications/GRAF Dev.app + one active manifest
        → rollback or next promotion
```

Builds may run concurrently, but only one manifest is active. Promotion is
lock-protected, atomic and reversible. The Dev app keeps bundle ID
`pro.2brain.graf.dev`, its designated requirement/signing identity and local
permission trust. Production app, data and origins are always rejected.

## CI and release rhythm

- Focused tests are the inner loop.
- `infra/scripts/ci-local.sh --fast` is the PR-ready gate and may repeat for a
  new SHA.
- A release operator freezes one candidate SHA and metadata digest. Exactly one
  authoritative `--full` run belongs to that candidate; changed SHA makes
  evidence stale.
- If GitHub Actions are enabled, `.github/workflows/governance-fast.yml` uses a
  per-ref concurrency group with `cancel-in-progress: true`; the workflow
  passes `GRAF_CI_REQUESTED_SHA` so a changed target is rejected fail-closed.
  Feature 222 owns the guarded enablement and canonical check name
  `governance-fast`; until its operator gate is complete, local evidence
  remains authoritative.
- Use release windows (for example twice weekly) to batch completed features.
  Hotfixes are explicit exceptions with a reason and the same evidence rules.
- A product release requires CalVer tag, GitHub Release and Russian notes with
  changes, validation, compatibility/migration impact, known limitations and
  links. Production execute still requires explicit approval.

## Files agents may change

- Own feature directory under `specs/<id>-<slug>/`.
- Own `changes/unreleased/F<id>.yaml` fragment.
- Source files explicitly listed by the task and their tests.
- Project-local adapter files when the task grants ownership.

Do not edit root `CHANGELOG.md` during feature work. Do not add current feature
or task pointers to root `AGENTS.md`. Do not auto-commit implementation code;
commit only after validation, convergence and explicit owner approval.

## Legacy Definition of Done

Every spec and PR has one `Legacy Impact` classification: `remove`,
`retain-with-exception` or `untouched`. New aliases, fallback names, flags,
dependencies, fixtures, tests or docs that preserve an old path are forbidden.
An exception requires owner, expiry, removal trigger, risk, validation and a
retirement task. The closeout target is:

```text
legacy_new=0
unowned_legacy=0
expired_exceptions=0
```

Existing migrations, Temporal history and client update compatibility are
retired in separate small features with cutover and rollback evidence.

## Blocked-state next actions

| State | Next action |
|---|---|
| No Feature ID/umbrella | reserve through GitHub; do not guess a number |
| Dirty or detached worktree | preserve changes, create a disposable clean worktree |
| Pointer/context mismatch | repair `.specify/feature.json`; do not use mtime |
| Dev promotion lock held | inspect active manifest; wait or rollback, never overwrite |
| SHA mismatch/stale CI | invalidate evidence and rerun the selected lane on the new SHA |
| Failed smoke | keep previous manifest active, capture reason, fix or rollback |
| Checklist/analyze blocker | reviewer updates requirements/design; implementation does not bypass |
| Legacy exception expired | block merge/release and create/execute retirement task |
