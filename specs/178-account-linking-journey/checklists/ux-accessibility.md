# UX and Accessibility Requirements Checklist: Подключение email без тупиков

**Purpose**: проверить качество IA, wording, responsive и accessibility требований до реализации
**Created**: 2026-08-20
**Feature**: [spec.md](../spec.md)

## Information architecture and wording

- [x] CHK001 Определён ли порядок трёх смысловых уровней: профиль/вход, пространства/данные, повторный вход? [Clarity, Spec §FR-009–FR-010]
- [x] CHK002 Продолжает ли заголовок исходную задачу «Подключить email», не подменяя её внутренним merge terminology? [Consistency, Spec §US2, FR-024]
- [x] CHK003 Различены ли явно «что изменится» и «что останется отдельным»? [Completeness, Spec §US1, FR-004, FR-010]
- [x] CHK004 Закреплены ли точные primary и safe secondary labels без неоднозначного «Отменить»? [Clarity, Spec §FR-012–FR-013]
- [x] CHK005 Определён ли единый словарь «профиль», «способ входа», «пространство» и запрещённые внутренние термины? [Consistency, Spec §FR-024]

## States and recovery

- [x] CHK006 Описаны ли confirmable, blocked, expired, stale, cancel, success и back-navigation состояния? [Coverage, Spec §US1–US3, Edge Cases]
- [x] CHK007 Имеет ли каждый настоящий blocker конкретное доступное действие либо честный configured-support fallback? [Completeness, Spec §FR-015–FR-016]
- [x] CHK008 Определено ли, что cancellation возвращает понятный результат и не оставляет пользователя на terminal screen? [Coverage, Spec §FR-013]
- [x] CHK009 Запрещает ли спецификация показывать mock providers вместо фактически verified methods? [Clarity, Spec §FR-011, US4.3]

## Responsive and accessibility

- [x] CHK010 Задан ли logical DOM/read order при переходе wide comparison в stacked narrow layout? [Clarity, Spec §FR-020, US4.1]
- [x] CHK011 Определены ли отсутствие horizontal scroll, clipping, overlap и unreachable actions на 390px и zoom? [Measurability, Spec §SC-006]
- [x] CHK012 Покрыты ли semantic headings, alert/status announcements, keyboard operation, visible focus и non-color labels? [Completeness, Spec §FR-021, SC-007]
- [x] CHK013 Согласованы ли wording и outcomes между web и embedded macOS surface? [Consistency, Spec §FR-019]
- [x] CHK014 Определён ли keyboard-accessible native disclosure для вторичных подробностей без сокрытия главного решения? [Coverage, Spec §US2.4, FR-021]

## Acceptance quality

- [x] CHK015 Можно ли объективно измерить понимание решения за 30 секунд и выполнение одной action? [Measurability, Spec §SC-004]
- [x] CHK016 Определены ли visual QA состояния для wide, narrow, keyboard focus, blocker и embedded chrome? [Coverage, Spec §US4, SC-005–SC-007]
