# Infrastructure Checklist: CI merge queue и provenance release train

**Purpose**: Reviewer-owned infrastructure requirements-quality gate

- [x] Event-specific target and base SHA contract is complete.
- [x] `merge_group` synthetic checkout is fail-closed and traceable to PRs.
- [x] Concurrency keys cancel only superseded logical targets.
- [x] Cancellation and stale evidence cannot satisfy a required check.
- [x] Final tracked/untracked cleanliness runs after all artifact generation.
- [x] Receipts are metadata-only and schema-validated.
- [x] Release train separates synthetic SHA from post-merge release SHA.
- [x] Exactly one authoritative Full CI is accepted per frozen candidate.
- [x] Actions/branch protection changes remain operator-owned after merge.

Implementation agents MUST NOT mark these boxes complete.

## Текущий срез T032–T033: качество требований

- [x] CHK010 Различены ли действующие serial условия и будущая приёмка native queue без объявления T029/T031 завершёнными? [Completeness, Spec §Уточнения, FR-009]
- [x] CHK011 Определено ли обязательное base → actual source независимо от synthetic, включая недоступную историю и отсутствие выходных записей при отказе? [Clarity, FR-011, SC-007]
- [x] CHK012 Разделены ли доказательства изолированного Git fixture, настоящих PR проверок и выпуска? [Consistency, Plan §Текущий срез, Quickstart]
- [x] CHK013 Указана ли воспроизводимая pinned Python matrix и предел её применимости? [Traceability, Research §R8, SC-006]

## Независимое ревью 2026-10-17

Результат: **13 checked / 0 unchecked**. Проверено качество требований перед
реализацией T032–T033, а не завершение инфраструктуры F227. Пункты 1–9 читаются
как требования к соответствующим защитам; доказательства и ограничения каждого
пункта приведены в [отчёте](../review-provenance-20261017.md).

На момент предреализационного ревью FR-011/SC-007 задавали исправление отказа:
связь base с synthetic могла ошибочно заменить связь с source. Результат
последующей независимой проверки исправления приведён ниже. T029/T031, настоящая очередь, три проверки будущего
PR и выпуск этим ревью не подтверждены. Исходные открытые tasks сохранены.

## Независимая проверка реализации T033

Минимальный diff и новая регрессия проверены; actionable findings **0**.
Независимый прогон `test_release_train.py`: **9 passed / 21.15 s**; shell syntax
и самопроверка train validator — PASS. Прежние schema/CLI/PR/Full CI/current/
cleanliness gates сохранены. Положительный serial и отрицательные случаи
происхождения/отсутствующего commit подтверждены только изолированным fixture.
Все 13 пунктов требований перечитаны: **13 checked / 0 unchecked**. Настоящие
GitHub PR checks, native T029/T031, merge и release этим не подтверждены.

## Текущая независимая сверка 19.10.2026

Все13 пунктов повторно прочитаны и сопоставлены с требованиями и текущим
порядком train-freeze: **13 checked / 0 unchecked**. Base→actual source
проверяется до создания train/identity; serial commit-tree не объявляется
GitHub merge-group доказательством. Новых противоречий требований текущему
срезу не найдено. Свежие локальные результаты, исторические проверки и
будущая настоящая приёмка различены в
[review-current-20261019.md](../review-current-20261019.md).

## Итоговое независимое ревью 21.10.2026

Все 13 пунктов перечитаны после устранения замечаний потребителей train
и refs/replace: **13 отмечено / 0 не отмечено**. Отметки не менялись.
APPROVE относится к текущему исправлению T033; исходные T001–T031,
настоящие GitHub/очередь/выпуск и закрытие #7645 требуют своих доказательств.
Код, исходные RED, итоговые журналы 11/103 и независимый повтор трёх
сценариев проверены в [итоговом отчёте](../review-final-20261021.md).
