# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

- No entries yet.

## [0.2.2] - 2026-06-26

### Added

- Added a `Risk / validation lane` section to the reusable pull request template so
  PRs record the selected validation scope, why it is sufficient, and which
  broader gates were not run.
- Updated the issue canon to require PR descriptions to include the selected
  validation lane alongside validation evidence and issue links.

## [0.2.1] - 2026-06-18

### Added

- Added release/versioning guidance to the reusable PR template and extension
  README: product apps and services should use CalVer `vYYYY.MM.DD.N`, reusable
  tooling should use SemVer `vMAJOR.MINOR.PATCH`, and human-readable release
  postfixes should live in GitHub Release titles rather than stable tags.

## [0.2.0] - 2026-06-18

### Changed

- Moved the GitHub issue canon to a Russian-only workflow. New Spec Kit issues
  must use Russian titles, Russian body sections, and simple wording that is
  understandable outside the engineering team.
- Replaced the old English issue body sections with the new canonical Russian
  order: `Кратко`, `Контекст`, `Проблема`, `Проверенные факты`,
  `Границы задачи`, `Критерии приемки`, `Что проверить перед закрытием`,
  `Заметки по реализации`, and `Ссылки`.
- Tightened PR linking rules to match GitHub behavior: use `Fixes`, `Closes`,
  or `Resolves` only when a PR fully closes an issue, use `Refs` or `Part of`
  for partial work, and do not rely on automatic closure for non-default-branch
  PRs.
- Strengthened issue closeout rules. Every closed issue now needs a detailed
  Russian closure comment explaining what changed, why it matters, how it was
  checked, what is out of scope, and which PR and Spec Kit task were closed.
- Updated normalization so old or incomplete issue bodies are rewritten into
  the new Russian canonical structure instead of being accepted as-is.

### Added

- Added a repository PR template that asks for a Russian summary, validation
  evidence, explicit issue links, out-of-scope notes, and a pre-merge checklist.
- Added extension installer support for `.github/pull_request_template.md` so
  refreshed projects receive the PR template automatically.

### Breaking

- English issue sections such as `Summary`, `Problem`, and
  `Validation Required` are no longer valid for current Spec Kit issues. Run
  the normalize command before expecting validation to pass on older open
  issues.

## [0.1.2] - 2026-06-18

### Changed

- Synced the issue canon template wording with the project-owned
  `docs/agent-guidance/github-issue-canon.md` location.

## [0.1.0] - 2026-06-04

### Added

- Added the initial Spec Kit GitHub issue canon extension with project files,
  issue templates, labels, normalization, validation, and task-to-issue hooks.
