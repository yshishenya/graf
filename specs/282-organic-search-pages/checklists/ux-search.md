# UX and Search Requirements Checklist: Поисковые страницы

**Purpose**: Ясность требований к сохранению главной, правдивому контенту, доступности и измерению.
**Created**: 2026-09-30
**Feature**: ../spec.md
**Review Ownership**: reviewer-owned; только независимый проверяющий меняет отметки.
**Marker Semantics**: [x] означает полноту требований, а не готовую реализацию.

## Сохранение и границы

- [x] CHK001 Определён ли точный разрешённый diff главной и способ сравнения прежнего смысла/экрана? [Clarity, Spec FR-003, SC-002]
- [x] CHK002 Различены ли текущая доступность платформ, браузерная загрузка и будущая Windows-версия без ложных обещаний? [Consistency, Spec FR-006]
- [x] CHK003 Определены ли самостоятельные ответы, примеры/проверка и ограничения всех трёх страниц? [Completeness, Spec FR-001, FR-002, US1]
- [x] CHK004 Определены ли метаданные, canonical, sitemap, ссылки и поведение неизвестных адресов? [Completeness, Spec FR-004, Edge Cases]

## Доступность и безопасность

- [x] CHK005 Заданы ли контрольные ширины, фокус, skip-link, заголовки и fallback без JS/картинок? [Measurability, Spec FR-007, SC-002]
- [x] CHK006 Зафиксированы ли границы счётчиков, согласия и недоступной БД без расширения analytics allowlists? [Consistency, Spec FR-005, Edge Cases]
- [x] CHK007 Указаны ли происхождение активов, требования законности записи и ограничения результатов AI? [Completeness, Spec FR-002, FR-006, FR-007]

## Приёмка и результат

- [x] CHK008 Отделены ли готовность изменения, выпуск, индексация и рост, определены ли окна/источники метрик и unknown? [Clarity, Spec FR-008, SC-003, SC-004, SC-005]
- [x] CHK009 Определены ли rollback и границы коммита/публикации без сброса чужой работы? [Coverage, Spec FR-008, Plan Delivery and rollback]

## Notes

Implementation читает отметки; requirements.md имеет отдельный built-in lifecycle.

## Independent review — 2026-09-30

PASS требований: 9 checked / 0 unchecked. Это не приёмка реализации, выпуска, индексации или роста.
Конкретные ссылки и сопоставление FR/SC с задачами: [requirements-review.md](../evidence/requirements-review.md).

- CHK001: spec.md:12,36,39,66,78; plan.md:31,41; contracts/public-search-pages.md:11; evidence/baseline.md:8–13.
- CHK002: spec.md:28–30,57,69; research.md:7; contracts/public-search-pages.md:5–7; существующий download.html:62.
- CHK003: spec.md:25–30,64–65; contracts/public-search-pages.md:3–7; tasks.md:T003/T005.
- CHK004: spec.md:54,67; contracts/public-search-pages.md:9; quickstart.md:17; tasks.md:T002/T004/T005.
- CHK005: spec.md:36,40,56,70,78; contracts/public-search-pages.md:11; quickstart.md:11; constitution.md:384 (WCAG 2.2 AA).
- CHK006: spec.md:55,68; plan.md:41; research.md:6; quickstart.md:17; public/templates.py:120–155 и public/analytics.py:660–746. «Новых cookies» означает отсутствие новых типов/полей cookies; существующий безопасный campaign cookie общего ответа сохраняется.
- CHK007: spec.md:29–30,65,69–70; plan.md:26; public/static/public/fonts/OFL.txt:1–5; product-gates.md раздел UX Reference Fidelity.
- CHK008: spec.md:46–50,71,79–81; evidence/measurement-plan.md:5–25; evidence/baseline.md:3–6.
- CHK009: spec.md:71; plan.md:17,39–42; quickstart.md:21; tasks.md:27.
