# Worker-Interrupted Startup Recovery Requirement Checklist

**Purpose**: Requirement-quality check for the 2026-07-17 production hotfix.
It does not claim runtime validation.

## Scope And Clarity

- [x] CHK001 Is the automatic recovery trigger limited to the durable machine-readable `worker_interrupted` reason? [Clarity, Spec §Clarifications 2026-07-17, FR-043]
- [x] CHK002 Does the requirement state that no user or workspace administrator performs a retry or repair action? [User value, Spec §Clarifications 2026-07-17, FR-023, FR-043]
- [x] CHK003 Does it preserve the original record/job lineage rather than create replacement work or media? [Consistency, Spec §FR-007, FR-010, FR-024, FR-043]

## Safety And Boundaries

- [x] CHK004 Is long scheduled backoff preserved for every reason other than `worker_interrupted`? [Safety, Spec §FR-011, FR-023, FR-043]
- [x] CHK005 Is recovery constrained to worker startup rather than each periodic reconciliation pass? [Bounded behavior, Plan §2026-07-17 Production Recovery Hotfix]
- [x] CHK006 Does the hotfix exclude schema, source-custody, playback-route and native-app changes? [Scope, Plan §2026-07-17 Production Recovery Hotfix]
- [x] CHK007 Is the existing lock/audit/lease/dispatch lifecycle retained rather than bypassed? [Lifecycle, Plan §2026-07-17 Production Recovery Hotfix]

## Acceptance Quality

- [x] CHK008 Is success measurable for both immediate interrupted-job dispatch and non-preemption of another retry reason? [Measurability, Spec §SC-023]

## Notes

- The checklist is complete for requirement quality. Runtime proof is owned by
  T117–T120 and must remain metadata-only.

## Независимое ревью 2026-11-17 — F099/T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; исходный HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Каждый исходный вопрос заново сопоставлен с текущими документами; `[x]` означает качество требований в области вопроса, без runtime-приёмки. Исторические итоги выше сохранены как история.
Итог этого файла: checked **8**, unchecked **0**, всего **8**. Общий допуск T014: **STOP**, пока не закрыты H1–H3.
Неподтверждённых исходных пунктов этого файла нет; его вопросы не заменяют отсутствующий контракт локального destination в requirements/lifecycle.
Полная построчная карта и минимальные правки: внешний отчёт `f099-t014-independent-requirements-review-20261117.md` в каталоге доказательств текущей задачи.

## Повторное независимое ревью 2026-11-17 — T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; тот же reviewer-диалог, HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Текущая spec SHA-256 `338751c8f41d766d8b09ec97a5cfc2a5beeb372e484d3b6273a396d5feff2136`; plan/tasks/quickstart и чтения привязаны в новом отчёте.
Итог этого файла: checked **8**, unchecked **0**, всего **8**. Все исходные вопросы заново оценены; вопросы и прежние STOP-заметки сохранены как история.
Все 8 исходных вопросов повторно сопоставлены с FR-043/SC-023 и Plan Production Recovery Hotfix. Worker-interrupted startup trigger, same lineage, non-preemption других reasons, lock/audit/lease/dispatch и отсутствие user repair остаются прежними; T014 не добавляет restart или runtime действие.
Общий reviewer-owned requirements gate: **PASS, 100/100**, только качество требований. Известный дефект кода и открытая T014 остаются; выполнение, analyze/issue sync, регрессии, code review/converge, exact-SHA PR/base и выпуск/развёртывание проверяются отдельно.
Полная карта каждого исходного пункта и текущие ограничения: внешний отчёт `f099-t014-independent-requirements-rereview-20261117.md` в каталоге доказательств текущей задачи.
