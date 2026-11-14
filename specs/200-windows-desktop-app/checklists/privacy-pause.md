# Privacy Pause Checklist: GRAF Windows T120

**Purpose**: Качество требований приватной паузы и её metadata prerequisite T116.
**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md), desktop contract §3, plan T120, quickstart §15.

**Review Ownership**: Независимый reviewer владеет отметками; основной агент
их не меняет. `[x]` — качество требований, не готовность реализации/выпуска.

## Полнота и согласованность

- [x] CHK001 Указан точный одобренный Mac-образец, связь FR-002/009 и отличия от старого bool drain? [Traceability, Spec §Clarifications 2026-10-04]
- [x] CHK002 Однозначно разделены обязательный OPEN до принятия Pause и best-effort CLOSE после успешного Resume? [Consistency, desktop §3]
- [x] CHK003 Определены queued/in-flight/prefetched/timeline/частичные данные паузы, без переписывания уже записанного доверенного prefix? [Completeness, desktop §3]
- [x] CHK004 Граница Resume согласована с producer/read FIFO, замена остатка и отсутствие ожидания пустой очереди определены? [Clarity, desktop §3]
- [x] CHK005 Заданы отказ Resume при недоступной границе, сохранение paused/OPEN и доступного Stop? [Recovery, desktop §3]
- [x] CHK006 System/PTS/count/format/route/AEC и исходная валидация остаются обязательными, raw fallback/padding запрещены? [Consistency, FR-009/010]

## Данные и ограничения

- [x] CHK007 Защищённый путь явно зависит от T116, новый plaintext journal не является временным обходом? [Dependency, plan T120]
- [x] CHK008 Модель сегментов/ISO8601/optional OPEN поля/legacy совместимость определены существующим Mac-контрактом, не приблизительным JSON? [Clarity, data-model §1]
- [x] CHK009 Manifest cap64KiB применяется к полному payload, отличается от неизменных memory/job/cache/root/queue/audio budgets и имеет явные boundary/failure условия? [Measurability, local custody §3, quickstart §15]
- [x] CHK010 Отказ OPEN при исчерпании вместимости не принимает Pause и не обрезает прошлую историю; consumer validator не ослабляется substring-проверкой? [Edge Cases, desktop §3]
- [x] CHK011 Определены single-owner ordering, асинхронный UI/Stop и отказ late completion изменять остановленную/новую сессию? [Coverage, desktop §3, plan T120]
- [x] CHK012 Разделены codec prerequisite T116, capture T120, synthetic/native/installed и непроведённые hardware/release gates без ложного общего PASS? [Dependencies, plan T120, quickstart §15]

## Notes

Новые пункты из `$speckit-checklist` оставлены unchecked. Historical packed
Reader gates/source reports не переотмечаются и не принимают новый capture flow.
Срез может быть принят только в явно обозначенном объёме; T116/T120 остаются
открыты до их полной приёмки. Reviewer report — отдельный файл.

Независимая оценка 2026-10-04: исходные12 unchecked проверены по текущим
нормам и точному Mac c8d67ccefe7848f731798b23d72d37757ad812f5. Итог12 checked,
0 unchecked; CRITICAL0/HIGH0/MEDIUM0 в ограниченной проверке требований.
Доказательства каждого пункта и SHA снимка:
[review-2026-10-04-privacy-pause-design.md](review-2026-10-04-privacy-pause-design.md).
Это не source acceptance, не проверка установленного приложения и не
разрешение обойти issue sync или незавершённую защищённую интеграцию T116.
