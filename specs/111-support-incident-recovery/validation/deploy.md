# Deploy evidence

Риск/валидационный lane: **significant/high-risk feature**.

- `infra/scripts/cd-remote.sh --dry-run --branch codex/111-support-incident-recovery`:
  **PASS**.
- `infra/scripts/cd-remote.sh --execute --branch codex/111-support-incident-recovery`:
  **PASS**.
- Исторический deploy receipt был выполнен с pinned SHA
  `6abd03bab3c4e859f72cb0b2cc508b4c9cbef9d1`; удалённая проверка runtime
  тогда подтвердила тот же SHA и clean worktree.
- Secret provisioning, backup и restore rehearsal: **PASS**.
- Production migration head: `0028_active_space_read`.
- Direct disposable PostgreSQL RLS probes: **PASS**; destructive live
  production probe не выполнялся.
- Production smoke, cleanup, API/media/processing readiness:
  **PASS**, `readiness_verdict=infra_smoke_ready`.
- Скриптовые проверки automatic retry, backfill, range playback и
  normalization cleanup отмечены `required_post_deploy`; этот smoke не является
  пользовательским end-to-end тестом support report с GitHub egress.
- После этого receipt PR [#3843](https://github.com/yshishenya/crisp/pull/3843)
  был merged; follow-up [#3867](https://github.com/yshishenya/crisp/pull/3867)
  восстановил macOS bridge response contract. Release
  [`v2026.07.18.2`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.18.2)
  опубликован. Старый SHA выше остаётся исторической deploy-точкой и не
  доказывает состояние runtime после последующих обновлений.

В evidence нет секретов, smoke IDs, live session material, аудио,
расшифровок и private production identifiers.
