# Feature Specification: Быстрый и доказуемый CI/CD

**Feature Branch**: `211-optimize-ci-cd`

**Created**: 2026-08-30

**Status**: A1–A3 released; PR #6953 is included in v2026.09.13.1. Active continuation A4: finish the delivery optimization program authorized on 2026-09-13. First implementation scope: E05.12/E05.16 and accurate deploy diagnostics; later scopes retain separate reviewed tasks and release acceptance.

**Input**: User description: "Упростить CI/CD, убрать повторные полные прогоны для маленьких изменений, ускорить выкладку, сохранить качество и не допускать просачивания дефектов в production; перед внедрением перепроверить процессы, документацию и фактическое поведение."

## Clarifications

### Session 2026-09-13 — A4, завершение программы

- Пользователь поручил довести до конца все выявленные улучшения разработки и выпуска, исключить бессмысленные повторы и сохранить качество. Продолжение включает реализацию, проверки, связанные PR и доведение принятого процесса до работающего состояния; старые ограничения отдельных A1–A3 описывают историю.
- Уточнение по контексту: focused остаётся первым локальным шагом; обязательные проверки подтверждают точные head/base и реальный выбранный состав. Новый кандидат не наследует старый Full PASS. Сохранены доступ, PostgreSQL/RLS/гонки, backup/restore, миграции, секреты, здоровье, подписи/notarization и установленная приёмка там, где меняется приложение.
- Первый объём A4: перенести существующие lint/compile перед серверным pytest именно в release-full, исключить повтор двух CI-контрактов между changed tests и infra tests, уточнить вывод dry-run. Изменение required checks, macOS DAG, ресурсов/фикстур, образов и упаковки проектируется отдельно до кода соответствующего этапа.
- Дедупликация относится только к текущему запуску и полному покрытию того же файла. Результаты старого SHA, другой базы, окружения, группы или попытки не кэшируются как PASS. Ошибка единственного исполнения останавливает зависимые действия.
- Блокирующих продуктовых вопросов для первого объёма нет. Риск: high-risk CI/governance; reviewer-owned checklist, analyze и задачи GitHub предшествуют коду. Публикационные действия следуют проверкам и действующему договору выпуска.

### Session 2026-09-12 — A3 / E01

- Пользователь поручил начать внедрение полного плана CI/CD. Первый самостоятельный результат — выбор существующих тестов кабинета и настроек, продолжение F211; массовое сокращение unit-тестов относится к E02.
- Уточнение по имеющемуся контексту: область, стороны проверки, точная база, ошибки, полномочия и критерии приёмки определены; блокирующих вопросов нет. Новая карта дополняет нынешний fast. Неизвестные области сохраняют ограниченную проверку и обязательный Full перед выпуском.
- Локальные проверки включают незакоммиченные файлы и всегда являются диагностикой. Просмотр выбора не запускает тесты, Docker, приложение, установку зависимостей или сеть и не выпускает CI receipt.
- Текущая защита GitHub: `governance-fast`, GitHub Actions app, `strict=true`. Отдельная проверка описания уже добавлена A2; защищённое разделение проверок ещё не выполнено. Исторические разрешения A1/A2 не являются новыми разрешениями на публикацию.

### Session 2026-09-09 — A2

- Publication continuation after local validation: user requested to proceed with the stated next step. Commit, synchronization with current master, push, draft PR and its GitHub checks are in scope; merge, protection changes, Full CI and release remain excluded. The publication branch includes A1 + A2; A1 PR #6846 remains untouched.
- User approved a separate local branch, independent requirements reviewer, GitHub task sync and local implementation/focused tests. Commits, push/PR publication, merge, branch protection, real Full CI and release remain excluded.
- A2 adds a standalone PR-description check while preserving the combined required gate. It does not yet eliminate edited-code reruns or qualify the new check as a required merge-queue gate.
- Clarification scan: scope, actors, identity, trust, failures, acceptance and authority are clear; no blocking question remains. The check uses the latest fetched PR title/body for matching event head/base, not stale event text. That snapshot is not an atomic merge-time approval.
- Complete code/metadata separation, merge-group metadata validation, live required-check activation, base-retarget handling in the code-only workflow and closeout-consumer changes require a later reviewed stage. Existing merge-group, manual and release paths remain unchanged in A2.

### Session 2026-09-09

- Existing Feature 211 is continued, not recreated. Prior task completion and release approval are historical, not approval of A1.
- Clarification scan: actor, scope, evidence identity, failures, compatibility and approval boundaries are specified below; no new blocking user decision. Upstream Spec Kit is unchanged; no ggshield, new dependency, external Tidy First skill, Full CI, commit, push, release or production action is included.
- A1 covers exact diff-base binding, earlier server static checks and consistent validation instructions. It does **not** remove CI reruns caused by PR text edits. That requires a separately reviewed two-stage required-check migration.

