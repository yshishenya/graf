# Agent Guidance Map

This folder holds long-lived Codex and Spec Kit operating guidance for the
repository. Root `AGENTS.md` is the automatic entrypoint; this folder is the
stable reference surface for detailed rules.

## Sources Of Truth

- Product baseline: `docs/prd-voice-layer-final.md`.
- Current merged status: `docs/current-product-status.md`.
- Governance: `.specify/memory/constitution.md`.
- Active feature: current Git branch, `specs/<number>-<slug>/`,
  `.specify/feature.json`, and the active `tasks.md`.
- Implementation tracking: `tasks.md` first, GitHub issues second.

The physical Codex worktree folder name is not a source of truth.

## File Roles

- `codex-worktrees.md`: how to choose the project root and reason about Codex
  worktrees.
- `spec-kit-flow.md`: the full feature workflow and quality gates.
- `product-gates.md`: non-negotiable product, privacy, AI, deletion, and
  clean-room gates.
- `tracker-policy.md`: GitHub issue sync, Russian/plain-language comments, and
  retired Linear policy.
- `github-issue-canon.md`: exact GitHub issue format.
- `release-and-validation.md`: local CI, deployment, changelog, release, and
  evidence rules.
- `legacy-audio-driver-cleanup.md`: read-only inspection and explicit,
  narrowly scoped cleanup for proof components already installed on a
  developer Mac.

## What Goes Where

Put short, always-needed rules in root `AGENTS.md`. Put longer procedural detail
in this folder. Add nested `AGENTS.md` files only when a subtree genuinely needs
different build, test, or ownership rules.

Do not create root `RULES.md` as a second Codex instruction source. If another
tool needs rules, derive them explicitly from `AGENTS.md` and this folder so the
project does not split into competing guidance surfaces.

Repeated cross-repository workflows belong in Codex skills or Spec Kit
extensions, not in large prompt blocks. Project-specific gates remain here.

## Shared Tooling Sources

When changing generated Spec Kit guidance, update the source repositories too:

- `/Users/yshishenya/Documents/speckit-bootstrap`
- `/Users/yshishenya/Documents/spec-kit-ext-github-issue-canon`

The installed copy under `.specify/extensions/` is project-local state. The
source extension repository is what future `speckit-bootstrap` refreshes pull
from.
