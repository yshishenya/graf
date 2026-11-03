# Независимое ревью проекта F224/T010 — 26.10.2026

Роль: независимый reviewer требований, до кода. Ветка codex/224-promotion-recovery,
основа8037c448935441051998995c7a5444a4f9a549ad. Текущий итог повторного прохода:
**PASS качества проекта US3**; requirements16/0, infra28/0, замечаний0.
Первый проход был BLOCK: infra24/4; R1–R4 устранены в договоре до кода.
Историческая US1 не является приёмкой новой US3.

## Границы и источники

Прочитаны AGENTS.md, guidance index, spec-kit-flow, product-gates, local-development,
release-and-validation, конституция7.1.0, активный pointer, восемь входных документов
ниже, оба checklist, обычные promote/rollback и связанные функции dev-harness.py,
startup/installer scripts. Проверены исходный probe.py/results.json и
lock-probe.py/lock-results.json из внешнего каталога graf-f224-crash-recheck.
Это чтение кода и имеющихся результатов. Новые процессы приложения, тесты,
Docker/Swift/сеть и изменение Git/GitHub не выполнялись. Reviewer меняет только
два checklist и этот отчёт.

Имеющийся SIGKILL probe выполняет настоящий control flow, но подменяет внешние
действия. Он доказывает рассогласование ordinary promote на трёх границах,
не причину отсутствия настоящего Dev. Lock probe на darwin подтверждает
наследование flock между Python-процессами, не работу настоящего installer.

## История первого прохода: устранённые замечания R1–R4

1. **R1/HIGH: достижимость обещания при снятии квитанции (CHK023).**
   Contract §Публикация обещает видимый marker при любой ошибке снятия.
   Но unlink может успешно убрать имя, а следующий fsync каталога — отказать.
   Минимальное исправление: явно определить commit point как проверенный
   durable manifest/pointer и допустимые исходы удаления. Если marker остался,
   status остаётся recovery-required до повторной проверки. Если после уже
   доказанной публикации marker отсутствует, согласованный target допускается
   с предупреждением; не обещать восстановление файла при невозможности записи.
   Добавить отрицательные сценарии до unlink и после unlink/до fsync.
2. **R2/HIGH: не задана запись идентичности контроллера (CHK022/024).**
   Состав operation перечисляет пути controller, но не controller PID/start token,
   хотя startup guard должен проверять его принадлежность. Минимально включить
   эти поля, правила проверки живости/времени старта и обновление при повторе
   только под общей блокировкой. Новый PID не подменяет target/controller SHA.
3. **R3/HIGH: frozen компенсация может обойти новый путь (CHK023/024/026).**
   Недостаточно направить только subprocess через новый helper. Старый
   _restore_app удаляет backup средствами shutil; старый _restore_runtime
   вызывает старый self._start_backend; текущий метод на старом self также
   может динамически вызвать старый _atomic_swap_dev_app/_start_backend.
   Минимально перечислить текущие тела всех изменяющих методов, включая
   вложенные вызовы и файловую компенсацию. Можно явно вызвать текущие
   unbound методы с проверенным adapter и его путями/окружением. Нельзя
   monkeypatch/rebind/редактировать globals или bytes frozen module.
4. **R4/MEDIUM: текущий smoke не доказывает installed bytes/signature (CHK023).**
   Он читает plist и службы. Минимально явно использовать существующий
   _validate_launch_bundle(chosen, DEV_APP_PATH) для целевого и восстановленного
   установленного пакета до снятия квитанции. Новая подсистема не требуется.

Малое фактическое замечание первого прохода: quickstart говорил, что профильный test-файл
добавляется позднее, но он уже существует с тремя статическими проверками.
Следует написать, что файл будет дополнен исполняемой crash-матрицей; нынешние
проверки не доказывают новый contract.

## Основания requirements16/0

