# F273/T113: независимый проектный гейт локального ресурсного режима

Дата: 30.10.2026. Проверяющий `/root/f273_release_boundary`.
Ветка `codex/f273-local-period-20261029`, основа
`dc8b0cd055bccbc73cf5dbdf6302f88225c4f8bc`, T113/#7804.
Путь проверки: `high-risk-product`, действующий Spec Kit, до изменения кода.

## Решение и точная область

**SCOPED DESIGN / ANALYZE PASS: CRITICAL 0, HIGH 0; открытых P1: 0, P2: 0.**
Полностью перечитаны все117 вопросов: **117 checked / 0 unchecked**.
Их отметки и исторические пояснения не менялись. Это качество проекта
ограниченного изменения, а не подтверждение реализации или работы сервера.

Полностью прочитан конечный precode
`.dev/growth/t113-local-resource-precode-20261030.md`, SHA-256
`33a72287327881b59b6a8b2bd11c1546d112442aaa8eaac29906b9484728e369`.
Исходный SHA-256 был
`629f77d06a9cac029d2f10f68e932b9faa1220a9c4a810f995841954f2a4ea8c`.
До кода устранены неопределённости обнаружения Docker, настоящего места
резервных копий, локального файлового ресурса и области устойчивого инцидента.
Полный проект верхнего оператора не менялся: SHA-256
`5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`.

Допускается реализация именно двух явных режимов существующих collector,
capacity, guard, alert и потребителей. Ни новый сервис, ни обход PostHog
готовности, ни переход рабочего состояния версии1 этим не разрешаются.

## Проверенные источники и текущий разрыв

Проверен фактический путь `posthog-storage.py::runtime_roots / allocated /
graf_relation_roots / measured_growth / main` → `posthog-capacity.py::evaluate /
transition / restore` → `posthog-runtime-guard.sh` →
`alert-analytics-degradation.sh::collect_reasons / metrics_summary /
build_message` → `provider_readiness.py::runtime_guard_blockers /
build_analytics_operations_readiness` → `activation_operator.py::_runtime_operations`.
Прочитаны действующие consumer fixtures и проверки ёмкости, инцидента,
восстановления, обхода файлов, роста и чтения guard в двух профильных contract
модулях. Тесты не запускались; это проектное ревью.

Применимые требования перечитаны: spec FR-031/032/033–039/048/050;
operations «Один физический диск», «Состав расхода T116», полнота входа,
численные пределы и локальные ворота; plan о local_only и полном операторе;
tasks T097/T113/T116 и уточнения; quickstart локального режима; capacity baseline;
provider rollback «Restoration». Проверены `backup-rec-stack.sh`, inventory
relations, wrapper collector и guard env example.

Сейчас collector без PostHog прекращает обнаружение до поиска оставшихся
томов; guard требует контейнеры и probes PostHog. Это не соответствует
принятой самостоятельной GRAF readiness для корректного local_only.
Сейчас образец/alert имеют версию2, а устойчивый инцидент — версию1 без scope;
им нельзя молча приписать новую семантику.

## Принятое решение о полных копиях GRAF

Полные смешанные копии GRAF могут оставаться **вне точной суммы
`analytics_storage_bytes`**. Они содержат продуктовую БД и объекты; приписать
весь объём аналитике означало бы нарушить уже проведённую границу класса
`graf_analytics_tables`. Доля аналитики в смешанной копии неизвестна,
не равна нулю и не даёт точного90дневного прогноза.

Это согласуется с FR-031/032/036 и существующим исключением общего WAL/каталогов
в operations при следующих обязательных условиях конечного проекта:

1. Отдельные аналитические архивы, manifests, staging, failed/incomplete
   по-прежнему полностью входят в `backup_artifacts`; присутствующий PostHog
   storage нельзя скрыть локальным режимом. Формула непересекающихся классов,
   выделенные блоки и учёт один раз по устройству/inode сохраняются.
2. Для смешанных GRAF копий защищается запас их настоящей файловой системы
   с ролью analytics: `<20%` отключает необязательную аналитику, `<10%` сохраняет
   дополнительный host факт. Ресурс дедуплицируется по идентичности.
