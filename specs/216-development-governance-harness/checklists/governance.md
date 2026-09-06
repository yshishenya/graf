# Governance Review Checklist: Feature 216

**Purpose**: Reviewer-owned gate для процесса, Dev harness, CI и reusable package
**Feature**: [spec.md](../spec.md)

## Feature identity and context

- [ ] Feature ID 216 не пересекается с локальными/remote refs, issues и PR
- [ ] Umbrella issue #6090 связан со всеми task-backed issues
- [ ] `.specify/feature.json` — единственный active pointer; mtime fallback отсутствует
- [ ] Root `AGENTS.md` остаётся стабильным и не содержит текущий task

## Parallel agents and repository hygiene

- [ ] Один agent/worktree имеет одного owner и один branch
- [ ] Changelog fragment namespace уникален; общий `CHANGELOG.md` меняется только release operator
- [ ] Auto-commit hooks не создают неожиданные implementation commits
- [ ] Evidence metadata-only и не содержит secrets/private content

## Dev harness and macOS app

- [ ] Build/promote/status/rollback/reset/smoke имеют dry-run и fail-closed поведение
- [ ] Active manifest единственный и SHA-consistent для backend/frontend/app
- [ ] Promote lock и атомарная активация доказаны конкурентным тестом
- [ ] `/Applications/GRAF Dev.app` сохраняет bundle ID, signing identity, designated requirement и permissions
- [ ] Dev reset не может затронуть production

## CI and release

- [ ] Stale SHA не считается evidence
- [ ] Frozen candidate допускает один authoritative Full CI
- [ ] Fast/full границы и cancellation описаны в PR/release templates
- [ ] CalVer/tag/GitHub Release/Russian notes связаны с exact SHA
- [ ] Rollback и skipped gates имеют metadata-only evidence

## Legacy and extraction

- [ ] Legacy Impact обязателен в spec и PR
- [ ] Исключения имеют owner, expiry, trigger и retirement task
- [ ] Existing legacy cleanup вынесен в отдельную Feature 217+ без опасного массового удаления
- [ ] Generic harness отделён от GRAF-specific product gates
- [ ] Публикация reusable repo блокируется при secret/path/provenance нарушении

## Reviewer decision

- [ ] PASS — можно переходить к implementation
- [ ] ACCEPT WITH RECORDED RISK — риск и владелец явно записаны
- [ ] BLOCK — сначала исправить spec/plan/tasks