### Session 2026-08-31

- Q: Может ли явно запрошенный `--fast` автоматически запускать полный CI? → A: Нет; fast остаётся ограниченным, а обязательный full выполняется только как отдельный release/deploy gate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Быстрая проверка небольшого изменения (Priority: P1)

Разработчик явно выбирает подходящий уровень проверки и быстро получает надежный результат по затронутой области, не запуская полный набор проверок без осознанного решения.

**Why this priority**: Повторный полный прогон является главным источником задержки и снижает скорость обратной связи даже для малых изменений.

**Independent Test**: Внести безопасное изменение в одну известную область, запустить быстрый уровень и подтвердить, что проверяется соответствующий компонент, вывод содержит состав и длительность этапов, а полный набор не запускается.

**Acceptance Scenarios**:

1. **Given** изменение только в известной низкорисковой области, **When** разработчик запускает быстрый уровень, **Then** выполняются обязательные проверки этой области и общие быстрые проверки без полного набора.
2. **Given** запуск общего CI без явно выбранного уровня, **When** команда стартует, **Then** она завершается до тестов с понятной подсказкой доступных уровней.
3. **Given** изменение общего, неизвестного или высокорискового пути, **When** разработчик запрашивает быстрый уровень, **Then** система выполняет ограниченные безопасные проверки затронутой области, явно сообщает о неполном покрытии и требует отдельный full перед release/deploy, не запуская full скрытно.

---

### User Story 2 - Один доказанный полный прогон на release candidate (Priority: P1)

Release engineer получает один авторитетный результат GitHub `release-full` для неизменного release candidate; production deploy проверяет это доказательство без второго полного прогона.

**Why this priority**: Убирает наиболее дорогой повторный прогон и не создаёт локальное доказательство, которое тот же пользовательский процесс может подделать.

**Independent Test**: Существующие контракты подтверждают, что execute после clean-tree и remote-sync проверяет авторитетное доказательство exact SHA до первого remote production шага. A1 этот контракт не меняет.

**Acceptance Scenarios**:

1. **Given** clean synchronized `master` и действительное авторитетное доказательство exact SHA, **When** запускается production execute, **Then** доказательство и неизменность кандидата проверяются до remote gates без повторного Full CI.
2. **Given** full завершается ошибкой, **When** выполняется deploy, **Then** production remote steps не начинаются.
3. **Given** локальное дерево грязное, branch не `master` или SHA расходится с `origin/master`, **When** начинается release/deploy flow, **Then** deploy блокируется до full и remote действий.

---

### User Story 3 - Понятная диагностика времени и результата (Priority: P2)

Разработчик и release engineer видят, какие этапы выполнялись, сколько занял каждый этап, почему был выбран или расширен уровень и где произошел сбой.

**Why this priority**: Без измерений невозможно отличить реальное ускорение от субъективного ощущения или безопасно оптимизировать следующий bottleneck.

**Independent Test**: Запустить успешный и намеренно падающий сценарии и проверить наличие итогового результата, длительности pipeline и завершенных этапов в обоих случаях.

**Acceptance Scenarios**:

1. **Given** любой явный уровень проверки, **When** pipeline завершается успехом или ошибкой, **Then** вывод содержит итог, длительность и результаты завершенных этапов.
2. **Given** fast lane не может доказать полное покрытие изменения, **When** определяется состав проверок, **Then** ограничение и требование отдельного release full перечислены до запуска этапов, а effective lane остаётся fast.

---

### User Story 4 - Документация совпадает с исполняемым контрактом (Priority: P2)

Участник команды следует одному актуальному процессу: focused для первого feedback loop, fast для интеграционной проверки и full один раз на точном release candidate.

**Why this priority**: Старые команды без режима неявно запускают дорогой full и воспроизводят проблему независимо от качества runner.

**Independent Test**: Автоматически просканировать активную документацию, шаблоны и quickstart на запрещенные неоднозначные команды и сверить примеры с `--help` и контрактными тестами.

**Acceptance Scenarios**:

1. **Given** активная инструкция или шаблон PR, **When** участник копирует CI-команду, **Then** уровень указан явно и соответствует назначению документа.
2. **Given** исторический evidence с фактом старого запуска, **When** выполняется consistency scan, **Then** историческая запись не переписывается и не считается активной инструкцией.

### Edge Cases

