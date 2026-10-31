# T111 — сообщение отказа APT

- [x] CHK001 Оба набора отделены от неизвестного AWS; граница T111 сохраняет открытый T110 и прежние отказы.
- [x] CHK002 JSON, точная классификация URI, ограничение4096 и отсутствие сырых unknown/credentials/control определены.
- [x] CHK003 Разрешённые источники, APT trust, source/mirror bytes, callers и порядок действий сохраняются.
- [x] CHK004 Настоящий трёх-caller harness проверяет отсутствие побочных действий и раскрытия на положительных/отрицательных данных; RED/GREEN различены.
- [x] CHK005 Временный workflow удаляется; before-code review/analyze/sync и последующие review/converge/exact PR gates обязательны; Full/CD не принимаются.


## Независимое before-code ревью — 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Основа: `7040d2502cd39dbc7c586d1fa69e683ab3bb4a57`.
Итог: **PASS требований, 5 отмечены / 0 открыты, P1/P2/HIGH0**.
Каждый пункт сопоставлен с T111 spec/plan/tasks/quickstart, реальным прежним
helper и исполняемым профилем трёх callers. Матрица и пределы —
[отчёт](../review-ci-apt-failure-diagnosis-20261101.md).
Разрешено только описанное расширение сообщения прежнего отказа; код,
RED/GREEN, фактический AWS, PR/Full/CD этим PASS не принимаются.


## Независимое implementation review / converge — 01.11.2026

**PASS ограниченной реализации T111; P1/P2/HIGH0.** Прочитаны реальный
helper/tests diff, безопасный JSON перед сохранённым отказом, удаление
временного workflow, RED30failed/243deselected и GREEN273passed87.33s.
Allowlist/parse/trust/bytes/три callers сохранены; новые URI случаи остаются
FAIL без действий после отказа. Тесты проверяющий не запускал.
Checklist перечитан: **5 отмечены / 0 открыты**. Детали и hashes —
[отчёт](../review-ci-apt-failure-diagnosis-20261101.md).
AWS/T110/#7849 и точные PR gates/Full/CD/release этим PASS не принимаются.
