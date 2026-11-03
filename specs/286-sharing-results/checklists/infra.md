# Delivery and infrastructure requirements review — F286

Reviewer-owned. Requirements quality, not release proof.

- [x] CHK001 Are durable queue/recovery and network reservation/unknown outcomes bounded and testable? [FR-009,011,019; plan Design 4]
- [x] CHK002 Are ready+5m/deadline24h, fresh complete actual roster, actual identities and stable series authority explicit? [FR-013–017; data-model]
- [x] CHK003 Are migration/RLS, retention/purge, no retroactive enabling and rollback prerequisites specified? [FR-012,020; plan; quickstart]
- [x] CHK004 Are exact-SHA PR/full release/CD/health/synthetic acceptance and preserved macOS distribution gates stated? [plan Release Gate; quickstart 6]
- [x] CHK005 Are cancellation, suppression, pause, current ACL and owner budget rechecked at egress with no fake device identity? [FR-006,014,019; plan Design 4]

## Независимая проверка — 2026-10-06

Проверены требования проектирования, не работа реализации. `tasks.md` и `analysis.md` перечитаны до реализации; задачи T001–T018 покрывают требования и последующие проверки.

- CHK001: plan Design 4; data-model строки 15,27; quickstart пункты 4–5: durable intent, sending до Postal, unknown при сбое и восстановление ограничены.
- CHK002: spec FR-013–017; plan Design 3; data-model строки 19,27; quickstart пункт 4: +5 минут/24 часа, реальные личности и точная серия/состав заданы.
- CHK004: plan Release Gate/Constitution Check; quickstart пункты 3,6: exact SHA, PR/full CI, CD, health, синтетические проверки и сохранение подписанной поставки заданы.
- CHK005: plan Design 4; data-model строка 27; spec FR-006,014,019: актуальные ACL, отмена/отписка/пауза перед резервированием; настоящий device и долговечный бюджет владельца заданы.

CHK003: первоначальное замечание устранено. plan Safe rollback и quickstart пункт 2: отключение новых операций, остановка неначатых попыток, drain/unknown, совместимый код, сохранение схемы и запрет возврата отозванного доступа заданы.

Итоговое чтение перед реализацией: 5 [x], 0 [ ]. Уточнения auto_epoch, устойчивого requires_review, Google <=15 минут/organizer.self и исключения дубликатов прочитаны в plan/data-model; покрытие — T011–T013 и T017.
