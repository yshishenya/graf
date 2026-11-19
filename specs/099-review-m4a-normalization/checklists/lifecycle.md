# Lifecycle And Operations Requirements Checklist: Review M4A Normalization

**Purpose**: Validate lifecycle, privacy, isolation, tenancy, rollout and rollback requirement quality before task generation
**Created**: 2026-07-14
**Feature**: [spec.md](../spec.md)

**Audience / depth**: PR, operations and release reviewers; formal high-risk gate.

## Requirement Completeness

- [x] CHK001 Are candidate, accepted source, attempt, canonical and temporary artifact ownership/lifecycle requirements all documented separately? [Completeness, Spec §FR-018/FR-030, Data Model §Data lifecycle]
- [x] CHK002 Are publication prerequisites defined for source fingerprint, full validation, immutable object registration, database visibility and one active canonical artifact? [Completeness, Spec §FR-006/FR-013/FR-035, Data Model §Publication]
- [x] CHK003 Are deletion and retention requirements defined for jobs, attempts, candidates, canonical objects, temp work files and operational reports? [Completeness, Spec §FR-018/FR-036, Lifecycle Contract §Deletion report/Retention]
- [x] CHK004 Are tenant isolation, forced RLS, worker tenant context and narrowly scoped global inventory/dispatch maintenance requirements documented? [Completeness, Spec §FR-026/FR-027, Lifecycle Contract §RLS and maintenance]
- [x] CHK005 Are deployment, migration, worker readiness, backfill gating, rollback and residue-free closeout requirements specified? [Completeness, Lifecycle Contract §Deployment gate/Rollback/Closeout evidence]

## Requirement Clarity

- [x] CHK006 Is the publication visibility boundary described without claiming a distributed MinIO/PostgreSQL transaction? [Clarity, Data Model §Transaction and race invariants]
- [x] CHK007 Is deletion-wins precedence explicit for every publish race and cleanup-pending state? [Clarity, Spec §FR-036/SC-017, Lifecycle Contract §Publication/deletion race]
- [x] CHK008 Are resource controls quantified for CPU, memory, concurrency, work storage, free-space reserve, output, timeouts and subprocess-output bounds? [Clarity, Spec §FR-021/FR-029, Lifecycle Contract §Resource controls]
- [x] CHK009 Are readiness and health states separated so a healthy worker cannot imply that media conversion or backfill succeeded? [Clarity, Lifecycle Contract §Readiness and metrics]
- [x] CHK010 Are rollback limits explicit for schema compatibility, previously published canonical objects and in-flight automatic jobs? [Clarity, Lifecycle Contract §Rollback]

## Privacy And Security Requirement Quality

- [x] CHK011 Is the safe metadata allowlist explicit and are raw filenames, paths, object keys/URLs, FFmpeg output, tags, content and credentials consistently forbidden? [Completeness, Spec §FR-020/FR-037/SC-010, Lifecycle Contract §Audit and logging]
- [x] CHK012 Are untrusted-media subprocess requirements specified for non-root execution, file-only protocols, process groups, private work files and image isolation? [Coverage, Plan §Constraints, Lifecycle Contract §Runtime topology]
- [x] CHK013 Are foreign-tenant and shared-viewer information-disclosure requirements defined for status and playback routes? [Coverage, Status Contract §Privacy/access rules]
- [x] CHK014 Are operational incidents metadata-only, deduplicated and clearly separated from any user repair action? [Consistency, Lifecycle Contract §Operational incidents]

## Scenario And Edge-Case Coverage

- [x] CHK015 Are object-upload-before-database-commit, database-commit-before-dispatch, worker crash, lease expiry and orphan cleanup scenarios addressed? [Coverage, Data Model §Transaction and race invariants, Backfill Contract §Restart recovery]
- [x] CHK016 Are concurrent deletion, retention purge, retry, backfill and publication scenarios assigned deterministic lock/precedence outcomes? [Coverage, Spec §FR-035/FR-036, Lifecycle Contract §Publication/deletion race]
- [x] CHK017 Are disk-full, no-temp-capacity, dependency outage, source mismatch and cleanup failure outcomes assigned safe durable states and recovery ownership? [Coverage, Spec §FR-031/FR-037, Lifecycle Contract §Resource controls/Operational incidents]
- [x] CHK018 Are migration upgrade/downgrade, legacy unvalidated artifacts and partial rollout with old API/processing workers covered? [Coverage, Data Model §Migration 0022, Lifecycle Contract §Rollback]

## Acceptance Criteria And Traceability

- [x] CHK019 Can lifecycle success be measured for 100% of overlapping deletion/retention events and reports? [Measurability, Spec §SC-008/SC-017]
- [x] CHK020 Can tenant isolation, no-secret egress, non-root worker/resource limits and zero-residue cleanup be evidenced independently? [Measurability, Spec §SC-010/SC-013, Quickstart §§7–8/15]
- [x] CHK021 Are release acceptance and rollback triggers tied to exact evidence rather than generic green health checks? [Acceptance Criteria, Plan §Release Gate, Lifecycle Contract §Deployment gate]
- [x] CHK022 Is deferred feature-097 security-scan work explicitly separated from ordinary 099 authorization/RLS/privacy acceptance gates? [Scope, Plan §Validation Plan, Quickstart §Purpose]

## Notes

