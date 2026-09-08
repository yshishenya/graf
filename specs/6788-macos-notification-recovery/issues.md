# GitHub ownership

Единый issue [#6825](https://github.com/yshishenya/graf/issues/6825) владеет
T001,T002,T003,T004,T005,T006,T007,T008,T009,T010,T011,T012,T013,T014,T015,T016.
Полный список записан в его Context (Spec tasks / Spec Kit task IDs). Новых
дублей не создавали; исходный umbrella reservation сохранён и уточнён.

2026-09-08: перед sync прочитаны open/closed issues feature6788 — только #6825.
После обновления обязательные ensure/validate: **279 Spec Kit issues, PASS**.
Усечение номера исправлено в T016; feature6788 больше не определяется как678.
Старые #6780/#6779/#6758 связаны через Refs, их закрытие требует отдельной сверки.

Объединение F258: #6825 теперь явно владеет T001–T021; read open/closed
feature6788 не обнаружил дублей, ensure/validate — 279 issues PASS.
Источники #6818–#6824 сохранены как Refs. T017 подготовительный gate завершён.

Convergence T022: #6825 расширен до T001–T022 после проверки open/closed
feature:6788. Ensure/validate: 279 issues PASS. При повторной проверке найдено
несоответствие area в новом #6827: только segment заголовка приведён к уже
назначенной метке docs/governance; его содержание и состояние не менялись.

T023: общий code review выявил рассогласование partial. #6825 прочитан заново и
расширен до T001–T023; ensure/validate завершены,268 active Spec Kit issues PASS
(число изменилось после закрытия задач другой фичи). Новых issues нет.
