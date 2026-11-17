# Media Requirements Checklist: Review M4A Normalization

**Purpose**: Validate that the media-acceptance and canonical-output requirements are complete, precise, consistent, and measurable before task generation
**Created**: 2026-07-14
**Feature**: [spec.md](../spec.md)

**Audience / depth**: PR and release reviewers; formal high-risk gate.

## Requirement Completeness

- [x] CHK001 Are the supported container/codec combinations defined without relying on filename extensions? [Completeness, Spec §FR-003, Contract §Supported source matrix]
- [x] CHK002 Are the canonical codec, object type, sample rate, channel count, bitrate range, stream disposition, duration, size, metadata, chapter and BMFF-layout requirements all specified? [Completeness, Spec §FR-001/FR-006, Contract §Canonical profile]
- [x] CHK003 Are input duration, source/package size, total-stream, audio-stream, output-size and work-storage limits documented with exact values? [Completeness, Spec §FR-021/FR-029, Contract §Limits]
- [x] CHK004 Are requirements defined for empty, corrupt, encrypted, video-only, album-art-only, unsupported and over-limit sources? [Coverage, Spec §FR-011/FR-012/FR-031, Contract §Failure classification]
- [x] CHK005 Are requirements defined for first-party playback candidates, manual source media and microphone/system fallback as separate accepted-source cases? [Completeness, Spec §FR-003/FR-004/FR-026, Contract §Accepted-source boundary]

## Requirement Clarity

- [x] CHK006 Is “supported valid accepted source with usable audio” bounded by an explicit matrix, source-integrity gate and stream-selection rule? [Clarity, Spec §FR-039/FR-040, Contract §Probe contract]
- [x] CHK007 Is byte-for-byte reuse distinguished unambiguously from lossless remux and audio transcoding? [Clarity, Spec §FR-038, Contract §Reuse/remux/transcode decisions]
- [x] CHK008 Is the unique-audio selection rule explicit for one usable stream, one unique default and ambiguous multiple streams, with guessing and mixing excluded? [Clarity, Spec §FR-039, Contract §Single-container audio selection]
- [x] CHK009 Is the first-party two-role mix rule precise about gains, alignment, longest timeline, missing tails and resampling? [Clarity, Spec §FR-004, Contract §First-party dual-source mix]
- [x] CHK010 Is complete validation defined as full decode plus bounded structural/profile checks rather than probe metadata alone? [Clarity, Spec §FR-006/FR-030, Contract §Complete output gate]

## Requirement Consistency

- [x] CHK011 Are reuse/remux/transcode requirements consistent between the clarified product decision, FR-038, research and the normalization contract? [Consistency, Spec §Clarifications/FR-038]
- [x] CHK012 Are the exact profile and resource values consistent across the plan, research, normalization contract, lifecycle contract and quickstart? [Consistency, Spec §FR-021, Assumption]
- [x] CHK013 Does first-party fallback remain consistent with the established microphone/system source roles without applying the manual multi-track ambiguity rule? [Consistency, Spec §FR-004/FR-039, Contract §First-party dual-source mix]
- [x] CHK014 Does the output-publication requirement consistently exclude partial, temporary, failed and legacy-unvalidated artifacts from playback readiness? [Consistency, Spec §FR-006/FR-013/FR-030/FR-041]

## Acceptance Criteria Quality

- [x] CHK015 Can the 100% automatic-conversion outcome be measured separately for supported valid inputs and objectively impossible inputs? [Measurability, Spec §SC-002/SC-006/SC-020]
- [x] CHK016 Can canonical readiness be decided from one versioned profile with no subjective or environment-dependent criteria? [Measurability, Spec §SC-001/SC-015, Contract §Canonical profile]
- [x] CHK017 Are seek/range and no-on-demand-conversion outcomes measurable without conflating them with normalization-worker behavior? [Acceptance Criteria, Spec §SC-003/SC-011]

## Dependencies And Assumptions

