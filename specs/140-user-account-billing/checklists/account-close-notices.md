# Account-close notice requirements checklist

**Purpose**: качество требований ACN1–ACN6 существующих T070/T068.
**Created**: 2026-11-12
**Feature**: [F140](../spec.md)

**Review Ownership**: независимый reviewer владеет markers; [x] означает только достаточность требований, не реализацию. Основной агент не отмечает пункты.

## Полнота, ясность и безопасность

- [x] CHK001 Определены ли события нового планирования, отмены, повтора и нового запроса без изменения FR-018? [Completeness, Spec ACN1]
- [x] CHK002 Задан ли атомарный исход ошибки/rollback между переходом и очередью? [Coverage, Spec ACN1]
- [x] CHK003 Однозначно ли определён исходный получатель и запрет подмены владельцем/плательщиком/merged аккаунтом? [Clarity, Spec ACN2]
- [x] CHK004 Определены ли active identity, личная область, membership/Owner, verified email и повторная проверка до claim? [Completeness, Spec ACN2, Plan ACN]
- [x] CHK005 Разделены ли отсутствие права/адреса, временная ошибка и mandatory preference bypass без backfill? [Consistency, Spec ACN2/5]
- [x] CHK006 Определены ли исторический смысл scheduled после canceled, даты/зона и отсутствие обещаний текущего состояния? [Clarity, Spec ACN3, Contract ACN]
- [x] CHK007 Заданы ли безопасная авторизованная ссылка, отсутствие секретов/PII/meeting content и граница recovery? [Security, Spec ACN3, Contract ACN]
- [x] CHK008 Определены ли exact snapshot/event identity/policy/date/state validation и подавление неполной старой очереди? [Completeness, Spec ACN4, Contract ACN]
- [x] CHK009 Задана ли граница финализации, closed и claimed до изменения состояния без ложного обещания отзыва транспорта? [Coverage, Spec ACN4]
- [x] CHK010 Однозначны ли границы retry, unknown, crash и persisted claim до HTTP? [Measurability, Spec ACN5]
- [x] CHK011 Определена ли защита от обратных блокировок schedule/finalize/F178 и изменения poll→claim? [Consistency, Plan ACN]
- [x] CHK012 Покрывают ли критерии реальный browser source→commit→outbox→sender, отрицательные права, конкуренцию и rollback? [Acceptance, Spec ACN6, Quickstart ACN]
- [x] CHK013 Сохранены ли исходные T068/T070, отдельная inbox #7524, выпуск/Dev/развёртывание и остальные уведомления? [Traceability, Spec ACN6]
- [x] CHK014 Соответствует ли дизайн конституции, RLS/существующим сущностям без новой таблицы, транспорта или расширения прав? [Consistency, Plan Constitution Check, Data Model ACN]

## Notes

Независимое ревью требований завершено 12.11.2026: 14 checked / 0 unchecked.
Все markers подтверждены в [отчёте](../review-account-close-notices-requirements.md),
checklist перечитан после изменения. PASS относится только к качеству требований
ACN1–ACN6. Детализация execution tasks принята повторной сверкой ниже; далее
обязательны Analyze и остальные ворота до кода;
реализация, тесты, CI, письмо/inbox и полные T068/T070 не приняты.


## Повторная сверка детализации T068/T070 — 12.11.2026

Изменённый tasks.md прочитан полностью после append-only детализации девяти
шагов; сохранение прежних 87 строк/отметок подтверждено. Применимость восьми
общих исторических чеклистов разобрана в отчёте без изменения их markers.
Блокирующих пропусков ACN-покрытия/порядка не найдено. Независимый итог
качества требований и задач: PASS, **14 checked / 0 unchecked**; checklist
полностью перечитан. Analyze и проверка существующих issues остаются воротами
до кода; реализация, runtime/inbox и launch этим результатом не принимаются.
