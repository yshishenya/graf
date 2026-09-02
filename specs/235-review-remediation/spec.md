# Feature 235: Review remediation harness

## Цель

Устранить подтверждённые P1/P2 gaps в governance harness, которые были
обнаружены после merge PR #6361, #6380 и #6383. Allocator, closeout validator,
PR metadata gate и task-to-issue mapping должны fail-closed и сохранять
трассируемость.

## Границы

Входит: исправления `scripts/claim-feature.py`,
`scripts/validate-issue-closeout.py`, PR metadata workflow и canonical
task↔issue links для Feature 231; regression tests и синхронизация источника
PR template.

Не входит: macOS runtime changes из PR #6362, production deploy и legacy
retirement.

## Требования

- Allocator must pass `args.issue_number` to every collision probe.
- Closeout validation must require expected exact SHA and positive,
  run-bound authoritative governance evidence.
- Task ownership is read only from canonical issue title and explicit
  `Spec tasks` field; each task row's issue number must match.
- Scoped PRs without a changed feature spec must use an explicit scoped
  identity and remain subject to the normal metadata contract.
- Generated PR template and its extension source remain equivalent.

## Validation

Focused governance tests, script self-tests, `git diff --check`, then explicit
`infra/scripts/ci-local.sh --fast` and GitHub `governance-fast` on one exact SHA.

## Legacy Impact

- Classification: `untouched`
- This slice changes governance validators, workflow metadata and task links;
  it does not add or remove product legacy paths.
- No legacy alias, fallback, flag, dependency, fixture, test or documentation
  path is introduced.
- Legacy retirement remains a separate follow-up and is not a prerequisite for
  this remediation.
