# Data model: F230 metadata

Новой БД, runtime schema или хранения персональных данных нет.

| Запись | Поля | Инвариант |
|---|---|---|
| Исходная задача | task_id, issue_number, body_sha256, source_url, observed_state | один исходный владелец; полный набор T001–T020 |
| Отмена дубликата | task_id, stateReason=NOT_PLANNED, successor_issue/tasks, comment_url, comment_sha256, observed_at | не completed и не [X]; преемник проверен |
| Задание агента | repository, source_sha, lane, feature/task или явное N/A для прямого задания, role, owner, worktree, owned_paths, validation | границы назначаются до записи; один явный владелец задания |
| Handoff | conclusion, facts, source_sha, checks, limits, next_action | ограниченный metadata-only ответ, без секретов/контента |
| CI observation | event, workflow, run_id/attempt, source/target/base_sha, conclusion, URL, observed_at | unknown не становится passed; событие не подменяется |
| Cutover | before, prerequisites, approval, mutation, after, rollback, rollback_validation | отсутствие before/approval блокирует применение |

Активная task: planned → reviewed → analyzed → tracker-linked → implemented
→ validated → approved commit → PR checks/review → approved merge → verified closeout.
Для отменённой: source → verified duplicate → detailed comment → not_planned;
это отдельный путь, не пропуск стадий completed.

Если SHA/base изменился, evidence становится историческим до новой проверки.
Если источник/API недоступен, observation=unknown/blocked с причиной. Если
файлы пересекаются, запись затронутых файлов приостанавливается до handoff владельца.