- Изменение одновременно затрагивает несколько известных компонентов: быстрый уровень запускает объединение обязательных проверок без дубликатов.
- Diff определить нельзя, база сравнения отсутствует или путь не классифицирован: fast выполняет ограниченный общий safety-набор, помечает покрытие как неполное и требует отдельный full перед release/deploy.
- Pipeline прерван сигналом или один из этапов падает: deploy останавливается до remote production steps.
- Локальный diagnostic full не становится авторитетным доказательством выпуска; обычный release path использует GitHub `release-full` и не требует предварительного локального full.
- Performance-порог нестабилен из-за нагрузки хоста: функциональные проверки остаются hard gate, а noisy gate не блокирует несвязанный diff без контролируемой линии.
- Изменена только документация: проверяется ее консистентность; полный продуктовый набор требуется только если документ меняет исполняемый release/deploy контракт.

### User Story 5 - Достоверная и ранняя обратная связь CI (Priority: P1, A1)

Разработчик получает проверки именно относительно базы текущего PR или merge group, а ошибки статического анализа сервера обнаруживает до длительных серверных тестов.

**Independent Test**: Изолированный Git-репозиторий с разными event base и `origin/master` показывает выбор путей по event base; существующий тестовый запуск runner доказывает порядок и остановку при ошибке без запуска настоящего полного набора.

**Acceptance Scenarios**:

1. **Given** PR или merge group с точными head/base SHA, **When** CI выбирает изменённые пути, **Then** merge base вычисляется относительно того же base SHA, который записывается в receipt; движение `origin/master` не меняет выбор.
2. **Given** отсутствующий, некорректный или недоступный event base, **When** начинается удалённая проверка, **Then** она завершается ошибкой до тестов, без подмены базой `origin/master` и без успешного receipt.
3. **Given** ручной диагностический запуск, **When** event identity имеет `base_sha=null`, **Then** сохраняется диагностическая семантика без заявления о происхождении результата от PR или merge group.
4. **Given** выбран серверный fast или full, **When** проходят статические проверки, **Then** те же команды lint и compile выполняются один раз до server/changed/performance tests; их ошибка не допускает эти тесты. Область и обязательность тестов не сокращаются.
5. **Given** обычная разработка, **When** участник следует инструкциям, **Then** локально выполняет целевые проверки, перед слиянием получает обязательный GitHub `governance-fast` на exact SHA, а локальный широкий fast использует только для диагностики или резервной проверки.

### User Story 6 - Отдельная проверка описания PR без ослабления защиты (Priority: P1, A2)

Разработчик получает отдельный результат проверки описания PR без ожидания продуктовых тестов в этой проверке. Это подготовка безопасного разделения: прежняя обязательная проверка продолжает работать полностью.

**Independent Test**: Корректное и ошибочное описание, устаревшее событие и разные ревизии проверяются на синтетических данных и реальном локальном Git. Новый путь не вызывает продуктовые тесты; старый обязательный путь не меняется.

**Acceptance Scenarios**:

1. **Given** открытие, обновление кода, повторное открытие, готовность к review или правка описания PR, **When** выполняется новая проверка, **Then** она проверяет актуальные полученные заголовок/описание по прежнему договору Feature ID, tasks, issue links, exact SHA, risk и Legacy Impact без продуктовых тестов.
2. **Given** старый текст события при неизменных head/base, **When** актуальный полученный текст отличается, **Then** оценивается актуальный текст; старый корректный текст не скрывает новую ошибку и старый ошибочный текст не отменяет исправление.
3. **Given** другой номер PR, закрытый PR, изменившиеся head/base или целевая ветка, недоступная база либо несовпадение checkout, **When** проводится проверка, **Then** она завершается ошибкой, а не выдаёт успешный результат по другому состоянию.
4. **Given** добавление, удаление или переименование файлов фич, в том числе нескольких фич, **When** определяется область PR, **Then** идентичность берётся из полного diff по точной базе; отсутствие feature-файлов допускает только явный scoped-договор.
5. **Given** ошибка получения актуальных данных, повреждённый документ или неверные типы обязательных полей, **When** выполняется новая проверка, **Then** результат неуспешен без вывода полного пользовательского текста или запуска команд из него.
6. **Given** новый запуск проверки описания, **When** отменяется её прежний запуск, **Then** отмена не затрагивает workflow проверок кода; при этом его собственные существующие edited-прогоны в A2 ещё сохраняются.
7. **Given** внешний PR, **When** запускается новая проверка, **Then** она не требует секретов или прав записи и использует те же правила проверки описания; требуемое GitHub одобрение запуска не обходится.
8. **Given** A2 завершён локально, **When** оценивается готовность к следующему этапу, **Then** старый required gate и все release/closeout ограничения сохранены, а отсутствие merge-group поддержки и live-проверки нового check явно блокирует его включение как обязательного.

### User Story 7 - Нужные регрессии проверяются до PR (Priority: P1, A3)