| Пункт | Основание текущего качества требований |
|---|---|
| Q001 | US1–US3 описывают результат; алгоритм квитанции находится в contract/plan |
| Q002 | Каждая история содержит Why this priority и независимую проверку |
| Q003 | Русское описание результата; точные технические идентификаторы сохранены |
| Q004 | Stories, edge cases, FR, entities, SC, assumptions, clarify заполнены |
| Q005 | Текущая clarify26.10 опирается на поручение владельца; продуктовых вопросов нет |
| Q006 | FR008/016 и assumptions сохраняют один Dev, отсутствие обходов |
| Q007 | SC003 задаёт реальный SIGKILL, повтор, данные, inode и определимые результаты |
| Q008 | FR012 задаёт конечный результат; фаз/новой схемы в требованиях нет |
| Q009 | US1–3 содержат положительные и отрицательные acceptance scenarios |
| Q010 | Edge cases содержат origin/path/concurrency/неполное состояние/процессы |
| Q011 | FR017/018 и T009–013 сохраняют широкий #6180 |
| Q012 | Assumptions и quickstart отделяют доступное исследование от live gates |
| Q013 | Requirement coverage связывает FR/SC с задачами, T010 остаётся открытой |
| Q014 | US3 scenario4 добавляет обе обычные операции и прерывание после публикации |
| Q015 | Status/spec/plan и quickstart различают US1, проект и будущую реализацию |
| Q016 | Восстановленное происхождение документов явно указано, новой готовности нет |

## Исторические основания первого infra24/4

| Пункты | Доказательство |
|---|---|
| CHK001–003 | Contract state-ownership §Канонизация/Одноразовое принятие; spec FR001–003/006–007 |
| CHK004–008 | Data-model и state-ownership задают неизменный root/inode, порядок lock, recheck и атомарный binding |
| CHK009–012 | State-ownership §Обычные операции/Проверки отказа: исходные пути, callers, fixture boundary, status snapshot |
| CHK013–014 | State-ownership §Закреплённые адаптеры и research ограничивают frozen resolver и самостоятельный старый controller |
| CHK015–020 | T009–013, spec FR008–018, quickstart и plan сохраняют runtime/schema/TCC/CI и индивидуальную приёмку |
| CHK021 | Новый contract включает promote, rollback, first install и повтор после pointer без idempotent bypass |
| CHK022 | **Не отмечен:** R2 — состав controller identity не определён |
| CHK023 | **Не отмечен:** R1/R3/R4 — снятие marker, потребление backup и доказательство установленного пакета |
| CHK024 | **Не отмечен:** R2/R3 — текущий controller и frozen вложенные мутации ещё не определены |
| CHK025 | State-ownership таблица + новый contract охватывают CLI, direct adapter retention/build, smoke/status/startup/fast return |
| CHK026 | **Не отмечен:** сохранён приоритет схемы, но R3 требует явного достижимого frozen пути |
| CHK027 | Contract §Матрица задаёт реальные процессы/handshakes/SIGKILL, данные/inode, ошибки и отрицательные identities |
| CHK028 | Plan US3/quickstart/research отделяют mechanism probe, design gate, regression, PR checks и live T009/011/012 |

## Ограничения реализации

_same_manifest_identity пригоден для rebuild и намеренно не сравнивает digest,
app_identity, boundary и lineage. Его одного недостаточно для точной цели
восстановления. Сопоставление receipt/manifests должно сохранять все immutable
поля и разрешать только предусмотренные status/health/promoted_at различия.
Реальный installer/Compose/lifecycle должен получить собственную проверку
наследования lock; Python research сам этого не доказывает.

Повторное независимое ревью проекта завершено; до кода остаются analyze/sync.
Этот отчёт не является implementation PASS, CI evidence, live приёмкой, выпуском
или основанием закрыть T010/#7641 либо #6180.

## Хеши прочитанных входов SHA256

