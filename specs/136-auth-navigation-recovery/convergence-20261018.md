# F136: повторное сопоставление реализации с требованиями — 18.10.2026

Полоса high-risk-product. Проверены текущие spec/plan/tasks, 9 FR, 4 SC,
7 сценариев приёмки трёх историй, 5 групп крайних случаев, решения плана и
применимые обязательные ограничения конституции. Новые задачи не добавлены:
оставшаяся работа уже имеет владельцев. Вся F136 пока не завершена.

| Требования | Реализация и доказательства | Оставшийся владелец |
|---|---|---|
| FR-001/002/003, SC-002 | POST не сохраняется как SwiftUI GET; auth nested actions исключены общим predicate; история вызывает тот же isSafeDocument. T018 RED 32 assertion failures → focused GREEN83. | T018 локально проверяется; OAuth T004/T011/T012 остаются открытыми. |
| FR-004 | navigationDidFinish определяет успешную смену; Coordinator сохраняет route/identity/state перед commitPendingSessionBoundary. 401/reselection закрывают историю сразу. | T005/T006/T010, принятие PR T017. |
| FR-005/006/009, SC-003/004 | Controller Back/Forward/Reload, жесты, canReload и history используют общий safe-document predicate. Обычные формы сохраняют boundary/WebView; accessibility identifiers не менялись. | T010; полный OAuth/manual T016 отдельно. |
| FR-007 | Изменены только macOS cabinet, существующий XCTest, owned fragment и документы. Сервер, способы входа, заголовки внешних origin и диагностика не расширены. | PR/release gates T017. |
| FR-008, SC-001 | Отмена принятой текущей навигации завершает loading; safe route сохраняется. Синтетические controlled сценарии проходят. Реальный provider-link continuation всё ещё boolean и не различает режимы. | T004/T011/T012 и ручной T016. |

Снятый synthetic P2 не считается исправленным: независимое решение
`review-native-overlap-disposition-20261018.md` объясняет отличие искусственного
порядка от наблюдаемого native fail A перед policy B. Новый постоянный overlap
тест использует настоящий Coordinator и не подменяет callbacks.

Настоящие незавершённые части F136: OAuth continuation T004/T011/T012
(HIGH, partial), ручная приёмка T016 (pending), разрешение на коммит и
дальнейшее принятие T017 (pending). Они не получают дубли T019 и далее.
В текущем срезе T005/T006/T010/T018 дополнительных новых пробелов не найдено;
итоговое code review и полный результат приводятся в validation.md отдельно.
Выпуск и развёртывание не выполнены и локальными тестами не заменяются.

Converge не менял существующие задачи; отметки выполнения принадлежат
implement после фактической проверки. Before/after converge hooks отсутствуют.
