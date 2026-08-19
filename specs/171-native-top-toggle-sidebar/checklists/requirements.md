# Specification Quality Checklist: Единый верхний toggle и аккуратный rail

**Purpose**: Проверить полноту и измеримость требований до планирования
**Created**: 2026-08-19
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Требования описывают пользовательскую ценность, а не внутреннюю реализацию
- [x] Границы native и web поверхностей явно разделены
- [x] Обе пользовательские истории имеют независимый способ проверки
- [x] Все обязательные разделы спецификации заполнены

## Requirement Completeness

- [x] Нет нерешённых маркеров NEEDS CLARIFICATION
- [x] Требования проверяемы и не противоречат друг другу
- [x] Указаны wide/narrow, keyboard, focus и reduced-motion состояния
- [x] Указаны ошибки компоновки: перекрытие, пустая полоса и overflow
- [x] Scope, assumptions и out-of-scope зафиксированы

## Feature Readiness

- [x] Native top slot и web rail state имеют отдельные acceptance criteria
- [x] Existing capture/auth/content boundaries защищены
- [x] Success criteria измеримы без привязки к реализации
- [x] Не добавлены лишние storage, router, analytics или dependencies

## Notes

Спецификация готова к clarify/plan; критических неоднозначностей не оставлено.
