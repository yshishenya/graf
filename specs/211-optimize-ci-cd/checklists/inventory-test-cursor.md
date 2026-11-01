# T115 — требования к целевому курсору inventory

Владелец отметок — независимый рецензент. Область только T115/FR-057/SC-025.

- [x] CHK001 Причина и назначение теста отличены от рабочего обхода страниц; точная область ограничена одним курсором, без SQL/ролей/RLS/лимита/assertions.
- [x] CHK002 Детерминированное RED/GREEN использует реальный disposable PostgreSQL с51 предшествующей записью и тот же test; cleanup и отсутствие новых skips обязательны.
- [x] CHK003 Заданы оставшееся покрытие None-path, весь normalization/maintenance профиль, независимый code review/converge/exact PR checks и отдельная приёмка Full/CD/T0.


## Независимое requirements review — 01.11.2026

Проверяющий `/root/public_counter_readiness_review`.
Основа `125b51042ff39a1a7b1d4d051ce2503ea8d1250c`.
**PASS: 3 отмечены /0 открыты; P1/P2/HIGH — 0/0/0.**
Матрица, доказательство курсора и пределы —
[отчёт](../validation-inventory-cursor-review-20261101.md).
Принимается только план одной тестовой предпосылки; implementation/native/
exact PR/Full/CD/T0 и коммерческие критерии не приняты.