- [x] CHK018 Are the required FFmpeg/FFprobe capabilities and the rule forbidding them from request-path processes documented as release-gated dependencies? [Dependency, Plan §Technical Context, Lifecycle Contract §Dependency capability gate]
- [x] CHK019 Is the accepted-source custody assumption explicit enough to exclude raw in-flight uploads, unmanaged files and replacement source fabrication? [Assumption, Spec §FR-026/FR-028/FR-033]
- [x] CHK020 Is video playback, user track selection, source editing and source-only retention explicitly outside this feature? [Scope, Spec §Out Of Scope]

## Notes

- Final 2026-07-14 reconciliation: `20/20` items remain satisfied and map to
  the media capability, supported/failure matrix, local E2E and near-limit
  performance receipts in `validation/traceability.md`.
- Items validate requirement writing, not implementation behavior.
- The user’s must-have is represented as a formal guarantee for every supported valid retained source, with no user or workspace-administrator repair action.

## Независимое ревью 2026-11-17 — F099/T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; исходный HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Каждый исходный вопрос заново сопоставлен с текущими документами; `[x]` означает качество требований в области вопроса, без runtime-приёмки. Исторические итоги выше сохранены как история.
Итог этого файла: checked **20**, unchecked **0**, всего **20**. Общий допуск T014: **STOP**, пока не закрыты H1–H3.
Неподтверждённых исходных пунктов этого файла нет; его вопросы не заменяют отсутствующий контракт локального destination в requirements/lifecycle.
Полная построчная карта и минимальные правки: внешний отчёт `f099-t014-independent-requirements-review-20261117.md` в каталоге доказательств текущей задачи.

## Повторное независимое ревью 2026-11-17 — T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; тот же reviewer-диалог, HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Текущая spec SHA-256 `338751c8f41d766d8b09ec97a5cfc2a5beeb372e484d3b6273a396d5feff2136`; plan/tasks/quickstart и чтения привязаны в новом отчёте.
Итог этого файла: checked **20**, unchecked **0**, всего **20**. Все исходные вопросы заново оценены; вопросы и прежние STOP-заметки сохранены как история.
Все 20 исходных вопросов повторно сопоставлены с Spec FR-001–044, contracts profile/matrix/selection/full gate и Plan/Quickstart. Медиа-профиль/лимиты/владение source не изменены. Для CHK012 новый Session 2026-11-17 согласует 4 MiB default/действующих consumers с явным chunk_size без изменения API. Старые dual-source описания не разрешают возвращать удалённую отправку вместо текущей F275.
Общий reviewer-owned requirements gate: **PASS, 100/100**, только качество требований. Известный дефект кода и открытая T014 остаются; выполнение, analyze/issue sync, регрессии, code review/converge, exact-SHA PR/base и выпуск/развёртывание проверяются отдельно.
Полная карта каждого исходного пункта и текущие ограничения: внешний отчёт `f099-t014-independent-requirements-rereview-20261117.md` в каталоге доказательств текущей задачи.

## Независимое ревью нового real-transport scope — 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы заново оценены по текущим требованиям. Старые STOP/PASS выше сохранены как история guard; новый общий допуск **STOP, implementation_admission=false**.
Итог файла: checked **20**, unchecked **0**, всего **20**. `[x]` означает только качество требований, не выполнение A/B/C и не закрытие T014.
Полная карта всех 120 вопросов, исходники и H1/H2: внешний `f099-t014-real-transport-independent-requirements-review-20261117.md`. Неподтверждённые пункты блокируют реализацию; A/B/C остаются неисполненными независимо от отметок.


## Повторное независимое ревью real-transport — H1/H2, 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы повторно сопоставлены с текущими оригиналами; прежние вопросы и заметки сохранены.
Итог файла: проверено **20**, непроверено **0**, всего **20**. Общий результат качества требований — **PASS, 120/0**. Это не допуск реализации: `implementation_admission=false` сохраняется; A/B/C не исполнены и T014 открыта.
Каждый вопрос проверен заново; изменённые требования не нарушают его исходные границы. Подробное основание каждого пункта приведено в новом отчёте.
Полная карта 120 вопросов, контрольные суммы, собственные чтения и сохранность: новый внешний `f099-t014-real-transport-independent-requirements-rereview-20261117.md`. После этого назначения автоматического перехода к реализации нет.