3. Поддерживаемый parent фиксирован `/opt/projects/2brain-rec/backups`, как
   штатный default backup script; его нельзя выводить из произвольного
   `GRAF_APP_DIR`. Override допускается лишь для прямого дочернего destination
   на том же ресурсе без links. Несовпадение/неизвестность — HOLD, а не обход.
4. Фактические runtime overrides сверяет `_runtime_operations`; будущая
   coherent backup использует тот же parent. Неизвестные установленные
   задания/cron и отдельные staging mounts остаются HOLD полного оператора.
   Ни collector, ни env файла одного процесса не доказывают отсутствие jobs.
5. Существование безопасного parent обязательно. Provisioning выполняется
   отдельно; guard не создаёт каталог ради PASS. Host staging остаётся там же;
   PostgreSQL staging требует привязанную FS либо подтверждённый tmpfs с
   действующей защитой памяти. Неизвестный ресурс не считается покрытым.
6. В operations, capacity baseline и runbook явно записываются mixed/dedicated
   граница и неизвестная доля. Верхний оператор отдельно проверяет место для
   двух новых полных копий, restore target и staging до stop по ранее принятому
   проекту. Резерв файловой системы не подменяет эту предпусковую оценку.

Таким образом не требуется разбор всех файлов продукта каждую минуту,
выделение приблизительной доли или новый общий сканер. Потолок128GiB,
дедлайн21.11.2026UTC, обязательное принятие T097 и режим без возрастного удаления
сохраняются. PASS здесь не принимает фактический бюджет или неизвестный рост.

## Обязательный алгоритм реализации

1. Два literal scope `posthog` и `graf-local`, default posthog. Неверный scope
   отвергается до probes, mkdir и иных изменений. API выбирает ожидаемый scope
   из проверенного режима Settings, не из guard env.
2. Обнаружение runtime использует полный `docker ps -aq --no-trunc` ID64hex,
   уникальность и точное равенство множества inspect Id. Пустой/частичный/
   повторный/лишний ответ или неверные project/service labels — INCOMPLETE.
   Оба volume lists обязательны даже без контейнеров; каждый inspect volume
   ровно один и с запрошенным Name. Остаточные labelled/prefix/detached volumes
   измеряются. Пустой успешный inventory и ошибка команды различаются.
3. Только local допускает доказанное отсутствие PostHog required classes и
   archive dir; отсутствие последнего проверяется lstat с безопасным существующим
   родителем. Links/PermissionError/неизвестный ресурс не означают отсутствие.
   GRAF relations остаются обязательными metadata-only. Локальные anchors —
   actual roots, app и mixed-backup parent; отсутствующий PostHog analytics path
   из общего env example не требуется. После24ч local не вызывает event_count.
4. Sample и alert version3 с обязательным scope, без fallback на version2.
   Scope входит в inventory digest; старый anchor не подтверждает рост,
   старый budget не принимается автоматически. Budget schema version1 остаётся,
   но связана с новым inventory/config. Неверный scope закрывает readiness;
   независимо проверенный свежий низкий запас не исчезает из protection.
5. Local пропускает только probes самого PostHog и выводит not_applicable,
   не PASS/0. Product ready, host sensors, collector, budget, reserve, durable
   incident и все прежние защиты остаются. Provider readiness явно posthog;
   local sample не открывает отправку провайдеру. Alert сообщает scope и не
   выдаёт разрешений; прежние независимые backup/retention проверки сохраняются.
6. Durable protection version2 хранит scope исходного инцидента. Version1,
   missing/invalid/другой scope дают HOLD без перезаписи; даже observed нельзя
   автоматически перенести между scope. Новое observed создаётся лишь при
   доказанно отсутствующем файле. Один успешный переход на инцидент, lock,
   retry после ошибки, dryrun/auto-off/apply_failed/readback остаются.
7. Manual receipt version2 совпадает по scope с explicit helper scope,
   sample и исходным инцидентом. Старый receipt запрещён. PostHog сохраняет
   provider_smoke/page_validation; local требует local_measurement_review
   вместе с прежними общими proofs, сроками, growth, budget/config и actual
   Config.Env hash. Смена scope не заменяет proofs. Timer не восстанавливает
   запись. Runtime protection reader обязан принять только новую точную схему.