Разработчик видит, какие существующие проверки связаны с изменением общего кабинета или настроек, и запускает их локально. Те же правила добавляют соответствующие проверки в GitHub fast, даже если сами тесты не менялись.

**Independent Test**: При изменении общего JS неизменённый тест состояния меню выбран; исторический ошибочный JS даёт FAIL, текущий — PASS. Проверяется реальный выбор для PR, merge group и ручного запуска без запуска полного CI.

**Acceptance Scenarios**:

1. Изменение общего JS/CSS, шаблонов или формирования кабинета выбирает проверки общей оболочки и настроек, включая обычный и embedded-режимы.
2. Одинаковые исходные пути выбирают одинаковые обязательные группы локально и в GitHub. При нескольких компонентах берётся объединение; тест, уже включённый целиком в другой выбранный набор этого уровня, не выполняется повторно.
3. Просмотр показывает пути, причины, группы, окружение, границы покрытия и дальнейшие обязательные проверки до выполнения тестов.
4. Добавление, удаление и оба пути переименования учитываются; удалённый тест не передаётся исполнителю. Потеря обязательного файла проверки даёт ошибку, а пустой локальный набор не объявляется успешным тестированием.
5. Пробелы, кавычки, `$`, обратные кавычки и Unicode в путях остаются данными. Неподдерживаемые управляющие символы дают явную ошибку до тестов, без подмены состава проверки.
6. Недоступная явно заданная база блокирует выполнение. Отсутствие диагностической базы сохраняет частичное покрытие fast. Локальный грязный результат и план выбора не заменяют проверку точного SHA.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Общий CI entrypoint MUST требовать явный validation lane и MUST не выбирать полный уровень по умолчанию.
- **FR-002**: Процесс MUST сохранять три различимых уровня доказательства: focused, fast и full; результат одного уровня MUST не представляться как результат другого.
- **FR-003**: Fast lane MUST выбирать ограниченные проверки по затронутым компонентам и MUST оставаться fast для shared, unknown, high-risk или неразрешимого diff; в таких случаях он MUST сообщать о неполном покрытии и требовать отдельный full перед release/deploy.
- **FR-004**: Каждый lane MUST сообщать выбранный состав, ограничение покрытия, требование следующего gate, результат и длительность pipeline и завершенных этапов, включая ошибочный выход.
- **FR-005**: Production execute MUST после clean-worktree, branch и exact remote-SHA проверок проверять авторитетное GitHub Full CI evidence неизменного кандидата, повторно подтверждать worktree/HEAD/remote SHA и только затем начинать remote production steps. Второй Full CI не требуется.
- **FR-006**: Обычный release path MUST не требовать отдельный локальный preflight full; локальный full MUST оставаться диагностическим, не заменять GitHub `release-full` и не выдавать авторитетное release evidence.
- **FR-007**: Любой hard-stage failure в authoritative full MUST блокировать remote production steps.
- **FR-008**: Упрощение MUST не ослаблять clean worktree, remote sync, exact SHA, backup/restore, migrations/RLS, secrets, health, smoke, cleanup и rollback readiness.
- **FR-009**: Проверка времени исполнения, чувствительная к нагрузке общего хоста, MUST быть отделена от универсального hard gate и оставаться обязательной для связанных изменений или контролируемой performance-линии.
- **FR-010**: Активная документация, quickstart, PR template, release guidance, status и changelog MUST описывать один явный lane contract: локальные focused, обязательный GitHub fast и один авторитетный GitHub full на release candidate с проверкой доказательства при deploy.
- **FR-011**: Автоматическая contract-проверка MUST покрывать отсутствие режима, каждый режим, component selection, unknown/shared fallback, порядок deploy/full/remote gates и активную документацию.
- **FR-012**: Исторические validation/evidence записи MUST сохраняться как неизменяемые факты и MUST не массово переписываться только ради нового синтаксиса.
- **FR-013**: Процесс MUST поддерживать объединение нескольких небольших проверенных изменений в осознанный release candidate; плановые окна остаются операционной рекомендацией, а hotfix path не блокируется искусственным расписанием.
- **FR-014**: Build/push immutable container images и deploy by digest MUST оставаться отдельным архитектурным slice до выбора registry, custody secrets и измерения доли production build; текущая оптимизация MUST не вводить скрытую registry-зависимость.
- **FR-015**: Для PR/merge group workflow MUST передавать полный event `base_sha` в существующий `GRAF_CI_BASE_REF`; реальный diff и receipt MUST использовать одну базу. Отсутствующий/невалидный/недоступный event base MUST блокировать CI до тестов. Ручной dispatch MUST сохранять `base_sha=null` и диагностический выбор базы, без притворной PR/MG-привязки.
- **FR-016**: Server lint и Python compile MUST выполнять прежние команды с прежней областью ровно один раз перед всеми выбранными серверными тестами fast/full; ошибка любого из них MUST блокировать эти тесты. Состав тестов, performance/RLS и правила результата MUST не ослабляться.
- **FR-017**: Все активные инструкции MUST различать обязательный GitHub `governance-fast` на текущем PR SHA и необязательный локальный широкий fast; локальные целевые проверки MUST оставаться первым циклом обратной связи.
- **FR-018**: A1 MUST не менять обязательные имена checks, события, concurrency, права GitHub, closeout trust или защиту веток. Разделение code/metadata MUST идти отдельно: сначала добавить metadata check при сохранении старого gate, затем с отдельным разрешением сделать оба обязательными, и только после подтверждения защиты убрать дублирующие edited-прогоны. Пропущенный check MUST не подменять успешную проверку кода.
- **FR-019 (A2)**: Отдельный `pr-metadata` MUST запускаться на тех же PR-событиях для `master`, что и текущая проверка описания, без path filters и без условного пропуска задания. Он MUST не запускать продуктовые тесты, установку Spec Kit или full/fast runner и MUST иметь предел исполнения задания 5 минут без учёта очереди GitHub.
- **FR-020 (A2)**: Новый путь MUST применять существующий договор проверки описания к последнему полученному из GitHub открытому PR. Номер PR, head SHA, base SHA и целевая ветка MUST совпадать с событием, checkout — с head SHA. Изменившийся текст при той же идентичности MUST проверяться в актуальном виде. Это снимок на время получения, не атомарная гарантия состояния в момент слияния.
- **FR-021 (A2)**: Feature IDs MUST определяться по полному diff точных head/base, включая удалённые и оба пути переименованных файлов, без зависимости от `origin/master`. Множественные фичи и scoped MUST сохранять существующие правила описания.
- **FR-022 (A2)**: Ошибки получения данных, JSON, обязательных типов/полей, Git/общей истории и договора описания MUST давать неуспех. Заголовок и описание MUST обрабатываться только как данные; токены, полный текст и содержимое API-ответа MUST не попадать в журнал диагностики. Новый путь MUST использовать только чтение и не получать пользовательские секреты.
- **FR-023 (A2)**: Concurrency новой проверки MUST быть отдельной по номеру PR и MUST не отменять проверку кода. A2 MUST сохранять исходный workflow `governance-fast`, его события, имена, права, receipt и потребителей evidence; ручные и merge-group проверки остаются в прежнем пути.
- **FR-024 (A2)**: Документация MUST называть новый check дополнительным и ещё не обязательным. Его пропуск/отмена/неуспех MUST не представляться успешным metadata-результатом, а его успех MUST не заменять проверку кода или релиза. Переход защиты ветки и удаление edited-code запусков запрещены до отдельно проверенных PR/merge-group, свежести/base-retarget, fork и closeout-контрактов и явного разрешения владельца.

