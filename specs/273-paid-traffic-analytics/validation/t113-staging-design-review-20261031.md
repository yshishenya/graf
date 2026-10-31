# F273/T113: независимый проектный гейт привязки временных файлов

Дата: 31.10.2026. Проверяющий `/root/f273_release_boundary`.
Ветка `codex/f273-local-period-20261029`, основа
`704abfbab4ee04609ce2186b892d14626b668944`, T113/#7804.
Полоса `high-risk-product`, действующий Spec Kit, до изменения кода.
Перед завершением HEAD стал `28cf82c52fb962f62635e90c0d7a4d0f75051c06`:
добавлены только два документа docs/growth о фактически измеренном ресурсе.
Проверяемые код и нормативные входы среза по-прежнему соответствуют
перечисленным ниже контрольным суммам; новых staging изменений нет.

## Решение

**SCOPED DESIGN / ANALYZE PASS: CRITICAL 0, HIGH 0; открытых P1: 0, P2: 0.**
Все117 действующих вопросов перечитаны и оценены: **117 checked / 0 unchecked**.
Отметки не менялись: это качество требований и проекта данного среза,
не приёмка реализации, рабочего сервера, полного T113 или роста продаж.

Разрешена реализация только описанной привязки staging к защищённому ресурсу:
четыре создателя PG staging + общий SQL-validator; Python metadata внутри
фиксированного backup parent; удержанный read-only runtime proof PGDATA.
Новые сервисы, зависимости, роли, миграции, включение writer и T0 не входят.

Полностью перечитан окончательный `.dev/growth/t113-staging-precode-20261031.md`.
SHA-256: `da81d4ab8e6c4f7fb2e4d56c48156596632e0176eead2979b0356e0b329dcf55`.
Начальная редакция `b7bb425b96b99826d28f2df581d9773feed7f337f49ed7a6b0a2fee7276956f5`
уточнена до кода: одного st_dev недостаточно для запрета tmpfs/overlay.
Окончательная редакция требует Linux fstatfs удержанных FD, поддерживает только
Linux64 amd64/arm64 и ext/XFS/Btrfs; неизвестный magic, ошибка, tmpfs и overlay
запрещают успех. Этот проектный вопрос закрыт; алгоритм не требует пакетов,
нового процесса или общего парсера mountinfo.

## Проверенная цепочка и обоснование

1. `rec-db-backup-inventory.sql` проверяет текущую DB/роль и точный staging
   до pg_export_snapshot, pg_dump и перенаправления inventory. Сейчас там
   только старый `/tmp` guard. Меняются SQL и все четыре вызывающих участка
   одновременно, без совместимости со старым путём и без fallback.
2. `backup-rec-stack.sh` создаёт уникальный закрытый PG staging, получает
   согласованный dump/schema/inventory/checksums через общий SQL, копирует
   комплект и очищает только присвоенный staging до PASS. Новый префикс,
   создание и проверка suffix должны совпасть; прежние проверки прав,
   коллизий, checksum, mirror и ошибок cleanup сохраняются.
3. `rehearse-rec-restore.sh` логически восстанавливает custom dump в отдельную
   UUID DB и отдельно разбирает schema.sql в UUID schema DB. Общий SQL
   вызывается дважды; обе цели и owned bucket очищаются перед PASS.
   Новый префикс PG staging совместим с этой схемой. Host TMPDIR этого shell
   всё ещё не доказан и явно не принимается как полный local_only путь.
4. Python `_create_coherent_backup` уже удерживает фиксированный parent,
   уникальную цель, controlled export, состояния unknown create/upload,
   завершение detached SQL и проверку cleanup. Изменение PG префикса не
   должно ослаблять эти гарантии или удалять архив/reference.
5. Python `_rehearsal_resources` должен создавать metadata tempfile только
   внутри существующего canonical root0700 MIXED_BACKUP_PARENT, удерживая
   идентичность parent/своей цели. Reference — прямой child этого parent.
   Нынешний свободный host tempfile заменяется; чужие каталоги и исходный
   комплект никогда не удаляются.
