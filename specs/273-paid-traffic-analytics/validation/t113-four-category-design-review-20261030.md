# F273/T113: независимый проект lifecycle четырёх локальных категорий

Дата: 30.10.2026. Проверяющий: `f273_release_boundary`.
База: `7b83ec21998cc24c2d4dc8a59a9d2c2edfcebe65`, ветка
`codex/f273-local-period-20261029`, F273/T113/#7804, `high-risk-product`.
Проверка выполнена до изменения кода. Назначение и precode прочитаны.

## Решение и границы

**SCOPED DESIGN / ANALYZE PASS** для алгоритма ниже. Неразрешённых P1/P2
в описанном алгоритме нет. Это разрешение реализовать согласованное изменение
существующей T113 и предъявить код/тесты на отдельную проверку. **Реализация,
полная готовность, T113/#7804, рабочее включение и выпуск остаются HOLD.**

Проверен конкретный `.dev/growth/t113-four-category-precode-20261030.md`,
SHA-256 `c4fa23863fb9ae82cde073bf563e082808e4288d2c83e69d6cfb931c14ce111d`,
включая принятые уточнения об acquisition metadata и точном account-удалении:
отдельный аккаунт не даёт основания очищать всю категорию других аккаунтов.

## Требования и найденные пробелы исходной реализации

1. FR-048 (`spec.md` 574–579) прямо разрешает удалить либо обезличить затронутые
   данные. `retention.py` 230–241 допускает delete or anonymise acquisition,
   а модель (`db/models/product_analytics.py` 233–280) хранит его отдельной
   строкой с FK на `user_identities`. Контракта, обязывающего сохранять именно
   эту строку после обязательного удаления, не найдено. Удаление acquisition
   сохраняет сам аккаунт и укладывается в существующий scope T109/T110/T111/T113.
   Отдельное решение, охват, ответственный, срок и результат остаются обязательны;
   это не возрастная очистка и не разрешение немедленно удалять рабочую историю.
2. **Пробел исходной реализации P2:** `CATEGORY_DISPOSITIONS` выбирает anonymise,
   а `apply_basis_loss_disposition` (`legal_basis_lifecycle.py` 122–129,760–768)
   обнуляет лишь шесть campaign полей. Сохраняются `account_id`, `landing_path`,
   времена и `graf_attribution_id`. Миграция `0096_client_attribution_bridge.py`
   1–9 прямо относит bridge к той же категории. Тест
   `test_product_analytics_legal_basis_erasure.py` 187–206 подтверждает сохранность
   строки/связи и потому не доказывает полное удаление категории. Сохранённая
   связь не может быть названа полным обезличиванием по `spec.md` 163–166 и
   `legal-basis.md` 55–59. Выбор DELETE всей отдельной acquisition-строки устраняет
   этот пробел без сложного нового механизма обезличивания.
3. **Пробел исходной реализации P2:** `finalize_account_close` 430–445 удаляет
   только ledger, затем сохраняет `user_identities` со status=closed; acquisition
   FK без ON DELETE CASCADE не удаляет связанную строку. Нужен общий точный
   acquisition DELETE helper, вызываемый finalizer и replay. Это ещё не существующий
   готовый helper: его необходимо реализовать. Ledger count/time не доказывают
   исполнение acquisition удаления.
4. Действующий v2 parser принимает только account_closure и ledger category
   (`legal_basis_lifecycle.py` 486–545); replay 141–169,271–310 и source operator
   775–786 охватывают только ledger. Новый parser без одновременного изменения
   исполнителей сделал бы новые случаи молча неисполненными. Предложенный единый
   выпуск parser/coverage/исполнения/сверки закрывает этот проектный риск.

Предыдущие approvals, отчёты о двух scopes и тесты шести NULL не подтверждают
новую реализацию. Исторические отчёты сохраняются; действующие plan/contracts,
описание реестра, retention metadata и тесты должны говорить о выбранном DELETE.

## Минимальный согласованный алгоритм

### Карта категорий и разбор реестра

Один закрытый перечень четырёх category/table: ledger,
anonymous_page_aggregate, visit_attribution, client_acquisition_attribute.
Переиспользовать его в catalog/parser/replay, без значения SQL из произвольного
operator input. Не вводить циклический импорт `legal_basis_lifecycle` ↔
`local_retention`: карта может жить в маленьком модуле без ORM и этих импортов.

