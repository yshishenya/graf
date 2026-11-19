# Specification Quality Checklist: Review M4A Normalization

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-07-09
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Final 2026-07-14 reconciliation: `16/16` items remain satisfied; the four
  feature checklists total `80/80`. Runtime and evidence ownership is recorded
  per FR/SC in `validation/traceability.md`; this checklist does not convert
  requirement-quality checks into runtime claims.
- Validation lane: significant/high-risk Spec Kit feature. It touches manual upload, processing, storage, playback, retention/deletion, audit and diagnostics.
- Implementation must continue later through `$speckit-clarify`, `$speckit-plan`, `$speckit-checklist`, `$speckit-tasks`, `$speckit-analyze`, `$speckit-taskstoissues` and only then `$speckit-implement`.
- This entry intentionally records the product decision from 2026-07-09: review playback uses a prepared `meeting-review.m4a`; manual uploads are transcoded/normalized into that artifact; playback does not transcode or assemble source media on demand.
- Updated after the upload/finalize safety review to preserve the current accepted-source boundary: 099 must consume accepted source artifacts, must not create a competing upload/finalize source-of-truth, and must not reintroduce full-buffer behavior through normalization, retry or backfill.
- Current-state safety baseline references are intentional product-boundary constraints for planning. They do not prescribe a new implementation service; they prevent 099 from conflicting with existing ingest/finalize, playback and MediaScribe lifecycle boundaries.
- Clarifications are listed as normal planning questions, not `[NEEDS CLARIFICATION]` blockers, because the user asked to preserve the feature context for later rather than start implementation now.

## Независимое ревью 2026-11-17 — F099/T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; исходный HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Каждый исходный вопрос заново сопоставлен с текущими документами; `[x]` означает качество требований в области вопроса, без runtime-приёмки. Исторические итоги выше сохранены как история.
Итог этого файла: checked **9**, unchecked **7**, всего **16**. Общий допуск T014: **STOP**, пока не закрыты H1–H3.
- Пункт 06: H1/H2: FR-029/031/037 не определяют до-create ownership и точное поведение ошибки локального destination.
- Пункт 09: H2: нет acceptance для EEXIST regular/symlink и собственного partial write/fsync/size/digest failures.
- Пункт 10: H1/H2: Edge Cases не включают существующий destination и отказ создания до владения.
- Пункт 11: H3: активные status/Legacy Impact и Plan owned paths описывают #7647, не текущую границу T014/#3361.
- Пункт 12: H3: общие storage/submit dependencies названы, но влияние shared helper на sync/async и обоих callers не закреплено для T014.
- Пункт 13: H1/H2: safety FR не имеют чётких критериев сохранности локального destination/его очистки.
- Пункт 15: H1/H2/H3: для текущего T014 отсутствует измеримый исход сохранности destination и его трассировка; исторические outcomes не подтверждают его.
Полная построчная карта и минимальные правки: внешний отчёт `f099-t014-independent-requirements-review-20261117.md` в каталоге доказательств текущей задачи.

## Повторное независимое ревью 2026-11-17 — T014/#3361

Проверяющий: `/root/f099_download_requirements_review`; тот же reviewer-диалог, HEAD `c22500f994a0dc5f951341e3c5f202d5d21ac8a2`.
Текущая spec SHA-256 `338751c8f41d766d8b09ec97a5cfc2a5beeb372e484d3b6273a396d5feff2136`; plan/tasks/quickstart и чтения привязаны в новом отчёте.
Итог этого файла: checked **16**, unchecked **0**, всего **16**. Все исходные вопросы заново оценены; вопросы и прежние STOP-заметки сохранены как история.
H1/H2: Spec Session 2026-11-17, FR-045/SC-025 и Quickstart T014 определяют сохранность существующих файла/ссылки/цели до create, очистку только своего partial после create, причины и ресурсы. H3: Status/Legacy Impact, Plan T014, открытая T014 и общие sync/async/оба callers теперь согласованы. Пункты 06/09/10/11/12/13/15 получили доказательство качества требований; измеримые сценарии ещё не исполнены.
Общий reviewer-owned requirements gate: **PASS, 100/100**, только качество требований. Известный дефект кода и открытая T014 остаются; выполнение, analyze/issue sync, регрессии, code review/converge, exact-SHA PR/base и выпуск/развёртывание проверяются отдельно.
Полная карта каждого исходного пункта и текущие ограничения: внешний отчёт `f099-t014-independent-requirements-rereview-20261117.md` в каталоге доказательств текущей задачи.