8. Действующая инструкция `product-analytics-provider-rollback.md` §Restoration
   входит в согласованное обновление runbook: explicit scope, receipt/state
   версии и разные proofs должны совпасть с кодом. Рабочий переход version1
   остаётся отдельным операторским HOLD с сохранением истории, без удаления
   старого файла и без автоматической миграции в этом срезе.

## Scoped analyze и покрытие

`speckit-analyze` применён к этому ограниченному срезу. before/after analyze
hooks отключены в extensions.yml; побочных hook действий не было. Установленный
prerequisite script не поддерживает `--require-spec`; после чтения help выполнен
поддержанный `--json --require-tasks --include-tasks`, путь F273 подтверждён.
Наличие spec проверено отдельно чтением. Новых tasks/issues не требуется:
действующие T113 и T116 уже покрывают локальный gate и ресурсный путь;
фактическая нагрузка/рост/принятие остаются T097.

| Требование | Задачи | Проектное покрытие |
| --- | --- | --- |
| FR-031/032 | T113, T116 | Точные объём/ресурс/область; analytics first; latch и известный низкий запас. |
| FR-033/034/035 | T113, действующие backup/restore задачи | Срез не выдаёт полноту/свежесть/restore из capacity; отдельные gates сохраняются. |
| FR-036 | T113, T116, lifecycle задачи | Нет нового удаления, TTL, ротации или очистки истории. |
| FR-038 | T113, T116 | Новые версии, явный scope, inventory/config binding, actual installed code gates. |
| FR-039 / SC-012 | T097, T116 | Рост и запас сохраняются; synthetic validation не выдаётся за измеренную нагрузку. |
| Локальная готовность | T113 | Settings-bound local consumer; provider gate остаётся posthog; верхний HOLD сохранён. |

Покрыто6/6 применимых групп (100% проектного покрытия); это не процент готовности
фичи. Новых непокрытых задач0, дублирующих реализаций0, нерешённых проектных
неоднозначностей0, нарушений конституции0. Указанные выше уточнения обязательны
для последующего независимого ревью кода, не факультативны.

| Checklist | Перечитано | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| requirements.md | 16 | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement.md | 45 | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security.md | 27 | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra.md | 29 | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| Всего | 117 | 117 | 0 | Отметки не изменены. |

Повторное чтение крупных неизменных документов — по разрешённому исключению
F273. Текущие хеши совпали с ранее прочитанными: constitution
`7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`, PRD
`0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`, status
`25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`, product-gates
`9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`, spec
`45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2`, operations
`733f9c5e4b4ff079ed016974d1f759c3100506a5cfbca8c0e4f301e665c85ced`, data-model
`488833fcc4b8e4841672485b35cfa0161e1f02983d10ad98b52eb71d55bb55f5`.
Применимые разделы и зависимости перечитаны целиком; хеши не являются
доказательством исполнения требований.

## Следующая проверка и сохранённые HOLD

Сначала причинные RED для local absence, residual volumes, inspect identity,
command error, old/mismatched schemas и запрета provider calls; затем полный
collector→capacity→guard→alert/runtime consumer на собственном synthetic
filesystem/command environment. Обязательны независимые known low-space19.9/9.9,
неизвестный budget/inventory, scope drift/incident, auto-off/dryrun/applyfail/
retry/once и manual restore с чужим scope/инцидентом/proofs. Нужны все текущие
unit consumers/fixtures и оба полных contract модуля, Linux actual resource/file
cases, lint/governance/process/fragment/link/whitespace и независимое code review.
PG профиль нужен при фактическом SQL/DB source изменении, которого проект не требует.

Не выполнены и этим отчётом не приняты: установленный полный каталог jobs/cron/
purge/retention/staging, рабочая миграция protection версии1, local shell/runtime,
верхний initial/backup/verify/actual restore/resume, место и две реальные копии,
CD/rollback/daily, рабочие ready/T0/IP/получатели, exact-SHA CI/Full/release,
T112/T113/#7804 и коммерческие AC01–AC06. `full_preflight_not_implemented` и
`activation_recovery_unverified` сохраняются. Трафик и продажи не доказаны.

Проверяющий не выполнял SSH, БД, Docker, тесты, Dev, production, commit/push,
GitHub или выпуск; изменён только этот отчёт. Следующий шаг — реализация
ограниченного проекта, затем независимая проверка фактического diff.
