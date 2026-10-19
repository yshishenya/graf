# Specification Quality Checklist: Управляемое поэтапное retirement legacy

**Purpose**: Reviewer-owned проверка качества требований перед implementation.
**Created**: 2026-08-31
**Feature**: [spec.md](../spec.md)

Независимое ревью требований выполнено 2026-10-19 по действующей конституции
7.1.0. Отметки принадлежат независимому проверяющему; они не подтверждают
реализацию задач. Доказательства первого и повторного проходов:
[отчёт ревью](../requirements-review-20261019.md).

## Requirement Completeness

- [x] CHK001 Are candidate discovery, approved classification and removal authorization explicitly distinguished? [Completeness, Spec §US1, FR-001, FR-008]
- [x] CHK002 Are all metadata-only record fields, forbidden content classes and stale-evidence conditions specified? [Completeness, Spec §FR-002–FR-004]
- [x] CHK003 Are owner, expiry, trigger, risk, validation and linked work required for every retained exception? [Completeness, Spec §FR-006]
- [x] CHK004 Are protected domains and their separate planning/rehearsal boundaries specified rather than delegated to generic cleanup? [Completeness, Spec §FR-010–FR-012]

## Requirement Clarity and Consistency

- [x] CHK005 Is the meaning of `candidate`, `approved`, `blocked` and `retired` unambiguous and consistent with classifications? [Clarity, Spec §FR-001–FR-002]
- [x] CHK006 Is a "legacy-sensitive path" sufficiently bounded to distinguish active compatibility from archival evidence and documentation? [Clarity, Spec §FR-007]
- [x] CHK007 Are the no-removal, no-production-mutation and no-reviewer-checkbox boundaries consistent across scope, requirements and tasks? [Consistency, Spec §FR-017–FR-018]
- [x] CHK008 Are the Feature 216 legacy contract and Feature 228 additions non-conflicting and traceably related? [Consistency, Spec §Assumptions]

## Acceptance and Safety Coverage

- [x] CHK009 Can each success criterion be objectively demonstrated without exposing user or production data? [Measurability, Spec §SC-001–SC-008]
- [x] CHK010 Are incomplete discovery, stale SHA, forbidden metadata, expired exceptions and missing rollback handled as explicit failure states? [Coverage, Spec §Edge Cases]
- [x] CHK011 Are migration, Temporal, MediaScribe (T036), macOS/Sparkle and rollback domains covered by domain-appropriate evidence requirements? [Coverage, Spec §FR-010–FR-012]
- [x] CHK012 Are release-train and individual fast-CI evidence requirements explicitly non-interchangeable? [Consistency, Spec §US5, FR-016]

## Agent Context and Governance

- [x] CHK013 Does the specification define the minimum context an agent reads and prohibit full-registry/root-file duplication? [Completeness, Spec §US4, FR-014]
- [x] CHK014 Are GitHub issue, PR, task, changelog-fragment and exact-SHA links required without making root CHANGELOG.md a parallel write target? [Completeness, Spec §FR-015–FR-017]
- [x] CHK015 Is the decision owner/reviewer role clear for every point that could otherwise authorize removal? [Clarity, Spec §Actors, §Assumptions]

## Примечания независимого проверяющего — повторный проход 2026-10-19

Первый проход: 13 подтверждено, 2 открыто; исходный BLOCKED и хеши сохранены
в отчёте. После полного чтения пяти исправленных документов H1/H2 устранены:

- CHK007: FR-017/SC-008, Scope, clarifications §6, plan, quickstart и tasks
  различают независимого reviewer-агента и агента реализации. Только первый
  ставит доказательные отметки, перечитывает и считает итоги; второй их не меняет.
- CHK009: SC-008 теперь проверяем безопасным отчётом, diff/ownership и
  итогами чеклистов; он не запрещает обязательное независимое ревью.
- H2: план, quickstart и T034 требуют три GitHub-проверки точного SHA/основы
  и `validate-pr-checks.py`; локальный общий fast остаётся диагностическим.
- Все 15 пунктов заново проверены по текущим требованиям. После повторного
  чтения: 15 подтверждено, 0 открыто. Это PASS только качества требований,
  без заявления о выполнении задач или закрытии issues. Анализ, issue sync,
  реализация и проверки продукта остаются отдельными воротами.
