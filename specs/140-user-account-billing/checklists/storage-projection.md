# Требования к storage projection T077/O15

**Purpose**: независимый допуск качества требований S1–S6 перед кодом.
**Created**: 2026-11-02
**Feature**: [spec.md](../spec.md), T077/#4932, high-risk-product.
**Review Ownership**: reviewer-owned. Только независимый проверяющий отмечает
`[x]` по конкретным доказательствам требований; это не приёмка реализации.

## Полнота и ясность

- [x] CHK001 Определены ли все workspace/reservation источники, database_inventory/current_state и отсутствие day/shop фильтра с учётом workspace без подписки? [Completeness, O15/S1]
- [x] CHK002 Однозначны ли existing used/reserved/capacity семантика, явные аргументы и общий as_of без default zero или новой финансовой формулы? [Clarity, O15/S2]
- [x] CHK003 Определены ли missing/unknown/nonfinite/nonpositive capacity, точные nullable totals и пустой inventory без ложного subtotal? [Coverage, O15/S3]
- [x] CHK004 Полны ли reservation state/NULL/unrecognized, invalid/expired-active границы и отдельный смысл counts/bytes без скрывающего clamp? [Clarity, O15/S4]
- [x] CHK005 Заданы ли точная JSON форма, сортировка, всегда partial, приоритеты reason и null reconciliation без заявления о shop/MinIO/финансовой сверке? [Consistency, O15/S3/S6]

## Приватность, пределы и приёмка

- [x] CHK006 Признано ли внутреннее чтение финансового JSON существующим helper с явным запретом экспорта/логов refs/snapshot/private полей и безопасным schema/helper отказом? [Security, O15/S5]
- [x] CHK007 Определены ли500/501 полный отказ без sampling, общий15с/5с/2с/500gaps/64KiB и прежний cleanup без нового бюджета на workspace? [Measurability, O15/S1/S6, O2]
- [x] CHK008 Описаны ли независимые от реализации критерии реальных PG/CLI/FORCE RLS/снимков/no-write/privacy/границ/source branches и синтетического defensive NULL без ослабления схемы? [Acceptance, quickstart §storage, O15/S6]
- [x] CHK009 Согласованы ли constitution/финансовые/privacy/retention границы, запрет writers/новых служб/прав/зависимостей и сохранение всего O6/сроков/T070/58gaps/87task lines? [Consistency, O15/S6, plan §storage]
- [x] CHK010 Зафиксированы ли существующая T077/#4932, роли/владение/порядок допуска/analyze/RED/code review/converge/exact PR gates без новой задачи и ложного closure? [Traceability, spec §T077/O15, plan §storage]

## Примечания

Основной исполнитель не меняет состояние пунктов. Неподтверждённое остаётся
`[ ]` с причиной в независимом отчёте. Все прежние checklists сохраняются;
этот узкий допуск не закрывает их58 gaps, O6 или исторический пропуск O8.


## Независимое решение — 02.11.2026

PASS качества требований O15/S1–S6: **10 отмечены / 0 не отмечены**.
Проверяющий `/root/f140_notification_content_review`; полный отчёт,
прочитанные оригиналы, их SHA-256 и основания всех10 решений:
[review-storage-projection-requirements-20261102.md](../review-storage-projection-requirements-20261102.md).
Проверен окончательный набор семи документов при HEAD/base
`4c7924ea69ac6c0968d563988b884a0ecc75ba21`, contract SHA-256
`411f95d513457110e150cc0be2a665857a88d60aeaf721a71ba2063aa9d692a6`.
R1–R3 устранены; новых замечаний к требованиям нет. Это не приёмка
реализации: scoped analyze, RED, код, PostgreSQL/CLI, независимые
code/converge и exact PR SHA/base gates выполняются отдельно. T077/T070,
O6 и58 прежних gaps остаются открытыми.
