# Automation And UX Requirements Checklist: Review M4A Normalization

**Purpose**: Validate the no-user-action guarantee, durable recovery, legacy backfill and truthful playback UX requirements before task generation
**Created**: 2026-07-14
**Feature**: [spec.md](../spec.md)

**Audience / depth**: PR and release reviewers; formal high-risk gate.

## Requirement Completeness

- [x] CHK001 Is automatic scheduling required at accepted-source availability and explicitly independent from transcript/summary completion? [Completeness, Spec §FR-042/SC-022]
- [x] CHK002 Are transient failure, exhausted-attempt-cycle, process restart, lost dispatch, expired lease and missing-ready-artifact recovery requirements all documented? [Coverage, Spec §FR-011/FR-023/FR-031, Backfill Contract §Restart recovery]
- [x] CHK003 Are no-user-action requirements defined for new ingest, automatic retry, reconciliation and legacy backfill, including the absence of user/admin mutation controls? [Completeness, Spec §FR-014/FR-023/FR-040, Status Contract §Mutation boundary]
- [x] CHK004 Are permanent outcomes limited to objective source problems while infrastructure/system failures remain automatically recoverable when source is retained? [Completeness, Spec §FR-011/FR-012/FR-040]
- [x] CHK005 Are inventory, planned action/skip reason, mutation ordering, cursor resume, batching, completion and safe progress requirements specified for each workspace backfill run? [Completeness, Spec §FR-014–FR-017/FR-041, Backfill Contract §Per-workspace run]

## Requirement Clarity

- [x] CHK006 Is the retry model quantified by attempts per cycle, in-cycle delay, long-term cycle cadence and retained-source stopping condition? [Clarity, Spec §FR-023/SC-012, Backfill Contract §Retry without manual action]
- [x] CHK007 Is the crash-gap guarantee quantified by a maximum accepted-source-to-queue delay even when immediate dispatch is lost? [Clarity, Plan §Performance Goals, Backfill Contract §Restart recovery]
- [x] CHK008 Are deterministic workflow identity, duplicate pickup and one-job/one-canonical convergence rules defined without relying on browser state? [Clarity, Spec §FR-010/FR-024/FR-035]
- [x] CHK009 Is workload priority explicit for new accepted sources, due retries and legacy backfill? [Clarity, Backfill Contract §Scheduling and priority]
- [x] CHK010 Is “no action” explicit enough to exclude retry, reprocess, repair, backfill, force-ready, track selection and source replacement controls? [Clarity, Spec §FR-023/FR-040, Status Contract §Mutation boundary]

## Requirement Consistency

- [x] CHK011 Are automatic recovery and terminal-unavailable rules consistent between the spec, status projection, backfill contract and quickstart? [Consistency, Spec §FR-011/FR-031/FR-040]
- [x] CHK012 Are playback and transcript/summary states consistently independent across scheduling, durable truth, list/review copy and success criteria? [Consistency, Spec §FR-005/FR-032/FR-042/SC-019]
- [x] CHK013 Are refresh, reconnect, multiple tabs, duplicate finalize and duplicate worker pickup consistently treated as reads/idempotent triggers rather than new work? [Consistency, Spec §FR-010/FR-022/FR-024]
- [x] CHK014 Are valid legacy artifacts preserved while invalid artifacts regenerate only from retained accepted source, with missing-source fabrication consistently forbidden? [Consistency, Spec §FR-033/FR-034/FR-041]

## Scenario And Edge-Case Coverage

- [x] CHK015 Are primary, alternate, exception and recovery requirements present for first-party, manual and legacy recordings? [Coverage, Spec §User Stories 1–5]
- [x] CHK016 Are source missing, source mismatch, temp-capacity failure, dependency failure, decode failure and generated-output validation failure assigned explicit recoverable/terminal ownership? [Coverage, Spec §FR-031/SC-018, Normalization Contract §Failure classification]
- [x] CHK017 Are deletion during queued/running/publishing/retry states and client disconnect during server work covered without requiring user intervention? [Coverage, Spec §FR-036, Status Contract §Polling/reconnect behavior]
- [x] CHK018 Are zero-eligible-workspace, partially completed inventory, worker restart and repeated automatic scan scenarios defined for legacy backfill? [Coverage, Backfill Contract §Restart recovery/Completion criteria]

## Acceptance Criteria And UX Quality

