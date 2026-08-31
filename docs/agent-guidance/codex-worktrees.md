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
- optional `base_sha` in `.specify/feature.json` when a feature is deliberately
  stacked on an unmerged reviewed feature; it must be the exact fork commit.
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
