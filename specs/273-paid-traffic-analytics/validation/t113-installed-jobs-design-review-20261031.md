# F273/T113: независимый проектный гейт установленных заданий

31.10.2026, проверяющий `/root/f273_release_boundary`, high-risk-product.
Ветка `codex/f273-local-period-20261029`, HEAD
`521670ddc1db2b9db25bcf987d622034a54a4248`, T113/#7804.
Это разбор проекта до кода. Рабочие задания/CLI/БД/Dev не запускались;
SSH/Docker/Git/GitHub/установка/конфигурация не изменялись. Записан только этот
отчёт. Чужих изменений на начало проверки не было; право менять их не получено.

## Решение

**DESIGN HOLD для заявления о полном installed-jobs proof:** CRITICAL0,
HIGH2, открытых проектных P1:2, P2:0. Требования уже определяют нужный результат,
но фраза «installed guard/purge/cron hashes» ещё не задаёт конкретную полную
проверку установки. Ни поиск слов в cron, ни установка прежних PostHog timers,
ни отдельный новый helper не дают рабочего local_only gate.

Все117 действующих вопросов непосредственно перечитаны и заново оценены:
requirements16/0, privacy45/0, security27/0, infra29/0; всего **117 checked /
0 unchecked**. Их отметки не менялись: это качество принятых требований,
а не готовность планирования каждой операторской операции или реализации.
Продуктовые решения/поля/получатели/сроки хранения менять не требуется.

Нужно до кода конкретизировать два алгоритмических пробела ниже в существующем
плане/договоре/quickstart, затем повторно принять этот ограниченный проект.
Общее разрешение писать весь T113 не превращает непроверенный scanner в
источник ready. Дополнительного решения владельца для обычного уточнения
алгоритма в прежних границах этот отчёт не требует.

## Проверенная текущая граница

- Host bootstrap принимает только `--preflight` и намеренно возвращает exit1 /
  `full_preflight_not_implemented`: `infra/scripts/activation-operator.py:337–373`.
  Рабочих CLI initial/backup/verify/restore пока нет.
- `_runtime_guard_units` проверяет ровно guard.service/timer, их исходные bytes
  и загруженные критические свойства до/после DB context. Это необходимая часть,
  а не каталог всех установленных запусков.
- `enforce-product-analytics-retention.sh:20` имеет прежние четыре позиции с
  measurement_events/PostHog; execute читает ClickHouse и проверяет существование
  трёх PostgreSQL tables. Нет graf-local scope и activation_milestone_decisions;
  такой receipt нельзя использовать для локального периода.
- Source retention.service вызывает этот старый shell --execute. Source backup/
  restore services вызывают PostHog helpers. Их UTC calendars не меняют смысла
  вызываемого кода и не создают локальные GRAF backup/rehearsal receipts.
- `local_retention_database_catalog` реально проверяет четыре local policies,
  tables/routines/triggers/ACL и отсутствие scheduler extensions/schemas **в
  текущей БД**. Это ещё не доказательство всего кластера/host schedules.
- Пишущие product maintenance loops существуют внутри текущего контейнера:
  account closure, deletion reconciliation и другие операции не обязаны иметь
  systemd timer или cron-строку. Их нельзя пропустить, перечислив только timers.
  Допустимые продуктовые удаления и сроки сессий/аудио не равны age purge
  аналитических четырёх категорий и не должны отключаться этим аудитом.

Сообщённые основным исполнителем серверные факты приняты как ограниченный
контекст, лично reviewer их не перепроверял: установлен только runtime guard;
PostHog backup/restore/retention timers отсутствуют; проверены два пользовательских
crontab, найдены три задания без прямых продуктовых слов. Их команды, аргументы,
закрытые пути и содержимое здесь намеренно не воспроизводятся. Это **не**
доказательство отсутствия косвенного доступа к GRAF или всех scheduler roots.

## Блокирующие находки scoped analyze

| ID | Тип / важность | Где | Пробел | Минимальное устранение |
| --- | --- | --- | --- | --- |
| J1 | Недостаточная определённость / HIGH / P1 | full-operator-design §Local retention; plan §Полный оператор; текущий `_runtime_guard_units` | Не названы конечный inventory scheduler roots, trusted expected contents/граница не-GRAF jobs и проверяемая цепочка indirect execution. Принять self-hash/keyword absence означало бы круговое доказательство | До кода зафиксировать небольшой installation-specific allowlist и метод полного native discovery; неизвестный путь/делегирование/состав остаётся HOLD. Проверять bytes и effective calls, а не разбирать произвольный shell |
| J2 | Неполнота охвата / HIGH / P1 | full-operator-design §Local retention; `local_retention.py:293–297`; `_runtime_databases` | Absence pg_cron/pgagent/timescaledb в twobrain_rec не исключает scheduler в другой БД того же PG-кластера и cluster background preload | Зафиксировать поддержанный закрытый PG17 cluster inventory и actual preload/config/DB coverage до reduced source; unknown/другая DB/невозможность чтения запрещают proof |