- [x] CHK019 Can the no-user-action guarantee be measured from accepted-source commit through validated ready or objective terminal reason? [Measurability, Spec §SC-020–SC-022]
- [x] CHK020 Are preparing, available, unavailable, deleting and deleted states defined with stable safe reasons and precedence? [Clarity, Status Contract §Derivation precedence/State mapping]
- [x] CHK021 Are status copy, accessibility announcements, localization, narrow/wide layout and browser/embedded parity requirements specified without adding repair affordances? [Coverage, Status Contract §Cabinet rendering]
- [x] CHK022 Is “100% works” translated into a testable supported-input guarantee without falsely promising successful output for corrupt, encrypted, no-audio or missing sources? [Acceptance Criteria, Spec §FR-040/SC-006/SC-020]

## Notes

- Final 2026-07-14 reconciliation: `22/22` items remain satisfied and map to
  automatic dispatch/retry/reconciliation/backfill and truthful-status
  receipts in `validation/traceability.md`. T100's real Chrome/embedded
  Play/Pause/seek, two-tab, reconnect, responsive, focus and reduced-motion
  receipt is now complete in `validation/browser-e2e.md`.
- Items validate requirement writing, not runtime tests.
- The explicit user decision is the highest-priority requirement: GRAF owns every retry/recovery/backfill step; the user does nothing.

## Независимое ревью 2026-11-17 — F099/T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; исходный HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Каждый исходный вопрос заново сопоставлен с текущими документами; `[x]` означает качество требований в области вопроса, без runtime-приёмки. Исторические итоги выше сохранены как история.
Итог этого файла: checked **22**, unchecked **0**, всего **22**. Общий допуск T014: **STOP**, пока не закрыты H1–H3.
Неподтверждённых исходных пунктов этого файла нет; его вопросы не заменяют отсутствующий контракт локального destination в requirements/lifecycle.
Полная построчная карта и минимальные правки: внешний отчёт `f099-t014-independent-requirements-review-20261117.md` в каталоге доказательств текущей задачи.

## Повторное независимое ревью 2026-11-17 — T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; тот же reviewer-диалог, HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Текущая spec SHA-256 `338751c8f41d766d8b09ec97a5cfc2a5beeb372e484d3b6273a396d5feff2136`; plan/tasks/quickstart и чтения привязаны в новом отчёте.
Итог этого файла: checked **22**, unchecked **0**, всего **22**. Все исходные вопросы заново оценены; вопросы и прежние STOP-заметки сохранены как история.
Все 22 исходных вопроса повторно сопоставлены с FR-010–042, backfill/status contracts, Plan/Quickstart. FR-045/SC-025 сохраняют прежние причины ошибок и автоматические повторы, не вводят ручное действие. Текущий storage repair не подменяет доказательства accepted-source→queue→playback/транскрипция и производственную приёмку.
Общий reviewer-owned requirements gate: **PASS, 100/100**, только качество требований. Известный дефект кода и открытая T014 остаются; выполнение, analyze/issue sync, регрессии, code review/converge, exact-SHA PR/base и выпуск/развёртывание проверяются отдельно.
Полная карта каждого исходного пункта и текущие ограничения: внешний отчёт `f099-t014-independent-requirements-rereview-20261117.md` в каталоге доказательств текущей задачи.

## Независимое ревью нового real-transport scope — 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы заново оценены по текущим требованиям. Старые STOP/PASS выше сохранены как история guard; новый общий допуск **STOP, implementation_admission=false**.
Итог файла: checked **22**, unchecked **0**, всего **22**. `[x]` означает только качество требований, не выполнение A/B/C и не закрытие T014.
Полная карта всех 120 вопросов, исходники и H1/H2: внешний `f099-t014-real-transport-independent-requirements-review-20261117.md`. Неподтверждённые пункты блокируют реализацию; A/B/C остаются неисполненными независимо от отметок.


## Повторное независимое ревью real-transport — H1/H2, 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы повторно сопоставлены с текущими оригиналами; прежние вопросы и заметки сохранены.
Итог файла: проверено **22**, непроверено **0**, всего **22**. Общий результат качества требований — **PASS, 120/0**. Это не допуск реализации: `implementation_admission=false` сохраняется; A/B/C не исполнены и T014 открыта.
Каждый вопрос проверен заново; изменённые требования не нарушают его исходные границы. Подробное основание каждого пункта приведено в новом отчёте.
Полная карта 120 вопросов, контрольные суммы, собственные чтения и сохранность: новый внешний `f099-t014-real-transport-independent-requirements-rereview-20261117.md`. После этого назначения автоматического перехода к реализации нет.