6. `_runtime_policy` уже сверяет точный Compose/image/Engine mount inventory,
   writable local volume, driver/scope/options/mountpoint и запрет лишних mounts.
   Compose PG17 сейчас имеет единственный data mount `/var/lib/postgresql/data`.
   Новый context связывает host Source с proc-root PGDATA удержанными FD,
   проверяет UID/GID70,0700/0750,noACL,dev/ino и тот же st_dev с backup parent.
   Один допустимый proc-root hop не превращается в разрешение symlinks в пути.
   Environment PGDATA и реальный SHOW data_directory проверяются отдельно;
   фактическая DB не выводится только из env или строки Compose.
7. Context охватывает runtime DB read и проверку после yield; процесс/PID start,
   FD/path identities и FS повторно проверяются. Наружу выходит digest,
   содержимое БД, env, секреты и пути доказательством не публикуются.

### PGDATA: влияние на восстановление и очистку

Текущие dump/restore логические: pg_dump снимает DB из одного snapshot,
pg_restore пишет в созданную UUID DB. Они не копируют PGDATA целиком.
Следовательно, отдельный top-level `twobrain-rec-backup.<alnum>` не становится
relation, не восстанавливается как каталог и не является целью DROP DATABASE.
Удалять разрешено лишь уникальный каталог, успешно созданный данной попыткой;
нельзя чистить PGDATA, его base/global/pg_wal или чужие sibling directories.
Unknown create/незавершённый SQL запрещают заявлять cleanup/PASS и не дают
права угадывать принадлежность пути. Ошибка или утечка оставляют HOLD.

Создание/очистка child меняют mtime/ctime/size/linkcount родителя. Новый context
намеренно связывает только dev/ino/uid/gid/mode и FS type; он не должен считать
обычную запись PostgreSQL подменой каталога. `_settings_file_identity` остаётся
полной для неизменных secret/config files. Текущий `_runtime_policy` включает
полную metadata volume roots; этот срез проверяет runtime во время read-only DB
контекста. Будущий upper operator обязан не предполагать неизменность прежнего
runtime digest после собственных mkdir/cleanup; это не доказанный полный
операторский протокол в данном проектном PASS.

Каталог находится на общем продуктовом диске. Это обоснованная привязка ресурса,
но не оценка требуемого места: два полных новых комплекта, restore targets,
PG/host staging и запас до stop по-прежнему принимает верхний оператор.
Проверка самого типа FS не доказывает отсутствие отдельных quota/тонкого
хранилища; такой ресурс не получает автоматическую ёмкостную готовность.

## Условия проверки реализации

Обязательные причинные RED→GREEN: новый путь принимается, старый/tmp,
произвольный/неканонический/вложенный suffix отклоняется до вывода SQL;
оба shell профиля используют тот же контракт. Python host metadata создаётся
в fixed parent, коллизия/reference/unsafe parent не изменяются.

Runtime proof: допустимый фактический FS/identity, wrong device, symlink,
подмена пути/процесса, лишний submount, env PGDATA и SHOW drift; реальные
same-device tmpfs/overlay обязаны дать HOLD. Ошибка fstatfs/неподдерживаемый
ABI/magic закрывает успех, без fallback и без чтения visitor/product rows.
Нужны Linux actual filesystem cases и PG17 native snapshot/restore/replay,
сохранение чужих PGDATA siblings/исходного reference и cleanup своих целей.
Повторяются collision, unknown create/upload, cancel/сигналы и cleanup failure.
Новый context не должен давать ложный отказ от нормального изменения timestamps.

Тесты этим проверяющим не запускались. Исходный код, shell, SQL, Compose,
тестовые callers и нормативные зависимости прочитаны; SSH, Docker, DB,
рабочий GRAF Dev и сервер не вызывались. Сохранение этого отчёта — единственная
мутация проверяющего. Чужие текущие изменения docs/growth сохранены.

## Scoped analyze

Расширения до/после analyze проверены: оба commit hooks отключены.
`check-prerequisites.sh --json --require-tasks --include-tasks` подтвердил F273
и наличие spec/plan/tasks; установленный скрипт не поддерживает --require-spec.
Спецификация существует и сверена отдельно. Нового функционального требования,
новой задачи или несовместимого протокола нет: staging выполняет уже принятые
operations/first-period/resource gates открытой T113.

