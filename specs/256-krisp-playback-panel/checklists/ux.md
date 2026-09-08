# Проверка требований F256: ux

Reviewer-owned. Исполнитель не отмечает пункты. Первый этап без ножниц.

- [x] CHK001 Согласованы ли US1–US3 и явное исключение ножниц во всех активных документах? [Scope, FR-002/012–019]
- [x] CHK002 Определены ли геометрия, темы, ширины, клавиатура, фокус, reduced motion и проверяемые допуски? [FR-003/017, SC-002–004]
- [x] CHK003 Описаны ли Listen, перекрытия, последний интервал, скорость, next/previous и ошибка play? [FR-004–009]
- [x] CHK004 Определены ли comments/replies/edit/reaction/resolve/filter/link и отмена/ошибка без потери ввода? [FR-010]
- [x] CHK005 Указаны ли независимые SVG, ограничения эталона и отдельная приёмка GRAF Dev? [FR-018, SC-006]

Независимый reviewer `requirements_review`, 2026-09-08: scope первого этапа в
spec.md имеет приоритет над сохранённым полным эталоном; contracts/playback-panel.md
определяет переходы, границы Listen и геометрию. T010/T012 и quickstart.md
разделяют браузер и GRAF Dev. Повторный проход: CHK004 закрыт после добавления
GET replies с limit/cursor, next_reply_cursor в contracts/comments.md10–11
и проверки пагинации в T005. См. [requirements-review.md](../requirements-review.md).
Это проверка требований, а не визуальная или функциональная приёмка.
