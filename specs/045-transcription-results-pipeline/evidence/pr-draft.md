# PR Draft: 045 Transcription Results Pipeline

## Кратко

Закрывает локально проверенный 045 pipeline после записи: структурно валидная
запись больше не блокируется только из-за локального quality/leakage/echo
warning, сервер после accepted finalize запускает или переиспользует processing,
а web/desktop review видят честный статус transcript/diarization для accepted
media revision.

Это не реализация AEC/noise suppression. Реальное эхоподавление и
шумоподавление остаются отдельной фичей `044`.

## Что изменилось

- Desktop upload queue разделяет hard package blockers и diagnostic quality
  warnings: missing files, consent, permissions, role/size/checksum/fingerprint
  остаются блокерами, а leakage/echo/silence/timing/readiness warnings больше
  не останавливают upload/transcription для структурно валидных пакетов.
- Server finalize запускает или переиспользует один processing workflow для
  accepted media revision, сохраняя upload success отдельно от processing
  dependency blockers.
- Processing/status/cabinet контракты показывают ready, partial, processing,
  failed и blocked states без transcript text, raw audio, signed URLs, provider
  payloads, credentials или private paths в diagnostics/status evidence.
- Web cabinet и desktop embedded review получают matching transcript and
  diarization availability для accepted media revision; failed/blocked
  processing states остаются review states, а не скрываются как потерянная
  запись.
- Добавлены Spec Kit artifacts, validation evidence, MVP readiness audit,
  PR-readiness audit и commit manifest для безопасного отделения 045 от 044.

## Как проверено

- `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
  подтвердил feature directory `specs/045-transcription-results-pipeline`.
- Checklists: `pipeline.md` 22/22 complete, `requirements.md` 16/16 complete.
- Tasks/checklists: open `[ ]` items не найдены.
- `python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py`
  passed.
- `git diff --check` passed.
- Focused macOS suite passed: `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopUploadQueueTests|LocalRecordingLeakageFinalizationTests|LocalRecordingManifestTests|DesktopCabinetUploadLinkTests|DiagnosticRedactionTests'`
  — 73 tests, 0 failures.
- Focused server suite plus source-role regression and one-hour orchestration
  benchmark passed: `PYTHONPATH=src uv run --extra dev pytest -q ...` — latest
  broad focused server recheck 44 tests, 0 failures, 1 warning; benchmark
  1 test, 0 failures.
- Latest full `infra/scripts/ci-local.sh` passed after the post-evidence-sync
  checks: server tests 546 passed, 4 skipped, 90 warnings; server lint passed;
  Python compile passed; production compose rendered; deployment evidence scan
  passed. RLS hardening used the safe no-Postgres default boundary in
  canonical CI.
- Code-level audit follow-up rechecked desktop sync failed/blocked semantics:
  focused recording-sync/cabinet tests passed, focused 045 server tests passed,
  focused macOS tests passed, and latest full `infra/scripts/ci-local.sh`
  passed after updating the old recording-sync conflict expectation.
- RLS disposable Postgres proof passed on an isolated local `postgres:17-alpine`
  database: migrations applied through `0008_recording_sync_loop`;
  `rls_validation_result=pass`; `destructive_probe_database=disposable`;
  `probe_suite=direct_sql_rls_probes`.
- Desktop runtime: current branch app build/launch/idle/quit non-recording
  preflight passed on repeat after one environmental pre-launch `coreaudiod`
  baseline blocker. After explicit owner approval, the current branch app-only
  package was installed over `/Applications/2brain Rec.app` and proved granted
  permissions, active recording, one-action Stop, saved `local_mic` plus
  `remote_speaker` tracks, and upload queue creation for a speakerphone/
  high-leakage package.
- Web cabinet runtime: local fixture server plus Playwright/Chrome covered
  ready, processing, partial, failed, desktop, and mobile review states without
  horizontal overflow.
- Web cabinet Russian-first follow-up: focused cabinet contract/integration/unit
  suite passed, 26 tests, 0 failures, 1 warning; fixture browser runtime passed
  with no visible legacy English launch labels, no `Политика workspace` copy,
  no horizontal overflow, and no clipped status chips.
- Latest web cabinet browser runtime recheck passed on 9 synthetic fixture
  pages with `health=200`, unauthenticated `/meetings=401`, no missing required
  Russian launch/result labels, no visible forbidden legacy copy, no horizontal
  overflow, no clipped chips, and `failures=[]`. Output:
  `/tmp/2brain-rec-045-web-cabinet-ru-20260624g`.
- Live production probe with a fresh installed current-branch desktop recording:
  a v3 `failed` / `leakage_detected` speakerphone package with meaningful
  microphone and incoming/system audio uploaded and finalized in production, then
  reached MediaScribe-backed `processed` review after targeted manual processing
  pickup. Production was still on `master` commit `e312d25`, not 045, so this is
  not proof of deployed 045 auto-start/reuse.