| Обязательство | Покрытие | Вывод |
| --- | --- | --- |
| FR-025, SC-006: устойчивый период и restore без нового T0 | T113, activation-milestones/first period | Срез T0/ledger не меняет |
| FR-031/032: настоящий общий ресурс, analytics first | T113/T116, operations/resource scope | PG/host staging на привязанном ресурсе; неизвестное HOLD |
| FR-033–035/051–053: полный закрытый комплект/restore/cleanup | T110/T113, общий SQL и оба rehearsal | Логический путь сохраняется; старые copies не удаляются |
| FR-036/048/050: until_decision/точное удаление | T109/T110/T113, lifecycle/replay | Новых age jobs/TTL/пересмотра сроков нет |
| Конституция III/IV/VI: секреты/lifecycle/доказательства | high-risk-product, reviewer/validation gates | Только metadata/digest; code/native/release gates отдельно |

Локально незакрытых CRITICAL/HIGH, противоречий или задач без применимого
обязательства для этого среза не найдено. Это не полный analyze закрытия F273.
Возможность логического restore и намерение проверить тестами не объявлены
результатом выполненной native-проверки.

## Перечитанные вопросы чеклистов

Каждый текущий вопрос оценён по указанному ниже договору. «Сохранено» означает
проверенное качество неизменного требования; не выполненную эксплуатационную
приёмку. Неподтверждённых требований в этом проектном объёме нет. При этом
перечисленные выше тесты ещё должны подтвердить реализацию.

### requirements: 16 checked / 0 unchecked

| Пункт | Основание и результат |
| --- | --- |
| Q01 | Сохранено: No implementation details (languages, frameworks, APIs); spec/SC/границы и зависимости. |
| Q02 | Сохранено: Focused on user value and business needs; spec/SC/границы и зависимости. |
| Q03 | Сохранено: Written for non-technical stakeholders; spec/SC/границы и зависимости. |
| Q04 | Сохранено: All mandatory sections completed; spec/SC/границы и зависимости. |
| Q05 | Сохранено: No [NEEDS CLARIFICATION] markers remain; spec/SC/границы и зависимости. |
| Q06 | Сохранено: Requirements are testable and unambiguous; spec/SC/границы и зависимости. |
| Q07 | Сохранено: Success criteria are measurable; spec/SC/границы и зависимости. |
| Q08 | Сохранено: Success criteria are technology-agnostic (no implementation details); spec/SC/границы и зависимости. |
| Q09 | Сохранено: All acceptance scenarios are defined; spec/SC/границы и зависимости. |
| Q10 | Сохранено: Edge cases are identified; spec/SC/границы и зависимости. |
| Q11 | Сохранено: Scope is clearly bounded; spec/SC/границы и зависимости. |
| Q12 | Сохранено: Dependencies and assumptions identified; spec/SC/границы и зависимости. |
| Q13 | Сохранено: All functional requirements have clear acceptance criteria; spec/SC/границы и зависимости. |
| Q14 | Сохранено: User scenarios cover primary flows; spec/SC/границы и зависимости. |
| Q15 | Сохранено: Feature meets measurable outcomes defined in Success Criteria; spec/SC/границы и зависимости. |
| Q16 | Сохранено: No implementation details leak into specification; spec/SC/границы и зависимости. |

### privacy-measurement: 45 checked / 0 unchecked