- **FR-025 (A3)**: Единая небольшая карта MUST связывать общие исходники кабинета и настройки с существующими проверками; изменение самого теста MUST не быть условием выбора.
- **FR-026 (A3)**: Локальная focused-проверка и GitHub fast MUST использовать одну карту. Fast MUST сохранять прежний safety-набор, общие unit, изменённые contract/integration, performance и проверки остальных компонентов; полное покрытие тестового файла или unit-набора MUST исключать повтор тех же тестов внутри уровня.
- **FR-027 (A3)**: Просмотр MUST показывать отсортированные входные пути, группы, причины, выбранные/уже покрытые тесты, требования окружения и `coverage=partial`. Он MUST быть без побочных действий, установки зависимостей и CI evidence. Локальный запуск MUST быть явно диагностическим и требовать последующий GitHub fast и релизный Full.
- **FR-028 (A3)**: Git diff MUST сохранять точную базу A1 и оба конца rename; пути MUST передаваться безопасно, без `eval`. Неподдерживаемый путь или отсутствие обязательного теста MUST давать ненулевой выход; удалённые необязательные тесты MUST сохранять текущий bounded fallback.
- **FR-029 (A3)**: Неизвестные/shared/high-risk изменения MUST сохранять честное частичное покрытие и запрет скрытого fast → full. Неразрешимая явная база MUST блокировать тесты; неизвестная область при пустом focused-наборе MUST не давать ложный PASS.
- **FR-030 (A3)**: Нынешние workflow, события, required checks, receipts, release/deploy и продуктовые исходники MUST оставаться совместимыми. Исправление MUST не обновлять закреплённые инструменты проекта и не создавать новую инфраструктуру тестирования.