Это проектные пробелы именно следующего полного proof. Уже принятые узкие
catalog/staging/guard проверки не объявлены ошибочными или полным T113 PASS.
Текущая намеренно отсутствующая реализация backup/verify сама по себе не новая
находка P1: это известная зависимость следующего цельного этапа.

## Минимальный конкретный алгоритм без общего parser

1. **Один fixed installation, один trusted оператор.** Переиспользовать
   существующие bootstrap/source snapshot/frozen uv, deployment lock,
   filesystem fence и reduced DB. Не принимать от CLI expected hashes,
   pass-file, SQL, arbitrary command или новый cutoff. В source задать небольшой
   закрытый expected набор идентификаторов/байтов/метаданных установленного
   продуктового scheduler, а не отдельный универсальный движок правил.
2. **Полный native discovery конечных входов установленной платформы.**
   Зафиксировать, какой именно cron/systemd установлен и какие файлы он читает:
   системный crontab, cron.d, подключаемые run-parts/anacron roots, user spool
   и user systemd roots субъектов с доступом к продуктовой установке/credentials/
   Docker. Проверить также наличие иных отложенных исполнителей этой установки:
   активный/доступный at или иной незнакомый scheduler не молча пропускать.
   Systemd discovery охватывает unit files и loaded/transient/generated state,
   а не только list-timers или файлы с префиксом graf. Фиксируется известная
   платформенная граница; читать всю файловую систему или строить анализатор
   произвольной ОС не требуется. Недоступный/неполный/неизвестный вход — HOLD.
3. **Сравнить с независимо проверенным expected набором.** Установленные GRAF
   units/scripts сравнить с pinned source. Посторонние задания классифицировать
   по фактически прочитанной цепочке executable/interpreter/config/hooks и
   её доступу к GRAF, а не названию. Для немногих известных administrative jobs
   достаточно отдельного закрытого ручного разбора и закрепления целого
   конечного набора digests/metadata в trusted installation policy, привязанной
   к source/review. Raw scripts/argv/секреты в Git не переносить. Не выводить
   expected digest из той же непроверенной установки и не считать digest
   доказательством семантики. Dynamic download/eval/изменяемые hooks или
   неизвестный transitive target остаются HOLD до конкретного решения, без
   самовольного отключения соседних задач. Доверенные ручные root-действия в
   обход оператора остаются прежней границей; известное периодическое root
   задание нельзя выдать за ручное действие и исключить из проверки.
4. **Нужен лишь точный шаблон собственной cron-строки.** Существующие чужие
   crontab/config можно проверять целыми bounded bytes/digests после review;
   не нужен общий синтаксический parser shell/cron. Свой canonical entry должен
   однозначно задавать root/fixed argv/frozen entrypoint/deployment lock и
   03:10 UTC. Семантику UTC подтвердить на фактической реализации scheduler:
   CRON_TZ не предполагается поддержанным только потому, что присутствует в
   файле. Подмена окружения, неизвестная timezone, duplicate/extra call дают
   HOLD. Глобальную зону сервера ради proof менять не требуется.
5. **Source bytes плюс effective state.** Для продуктовых systemd units
   переиспользовать строгое чтение FD/path/ancestors/ACL и native typed busctl,
   фактические argv/ExecStartEx flags/env sources/dropins/credentials/прочие
   команды, enable/active/loaded state и UTC calendar. Удержать proof до/после
   DB read/последнего await. Для cron закрепить executable/config generation,
   весь набор entrypoints и identities до/после; ошибка команды не означает
   «пустой crontab». Объём/число файлов конечны, links/неподдержанные формы/
   extra job/подмена после yield закрывают успех. Raw outputs не публикуются.
6. **Весь PG-кластер, а не одна schema.** Через уже доверенного owner в postgres
   получить реальный `pg_database` inventory и actual shared/session/local
   preload и scheduler-relevant effective settings/overrides. Поддержать только
   конкретно проверенный чистый PG17 набор без background scheduler; unknown
   preload/extension/library либо дополнительная непроверенная DB — HOLD.
   Если выбран подход inspection каждой DB, перечисление/права/физические
   подключения должны покрывать все потенциальные scheduler DB, включая
   postgres/template/закрытые цели; невозможность чтения не значит absence.
   Нельзя временно открывать закрытые БД ради read-only preflight. Минимальнее
   строгий известный набор и отказ неизвестного, чем executor чужих job SQL.
   Результат связывается с cluster ID/PGDATA/roles/schema/source до/после.
