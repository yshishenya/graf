# Specification Quality Checklist: Единый процесс разработки и переносимый harness

**Purpose**: Проверить полноту и качество спецификации до планирования
**Created**: 2026-08-31
**Feature**: [spec.md](../spec.md)

## Content Quality

- [ ] Нет лишних деталей реализации в пользовательских сценариях
- [ ] Описана ценность для владельца, агента, reviewer и operator
- [ ] Текст понятен участникам без знания внутреннего кода
- [ ] Все обязательные разделы шаблона заполнены

## Requirement Completeness

- [ ] Нет нерешённых маркеров `NEEDS CLARIFICATION`
- [ ] Требования проверяемы и однозначны
- [ ] Success criteria измеримы и проверяются без скрытых допущений
- [ ] Описаны позитивные, конкурентные и отказные сценарии
- [ ] Границы In Scope / Out of Scope явны
- [ ] Assumptions и зависимости зафиксированы
- [ ] Legacy Impact и follow-up boundary зафиксированы

## Governance Readiness

- [ ] Каждый user story независимо тестируем
- [ ] Worktree, Feature ID, Dev, CI, release и harness имеют трассируемые критерии
- [ ] Reviewer-owned checklist не смешан с implementation DoD
- [ ] Требования не ослабляют constitution, product gates или public signing rules
- [ ] Отдельный reusable repository имеет provenance, versioning и secret/path boundary

## Notes

Чекбоксы изменяет reviewer, а не агент реализации. После clarify и plan этот
лист должен быть проверен повторно; незакрытые пункты блокируют переход к
implementation, если они влияют на безопасность, данные, release или rollback.
