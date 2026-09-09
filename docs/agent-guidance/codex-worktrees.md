# Codex Worktrees

## Canonical Project Root

Start new Crisp Codex sessions from:

```text
/Users/yshishenya/Documents/crisp
```

Use Codex-managed worktrees for disposable thread work. Use a permanent
feature-named worktree only when the user explicitly wants a long-lived
workspace.

## Source Of Truth

Do not infer active work from the physical folder name under `.codex/worktrees`.
Names such as `019-*`, `13b8`, or an old feature slug can be stale.

Anchor the current feature from:

- current Git branch;
- `specs/<number>-<slug>/`;
- `.specify/feature.json`;
- active `tasks.md`;
- GitHub issue labels and links when issue sync exists.

Recommended orientation commands:

```sh
git status --short --branch
git branch --show-current
git rev-parse --show-toplevel
cat .specify/feature.json 2>/dev/null || true
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Use `SPECIFY_FEATURE_DIRECTORY=... .specify/scripts/bash/check-prerequisites.sh`
when you need to force a specific feature anchor.

## Starting New Work and Choosing a Feature ID

For a new feature, verify a fresh `origin/master` and its exact SHA, then use a
disposable worktree based on that revision. An existing session may intentionally
remain on an older feature: never switch it, reset it, or discard its changes to
start unrelated work. Continuing an existing feature uses its own branch and
tasks, not a newly allocated number.

Treat injected `spec_last`/`spec_next` values and local directory maxima as hints,
not reservations. From the fresh worktree, run `python3 scripts/claim-feature.py
--json` for a read-only online proposal. The branch-creation commands delegate to
the same allocator, which repeats the choice under the shared lock when reserving
it; a proposal can become stale before reservation. `--offline` only gives a local
draft suggestion and does not establish availability on GitHub.

`.specify/feature-numbering.json` lists explicit historical exceptions to the
sequence start. F6788 is retained unchanged but does not push new features into
the 6789+ range. Exceptions remain occupied in specs, refs, shared claims and
GitHub; this file never releases a number. Normal F1000+ numbering remains valid.
No policy means the existing highest-spec start; an unreadable or malformed
policy stops selection. Do not add exceptions merely to obtain a preferred ID.

## Instruction Loading

Codex reads `AGENTS.md` automatically and applies closer nested `AGENTS.md`
files to files under their directory. Root `AGENTS.md` should stay concise
enough to load every session without crowding out task context. Long details
belong in `docs/agent-guidance/` and should be read when relevant.

Fallback rule files are not a replacement for `AGENTS.md`; a fallback filename
is only useful where no `AGENTS.md` exists at that level.

## Workspace Closeout

Before declaring a workspace reusable or done:

- confirm the branch/spec/task anchor;
- run the relevant validation gate;
- check local status and untracked files;
- distinguish generated/local Spec Kit state from user changes;
- do not remove or reset user changes.

If the user asks to close a temporary worktree, state whether it is reusable or
remove it only after confirming there is no uncommitted work that should be
preserved.
