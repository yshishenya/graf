# Calendar operation requirements: T119

**Purpose**: ограниченная проверка полноты жизненного цикла единой операции подключения.
**Created**: 2026-10-04.
**Feature**: [spec.md](../spec.md), US2/FR-002/005/006/015, existing T119.
**Review Ownership**: reviewer-owned; основной агент не отмечает пункты.
**Marker Semantics**: `[x]` означает качество требований, не выполненный код.

## Жизненный цикл и актуальность

- [x] CHK001 Однозначно ли определён один busy для всех источников и запрет нового действия до actual completion, независимо от terminal UI? [Clarity, bridge §10, plan T119 operation]
- [x] CHK002 Полон ли exact context snapshot, включая смену token и различие document/native action, без передачи URL/auth странице? [Completeness, bridge §10, data-model §8]
- [x] CHK003 Заданы ли исходный resolver budget15s, включение dispatch/queue и отсутствие продления chunks? [Measurability, bridge §10, plan T119 operation]
- [x] CHK004 Ясно ли различие отмены UI, фактического окончания worker/OS/dialog и старого completion, не освобождающего новую операцию? [Consistency, bridge §10, plan T119 operation]

## Восстановление и границы

- [x] CHK005 Согласованы ли нетерминальный opening во время recovery, fresh resolver после подтверждения и запрет оживления terminal request с целевым Mac? [Consistency, bridge §10, plan T119 operation]
- [x] CHK006 Определены ли неизменность исходного action/card expiry и отсутствие автоматического переноса resolver timeout на OS/dialog? [Clarity, bridge §10, quickstart §13]
- [x] CHK007 Сохраняются ли card-close-only-handoff, Record-after-current и native-only capture prerequisites? [Coverage, FR-015, bridge §10]
- [x] CHK008 Разделены ли state helper, будущие adapter lifetime proofs и installed приёмка, без дублирования задач/HTTP/launcher/backend? [Traceability, T119, plan T119 operation, quickstart §13]

## Notes

Новый checklist перед implementation. Требует независимого review всех8 пунктов;
основной агент читает gate и не меняет markers. Старые reports неизменны.

Независимая проверка 2026-10-04: requirements PASS, checked8 / unchecked0,
C0 / H0 / M0 в ограниченной области этих восьми критериев. Evidence и границы:
[review-2026-10-04-calendar-operation-gate.md](review-2026-10-04-calendar-operation-gate.md).
Отметки не подтверждают helper/adapter implementation, actual native completion,
installed launch, общий analyze или выполнение T119.