Разрешены только account_closure с каноническим UUID запроса и четыре категории
с selector=all. Сохраняются строгие поля, уникальность case/decision/scope-selector,
owner/reason/time/result validation, отказ failed и неизвестным scopes. Каждый
потребитель должен распознать и обработать новую категорию либо отказать:
`read_basis_withdrawal_register`, `replay_accounts`, `source_replay_accounts`,
`reconcile`, `_backup_lifecycle`, `_runtime_operations`. Потребитель только
синтаксической проверки не становится исполнителем удаления.

Withdrawal anonymous_aggregate требует aggregate-case; attribution_profiles
требует acquisition+visit+ledger cases, даже при пустых таблицах. Данные уровня3
и provider withdrawal не объявляются исполненными локальными запросами:
текущий scope ограничен четырьмя локальными категориями и не даёт общей readiness.
Разбор provider withdrawal должен сохранять его силу и явную границу покрытия.

### Исполнение и результат закрытия аккаунта

CATEGORY_DISPOSITIONS acquisition становится DELETE, его local SQL удаляет
отдельную строку полностью; `user_identities` не удаляется. Один account helper
удаляет только `ClientAcquisitionAttribute.account_id == account_id`, не делает
COMMIT, не выполняет category/all и возвращает отдельный count. Finalizer
использует прежнюю identity/deletion блокировку и одну transaction для ledger,
acquisition, состояния completed и двух отдельных purge-results. При ошибке
второго удаления первое и completion откатываются вместе. Сериализация с
пишущими путями и запрет восстановления строки закрытого аккаунта остаются
обязательным свойством account lifecycle; не объявлять одного FK достаточным.

CLOSURE_ROWS_QUERY добавляет только whitelist acquisition purge time/count/type.
Сохранённый результат валидируется отдельно: полный набор, числовой тип,
неотрицательный bounded count, aware время и
`finalize_at <= acquisition_purged_at <= finalized_at <= now`. Старый ledger-result
не приравнивается к нему. Частичный/повреждённый новый результат — HOLD.
Полное отсутствие всех новых полей у legacy completed позволяет проверить
текущее фактическое отсутствие строки, но оставляет историю/сроки unverified.

Уже completed finalizer не переписывает историю и не делает скрытое исправление
старых строк. Если legacy acquisition осталась, source-reader даёт HOLD.
**Её нельзя устранять автоматическим category/all только ради PASS одного
аккаунта.** Отдельное согласованное исполнение точного account-case может удалить
только этого аккаунта; category/all допустим лишь при собственном решении на
весь охват. Добавление рабочего repair/backfill в этот reader не требуется
и не разрешается настоящим проектом. В восстановленной учебной цели account
replay использует прежний явный account-case и оба точных helper.

### Проверка действующего источника

Сохранить строгую source-хронологию и точный completed-case coverage из
предыдущего принятого этапа. Account accepted допустим с authoritative ledger
purge-result и фактическим отсутствием ledger+acquisition; category требует
applied. Не смешивать это с разрешённым synthetic accepted intent, который
только предстоит исполнить в восстановленной цели. Сроки/count разных операций
не приравниваются; позднее applied наблюдается отдельно без deadline PASS.

Источник читается тем же reduced соединением в одной RR read-only transaction.
Catalog обычных persistent таблиц без inheritance/partition/rules сохраняется.
Closure и ledger: ENABLE/FORCE RLS, SELECT и точные одиночные policies. Ledger
predicate source-оператор по-прежнему получает из trusted rec-db-verify.py.
Для остальных трёх по миграциям0094/0095: отсутствие RLS/policies плюс SELECT.
Любое отклонение, отсутствие доступа или неполная видимость — HOLD.

Фиксированные EXISTS проверяют всю категорию при её category/all case;
ledger/acquisition также проверяются по точным completed accounts. Агрегат
и visit не сопоставляются аккаунтам по догадке: их схема такой связи не даёт.
Реестр перечитывается; наружу только безопасные количества/контрольные суммы
coverage/access и явное отсутствие исторического подтверждения.