### A4: ранние отказы и отсутствие повторов

- **FR-031 (A4)**: Авторитетный release-full MUST выполнять существующие server lint и Python compile с прежней областью до любого server pytest, включая setup тестовых БД; каждый выполняется один раз, ошибка блокирует последующие тесты и не выдаёт PASS компонента. Остальные полные проверки и итоговое свидетельство остаются обязательными.
- **FR-032 (A4)**: При пересечении changed server tests и infra CI contracts один и тот же целый файл MUST выполняться один раз. Оба CI-контракта по-прежнему обязательны для infra; при изменении только тестового файла он выполняется в focused changed tests. Другие изменённые файлы и обязательные performance/behavior tests сохраняются.
- **FR-033 (A4)**: Вывод cd dry-run MUST правдиво называть проверку и использование authoritative Full evidence. Отсутствие candidate означает required evidence, а не запуск локального Full. Наличие проверенного candidate означает reuse; incident bypass остаётся явно обозначенным и не расширяется.

### Key Entities

- **Validation Lane**: Явно выбранный уровень проверки, его обязательный состав, причина выбора или расширения и итог.
- **Release Candidate**: Точный commit и дерево, которые прошли требуемые gates и рассматриваются для deploy.
- **Component Classification**: Консервативное отображение измененных путей в обязательный набор быстрых проверок.
- **Stage Result**: Имя этапа, итог, длительность и доступный безопасный диагностический контекст.
- **PR Metadata Snapshot (A2)**: Номер открытого PR, точные head/base, целевая ветка и актуальные полученные заголовок/описание. Это временные данные проверки, не новый долговечный receipt или разрешение слияния.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% запусков общего CI entrypoint без явного lane завершаются до выполнения тестов с понятной ошибкой.
- **SC-002**: 100% явных fast-запусков сохраняют effective lane `fast`, не запускают полный набор и для неизвестных/shared/high-risk путей явно выдают `full required before release`; независимые компоненты не запускаются.
- **SC-003**: В обычном release path имеется один действительный авторитетный GitHub full для неизменного кандидата; execute проверяет его без повторного Full CI, worktree/HEAD/remote SHA остаются неизменными до remote production steps.
- **SC-004**: 100% неуспешных authoritative full runs блокируют remote production steps.
- **SC-005**: Каждый проверенный успешный и ошибочный сценарий показывает итоговую длительность и результаты всех завершенных этапов.
- **SC-006**: Автоматическая consistency-проверка находит 0 неоднозначных bare CI-команд в активных инструкциях и шаблонах, сохраняя исторические evidence записи.
- **SC-007**: Существующие security, privacy, migration/RLS, health, smoke, cleanup, rollback и notarization gates не удалены и продолжают блокировать release в своих областях.
- **SC-008**: Contract tests доказывают положительные и отрицательные пути lane selection и порядок deploy gates; полный repository CI проходит на финальном кандидате.
- **SC-009**: После внедрения p50 времени feedback loop для малого server-only или macOS-only изменения MUST быть не более 25% исходного full run (`351.59s` от baseline `1406.36s`); измерение выполняется минимум тремя последовательными component-only fast-прогонами.
- **SC-010 (A1)**: Исполняемые проверки покрывают различающиеся event/default базы, PR и merge group, отсутствующую/невалидную/недоступную event base, diagnostic dispatch и остановку server tests при lint/compile failure. Набор проверок и терминальные результаты сохраняются.
- **SC-011 (A1)**: В активных руководствах нет требования повторять GitHub fast локальным широким fast. Сокращение времени A1 доказывается порядком/ранней остановкой, не выдуманным процентом ускорения или новым замером SC-009. GitHub PR и release gates остаются отдельной непроверенной стадией до разрешённой публикации.
- **SC-012 (A2)**: Целевые исполняемые проверки подтверждают все 8 сценариев US6, включая отличающиеся event/current тексты, небезопасные строки, scoped/multi-feature, удаления/переименования и ошибки идентичности. Старые тесты договора описания и workflow остаются успешными.
- **SC-013 (A2)**: Новый workflow содержит только получение исходников/актуальных PR-данных и проверку описания; 0 вызовов продуктовых тестов или runner. Исходные governance-fast/release workflows и настройки защиты не изменены. Локальный PASS не объявляется live-приёмкой, устранением повторов или измеренной общей экономией.

- **SC-014 (A3)**: Исполняемые проверки подтверждают 6 сценариев US7, в том числе реальный Git diff и одинаковую карту для PR/MG/manual. Историческая ошибка меню обнаруживается выбранным неизменённым тестом; исправленная версия проходит.
- **SC-015 (A3)**: Короткий набор кабинета/настроек проходит локально менее чем за 60 секунд в подготовленном окружении, без Docker и БД. Это цель времени тестов, не установки окружения, очереди GitHub или полного workflow; фактическая длительность и число тестов записываются отдельно.