- `spec.md`: `edf28827b21e7c29fadcf58533d0db3e53d1ec0ee03a17ad7d2ebe6001b88fdc`
- `plan.md`: `cd8f4da5d89b35cce70adfd6087be7bec4d84f28da103ad7d3261d14c662b59c`
- `tasks.md`: `d17a7f27f2d695fb00507c89b41c81048d62a9095ce85cf48bec5422247bf087`
- `research.md`: `685e8e5a7092b1b9b9400016565715cf07325efb6035b5b1525c68e68e32a675`
- `data-model.md`: `f65c50320ebfd6254427311eebcbafa6f779ab37e5a5cb6f22c917557bd759f3`
- `quickstart.md`: `6dce4a6de8c780af6a2c540aff48dc0d423c053a612003e909270dd2d2b8440a`
- `contracts/promotion-recovery.md`: `83f9b55da02ffbfb3b9cc6d77a7b515dc6cab912064712f44dc82e141815e55c`
- `contracts/state-ownership.md`: `ee4d3d6e618dd83f5ce414edc70f15c403688434180532e04f3fdcb35e38018d`


## Повторное ревью: фактические основания снятия R1–R4

Полностью перечитаны четыре обязательных документа: конституция, PRD, текущий
статус и product-gates. Также перечитаны AGENTS/index/document-reading,
spec-kit-flow/local-development, применимые разделы release-and-validation
(Local Validation, Validation Lanes, Development-To-Release до Release candidate,
Git Safety, Evidence Safety), восемь документов F224 и оба checklist.
Повторно просмотрены реальные тела lock, checkout adapter, startup gate,
startup guard, snapshot/restore, установленная проверка подписи и публикация.
Совпадение хешей подтверждает версию входов; не является выполнением продукта.

- R1 снят: договор §Публикация отделяет долговечный commit point от удаления
  имени квитанции. Остался marker — повтор; unlink прошёл, fsync отказал —
  согласованный доказанный результат с предупреждением без очистки. Для
  компенсации действует тот же порядок. Невыполнимого обещания восстановить
  marker при ошибке записи больше нет; обе границы входят в матрицу.
- R2 снят: §Одна существующая квитанция/Повтор явно задают controller PID и
  start token, проверку живости, обновление только под прежним lock после
  завершения прежнего контроллера. Target/SHA/checkouts при этом неизменны.
- R3 снят: §Процессы создаёт новый экземпляр текущего GrafLocalAdapter с
  verified root/state. Все тела Python и вложенные self-вызовы принадлежат
  текущему классу; перечислены файловая компенсация, restore runtime,
  launch/stop/install, registration/archive/retention. Frozen object нужен
  только для проверки источника/resolver. Динамический вызов старого self
  исключён; globals/bytes старого модуля не подменяются.
- R4 снят: для target и восстановленного previous обязателен существующий
  _validate_launch_bundle(manifest, DEV_APP_PATH). Его тело действительно
  проверяет полный tree digest, codesign и signing identity/requirement/
  entitlements, дополнительно к plist/channel/SHA. Smoke это не подменяет.
- Малое замечание снято: quickstart верно называет существующий test-файл
  и три статические проверки; исполняемая матрица ещё должна быть добавлена.

По исходникам подход достижим без новой подсистемы: текущий конструктор
GrafLocalAdapter(root,state) задаёт пути из проверенной рабочей копии, а
вложенные self-вызовы нового экземпляра используют текущий класс. Существующий
SCHEMA_STARTUP_GATE ждёт байт и делает exec; _start_backend уже пишет runtime
до байта для схемной операции. Новая обычная проверка до байта может быть
добавлена в текущий Python, тогда как закреплённый shell запускает собственный
schema-start-guard без изменения bytes. _state_file_lock закрывает fd без
явного unlock; отдельный child с унаследованным fd может удерживать прежний
flock. Это оценка достижимости проекта, а не тест новой реализации.

## Итоговая поштучная сверка infra28/0

