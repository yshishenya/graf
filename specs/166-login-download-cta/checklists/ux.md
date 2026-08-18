# UX Requirements Checklist: Контекстная ссылка на приложение на экране входа

**Purpose**: Проверить полноту UX, accessibility и responsive требований
**Created**: 2026-08-18
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] Определено, где web CTA находится относительно primary auth task [Completeness, FR-001–FR-002]
- [x] Для embedded-поверхности явно задано отсутствие CTA без placeholder [Completeness, FR-003]
- [x] Сценарии обычного входа и auth error покрыты отдельно [Coverage, FR-006]
- [x] Соседние login/signup/referral/public поверхности включены в границы [Coverage, FR-007]

## Requirement Clarity

- [x] «Заметный» CTA связан с нижней левой областью и широким viewport [Clarity, FR-002]
- [x] Responsive boundary и minimum width 320 px указаны явно [Measurability, FR-005]
- [x] Видимый focus state и понятное accessible name заданы явно [Accessibility, FR-005]

## Scenario And Edge Coverage

- [x] Direct login без `next`, desktop settings path и unsafe `next` описаны [Edge Case]
- [x] Требование non-overlap включает форму, alert, legal copy и узкое окно [Edge Case, FR-005]
- [x] Acceptance criteria различают browser и embedded visual outcomes [Acceptance, SC-002–SC-003]

## Notes

- Checklist проверяет качество требований, а не конкретные DOM или CSS детали.