| Пункт | Основание и результат |
| --- | --- |
| CHK001 | Сохранено: Clarity, Spec §Правовая конструкция измерения; spec/правовые уровни; operations/first period/resource scope. |
| CHK002 | Сохранено: Clarity, Spec §FR-010; spec/правовые уровни; operations/first period/resource scope. |
| CHK003 | Сохранено: Completeness, Spec §Правовая конструкция измерения, legal-basis.md; spec/правовые уровни; operations/first period/resource scope. |
| CHK004 | Сохранено: Clarity, Spec §Правовая конструкция измерения, research.md §1; spec/правовые уровни; operations/first period/resource scope. |
| CHK005 | Сохранено: Ambiguity, Spec §Правовая конструкция измерения; spec/правовые уровни; operations/first period/resource scope. |
| CHK006 | Сохранено: Completeness, Spec §Out of Scope; spec/правовые уровни; operations/first period/resource scope. |
| CHK007 | Сохранено: Clarity, Spec §FR-047; spec/правовые уровни; operations/first period/resource scope. |
| CHK008 | Сохранено: Ambiguity, Spec §FR-003; spec/правовые уровни; operations/first period/resource scope. |
| CHK009 | Сохранено: Measurability, Spec §FR-004; spec/правовые уровни; operations/first period/resource scope. |
| CHK010 | Сохранено: Consistency, Spec §FR-001; spec/правовые уровни; operations/first period/resource scope. |
| CHK011 | Сохранено: Coverage, Edge Case, Spec §FR-003; spec/правовые уровни; operations/first period/resource scope. |
| CHK012 | Сохранено: Coverage, Exception Flow, Gap; spec/правовые уровни; operations/first period/resource scope. |
| CHK013 | Сохранено: Consistency, Spec §FR-003, §FR-009; spec/правовые уровни; operations/first period/resource scope. |
| CHK014 | Сохранено: Clarity, Spec §FR-005; spec/правовые уровни; operations/first period/resource scope. |
| CHK015 | Сохранено: Consistency, contracts/anonymous-aggregate.md; spec/правовые уровни; operations/first period/resource scope. |
| CHK016 | Сохранено: Measurability, Spec §FR-010, SC-002; spec/правовые уровни; operations/first period/resource scope. |
| CHK017 | Сохранено: Coverage, Gap, data-model.md; spec/правовые уровни; operations/first period/resource scope. |
| CHK018 | Сохранено: Ambiguity, Spec §FR-011; spec/правовые уровни; operations/first period/resource scope. |
| CHK019 | Сохранено: Gap, Measurability; spec/правовые уровни; operations/first period/resource scope. |
| CHK020 | Сохранено: Completeness, Spec §FR-013; spec/правовые уровни; operations/first period/resource scope. |
| CHK021 | Сохранено: Consistency, contracts/anonymous-aggregate.md; spec/правовые уровни; operations/first period/resource scope. |
| CHK022 | Сохранено: Clarity, Spec §FR-017; spec/правовые уровни; operations/first period/resource scope. |
| CHK023 | Сохранено: Consistency, Spec §FR-017, SC-008; spec/правовые уровни; operations/first period/resource scope. |
| CHK024 | Сохранено: Coverage, Edge Case, Spec §FR-018; spec/правовые уровни; operations/first period/resource scope. |
| CHK025 | Сохранено: Clarity, Spec §FR-024; spec/правовые уровни; operations/first period/resource scope. |
| CHK026 | Сохранено: Completeness, Spec §FR-025; spec/правовые уровни; operations/first period/resource scope. |
| CHK027 | Сохранено: Completeness, contracts/activation-milestones.md; spec/правовые уровни; operations/first period/resource scope. |
| CHK028 | Сохранено: Coverage, Edge Case, Spec §FR-022; spec/правовые уровни; operations/first period/resource scope. |
| CHK029 | Сохранено: Measurability, Spec §FR-019; spec/правовые уровни; operations/first period/resource scope. |
| CHK030 | Сохранено: Completeness, Spec §FR-021, contracts/activation-milestones.md; spec/правовые уровни; operations/first period/resource scope. |
| CHK031 | Сохранено: Completeness, Spec §SC-009; spec/правовые уровни; operations/first period/resource scope. |
| CHK032 | Сохранено: Consistency, Spec §FR-031; spec/правовые уровни; operations/first period/resource scope. |
| CHK033 | Сохранено: Ambiguity, Spec §FR-033; spec/правовые уровни; operations/first period/resource scope. |
| CHK034 | Сохранено: Clarity, Consistency, Spec §FR-052/053, contracts/operations.md; spec/правовые уровни; operations/first period/resource scope. |
| CHK035 | Сохранено: Completeness, Spec §FR-036; spec/правовые уровни; operations/first period/resource scope. |
| CHK036 | Сохранено: Coverage, Exception Flow, Gap; spec/правовые уровни; operations/first period/resource scope. |
| CHK037 | Сохранено: Measurability, Spec §FR-034, SC-010; spec/правовые уровни; operations/first period/resource scope. |
| CHK038 | Сохранено: Measurability, Spec §SC-012; spec/правовые уровни; operations/first period/resource scope. |
| CHK039 | Сохранено: Traceability; spec/правовые уровни; operations/first period/resource scope. |
| CHK040 | Сохранено: Completeness, Spec §FR-040; spec/правовые уровни; operations/first period/resource scope. |
| CHK041 | Сохранено: Measurability, Spec §FR-042; spec/правовые уровни; operations/first period/resource scope. |
| CHK042 | Сохранено: Assumption, plan.md; spec/правовые уровни; operations/first period/resource scope. |
| CHK043 | Сохранено: Dependency, Spec §Legacy Impact; spec/правовые уровни; operations/first period/resource scope. |
| CHK044 | Сохранено: Clarity, Spec §FR-044; spec/правовые уровни; operations/first period/resource scope. |
| CHK045 | Сохранено: Gap, plan.md; spec/правовые уровни; operations/first period/resource scope. |