7. **Product purge покрывается code/runtime closure.** Переиспользовать exact
   writer container/image/command/source/config/roles binding. Сопоставить
   реальный maintenance/API/account-closure dispatch с известными source
   операциями удаления четырёх категорий; доказать, что age-based путь для них
   отсутствует, а exact decision/withdrawal/account deletion остаются рабочими.
   Existing shared lifecycle reader/replay + current register проверяют coverage,
   результаты/сроки и остатки. Нельзя заменить это grep DELETE или отсутствием
   cron; неизвестный worker/Temporal task/подменённый образ закрывает proof.
8. **Один общий local retention результат.** Fixed graf-local ветвь существующего
   shell делегирует тому же trusted host entrypoint, который ordinary verify
   использует online. Сам core работает на удержанной reduced source, в том
   числе при закрытой DB без reconnect. Ровно четыре категории из
   LEVEL_RETENTION_CATEGORIES, until_decision/None, actual catalogs/access,
   lifecycle/disposition и полный installed-job proof. ClickHouse/Yandex и
   provider calls отсутствуют. Проверка не удаляет данные ради испытания.
   Receipt строится только из выполненных проверок: category/policy/schema/
   cluster/source/register/jobs digests, окончание и result; без content/IDs.
   Freshness0≤age<26ч; после restore/code/schema/job invariant change прежний
   receipt недействителен. До initial/T0 всё равно нет writer-ready.

Выбор точного supported platform inventory, expected nonproduct closure и
подхода cluster inventory должен быть записан исполнителем перед кодом.
Этот список задаёт минимальную форму решения, а не утверждает, что нынешние
три чужих задания или текущая ОС уже прошли такой разбор.

## Следующий цельный этап, который даёт рабочий путь

Нужен **полный доверенный цикл локального периода**, а не ещё один автономный
jobs helper. В той же T113 соединить уже принятые функции в actual
preflight → initial/backup/verify/restore, durable attempts/manifests/rehearsal,
local retention/resource/access receipts и admission/CD gates по полному
алгоритму. Внутренние функции допустимо писать последовательно, но готовность
принимается только сквозным сценарием; общий unconditional blocker до этого
не снимается.

Для ежедневного пути конкретная цепочка должна быть явной:

- 03:10 UTC: собственная canonical host cron запись → pinned bootstrap →
  **реальная** planned coherent backup со stop/drain/export, проверкой минимума
  двух полных комплектов, cleanup/безопасным resume/последней попыткой;
  не --preflight. Две новые копии обязательны для initial; далее создаётся новая
  копия с сохранением установленного минимума, а не две новые каждую ночь.
- 03:15 UTC: переиспользуемый существующий retention scheduler и fixed graf-local
  shell scope → **реальная ordinary verify**, без остановки продукта: fresh
  backup/при необходимости rehearsal/local policy+jobs+lifecycle/resource/access,
  финальное readback и сохранение той же initial/T0. Конкретный argv/source и
  порядок блокировки фиксируются до установки; нельзя просто включить прежний
  PostHog service и рассчитывать на новое поведение.
- До первой T0: полный initial/provisioning, две доказанные копии, проверка
  восстановления и возврата продукта. До открытия writer: supported actual
  restore и runtime/schema CD revoke/drain тоже реализованы и испытаны.
- Нагрузка/пауза/клиентский повтор и место до stop принимаются отдельно, затем
  один exact-SHA выпуск, установка только своих entries, наблюдение реального
  исполнения и свежих receipts. Отсутствующий timer или CLI оставляет runtime
  HOLD, не превращается в успешный пустой список.

Новых daemon/service/ролей/пакетов/общего scheduler framework не требуется.
PostHog исторические schedules/receipts сохраняют собственный scope; они не
доказывают local_only и не требуют ненужного запуска для его приёмки.

## Обязательная причинная проверка после уточнения проекта

До кода RED на каждый закрываемый пробел. Изолированные Linux/PG17 испытания:
extra/indirect job без слова GRAF; unreadable/частичный список; заменённый
executable/hook/config/loaded unit; duplicate scheduled call; изменение после
проверки; cron UTC/DST/native semantics; pg_cron в другой DB/неизвестный preload;
неизвестный worker/image; age>365/1095 без удаления; точный отдельный case и
account deletion с сохранностью остальных; замена restored receipt; future/
26ч/missing categories; cancellation/reap/locks и отсутствие ложного PASS.

Сквозная проверка должна вызвать настоящий scheduled argv через доверенный
entrypoint, получить полностью вычисленный receipt, затем тот же ordinary
verify/admission; no supplied-pass. Для negative случая запрещён ready, но
продукт и обязательное удаление не блокируются обычным analytics HOLD.
Рабочие jobs/DELETE для теста не запускаются. Tests personally run by reviewer:0.

## Scoped analyze: покрытие и пределы

