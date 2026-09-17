# Spec Kit analyze — 2026-09-08

Проверены spec/plan/tasks/data-model/contracts/quickstart и Constitution.
После закрытия R1–R4 и редакционных правок: **CRITICAL 0 · HIGH 0 · MEDIUM 0**.
16 задач, 10 FR и 6 SC, покрытие100%, несвязанных задач нет.

| Требование | Задачи |
|---|---|
| FR001 / SC001 | T003,T004,T014 |
| FR002 / SC002 | T005,T014 |
| FR003 | T003,T005,T014 |
| FR004 / SC003 | T006,T007,T008,T014 |
| FR005 | T009,T010 |
| FR006 | T009,T011 |
| FR007 | T007,T009,T010,T011 |
| FR008 | T012,T013 |
| FR009 | T005,T012,T013 |
| FR010 | T006,T008,T014 |
| SC004 | T009,T010,T011,T012,T013,T014 |
| SC005 | T006,T009,T010,T011,T012,T013,T014 |
| SC006 | T014,T015 |

T001/T002 — обязательные подготовительные gates; T015 — итоговая проверка.
Продуктовое исключение из буквального Constitution §II one-action Stop явно
основано на решении владельца убрать widget и оставить F255: меню + Stop =2
действия. Остальные capture/privacy/F214 gates сохраняются. Старые screenshots,
тесты и гипотеза гонки не принимаются как новая runtime-проверка.

Implementation gate: reviewer-owned checklists, issues.md и canon validation.
Данный документ сохраняет результат отдельного read-only analyze; анализ не
менял spec/plan/tasks. Результат не является реализацией или release evidence.

Повторный analyze T016: полный ID в common/normalizer, числовой fallback и регрессия. Это исправление prerequisite canon, без ослабления body/labels. Дополнительных HIGH/CRITICAL нет.

Актуальный объединённый объём: [affected-analysis.md](affected-analysis.md),
21 задача и 22 FR/SC, независимый review 38/38. Это заменяет прежний объём
16 задач, не его историческое evidence.
