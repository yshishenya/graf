# F224/T009: независимое ревью уточнённого проекта, 27.10.2026

**PASS требований. CRITICAL 0, HIGH 0, открытых замечаний 0.**
Промежуточные CHK029/Q015 закрыты после узкого авторского исправления
Summary/Status и покрытия FR-003/007 задачей T009. Изменённые plan/tasks
полностью перечитаны. Сам новый договор принадлежности и архивов не потребовал
нового механизма; принято качество требований, а не подготовленная реализация.
Проверена ветка `codex/224-preserved-archives`, основа
`5dffd0537e66e7f4e88bd0d4fd5103393fc7c486` и незакоммиченные документы.
Lane: high-risk-product, существующая T009/#7640. Применён code-reviewer.
Проверяющий не является автором проекта или кода. Изменены только два
reviewer-owned чеклиста и этот отчёт. Проверяющий код не изменял;
рабочая дельта scripts/dev-harness.py и ownership tests существует,
в это ревью требований не входит и данным отчётом не принимается.
Автор подтвердил, что предварительные 127 PASS получены до окончательного
gate и не заменяют последующие RED/GREEN, независимое ревью кода или
приёмку T009. После промежуточного замечания дальнейшая работа над кодом
приостановлена до этого итогового решения. Проверяющий тесты не запускал.

## Решение и границы

FR-003/007 изменены явно: историческая принадлежность обязательна для
выбранного управляющего root, остальные roots не присваиваются репозиторию.
Для неизвестного соседа это разрешение сохранить существующие байты,
а не управлять ими. Остаются обязательными безопасные пути и права,
согласованное состояние без незавершённой операции, полный неизменный снимок
и согласованное исключение самостоятельных писателей. При недоказанности
любого из этих условий — отказ. Неизвестный выбранный root по-прежнему
нельзя принять по SHA, подписи, UID, имени, возрасту или отсутствию PID.
Такое уточнение не меняет конституционный принцип, не присваивает чужие
ресурсы и не создаёт второго стенда или самостоятельного старого workflow.

У build другая граница доверия, чем у app: конкретные каталоги перечислены
в `build_archives`, путь ограничен `artifacts/<candidate>/build` с соседним
app. Происхождение build остаётся UNKNOWN. Проверка подписи и source app
не распространяется на build; исполнение, импорт, копирование, восстановление
и использование в качестве временной сборки запрещены. Build не может поглотить
root, app, управляющую запись или соседний архив. Допускаются только
существующие относительные ссылки внутри своего build на каждом префиксе
разрешения; выход и возврат внутрь также запрещён. Это узкое расширение
существующего входного плана, без нового менеджера, реестра или зависимости.

Порядок registration → прежние operational locks, открытие соседних locks
без создания, физическая идентичность, повторная сверка root set/плана/снимка
после каждого ожидания и перед binding, fsync/read-back и immutable binding v1
сохранены. Selected lock сохраняет выдачу fd принятой T010. Без плана
сохраняется прежний отказ. Никаких файлов, исправлений или очистки у соседей.

Отдельное операторское исключение будущих писателей остаётся предусловием.
Наблюдения ps/lsof/Docker не объявлены гарантией. Протокол не обещает
предотвратить произвольный старый процесс, запущенный вопреки правилам.
Исторические 125/306PASS и APPROVE сохранённого `06ad4cb` относятся
к app-only договору; новый проект ими не принят. Тесты нового договора,
реальная классификация/binding и фактические T009/T011/T012/T013 разделены.

## Постатейная проверка infrastructure

`state-ownership` ниже означает текущий contracts/state-ownership.md;
`promotion-recovery` — отдельный принятый договор T010. Старые отметки
оцениваются как качество требований своей области, не новая реальная приёмка.

