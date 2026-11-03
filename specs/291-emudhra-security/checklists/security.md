# Security requirements checklist F291

Purpose: reviewer-owned requirements quality. Created: 2026-10-23.
Feature: [spec.md](../spec.md). `[x]` means reviewed requirements, not implementation. Main implementation must not mark items.

- [x] CHK001 Are the exact advisory minimums and all lock/CI/runtime paths specified? [Completeness, FR-001/002/003]
- [x] CHK002 Are TLS rejection, ordinary HTTPS control and inconclusive network outcomes defined? [Measurability, FR-004, SC-001]
- [x] CHK003 Are trust-policy/TLS/secret/data boundaries explicit and consistent? [Consistency, FR-003/004/006]
- [x] CHK004 Are exact-SHA release evidence and honest incomplete-status requirements specified? [Traceability, FR-005/008, SC-003]

## Reviewer notes — 2026-10-23

CHK001 resolved after full reread of amended spec.md and plan.md: FR-001 now requires certifi >=2026.10.19 in pyproject plus all applicable lock/constraints; plan makes the floor mandatory. This matches release-and-validation.md dependency synchronization guidance. CHK002: FR-004/SC-001 and quickstart §5 specify both endpoints, ordinary control, 15-second timeout, no redirects and inconclusive DNS/timeout results. CHK003: FR-003/004/006 prohibit manual trust/TLS weakening and secret/data exposure. CHK004: FR-005/008 and SC-003 require exact-source release evidence and readback. All approvals concern requirements quality only; tasks.md reread remains required before implementation.

## Независимое ревью применимости — 2026-10-28

Повторно прочитаны требования и исходный runtime/image evidence. CHK002:
неприменимость внешней HTTPS-пробы к текущему media-worker обоснована
отсутствием прикладного внешнего HTTPS в прослеженном пути и единственной
internal-сетью, а не сетевым отказом. Исходные 9 inconclusive и `all_pass=false`
сохраняются; 9 PASS точного образа отдельно не являются runtime TLS PASS.
CHK001/003/004: версии, границы trust/TLS и требование точного доказательства
сохранены. Повторно прочитаны итог сверки и добавление quickstart: исходные
результаты не подменены. Первичные журналы объясняют ранний abandoned marker
отказом `branch_mismatch` до удалённого CD и поздний штатный deploy отдельно.
Общая приёмка T007/T008 не дана: остаются исходные backup authority/restore
доказательства; один `backup_result=pass` их не заменяет.
Основания, пределы и контрольные суммы:
[независимый отчёт](../review-runtime-applicability-20261028.md).
После записи файл полностью перечитан: **4 checked / 0 unchecked**.