- Speaker/source-role attribution regression: the current branch now matches
  transcript and diarization segments by normalized `(sequence, source_role)` so
  duplicate per-track sequences do not visually swap local microphone and
  incoming/system attribution. Focused cabinet/source-role tests passed, 20
  tests, 0 failures, 1 warning.
- Deploy dry-run passed: `infra/scripts/cd-remote.sh --dry-run` returned
  `deploy_result=dry_run` for branch `045-transcription-results-pipeline` and
  did not deploy.
- Remote apply-check passed: the 045 include-set patch was generated relative
  to current `origin/master` `a89cf91` with 65 changed paths and 25 new paths,
  then `git apply --unidiff-zero --check` passed in a detached temporary
  worktree; `git diff --check` passed after applying it. A strict added-line
  privacy scan over the generated patch found 0 real user paths, owner-session
  cookies, API keys, private-key literals, or provider tokens.
- Focused cabinet playback/timestamp truth tests passed: timestamp labels,
  speaker/source-role mapping, playback availability state, and
  `detail-playback` shell presence are covered. This is not a claim that
  interactive audio playback, waveform, or transcript-segment seek is complete.

## Issues

Все `feature:045` issues уже закрыты после task/evidence validation. PR связывает
реализацию с ними через `Refs`, а не через closing keywords.

Refs #1465
Refs #1466
Refs #1467
Refs #1468
Refs #1469
Refs #1470
Refs #1471
Refs #1472
Refs #1473
Refs #1474
Refs #1475
Refs #1476
Refs #1477
Refs #1478
Refs #1479
Refs #1480
Refs #1481
Refs #1482
Refs #1483
Refs #1484
Refs #1485
Refs #1486
Refs #1487
Refs #1488
Refs #1489
Refs #1490
Refs #1491
Refs #1492
Refs #1493
Refs #1494
Refs #1495
Refs #1496
Refs #1497
Refs #1498
Refs #1499
Refs #1500
Refs #1501
Refs #1502
Refs #1503
Refs #1504
Refs #1505
Refs #1506
Refs #1507
Refs #1508
Refs #1509
Refs #1510
Refs #1511
Refs #1512
Refs #1513
Refs #1514
Refs #1515
Refs #1516

## Что не входит

- `044-speakerphone-echo-noise-suppression`: реальное AEC/noise suppression,
  выбор clean-audio runtime path и любые claims, что microphone audio очищен.
- Production deploy и post-deploy 045 upload-to-transcript-to-review evidence.
- Post-deploy 045 auto-start/reuse proof. The fresh live production probe used
  manual processing pickup because production was still on `master e312d25`.
- Clean low-leakage/headphones `saved` / `ready` artifact proof. Current-branch
  permissioned Record/Stop is proven for a speakerphone/high-leakage package,
  but that package is intentionally not a clean-audio claim.
- Live MediaScribe latency and large-object throughput: one-hour benchmark uses
  fake dependency and validates product-owned orchestration, not provider speed.
- Interactive playback/timestamp seek: 045 renders timestamp labels and a
  playback shell, but PRD-level play/pause/seek/waveform/segment seek remains a
  separate MVP gap. `playback-timestamp-seek-preflight.md` records the possible
  `046-meeting-playback-timestamp-seek` handoff.
- Notes/actions launchable output, unless owner separately approves MVP deferral
  or a future implementation slice.

## Release / versioning

- [ ] Если PR готовит релиз, выбран правильный тип версии:
      CalVer `vYYYY.MM.DD.N` для продукта/apps/services или SemVer
      `vMAJOR.MINOR.PATCH` для libraries/CLI/extensions/bootstrap.
- [ ] Читаемый postfix релиза записан в GitHub Release title, а не в stable tag.
- [x] `CHANGELOG.md` обновлен понятной русской записью.
- [ ] Release notes включают validation evidence, compatibility/migration notes
      и known limitations.

## Перед merge

- [x] Описание PR написано на русском и понятно не только инженеру.
- [x] Closing keywords не используются, потому что все `feature:045` issues уже закрыты; связи перечислены через `Refs`.
- [x] Связанные issues перечислены через `Refs`, потому что PR не должен повторно закрывать уже закрытые issues.
- [ ] Validation evidence записан в PR после финального rebase/merge с
      `origin/master`.
- [x] Новых закрываемых issue в этом PR draft нет; уже закрытые `feature:045`
      issues связаны через `Refs`.

## Known Limitations

- Ветка все еще локальная до commit/push/PR/merge approval.
- `origin/master` ahead by 4 commits; latest remote apply-check passed, but the
  branch still needs the normal commit/rebase-or-merge/validation path after
  owner approval.
- Full MVP пока не доказан: нет post-deploy 045 production e2e, clean
  low-leakage desktop artifact proof и post-deploy speaker/source-role
  verification.
- PRD-level audio playback linked to transcript timestamps is not proven by
  045; it needs `046` or explicit pilot-MVP deferral.