### security: 27 checked / 0 unchecked

| Пункт | Основание и результат |
| --- | --- |
| CHK001 | Сохранено: Completeness, Spec §Правовая конструкция измерения; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK002 | Сохранено: Completeness, Spec §FR-008; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK003 | Сохранено: Consistency, Spec §FR-008, §Legacy Impact; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK004 | Сохранено: Coverage, Exception Flow, Gap; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK005 | Сохранено: Completeness, Spec §FR-028, plan.md; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK006 | Сохранено: Clarity, contracts/operations.md; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK007 | Сохранено: Measurability, Spec §FR-028; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK008 | Сохранено: Consistency, Spec §FR-029; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK009 | Сохранено: Coverage, Gap; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK010 | Сохранено: Completeness, Spec §FR-036, data-model.md; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK011 | Сохранено: Clarity, contracts/operations.md; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK012 | Сохранено: Coverage, Exception Flow, Gap; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK013 | Сохранено: Measurability, Spec §FR-036; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK014 | Сохранено: Consistency, Constitution §IV; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK015 | Сохранено: Completeness, Constitution §IV; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK016 | Сохранено: Consistency, Spec §FR-001; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK017 | Сохранено: Clarity, data-model.md; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK018 | Сохранено: Consistency, Spec §FR-002; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK019 | Сохранено: Coverage, Spec §FR-003; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK020 | Сохранено: Consistency, contracts/anonymous-aggregate.md; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK021 | Сохранено: Measurability, Spec §FR-037; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK022 | Сохранено: Clarity, Spec §FR-038; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK023 | Сохранено: Completeness, contracts/operations.md; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK024 | Сохранено: Coverage, Gap; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK025 | Сохранено: Completeness, Spec §FR-047; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK026 | Сохранено: Completeness, Spec §FR-062; Quickstart §Сценарий 8; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |
| CHK027 | Сохранено: Consistency, Spec §FR-061; Plan §Полный вход T098; spec/FR-001–008/026/036/048–050/061; operations/lifecycle. |

### infra: 29 checked / 0 unchecked

| Пункт | Основание и результат |
| --- | --- |
| CHK001 | Сохранено: Ambiguity, Spec §FR-033; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK002 | Сохранено: Clarity, Consistency, Spec §FR-034/052/053, Session 2026-10-22; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK003 | Сохранено: Measurability, Spec §FR-033; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK004 | Сохранено: Coverage, Exception Flow, Gap; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK005 | Сохранено: Coverage, Gap; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK006 | Сохранено: Measurability, Spec §FR-034, SC-010; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK007 | Сохранено: Measurability, Spec §FR-035, SC-010; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK008 | Сохранено: Clarity, Spec §FR-035; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK009 | Сохранено: Coverage, Exception Flow, Gap; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK010 | Сохранено: Coverage, Gap; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK011 | Сохранено: Measurability, Spec §SC-012; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK012 | Сохранено: Ambiguity, Spec §SC-012; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK013 | Сохранено: Clarity, Spec §FR-032, research.md §2; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK014 | Сохранено: Consistency, Spec §FR-032; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK015 | Сохранено: Coverage, Edge Case; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK016 | Сохранено: Consistency, Spec §FR-031; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK017 | Сохранено: Clarity, Spec §FR-031; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK018 | Сохранено: Completeness, Spec §SC-009; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK019 | Сохранено: Clarity, Spec §FR-030; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK020 | Сохранено: Coverage, Exception Flow, Gap; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK021 | Сохранено: Completeness, contracts/operations.md; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK022 | Сохранено: Completeness, Spec §FR-039; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK023 | Сохранено: Measurability, Spec §FR-039; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK024 | Сохранено: Coverage, Edge Case, Spec §Edge Cases; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK025 | Сохранено: Coverage, Edge Case, Spec §Edge Cases; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK026 | Сохранено: Completeness, Plan §Полный вход T098; Quickstart §Сценарий 8; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK027 | Сохранено: Measurability, Quickstart §Сценарий 8; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK028 | Сохранено: Coverage, Plan §Полный вход T098; spec/FR-030–039/051–056; operations/backup/resource scope. |
| CHK029 | Сохранено: Consistency, Spec §Legacy Impact; Plan §Полный вход T098; spec/FR-030–039/051–056; operations/backup/resource scope. |

