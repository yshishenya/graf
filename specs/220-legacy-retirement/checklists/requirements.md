# Specification Quality Checklist: Безопасная инвентаризация и retirement legacy

**Purpose**: Проверить полноту и качество требований до clarify/plan.
**Created**: 2026-08-31
**Feature**: [spec.md](../spec.md)

**Review Ownership**: reviewer-owned; implementation agent не меняет checkbox state.

## Content Quality

- [ ] Нет implementation details в user-facing requirements.
- [ ] Ценность и границы понятны владельцу продукта.
- [ ] Определены actors, цели и приоритетные user stories.
- [ ] Scope и out-of-scope явно разделены.

## Requirement Completeness

- [ ] Нет нерешённых `[NEEDS CLARIFICATION]`.
- [ ] Каждый FR тестируем и однозначен.
- [ ] Edge cases покрывают drift, stale SHA, secrets и compatibility history.
- [ ] Для exception определены owner, expiry, trigger, risk и validation.
- [ ] Для retirement slices определены cutover, backup и rollback.

## Traceability and Safety

- [ ] Каждый success criterion измерим и проверяем.
- [ ] Metadata-only boundary исключает пользовательские данные и секреты.
- [ ] Production, migration pointer и irreversible deletion защищены отдельными gates.
- [ ] Legacy Impact и запрет нового legacy согласованы с constitution и Feature 216.

## Notes

- Чеклист остаётся reviewer-owned и не отмечается агентом реализации.
