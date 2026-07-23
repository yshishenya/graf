# Feature 124 GitHub issue mapping

Синхронизировано после `$speckit-taskstoissues` 2026-07-23 и post-review
follow-up; closeout завершён 2026-07-23. Все 24 mapped issues закрыты после
evidence-комментариев. `tasks.md` остаётся
источником правды по выполнению; issues используются для review, статусов и
validation evidence. Дубли не найдены, все Feature-124 заголовки, labels и
bodies прошли `github-issue-canon` до closeout. Последующий repository-wide
rerun затронут четырьмя новыми внешними Feature-121 issues (#4320–#4323) с
неполным canon; они не относятся к Feature 124 и не изменялись.

| Task | Issue | Область |
|---|---|---|
| T001 | [#4296](https://github.com/yshishenya/crisp/issues/4296) | setup |
| T002 | [#4295](https://github.com/yshishenya/crisp/issues/4295) | macos/meeting-detection |
| T003 | [#4297](https://github.com/yshishenya/crisp/issues/4297) | macos/meeting-detection |
| T004 | [#4310](https://github.com/yshishenya/crisp/issues/4310) | macos/meeting-detection |
| T005 | [#4313](https://github.com/yshishenya/crisp/issues/4313) | macos/meeting-detection |
| T006 | [#4305](https://github.com/yshishenya/crisp/issues/4305) | macos/prompt |
| T007 | [#4307](https://github.com/yshishenya/crisp/issues/4307) | macos/prompt |
| T008 | [#4309](https://github.com/yshishenya/crisp/issues/4309) | macos/prompt |
| T009 | [#4311](https://github.com/yshishenya/crisp/issues/4311) | macos/settings |
| T010 | [#4302](https://github.com/yshishenya/crisp/issues/4302) | macos/settings |
| T011 | [#4298](https://github.com/yshishenya/crisp/issues/4298) | macos/privacy |
| T012 | [#4301](https://github.com/yshishenya/crisp/issues/4301) | macos/capture |
| T013 | [#4303](https://github.com/yshishenya/crisp/issues/4303) | docs/product |
| T014 | [#4308](https://github.com/yshishenya/crisp/issues/4308) | docs/specs |
| T015 | [#4300](https://github.com/yshishenya/crisp/issues/4300) | docs/release |
| T016 | [#4304](https://github.com/yshishenya/crisp/issues/4304) | docs/governance |
| T017 | [#4299](https://github.com/yshishenya/crisp/issues/4299) | validation/macos |
| T018 | [#4306](https://github.com/yshishenya/crisp/issues/4306) | validation/ci |
| T019 | [#4312](https://github.com/yshishenya/crisp/issues/4312) | validation/quality |
| T020 | [#4315](https://github.com/yshishenya/crisp/issues/4315) | macos/prompt |
| T021 | [#4316](https://github.com/yshishenya/crisp/issues/4316) | macos/capture |
| T022 | [#4316](https://github.com/yshishenya/crisp/issues/4316) | macos/capture |
| T023 | [#4317](https://github.com/yshishenya/crisp/issues/4317) | docs |
| T024 | [#4318](https://github.com/yshishenya/crisp/issues/4318) | docs/release |
| T025 | [#4319](https://github.com/yshishenya/crisp/issues/4319) | validation |

Все issues выше закрыты после выполнения задач, validation evidence и явного
closeout по правилам `docs/agent-guidance/tracker-policy.md`; #4316 содержит
общий closeout для T021 и T022.

## Release и production closeout

- Feature 124 выпущена как [`v2026.07.23.9`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.23.9)
  и развернута на exact SHA `5d5b8428239f9f1439cefc63e11bd1b07e3f4279`.
- Backup/restore rehearsal, migration head `0033_prompt_opt_maintenance`,
  production smoke/cleanup, worker/API/Temporal readiness и automatic dispatch
  прошли; итоговый `readiness_verdict=infra_smoke_ready`.
- Production RLS read-only metadata probe прошёл: 77/77 таблиц с RLS и FORCE,
  failed tables: none; live/ready health оба HTTP 200.
- Предыдущий tag-кандидат `v2026.07.23.8` остановлен fail-closed на
  несовместимой с production migration lineage и superseded `.9`; его не
  публиковали как production release.
