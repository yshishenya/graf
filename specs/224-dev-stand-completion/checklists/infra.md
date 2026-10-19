# Infrastructure Checklist: единый безопасный стенд GRAF Dev

**Purpose**: независимая проверка полноты и согласованности требований текущего US1.
**Created**: 2026-10-16
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md)
**Review Ownership**: checkbox state меняет только независимый reviewer.
`[x]` означает качество требований, а не завершённую реализацию или живую приёмку.

## Принадлежность и сохранение состояния

- [x] CHK001 Определены ли эквивалентные формы origin и отказ неоднозначного адреса без утечки credentials? [Clarity, Spec FR-001–003, Contract §Канонизация]
- [x] CHK002 Разграничены ли worktrees, независимые clones и чужие репозитории без зависимости от basename/cwd? [Completeness, Spec US1, FR-001–002]
- [x] CHK003 Требуется ли явное доказательство исторического владельца вместо автоматического присвоения по SHA? [Coverage, Spec FR-003/006–007, Research §Решение]
- [x] CHK004 Определено ли сохранение manifests/runtime/journals/data/secrets/archives и inode прежнего lock без переноса? [Completeness, Spec FR-006, Data model §Существующее состояние]
- [x] CHK005 Определены ли отказ нескольких неизвестных roots и граница обнаружения старых overrides? [Edge cases, Spec FR-007, Contract §Одноразовое принятие]
- [x] CHK006 Различаются ли регистрационная сериализация и единственное право изменять стенд; задан ли порядок lock? [Consistency, Spec FR-004–006, Contract §Одноразовое принятие]
- [x] CHK007 Заданы ли повторная проверка после ожидания, устаревший parent и несовпадение ожидаемого active SHA? [Coverage, Spec FR-005, Contract §Обычные операции]
- [x] CHK008 Определены ли повтор регистрации и прерывание до/после публикации с одним результатом без перезаписи другого binding? [Recovery, Spec FR-006–007, Data model §Переходы]

## Отказ до воздействия

- [x] CHK009 Определены ли исходные symlink/owner/type/inode/path проверки до записи, а не только после resolve? [Completeness, Spec Edge Cases, Contract §Одноразовое принятие]
- [x] CHK010 Названы ли все прямые callers и shared effects, включая prune без --live и startup guard? [Coverage, Spec FR-004/016, Contract §Обычные операции]
- [x] CHK011 Запрещено ли управление общими Docker tags и canonical state из искусственного root? [Consistency, Spec FR-004/015–016, Contract §Обычные операции]
- [x] CHK012 Разграничены ли snapshot status, fixture результат и фактическая живая приёмка? [Clarity, Spec FR-009–011, Contract §Обычные операции]

## Старые версии и широкая общая задача

- [x] CHK013 Сохраняются ли exact SHA/tracked bytes/digest/clean gates для frozen adapters и отказ несовпадающего resolver до stop/install? [Completeness, Spec FR-009/016, Contract §Закреплённые адаптеры]
- [x] CHK014 Явно ли ограничена защита от самостоятельного старого controller без обещания технически невозможного запрета? [Assumption, Spec FR-007/016, Research §Старые адаптеры]
- [x] CHK015 Сохранены ли широкие lifecycle/runtime/atomic recovery/migration/TCC обязательства #6180 с отдельными критериями приёмки? [Completeness, Spec FR-008–014/017–018]
- [x] CHK016 Указаны ли текущий пробел ordinary-promote SIGKILL и существующий миграционный владелец F249 T038/#6786 без дублирования? [Traceability, Research §Широкие требования, Plan §Оставшиеся истории]
- [x] CHK017 Определена ли Dev-only TCC матрица без reset, второго приложения или подмены production bundle ID? [Coverage, Spec FR-014, Quickstart §Широкая приёмка]
- [x] CHK018 Отделены ли historical exact-SHA evidence от текущей приёмки и исходные T001–T008 от полного закрытия #6180? [Consistency, Spec FR-017–018, Research §Широкие требования]

## Ворота реализации и принятия

- [x] CHK019 Определены ли изолированные отрицательные/межпроцессные сценарии и отсутствие побочных действий при отказах? [Measurability, Spec SC-001–003, Quickstart §US1]
- [x] CHK020 Различаются ли готовность требований US1, будущая реализация US3, точные PR-проверки, исходный fast и frozen release-full? [Consistency, Plan §Validation Plan, Quickstart §Широкая приёмка]

## Notes

Независимое ревью 2026-10-16: 20 checked, 0 unchecked. Основания по каждому
пункту — в [отчёте](../review-design-20261016.md). Требования текущего US1
прошли этот gate. Генерация полных tasks, analyze и issue sync остаются
обязательны до реализации; US2/US3 и живая приёмка этим не завершены.

Повторная независимая проверка 2026-10-19: все 20 пунктов перечитаны по текущим
документам, результат 20 checked / 0 unchecked. Отметки сохранены; актуальные
основания, проверенные журналы и незавершённые ворота — в
[отчёте](../review-current-20261019.md).