## Независимое ревью нового real-transport scope — 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы заново оценены по текущим требованиям. Старые STOP/PASS выше сохранены как история guard; новый общий допуск **STOP, implementation_admission=false**.
Итог файла: checked **11**, unchecked **5**, всего **16**. `[x]` означает только качество требований, не выполнение A/B/C и не закрытие T014.
- R06: H1/H2: Нельзя однозначно реализовать outer PG ownership/image check при закрытом runner interface; обычный CI режим не задан.
- R09: H2: Не определены обычные all-suite collection/execution без подготовленных CLI/MinIO и отличие от явного acceptance failure.
- R10: H1/H2: Названы аварии/timeout, но нет проверяемого handoff identity до создания ресурса и контракта обычного discovery.
- R12: H1/H2: Перечень компонентов есть, но ограничения существующего PG interface и default CI discovery не разрешены design-решением.
- R13: H1: Для cleanup при смерти PG child отсутствует доказуемый источник точной identity; одно обещание ID/label не образует исполнимый критерий.
Полная карта всех 120 вопросов, исходники и H1/H2: внешний `f099-t014-real-transport-independent-requirements-review-20261117.md`. Неподтверждённые пункты блокируют реализацию; A/B/C остаются неисполненными независимо от отметок.


## Повторное независимое ревью real-transport — H1/H2, 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы повторно сопоставлены с текущими оригиналами; прежние вопросы и заметки сохранены.
Итог файла: проверено **16**, непроверено **0**, всего **16**. Общий результат качества требований — **PASS, 120/0**. Это не допуск реализации: `implementation_admission=false` сохраняется; A/B/C не исполнены и T014 открыта.
- R06: PASS: Контракт H1 задаёт единственный служебный вход, точную схему manifest, известное до create имя/token/image, сверку до SQL, ограниченные сроки и безопасную очистку. H2 выбирает отдельный acceptance-путь и обычный CI без его импорта; неоднозначность H1/H2 устранена.
- R09: PASS: H2 раздельно требует обычные collection/execution без CLI/MinIO/контекста и явный вызов без контекста с FAIL до импорта приложения/миграций и ресурсов. A/B/C по-прежнему открыты.
- R10: PASS: H1 перечисляет malformed/symlink/foreign manifest, mismatch до SQL, отказы create до/после контейнера, смерть до cidfile, TERM/KILL, сроки, неизвестное отсутствие и чужой параллельный контейнер. H2 покрывает обычное обнаружение и явный вызов.
- R12: PASS: H1 теперь явно признаёт ограничение исходного runner и разрешает узкий manifest/image/label/cidfile/state интерфейс с сохранением обычного режима. H2 описывает testpaths, filename pattern и порядок plugin до CLI parsing; недостающий evaluation extra готовится явно.
- R13: PASS: Критерий очистки опирается на известные до create имя/token/image и внешнюю cleanup_required квитанцию; точный lookup сверяет имя/label/image и удаляет только фактический ID. Неизвестность даёт FAIL без удаления; после смерти supervisor назначен последующий владелец.
Полная карта 120 вопросов, контрольные суммы, собственные чтения и сохранность: новый внешний `f099-t014-real-transport-independent-requirements-rereview-20261117.md`. После этого назначения автоматического перехода к реализации нет.