| Пункт | Основание принятия качества требований |
|---|---|
| CHK001 | State-ownership §Канонизация задаёт формы origin и отказ credential/ambiguity |
| CHK002 | Spec US1/FR001–002 и contract связывают clones/worktrees по repository |
| CHK003 | Research/contract требуют доказательства исторического владельца, SHA недостаточно |
| CHK004 | Data-model/FR006 сохраняют manifests/runtime/journals/data/secrets/archives/inode |
| CHK005 | Adoption требует отказа неизвестных roots и явно ограничивает scan overrides |
| CHK006 | Порядок registration→operational; единственное право мутации остаётся promote.lock |
| CHK007 | Contract требует повторной проверки binding/active/parent после ожидания |
| CHK008 | Data-model/contract определяют один binding и безопасный повтор до/после публикации |
| CHK009 | Adoption preflight требует проверки исходных path/type/owner/symlink до записи |
| CHK010 | Таблица обычных callers и T005 включают startup, build, prune и direct adapter |
| CHK011 | Fixture не управляет общими Docker tags или canonical state |
| CHK012 | FR011 и contract явно отделяют status snapshot, fixture и live evidence |
| CHK013 | Checkout contract сохраняет clean/SHA/tracked bytes/digest/resolver до воздействия |
| CHK014 | Research/contract ограничивают защиту от самостоятельно запущенного старого controller |
| CHK015 | FR008–018/T009–013 сохраняют runtime/lifecycle/schema/TCC с отдельной приёмкой |
| CHK016 | Research воспроизводит ordinary SIGKILL; F249 T038/#6786 остаётся владельцем миграции |
| CHK017 | Quickstart/T012 задают Dev-only before/update/relaunch/after без reset/второй копии |
| CHK018 | Research/T013/FR017–018 сохраняют версии evidence и широкий #6180 |
| CHK019 | Quickstart задаёт реальные процессы, ранние отказы, данные и inode без shared effects |
| CHK020 | Plan/quickstart различают US1, новый US3 gate, PR exact SHA/base, fast и release-full |
| CHK021 | Recovery contract включает promote/rollback/first install, повтор после pointer и запрет fast bypass |
| CHK022 | Полная квитанция, immutable manifest compare, PID/start token, чужой/старый формат и target дают определимый отказ |
| CHK023 | До stop готовятся backup/receipt; backup не потребляется; target/previous bytes проверяются; commit/unlink/fsync определены |
| CHK024 | Короткий child наследует held fd; долгий backend ждёт byte после fsync runtime; текущий класс владеет всеми мутациями |
| CHK025 | Общий запрет охватывает CLI/direct build/retention/prune, cleanup, status/smoke/startup/idempotent |
| CHK026 | Schema recovery имеет приоритет; frozen источники/resolver/guard остаются точными; старые мутации не вызываются |
| CHK027 | Матрица содержит реальные SIGKILL/retry/child/lock и ошибки записи/очистки/identity, данные/inode |
| CHK028 | T010 отделён от mechanism probe, независимого проекта, регрессии, PR и live T009/011/012 |

Все Q001–Q016 повторно сверены по таблице выше и текущему spec;16отметок
сохранены. После изменения checklist снова прочитаны целиком: requirements
16отмечено/0неотмечено; infra28отмечено/0неотмечено; всего44/0.
Открытых замечаний к качеству текущего проекта нет. Lane: high-risk-product,
независимое ревью проекта до реализации. До кода обязательны чистый analyze и
синхронизация существующей #7641. Изолированная новая crash-матрица, независимое
ревью кода/converge, три текущих PR-проверки и реальная приёмка T009/T011/T012,
F249 T038 остаются будущими воротами. T010/#7641 и общая #6180 не закрываются.

## Дополнительные хеши прочитанных источников SHA256

| Источник | SHA256 |
|---|---|
| AGENTS.md | 24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958 |
| Guidance README | 2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb |
| document-reading | 5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411 |
| spec-kit-flow | afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e |
| local-development | 904745b03ca97ac28f76b92cc056ad7936f7051b3a2ae7910bfb3e02cd55f356 |
| release-and-validation | ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f |
| Constitution7.1.0 | 7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8 |
| PRD | 0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2 |
| Current product status | 25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16 |
| product-gates | 9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5 |
| scripts/dev-harness.py | 4d396a1ab7c3a7abaaee9b9f0cb97eca9872483ded9d81a1d18afdc545a31d50 |
