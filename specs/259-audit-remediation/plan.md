# План F259 — первый этап B019

## Полный объём после уточнения владельца

2026-09-09 владелец потребовал завершить весь бэклог аудита перед выкаткой. Текущий ремонт B019 доводится до приёмки первым, затем работа продолжается по всем направлениям. Актуальный реестр и порядок — [execution-status.md](execution-status.md): 257 OPEN из исходных 279. Это расширение очереди исполнения, без автоматического разрешения deployment или ложного закрытия post-release критериев. Исходные spec/backlog и требования каждого issue сохраняются.


## Текущий ремонт последовательности — 2026-09-09

US3, FR-023–FR-026, SC-006/007; high-risk-product / significant governance.
Ветка `codex/259-sequence-policy` от495cefab3; T013 сохранён без повторной
реализации. Пользователь разрешил ремонт без перенумерации и новый этап
процесса; автоматические коммиты, публикация и release не разрешены.

Constitution check до/после проектирования: PASS. Политика не ослабляет
clean-tree, проверки коллизий, блокировку, GitHub completeness и разрешения.
Upstream и generated skills не меняются. Независимый checklist и issue sync
предшествуют коду; общий продуктовый бэклог не объявляется завершённым.

Решение: `.specify/feature-numbering.json` с единственным полем
`out_of_sequence_spec_ids: [6788]`. Малый Python stdlib reader проверяет
объект, точные неповторяющиеся ключи, список уникальных положительных целых (не bool).
Начало = max(spec IDs минус явные исключения)+1, занятость = все прежние
источники без исключений. Один helper в _next_feature_id обслуживает все
оболочки; отдельный счётчик, сервис резервирования и предел999 не нужны.

Файлы: scripts/claim-feature.py, .specify/feature-numbering.json,
tests/governance/test_feature_allocator.py, docs/agent-guidance/codex-worktrees.md.
В руководство добавить начало новой работы от проверенного master и запрет
принимать spec_next старой папки за резерв. Чужой основной checkout не менять.
Ошибку формата umbrella issue не смешивать с этой задачей: её исправление и
live task sync для новой фичи будут отдельным необходимым шагом.

Проверки: сначала failing regression с историческим spec6788; затем позитивные
и отрицательные политики, F1000+, занятость исключённого ID, read-only invariance,
повторный выбор/конкуренция, действующие shell entrypoints и validator tests.
Ограниченная live-подсказка ничего не резервирует. Проверить источник данных
до/после по хешам. Полный CI не запускается. После локальной проверки требуется
отдельное разрешение на commit для переноса ремонта в чистую новую рабочую копию.

## Summary

Исправить выбор номера и подготовку feature-метки. Только US3/FR-012–FR-018; остальные B-пункты не входят в эту итерацию. База e81b412dff920cc29ed37de60be13dd8fc4d1c43.

## Technical Context

Python stdlib, существующий GitHub CLI, Bash/Python/PowerShell оболочки. Новых зависимостей нет. Состояние — существующий JSON под общим git lock; формат не меняется.

## Constitution Check

Риск: significant governance / полный Spec Kit для этапа. Clarify записан в spec. Capture/auth/production/данные пользователя не изменяются; credentials не логируются. Clean tree, collision, mutex и GitHub проверки обязательны. Root AGENTS и общая рабочая копия аудита не меняются.

## Structure / Design

- scripts/claim-feature.py: только heads/remotes, распознавание конечного feature segment, единый поиск от specs; strict online lookup; подготовка метки.
- .specify/extensions/git/scripts/{bash,python,powershell}/create*feature*: одинаковый вызов предложения через repository-local allocator; generic путь без allocator сохраняется.
- tests/governance/test_feature_allocator.py: реальные git refs и изолированные GitHub responses, поведение оболочек; действующий test_validator_safety.py остаётся регрессией.
- /Users/yshishenya/Documents/speckit-bootstrap/bin/speckit-bootstrap: сохранить те же изменения оболочек в source overlay, не перезаписывать чужой dirty diff.

## Validation

Focused allocator/validator tests, self-test, Bash syntax, Python compile, read-only online suggestion на текущих refs; live label/issue не создаётся тестами. Полный CI только перед выпуском. governance-fast/merge/release не объявляются пройденными без точного commit/remote evidence. См. quickstart.md.

## Legacy Impact

Classification: untouched. Generic ветка — действующий standalone контракт, не legacy fallback; существующие IDs/claims не переписываются.

## Дополнение: завершение workflow

Scope US3/FR-019–FR-022: .specify/workflows/speckit/workflow.yml, project-local implement/taskstoissues skills и source bootstrap overlay; scripts/validate-issue-closeout.py получает только --verify-live режим чтения для одного issue. Существующая verify_feature_runs переиспользуется без нового сервиса. GitHub Actions permissions и production не изменяются. Проверки: CLI acceptance/rejection, YAML order/gates, загрузка workflow реальным specify, source overlay и governance tests.

## Ремонт трёхзначного диапазона — 2026-09-11

Lane: active-spec-kit, продолжение US3/B019, significant governance.
Основание: актуальный origin/master ad71f2ce4db68d846d7c333213961c5f5f7d5e89.
Constitution check до и после проектирования: PASS; продукт, данные,
безопасность, Git lock и строгие проверки источников сохраняются.

Текущее решение заменяет прежний отказ от предела999: необязательный
max_feature_id в существующей политике, для GRAF 999. Общий распределитель
фильтрует только начало и проверяет границу каждого кандидата. Новый explicit
claim проверяется до записи; старые повторы/upgrade проходят прежние проверки.
Никаких зависимостей и дополнительных счётчиков. Generated specify и старый
script создания spec используют общий номер; изменения шаблонов закрепляются
в source bootstrap с сохранением его имеющихся изменений.

Порядок: уточнение/requirements review → регрессия → код → целевые тесты →
converge. Issue #6837 — закрытое историческое основание, этот ремонт не выдаётся
за уже принятую часть того issue. Новый внешний комментарий/публикация не
входят в локальное поручение. Commit, PR CI и включение в master — отдельные
этапы после представления проверенного diff владельцу.
