# Требования seekable packed writer: F200 / T116

**Purpose**: Независимая проверка полноты и согласованности packed §6.0 до кода.
**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md), [packed contract §6.0](../contracts/windows-protected-packed-custody.md)

**Review Ownership**: Reviewer-owned. `[x]` означает принятие качества требований,
не выполнение T116 или готовность Windows. Основной агент markers не меняет.

## Полнота и ясность

- [x] CHK001 Определены ли область worker-only open, проверенный context/role и отсутствие package authority? [Completeness, packed §6.0/§6.1]
- [x] CHK002 Однозначно ли задан reuse одного Writer State/dirty/API без второго backend и flat index? [Clarity, packed §6.0; Plan dependency step3]
- [x] CHK003 Разделены ли принятие Write, pending view и durable checkpoint, включая несколько actual generations? [Clarity, packed §6.0; base contract §6]
- [x] CHK004 Заданы ли пустой Write, invalid pointer/offset/overflow, EOF и отсутствие partial byte ACK при ошибке? [Coverage, packed §6.0]
- [x] CHK005 Различены ли авторизованные sparse ZERO/SetSize и запрещённая подмена ещё не записанного аудио нулями? [Consistency, packed §4/§6.0]
- [x] CHK006 Описаны ли shrink→grow, dirty suffix и сохранение старых committed Reader/Clone? [Coverage, packed §4/§6.0]

## Ошибки, безопасность и критерии

- [x] CHK007 Полны ли требования first fault, notCommitted/ambiguous, сохранения actual ACK и retained owner при поздней отмене? [Coverage, packed §5/§6.0]
- [x] CHK008 Определены ли границы healthy release/cancel и запрет destructor flush/I/O? [Clarity, packed §2/§6.0]
- [x] CHK009 Согласованы ли память/dirty/pin/job/readback budgets с прежними численными пределами без скрытого расширения? [Consistency, packed §3/§6/§6.0]
- [x] CHK010 Измеримы ли требования partial/cross-block/pinned/cold/failure/wipe, без подмены проверки приложения тестами storage? [Measurability, packed §6.0/§7]
- [x] CHK011 Явны ли зависимости package schema/cadence/Stop/migration/T120 и отсутствие допуска к installed/release? [Dependencies, packed §6.0/§6.1; T116–T120]
- [x] CHK012 Нет ли противоречий с FR-012/013/022, SC-006, constitution и существующим open owner T116? [Traceability, Spec; Tasks T116; packed §6.0]

## Notes

High-risk storage lane. До завершённого независимого review/analyze код нового
packed writer не меняется. Исторические checklist PASS не принимают этот scope.

## Независимая оценка 2026-10-04

**PASS — 12 checked / 0 unchecked; C0/H0/M0** для качества требований
worker-only packed Writer. Основания каждого пункта, текущие SHA, чтение
существующего кода и ограниченный analyze записаны в
[review-2026-10-04-packed-writer-gate.md](review-2026-10-04-packed-writer-gate.md).
Каждый исходный пункт прочитан и оценён отдельно; новых пунктов не добавлено.
Маркеры не принимают будущую реализацию, потребителей, T116 целиком или приложение.