- Final 2026-07-14 reconciliation: `22/22` items remain satisfied and map to
  migration/RLS, deletion-race, resource, cleanup and rollout evidence in
  `validation/traceability.md`.
- Items validate the written lifecycle and operations contract, not implementation behavior.
- Feature 097 remains deferred and untouched; this checklist does not claim completion of its standalone security scan.

## Независимое ревью 2026-11-17 — F099/T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; исходный HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Каждый исходный вопрос заново сопоставлен с текущими документами; `[x]` означает качество требований в области вопроса, без runtime-приёмки. Исторические итоги выше сохранены как история.
Итог этого файла: checked **19**, unchecked **3**, всего **22**. Общий допуск T014: **STOP**, пока не закрыты H1–H3.
- Пункт 01: H1: Model/Contract описывают DB/object ownership, но не границу владения локальным destination перед os.open и при его отказе.
- Пункт 17: H1/H2: общие retryable temp/resource состояния есть, но safe outcome до-create ENOSPC/permission/EEXIST и cleanup только своего partial не заданы.
- Пункт 20: H2: Quickstart не задаёт независимые проверки сохранности existing file/link, удаления only-own partial и освобождения transfer resources для T014.
Полная построчная карта и минимальные правки: внешний отчёт `f099-t014-independent-requirements-review-20261117.md` в каталоге доказательств текущей задачи.

## Повторное независимое ревью 2026-11-17 — T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; тот же reviewer-диалог, HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Текущая spec SHA-256 `338751c8f41d766d8b09ec97a5cfc2a5beeb372e484d3b6273a396d5feff2136`; plan/tasks/quickstart и чтения привязаны в новом отчёте.
Итог этого файла: checked **22**, unchecked **0**, всего **22**. Все исходные вопросы заново оценены; вопросы и прежние STOP-заметки сохранены как история.
CHK001: FR-045 и Plan T014 определяют локальное владение после exclusive create отдельно от artifact registry. CHK017: Quickstart T014 различает EEXIST/ENOSPC/EACCES до create и write/fsync/size/digest после create, назначает safe outcome/reason/cleanup only-own partial. CHK020: inode/bytes/mode/link/target, descriptor fstat и раздельные response close/release — независимые утверждения; не один shared fake closed flag. Отказы самой cleanup/close/release и post-open pathname replacement прямо не объявлены проверенными.
Общий reviewer-owned requirements gate: **PASS, 100/100**, только качество требований. Известный дефект кода и открытая T014 остаются; выполнение, analyze/issue sync, регрессии, code review/converge, exact-SHA PR/base и выпуск/развёртывание проверяются отдельно.
Полная карта каждого исходного пункта и текущие ограничения: внешний отчёт `f099-t014-independent-requirements-rereview-20261117.md` в каталоге доказательств текущей задачи.

## Независимое ревью нового real-transport scope — 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы заново оценены по текущим требованиям. Старые STOP/PASS выше сохранены как история guard; новый общий допуск **STOP, implementation_admission=false**.
Итог файла: checked **19**, unchecked **3**, всего **22**. `[x]` означает только качество требований, не выполнение A/B/C и не закрытие T014.
- CHK015: H1: Продуктовые recovery пути описаны, но новый outer runner после смерти child не получает подтверждённую identity своего PG и не может доказать orphan cleanup.
- CHK017: H1: Cleanup failure назван FAIL, но не задан исполнимый владелец PG cleanup/ID handoff и безопасный bounded сценарий его аварийного окончания.
- CHK020: H1: Независимая RLS/host/container граница ясна, но zero-residue нового запуска нельзя доказать без надёжно полученного собственного PG ID.
Полная карта всех 120 вопросов, исходники и H1/H2: внешний `f099-t014-real-transport-independent-requirements-review-20261117.md`. Неподтверждённые пункты блокируют реализацию; A/B/C остаются неисполненными независимо от отметок.


## Повторное независимое ревью real-transport — H1/H2, 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы повторно сопоставлены с текущими оригиналами; прежние вопросы и заметки сохранены.
Итог файла: проверено **22**, непроверено **0**, всего **22**. Общий результат качества требований — **PASS, 120/0**. Это не допуск реализации: `implementation_admission=false` сохраняется; A/B/C не исполнены и T014 открыта.
- CHK015: PASS: Контракт H1 закрывает аварийное окно PG: имя/token/image известны и сохранены до Docker; потеря ответа create и отсутствие cidfile не теряют связь. Отдельные bounded проверки покрывают смерть child и повтор только после доказанного отсутствия.
- CHK017: PASS: H1 назначает parent supervisor владельцем очистки после child error/TERM/KILL/timeout; TERM и KILL ожидание по 5 секунд, операция очистки до 30 секунд. SIGKILL supervisor оставляет cleanup_required и FAIL следующему основному агенту/оператору.
- CHK020: PASS: Точная проверка name/label/image/ID и успешный lookup отсутствия отделены от RLS и остальных утверждений; ошибка Docker не считается отсутствием. Contract tests обязаны независимо проверять zero residue и сохранность чужих ресурсов; исполнение ещё открыто.
Полная карта 120 вопросов, контрольные суммы, собственные чтения и сохранность: новый внешний `f099-t014-real-transport-independent-requirements-rereview-20261117.md`. После этого назначения автоматического перехода к реализации нет.