## Остаток и запрет расширения PASS

Сохраняются `full_preflight_not_implemented` и `activation_recovery_unverified`.
Не приняты installed jobs/cron/purge/retention/staging целиком, working v1
protection migration, верхние initial/backup/verify/actual restore/resume,
CD/rollback/daily, ready/T0/IP/получатели, exact-SHA PR/CI/Full/выпуск.
T112/T113/#7804 и коммерческие AC01–AC06 остаются OPEN. Проверки исходников
и качества требований не доказывают внешний трафик, конверсию или продажи.

## Контрольные суммы источников

Неизменные крупные baseline повторно сверены по SHA-256 в рамках прямо
разрешённого владельцем исключения F273 на повторное чтение. Затронутые целые
разделы spec/operations/plan/tasks/quickstart и зависимости перечитаны; все117
вопросов перечитаны непосредственно. Хеши не выданы за продуктовую приёмку.

| Путь | SHA-256 |
| --- | --- |
| `.dev/growth/t113-staging-precode-20261031.md` | `da81d4ab8e6c4f7fb2e4d56c48156596632e0176eead2979b0356e0b329dcf55` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `.agents/skills/speckit-analyze/SKILL.md` | `07ead5c0db569e93b75c4cada8139ef799d5721d6037c3ed15b7482d114d22d1` |
| `.specify/extensions.yml` | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| `specs/273-paid-traffic-analytics/spec.md` | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| `specs/273-paid-traffic-analytics/data-model.md` | `488833fcc4b8e4841672485b35cfa0161e1f02983d10ad98b52eb71d55bb55f5` |
| `specs/273-paid-traffic-analytics/plan.md` | `2b25a48d91640321fb47582b0d5fe2d0a249dfe72a8436a4a8c87b0188e9ffab` |
| `specs/273-paid-traffic-analytics/tasks.md` | `edbec930f15d85ff9b45a84d8d7ca6fe3b8133c69375cdb2849c3a7e9e75f2db` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `4e885f846adf9890d04668df585b4485f8b23aa1eec70fbc0326f79ee0e52c4d` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `d7a55b9b0c7ef99b8e4db5fa28136fd6c3748ccb376a94ec3f254712931e239b` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9` |
| `specs/273-paid-traffic-analytics/validation/t113-full-operator-design-20261030.md` | `5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec` |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| `specs/273-paid-traffic-analytics/checklists/security.md` | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| `apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py` | `16fe8c3e5a6e57642572d28755e0c89164be3f577636b007f3180ca0f68e9421` |
| `infra/scripts/rec-db-backup-inventory.sql` | `d9e761add12c8504b55624d72c286b2eb3dafd981afa99a01ffe2107d92e0295` |
| `infra/scripts/backup-rec-stack.sh` | `603738f16525d86fbed1c681ce0dfcca5cb90bdebd37c9af6641d306c907efc9` |
| `infra/scripts/rehearse-rec-restore.sh` | `1d597450088a7667aa83fad718b3aa6469df04782a979e20d02fb9eebb922a35` |
| `infra/docker-compose.yml` | `9098cb15c8c4a675beae529664e128d46a2dc50671dee8171d05b659b482bcc6` |
| `infra/scripts/posthog-storage.py` | `1dc62e52415778a3f6c18a1e0c926446eb4cbf8cc5ca6785ed6de3e7b9d26bba` |