| Пункт | Основание сохранённой или новой отметки |
| --- | --- |
| CHK001 | state-ownership §Канонизация: один raw/effective origin, ограниченные формы, отказ неоднозначности без сырого URL. |
| CHK002 | Spec FR-001/002 и plan Phase1: worktrees/clones связываются по origin, basename/cwd не определяют состояние. |
| CHK003 | Уточнённые FR-003/007 и state-ownership §Принадлежность: владелец выбранного root доказан; неизвестный сосед не присваивается. |
| CHK004 | FR-006 и data-model §Существующее состояние: bytes, пути, журналы, материалы и inode lock сохраняются. |
| CHK005 | state-ownership §Одноразовое принятие и §T009: без полного допустимого плана второй неизвестный root блокирует принятие; нестандартные overrides не выдаются за полный scan. |
| CHK006 | state-ownership §Полнота: registration сериализует принятие, прежний operational lock остаётся единственным правом изменения выбранного стенда. |
| CHK007 | FR-005, state-ownership §Обычные операции/Полнота: SHA/parent и полный план повторно проверяются после ожидания. |
| CHK008 | data-model §Переходы и state-ownership §Одноразовое принятие: атомарная привязка, неизменяемость, безопасный повтор. |
| CHK009 | state-ownership §Одноразовое принятие/Полнота/Архивы: исходные пути, owner/mode/type/inode и границы ссылок проверяются до публикации. |
| CHK010 | state-ownership §Обычные операции и §Проверки отказа: shared callers, direct adapter, prune и startup учитываются до side effects. |
| CHK011 | state-ownership §Обычные операции: fixture не управляет app/Docker/shared tags и не обходит плохой binding. |
| CHK012 | FR-009/011, state-ownership §Обычные операции и quickstart: status — снимок; synthetic не заменяет фактическую приёмку. |
| CHK013 | state-ownership §Закреплённые адаптеры и promotion-recovery §Процессы: clean/SHA/bytes/digest/resolver guards сохраняются. |
| CHK014 | state-ownership §Принадлежность: будущие старые jobs исключаются оператором; абсолютная техническая защита не обещается. |
| CHK015 | FR-008–014/017/018 и tasks T009/T011/T012/T013 сохраняют broad lifecycle/runtime/migration/TCC. |
| CHK016 | Research описывает исходный SIGKILL-пробел; отдельная T010 и promotion-recovery владеют исправлением, F249 T038/#6786 не дублируется. |
| CHK017 | FR-014 и quickstart §Широкая приёмка: Dev-only same-signer до/update/relaunch/после без TCC reset и второй установки. |
| CHK018 | FR-017/018, tasks и новые датированные разделы отделяют US1/T010 от ещё открытой фактической F224. |
| CHK019 | Quickstart US1/T009: временные HOME/Git/state, два процесса, ранние отказы и сохранность bytes/inode без внешних действий. |
| CHK020 | Plan/quickstart разделяют исходный US1, отдельный T010, новые focused checks, exact-SHA PR gates и frozen release-full. |
| CHK021 | US3/FR-012/SC-003, promotion-recovery §Повтор: promote/rollback, first install и прерывание после pointer не дают ложного повтора. |
| CHK022 | promotion-recovery §Квитанция/Повтор: полные закреплённые manifests/checkouts, PID+start token, строгий отказ старого/плохого receipt. |
| CHK023 | promotion-recovery §Подготовка/Публикация: durable receipt до воздействия, сохранённый backup; при компенсации durable previous/отсутствие pointer → target_record/отсутствие → receipt. |
| CHK024 | promotion-recovery §Процессы и state-ownership §Полнота: тот же operational fd для коротких child, pipe gate перед startup, новый код не теряет fd T010. |
| CHK025 | promotion-recovery §Повтор/Публикация: общий запрет включает direct build/retention/prune, status/smoke/startup и idempotent return. |
| CHK026 | promotion-recovery §Процессы/Публикация и FR-013/016: schema recovery приоритетен, frozen bytes/guard не подменяются. |
| CHK027 | promotion-recovery §Матрица приёмки: реальные процессы/SIGKILL, ошибки публикации/очистки, чужая цель/PID, bytes/inode; настоящего приложения нет. |
| CHK028 | Plan/T010 и quickstart отделяют исследование, reviewer gate, исполняемую матрицу, текущие PR checks и открытые live gates. |
| CHK029 | FR-003/007 и state-ownership §Принадлежность прямо меняют старое owner-required правило для невыбранных соседей без полномочий управления. |
| CHK030 | Data-model §T009 и state-ownership §Полнота: строгий полный вход, canonical POSIX snapshot, root set/device/inode, повтор после каждого ожидания/перед binding, отсутствие соседних записей. |
| CHK031 | Data-model build_archives и state-ownership §Архивы: явный конкретный path, UNKNOWN build provenance, app facts отдельно, no execute/import/copy/rehydrate/scratch. |
| CHK032 | state-ownership §Архивы и quickstart T009 п.3: каждый префикс relative target, отдельная build boundary, absolute/cross/escape-return/broken/cycle/unsafe/special — отказ. |
| CHK033 | state-ownership §Принадлежность/Полнота: согласованные no-writers, ограниченность снимков, прежние inode и T010 fd, без нового lock у соседей. |
| CHK034 | Plan/quickstart T009 и tasks T009: новый checklist/analyze/sync → RED на06ad → GREEN/review/converge/PR → отдельная реальная приёмка; старый PASS не заменяет этапы. |

## Постатейная проверка requirements