Использован `speckit-analyze`; prerequisites подтвердили F273. Установленный
script не поддерживает --require-spec, поэтому использованы --require-tasks
--include-tasks и отдельно проверено наличие spec. Before/after analyze hooks
явно disabled; меняющие состояние hooks не запускались.

| Требование | Покрывающие существующие задачи | Что требуется здесь |
| --- | --- | --- |
| FR-033/034/035 | T110/T113 | Реальные scheduled backup/verify, distinct manifests/receipt/freshness |
| FR-036/050 | T109/T113 | Полный actual jobs/TTL/local policy proof,0≤age<26ч |
| FR-038 | T100/T113 | Pinned source и effective installed code/config |
| FR-048 | T111/T113 | Точный case/deadline/result и обязательное удаление |
| FR-032 | T113/T116 | Обычный HOLD не ломает продукт и не разрешает удалять историю |

Прямой scope8 FR,8/8 имеют существующие задачи; новых непокрытых задач0,
дублирующих задач0. Implementation coverage этим числом не утверждается.
Открытых design ambiguity2, HIGH2, CRITICAL0. Противоречий конституции нет;
недостающие алгоритмы нельзя закрыть ослаблением FR-036/050.

Все117 вопросов оценены заново. Здесь особенно применимы privacy CHK031–038,
security CHK010–015/021–024, infra CHK003–009/016–025: их требования ясны и
сохраняются, реализации/полнота installed proof не приняты. Остальные пункты
сохраняют основания ранее полностью прочитанных неизменных контрактов;
новых категорий/получателей/согласий/атрибуции этим проектом не вводится.

## Сохраняющиеся HOLD

`full_preflight_not_implemented`, `activation_recovery_unverified`, T113/#7804,
T112 и AC01–AC06 открыты. Рабочие protection v1 migration/history, installed
jobs, полный upper operator/restore/resume/CD, место для2полных копий+restore+
staging, ресурсный бюджет/фактический остаток ниже20%, права trusted установки,
двое операторов/MFA, ready/T0/IP/получатели и exact-SHA CI/Full/выпуск отдельно.
Новый runtime успех/трафик/продажи данным разбором не заявляются.

## Снимок источников

Неизменные baseline повторно сверены в пределах разрешённого владельцем
исключения F273; затронутые целые разделы и все117 вопросов перечитаны.

| Файл | SHA-256 |
| --- | --- |
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current-product-status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `specs/273-paid-traffic-analytics/spec.md` | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| `specs/273-paid-traffic-analytics/data-model.md` | `488833fcc4b8e4841672485b35cfa0161e1f02983d10ad98b52eb71d55bb55f5` |
| `specs/273-paid-traffic-analytics/plan.md` | `1dc9dc7019e81e4166de9ea636e64eacfad81da67d101566a75c134894bb370f` |
| `specs/273-paid-traffic-analytics/tasks.md` | `adf455dfba084d14618bde48953cbd958b950971ba6b22a9fc83581daf2fc7f4` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `a6d742666e14cea1a4940f0f00ed71438c7848d17da73b4fd8a25b32bdf665d9` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `aa4536d6e082f9c830c342013c9ef4de5fc2f914a2e6cea6911521c613f6df95` |
| `validation/t113-full-operator-design-20261030.md` | `5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec` |
| `infra/scripts/activation-operator.py` | `e11efddb4001602014977be3dff5e86550978cf81bfe67f23d7ae60a0bdfbfb5` |
| `infra/scripts/enforce-product-analytics-retention.sh` | `ab367e1af976707fbc8cff91368e7fbba3b7308db0b2ae856de904587e2a6dcd` |
| `activation_operator.py` package | `b086459d5f3a2a16571041cc96c7120543a6ebfed3dd1ae4887a0a7405ea4ced` |
| `local_retention.py` package | `a9e50827c463800957738ba0192b6fe9d4c38f5c9c3541428ee5a6b89b0661b6` |
| `activation_fence.py` package | `142fcacf6f5a43c9fc2358b197245e7ef312ed57b0c3dd4dd2ad1f6da17e902b` |
| `workflows/maintenance_worker.py` | `8e5ae2d4928f732a784cefabbf7da42b2b9435d7e668a091963ff335a10c1417` |
| `workflows/worker.py` | `376820913dfd73477d25cb07945ebbc9547772126758fa1ab1e59a70881d2ba7` |
| `infra/docker-compose.yml` | `9098cb15c8c4a675beae529664e128d46a2dc50671dee8171d05b659b482bcc6` |
| retention service | `0430c51e9a1d94d7e5b86985fc397a4c8a1158214726ff202ffd504c4790e826` |
| retention timer | `a7b17e7f1244dc33e98f1a1e4de3315c4b4a2113b2bb616506f6046212bcc521` |
| checklist requirements16/0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| checklist privacy45/0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| checklist security27/0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| checklist infra29/0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