### Повтор после восстановления

Synthetic CLI сохраняет имена/OID/ownership/password/закрытые файлы и никогда
не получает рабочие имена. Прежняя native предварительная сверка полной схемы
и ledger обязательна до него; caller сохраняет владение источником/целью и
остановку writers. В server image нет infra/scripts: новый runpy-путь к
rec-db-verify.py внутри reconcile не требуется и нарушил бы самостоятельный
образ. Новый общий access-check до чтения closure и трёх других таблиц
проверяет flags/policies/SELECT. Он не заменяет предварительную native
сертификацию ledger и не объявляется полной проверкой его функций/всей схемы.

Target snapshot всех четырёх таблиц хранится только в закрытой памяти.
Expected ledger учитывает прежний quarantine и точные удаления; expected
survivors остальных таблиц удаляют только account rows либо соответствующую
категорию/all. Category plans получают правильный level/category/deadline.
Карантин и все удаления исполняются одной transaction через общий lifecycle
и два account helper. Сравниваются полные ожидаемые survivors до COMMIT и
свежим физическим соединением после COMMIT. Недостаток DELETE/SELECT не
обходится повышением роли и не считается успехом. Потеря ответа COMMIT,
ошибка readback/очистки/изменившийся register или ownership остаются отказом
или unknown. Источник и реестр не изменяются. Внешний результат — metadata,
counts/digests и hold, без campaign values, ID, payload или SQL-ошибок.

## Обязательная проверка реализации

- Причинный RED шести NULL с ненулевым bridge и сохранённой acquisition после
  настоящего account finalizer; затем проверка полного удаления отдельной строки
  при сохранении самого аккаунта и чужих строк.
- Финализация: отдельные counts/times, атомарный rollback при ошибке второго
  удаления, повтор completed без backfill/переписывания metadata.
- Parser/все consumers: четыре scopes, неизвестный/дублирующий scope, полный
  withdrawal coverage, failed, missing case даже при пустой таблице, v1 остаётся
  допустимым для withdrawals без разрешения replay.
- Native source: остатки каждой category/all, ledger/acquisition по account,
  legacy all-absent против partial/malformed new metadata; старые сроки остаются
  unknown. Неверные policies/RLS/SELECT никогда не дают false empty.
- Native восстановленная цель: непустые четыре таблицы, отдельно каждый scope,
  общий scope, точный account, непричастные survivors, повтор после потери ответа,
  idempotence, fresh readback и отсутствие внешних отправок.
- Старые lifecycle/source/native replay/coherent backup сценарии сохраняются;
  code-review выполняется на конечных хешах после проверок. Пропуски тестов
  и прежние approvals не объявляются новым доказательством.

## Чек-листы и хеши

Все 117 вопросов перечитаны; marks не менялись. Итог 117/0 относится к качеству
требований, а не к выполнению будущего кода.

| Чек-лист | Отмечено | Не отмечено | SHA-256 |
|---|---:|---:|---|
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Сверены неизменные baseline hashes прежнего полного чтения и повторно
прочитаны применимые lifecycle/правовые разделы и зависимости по разрешённому
исключению F273. Source текущий, память других диалогов не использовалась.

| Документ | SHA-256 |
|---|---|
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| spec | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| data-model | `4dba6d438a50cfa20b06e5d8f1d1fdd7fe216f271341c95a1d4bb553e135e962` |
| operations | `7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb` |
| activation-milestones | `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9` |
| legal-basis | `f5c8b5ea1bb2a145f438069dc64b0e3816fb46496de86aecd17d02d47db3d423` |
| research | `e1e91d00165b3abafbedf061901400dbc2fc8f6fa70d994d0eeba58de3243d5f` |
| документ реестра | `db4a05ada72b400520b8bfad8fc13796998793b4fe94f5ddc6205696eebd3ebe` |

Изменён только этот независимый отчёт. Код, spec/plan/tasks, Git/GitHub,
тесты, процессы, БД/Docker/SSH, GRAF Dev и рабочие службы не изменялись.
Полный верхний оператор, actual restore/resume, executable/jobs catalog,
T112, CD, выпуск и оба общих HOLD сохраняют прежний открытый объём.
