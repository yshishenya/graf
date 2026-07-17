# Deploy evidence

Риск/валидационный lane: **significant/high-risk feature**.

- `infra/scripts/cd-remote.sh --dry-run --branch codex/111-support-incident-recovery`:
  **PASS**.
- `infra/scripts/cd-remote.sh --execute --branch codex/111-support-incident-recovery`:
  **PASS**.
- Production был обновлён с pinned SHA
  `6abd03bab3c4e859f72cb0b2cc508b4c9cbef9d1`; удалённая проверка runtime
  подтвердила тот же SHA и clean worktree.
- Secret provisioning, backup и restore rehearsal: **PASS**.
- Production migration head: `0028_active_space_read`.
- Direct disposable PostgreSQL RLS probes: **PASS**; destructive live
  production probe не выполнялся.
- Production smoke, cleanup, API/media/processing readiness:
  **PASS**, `readiness_verdict=infra_smoke_ready`.
- Скриптовые проверки automatic retry, backfill, range playback и
  normalization cleanup отмечены `required_post_deploy`; этот smoke не является
  пользовательским end-to-end тестом support report с GitHub egress.
- Отдельный CalVer release/tag и merge PR не выполнялись этим deploy; PR
  оставлен открытым для review.

В evidence нет секретов, smoke IDs, live session material, аудио,
расшифровок и private production identifiers.
