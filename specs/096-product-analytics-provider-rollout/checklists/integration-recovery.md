# Требования к интеграции аналитики

Reviewer-owned. Область: T109 и integration-recovery-plan-2026-10-16.md; только качество требований, не production readiness.

- [x] CHK001 Зафиксированы точные source/base, сохранение исходного draft-контракта FR-030–034a и отсутствие нового разрешения provider/runtime?
- [x] CHK002 Обе ветки миграций и единственная итоговая вершина определены без изменения прежних revision IDs и автоматического согласия?
- [x] CHK003 Определены реальные disposable DB проверки upgrade с обеих текущих вершин, null/no-default/no-backfill и сохранения sharing?
- [x] CHK004 Личное согласие/identity/повторы и приватность сохраняют исходные gates; старые CI/readback не выдаются за новые?
- [x] CHK005 Различены локальная интеграция, реальный isolated ingestion и production запуск; оставшиеся proof/approval блокеры перечислены?
- [x] CHK006 Определены независимое review/converge, commit approval, exact-SHA PR CI, отдельный release и сохранение чужих работ?

Проверено независимым рецензентом 16.10.2026: **PASS, 6 выполнено / 0 открыто** на уровне качества требований. CHK003 уточнён как требование к будущей проверке; отметка не означает, что PostgreSQL или другие проверки уже выполнены. Основания и границы: [integration-recovery-requirements-review.md](../integration-recovery-requirements-review.md). Исторические списки проверок не изменены и не переаттестованы.