## Assumptions

- Неявный full и повторный full внутри deploy — исторические причины, уже устранённые до A1. Текущие причины A1: несогласованная база diff, поздние статические проверки и противоречивые инструкции о локальном fast.
- Existing shell и Git достаточны; новая runtime-зависимость не требуется.
- Локальный receipt не имеет независимого provenance против процесса того же пользователя и поэтому не используется как release gate.
- A1/A2 объединены в PR #6851; прежние записи разрешений ниже относятся к истории. A3 продолжает существующий Spec Kit, выполняет локальные проверки и сохраняет отдельное согласование implementation commit после проверки.
- Immutable-image pipeline может дать дополнительное ускорение, но требует отдельного решения по registry и secrets; он не нужен для устранения текущего дублирования тестов.
- Плановые release-окна полезны для batching, но остаются рекомендацией; аварийный hotfix должен оставаться доступен.

## Legacy Impact

- Classification: untouched
- A1/A2 introduce no compatibility alias, fallback command, dependency or retained legacy runtime path. A2 retains the current required gate as the mandatory first stage of a protected migration, not as a newly introduced legacy alternative. Existing diagnostic/production boundaries remain unchanged.

### A4 outcomes

- **SC-016 (A4)**: Исполняемый shell полного серверного компонента доказывает порядок lint/compile перед pytest и ноль вызовов pytest при отказе каждого статического шага. Успешный путь сохраняет все команды и терминальный результат.
- **SC-017 (A4)**: Проверки смешанного infra/changed diff доказывают по одному исполнению каждого CI-контракта и сохранение прочих файлов. Отдельный server-only diff сохраняет focused-проверку; отсутствие обязательного файла или отказ единственного infra-stage не даёт PASS. Dry-run без candidate показывает evidence-required и не запускает тесты; действующий reuse-контракт execute остаётся зелёным.


## A5 — ресурсы и подготовка тестов (2026-09-13)

Уточнение: пользователь поручил закончить всю оптимизацию. Для A5 нет открытого продуктового решения: PostgreSQL остаётся реальным и изолированным; меняется только подготовка и порядок тестов. Нельзя заменять транзакции/права заглушками ради скорости.

- **FR-034**: Help, неверные аргументы и collection-only не запускают Docker. Чистый unit-набор определяется реальной зависимостью фикстур pytest от PostgreSQL; все случаи с БД сохраняются в отдельной обязательной части. Отсутствие безопасной БД — ошибка подготовки, не skip/PASS. Full сохраняет весь набор.
- **FR-035**: В fast чистые unit-тесты выполняются перед запуском PostgreSQL, DB-часть — через прежний runner с изоляцией worker databases и максимум четырьмя процессами. Никакая часть unit не теряется и не выполняется в обеих группах; маркер выставляется по dependency closure, прямое создание ресурса требует явного маркера. Два чистых account-close теста больше не скрыты module-wide skip. Браузерные случаи имеют явный маркер browser, исключаются из pure и входят в обязательную resource-часть вместе с DB. Playwright с закреплённым lock и Chromium готовятся заранее; отсутствие среды вызывает ошибку вместо skip. Все три существующих browser skip переводятся в этот договор.
- **FR-036**: Оптимизация Cabinet fixture создаёт только явно нужные тесту состояния. Начать с полностью проверенных artifact-egress и speaker-names, сохранить HTTP/SQL вызовы самой проверяемой операции, статусы/права/аудит и отрицательные сценарии. Общий набор пяти состояний остаётся прежним по умолчанию; косвенные callers/list/count/foreign-state сценарии не сокращаются автоматически.
- **FR-037**: CI использует Python 3.13, frozen lock и явно подготовленный Node для JS. Безопасные JSONL-отчёты Full сохраняют только относительный путь файла, SHA-256 node ID, when, outcome и duration отдельно для setup/call/teardown по каждой фазе и доказывают отсутствие потери/повтора node IDs. Тексты ошибок, stdout/stderr, SQL/параметры и сырой JUnit не публикуются; контроллер xdist пишет каждый report один раз. Файл отдельный для каждого запуска/фазы; имя GitHub artifact связывает точный requested SHA, run_id и run_attempt с именем фазы. Это диагностическое приложение к существующему Full, не новое основание допуска релиза.
- **SC-018**: Исполняемые проверки help/invalid/collect/pure при недоступном Docker, разделение real collection и обязательный отказ отсутствующей DB. Исходные и оптимизированные fixture-семейства проходят один состав сценариев; число HTTP подготовки сокращается с 24 до 6 на single-ready caller. Время измеряется одинаковой командой до/после, без переноса локальных чисел на hosted Full.