| Пункт | Основание |
| --- | --- |
| Q001 | Spec описывает сохранение, границы полномочий и результат без алгоритма snapshot/новой зависимости. |
| Q002 | US1–US3 объясняют единственность стенда, версию, восстановление и разрешения. |
| Q003 | FR-003/007 и Clarifications 27.10 явно объясняют смысл неизвестного соседа; программные обозначения уточняются в договоре. |
| Q004 | Scenarios, требования, сущности, SC, допущения, clarify и Legacy Impact заполнены. |
| Q005 | Два изменения смысла решены явными Q/A: selected ownership и неизвестный build; пользовательских продуктовых вопросов не осталось. |
| Q006 | Один выбранный root/binding; чужие соседи не управляются, архив не используется; FR-004/008/016 сохраняются. |
| Q007 | SC-001–006 и quickstart дают определимые положительные/отказные результаты, snapshot/side-effect проверки. |
| Q008 | Spec не навязывает отдельную службу, менеджер, реестр или библиотеку; техника остаётся в плане/контракте. |
| Q009 | Три истории и US3 fourth scenario покрывают обычный цикл, SIGKILL, отказ и восстановление. |
| Q010 | Edge Cases + FR-003/007 + contract/quickstart покрывают origin/owner, links, writers, locks, snapshot и unknown states. |
| Q011 | Tasks T009/T011/T012/T013 и FR-017/018 сохраняют broad #6180; ни binding, ни код его не закрывают. |
| Q012 | Доступность Dev, writers, доказанный selected root, совместимость схемы и ещё не полученная live/TCC приёмка названы. |
| Q013 | Tasks Requirement coverage и текст T009 связывают FR-001–018/SC-001–006 с исполнением; новое уточнение прямо принадлежит #7640. |
| Q014 | US1 принадлежность, US2 фактический runtime и US3 восстановление имеют собственные Independent Test/Acceptance Scenarios. |
| Q015 | Новые dated sections явно отличают проект от старой реализации/изолированных PASS, фактические gates открыты. |
| Q016 | Input сохраняет восстановленное происхождение требований; новый договор не выдаёт неизвестное build за proven source. |

## Прочитанные документы и пределы доказательства

Полностью прочитаны текущие spec, plan, tasks, research, data-model,
state-ownership, promotion-recovery, quickstart и оба checklist. Полностью
перечитаны constitution7.1.0 и PRD; полное чтение current-product-status из
предыдущего прохода этого же проверяющего доступно в текущем диалоге,
хеш этой копии подтвердил идентичные bytes. Прочитаны AGENTS, guidance README,
document-reading, spec-kit-flow, product-gates, local-development,
development-process и infra/dev/README; применимые целые разделы
release-and-validation: Validation Lanes, Development-To-Release Workflow
(local development/PR and merge), Git Safety, Evidence Safety.

Прочитаны безопасные внешние metadata-отчёты проверки применимости и всех
171 build links:0absolute/escaping/broken/cyclic/missing-boundary. Это
наблюдение формы фактических архивов, а не исполнение нового кода или
доказательство исторической принадлежности. Частные файлы roots не открывались.
Сохранённые06ad code/requirements/implementation reports использованы только
для сопоставления старого app-only договора, не как PASS нового проекта.

Проверка не исполняла тесты с записью, Git/GitHub mutations, Dev, build,
установку, Docker, процессы управления, релиз, deploy или adopt-state.
Никакой source/governance/spec/plan/tasks reviewer не изменял.
Далее обязательны отдельные analyze и sync, затем RED/GREEN и независимое
ревью кода. При смене документа его затронутые требования проверяются заново.

Итог после перечитывания чеклистов: infrastructure 34 отмечено / 0 открыто,
requirements 16 отмечено / 0 открыто. Это качество требований, не приёмка продукта.
Обновлённые ссылки и статусы US1/T010 проверены здесь на согласованность
проектных документов; новую live-проверку GitHub этот reviewer не выполнял.

## Хеши входов

- spec.md: `c4eadc1a3d2eaede6b02051e94faab863a1d888e48bb7e47d617dbd3f07bae06`
- plan.md: `397127bad23bb6cab43cc39fc91e809b1ce0cece8983e982f5a31b478d136348`
- tasks.md: `dd1c2a0757f041abda811915a724869d81cfbfaa1284744b1dddd318d284675a`
- research.md: `0fbdccc1fbbf11978ee9bde81b8054ec5f03c302a47cd3287474a53a88d96e5f`
- data-model.md: `7df143635b977f549d913569ddca75c668b4204616bd01104ad2556f6df7802d`
- contracts/state-ownership.md: `220f25552174fbb0085b2348625a2f1f8e4c37b3285dda576aae134a70e749a8`
- contracts/promotion-recovery.md: `cae00836244a22b75428ff533bf87c756791ae33b13855e43b8d9620e6ff295c`
- quickstart.md: `df49d20833a17e91b7ddd52240937985728679c35261ff3b0c1606a87f7d1b6c`
- AGENTS.md: `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958`
- constitution.md: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`
- PRD: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`
- current-product-status.md: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`
- product-gates.md: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`
- spec-kit-flow.md: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`
- local-development.md: `904745b03ca97ac28f76b92cc056ad7936f7051b3a2ae7910bfb3e02cd55f356`
- release-and-validation.md: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`
- guidance README: `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb`
- document-reading.md: `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411`
- development-process.md: `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864`
- infra/dev/README.md: `0ad820a5fcfea24dfcf322d2f292aa6cb973b33f29d8c28af5d1d325f41827a9`