## A6 — проверки PR и безопасное переключение (2026-09-13)

Уточнение доверия: текущий public personal repository сохраняет доверие владельцу/admin, имеющему право менять protection и workflow. Перенос в организацию, новый GitHub App и новые credentials не нужны. Доверенный metadata-validator защищён от изменения внутри обычного PR; не заявляется защита от владельца, намеренно изменяющего всю политику. Нативная merge queue для personal repo недоступна; последовательный release train сохраняется, существующий code merge_group путь не удаляется, живая приёмка очереди не выдумывается.

- **FR-038**: PR получает `macos-pr` на точном head/base. Успех означает успешный консервативный выбор области и либо реальные Swift build/tests/ContractValidation на macos-14/Swift 6.0.3, либо доказанную незатронутость macOS. Failed/missing scope, required+skipped, cancelled/neutral не разрешают merge. Изменения macOS, общего/неизвестного кода, кабинета/моста/API требуют macOS; чистые документы и явно независимые server-only paths могут его не запускать. Rename/delete рассматривают обе стороны. Кэш компиляции не заменяет вызов компилятора и тестов.
- **FR-039**: Metadata workflow выполняется через pull_request_target из закреплённого trusted workflow SHA; код PR не checkout/исполняется, PR head/base доступны лишь как Git objects для diff. Python запускается isolated mode. Два API-снимка до/после проверки должны совпасть по repo, PR number, open state, head/base/ref, title/body hash. API/JSON/identity/policy failure закрывает проверку без возврата к старому event body. Сохранённый локальный CLI совместим. Артефакт содержит только identity/digests/status, без body/credentials.
- **FR-040**: Только подтверждённое изменение title/body (точно известная форма changes) не запускает повтор кода/macOS, не отменяет выполняющийся code run и не создаёт новый успешный check с required code/native именем. Retarget, неизвестный/пустой changes и всякая смена кода запускают проверку. Прежний failed/running code result не заменяется skipped/зелёным текстовым результатом.
- **FR-041**: Активация двухэтапная: сначала подготовить trusted metadata/macOS и получить checks, затем добавить required contexts к governance-fast с сохранением strict/base/linear history. Только после read-back protection убирать прежний metadata gate и дорогие text-only исполнения. Closeout и freeze новых PR проверяют полный актуальный набор и текущее описание; исторические combined PR сохраняют свою политику по явно закреплённой границе включения. После merge base сверяется с сохранённой проверкой/историей слияния, не с движущимся сегодняшним master.
- **SC-019**: Негативные исполняемые сценарии: failed/running code + body-only edit; retarget/unknown changes; bad/missing base; native required+skipped; fork repository mismatch; PR меняет validator/sitecustomize; оба API snapshot различаются по body или head/base; ошибки API; closeout не принимает wrong workflow/event/SHA и неполный набор. Live read-back доказывает все требуемые contexts после включения. Snapshot freshness не заявляется атомарной с нажатием merge.


A6 consumer identity clarification: all three successful results must bind to the same final PR head **and checked base**. Code uses its existing CI receipt, native uses the scope artifact, metadata uses the trusted snapshot artifact; each is tied to the verified workflow run/attempt. Missing, expired, mismatched or mixed-attempt proof fails closed. A fresh metadata result never refreshes stale code/native base evidence. For an open PR the common base must equal the live PR base. For a merged PR it must be the actual base of the merge: squash requires merge_commit first parent = checked base and merge tree = final head tree; linear rebase requires the parent before the recorded PR commit count = checked base, a linear source range of that count, and identical final trees. Mere ancestry is insufficient; unknown merge shape is blocked.

A6 historical-policy clarification: record the real foundation merge SHA/PR and activation UTC time from the successful protection read-back in `.github/pr-check-policy.json` during T060/T062. A merged PR strictly before that recorded activation (including the foundation and intervening merges) uses the old combined policy. Every open PR at/after activation, and every PR merged at/after activation, uses all three checks regardless of when its branch/head was created. Missing/invalid/ambiguous activation evidence does not grant a historical exemption. The old combined gate stays until the cutover PR, so this recorded boundary cannot create a protection gap.

For a legitimate metadata edit after merge, the trusted metadata workflow may refresh **merged closed** PR metadata using the immutable merge identity and the checked base derived above; a merely closed/unmerged PR is rejected. Both API snapshots must still agree on state/merged flag/merge SHA/head/base/ref and metadata hash. This cheap refresh never executes PR code or reruns product tests, and never compares historical base with today's master. Required proof artifacts use 90-day retention and names binding run/attempt, not reusable pass caches.
