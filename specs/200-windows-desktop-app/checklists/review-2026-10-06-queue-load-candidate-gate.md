# Round265 — REQUIREMENTS: candidate при загрузке существующего queue ledger

## Решение и границы

**SCOPED REQUIREMENTS GO**: разрешён RED и следующий source review только
предложенного разделения существующего `DesktopUploadQueueService::load` на
частный decoder и загрузку/проверку/сохранение временного candidate.
Неустранённых требований-блокеров этого предложения: **CRITICAL=0, HIGH=0**.
Это допуск требований до кода, не SOURCE approval и не выполненные тесты.

Lane: `high-risk-product`, существующая задача T116 / #7444. Рабочая копия
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, ветка
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Dirty изменения сохранены.
Единственная запись reviewer — этот новый отчёт; старые checklist markers,
отчёты, spec/plan/tasks, production, tests и GitHub не изменяются.

GO **не** разрешает считать plaintext load защищённой queue authority:
нет BOTH-index queue validator, retained protected owner, shared-budget
adoption, bootstrap reconciliation, migration switch, account/current epoch,
typed durable ticket или запуска effects по новому proof. Эти зависимости
остаются T116/T117/T118; H250, B1/legacy AAC RED257 и общая приёмка открыты.
T119/T120 также не закрываются. Отдельный класс/Snapshot, публичный uncharged
decoder, новый JSON parser/schema/target/dependency не нужны и не согласованы.

## Инструкции и независимая проверка

Лично прочитаны полностью текущие project-local `speckit-checklist` и
`speckit-analyze` skills. Применены как проверка качества требований и
неразрушающий scoped analyze, без изменения основных артефактов. Полный ранее
прочитанный AGENTS/constitution/guidance context сохранён; свежие hashes
подтверждают тот же текст. Guidance index перечитан, актуальные нормы и
относящиеся к queue части spec/plan/tasks/quickstart/data-model/contracts
проверены непосредственно. Все критерии десяти текущих normative checklists
перечитаны; исторические отчёты не подменяют их и не превращаются в новые задачи.

Поддерживаемые project prerequisite команды вернули feature200. Предписанный
skill вариант `--require-spec` не поддерживается текущим script; после отказа
использован поддерживаемый `--require-tasks --include-tasks`. Это исправленная
проверка входа, не выполнение implementation или теста. Уточнения владельца
про fresh candidate, `ledgerKnown_` и исключения достаточно конкретны;
новое продуктовое решение/новая схема не требуются.

Текущий `.specify/extensions.yml`: before/after `implement`, `analyze`,
`checklist` — **каждая** из шести стадий содержит 1 зарегистрированный
`git.commit`, `enabled:false`; на всех шести enabled=0. Hooks не запускались.
#7444 OPEN/владелец — актуальная информация main; reviewer не выполнял
самостоятельный GitHub запрос и не менял внешний трекер.

## Нормативная связь и scoped analyze

| Требование | Норма / покрытие предложением |
| --- | --- |
| Совместимость ledger, server truth/ranges/retry/identity | Spec FR-013; data-model §7; неизменный logical v3 writer/read-v2, прежний `schema_version` и filename |
| Ошибка не заменяет данные пустой очередью | Spec FR-012/013; security CHK013; custody §3/4; старое состояние сохраняется, quarantine блокирует effects |
| Полная metadata value, не частичный JSON | custody §5; временный candidate и одно принятие всех трёх vectors/document stamp после необходимых проверок и persist |
| Сохранение подтверждений удаления | Spec FR-022; T117; `purgeAcknowledgements_` принадлежит тому же принятому документу, не остаётся от прежнего load |
| Bounds до allocation и recoverable failure | custody §3: queue≤4MiB, oversized legacy blocked, не trimmed; ошибки IO/allocation не объявляются malformed content |
| Не объявлять primitive защищённым приложением | plan «Актуальный порядок» 1501–1535; tasks T116–T118; quickstart §12; owner/admission/installed/whole-pipeline gates остаются открыты |

Scoped analyze: все шесть строк покрыты существующими нормами и T116;
новых/несвязанных задач нет. Не обнаружено противоречия версии, alias,
параллельного источника truth, неразрешённого продуктового выбора или C/H
блокера **для этого подготовительного шага**. Это не переоценка полного
missing CRITICAL потока T116 и не отмена существующего общего NO-GO.

## Проверенные исходные причины

Исходный CPP135–159 очищает live items/operations/stamp и снимает quarantine
до полной проверки, не очищает purge ACK; читает весь файл через iterator до
проверки 4MiB. CPP165–352 публикует разобранные объекты непосредственно в live
vectors. Поэтому повторный load может наследовать ACK/дубликаты, а поздний
malformed объект или отказ required rewrite возникает после изменения live
projection. CPP353–374 восстанавливает uploading и переписывает v2; persist
CPP1220–1231 меняет document stamp до writer result. Это реальные существующие
места, не новая очередь и не повод копировать parser.

Проверен caller trace: единственный production load — AppMain ctor600.
`nextPending`/`pendingItems` CPP671–690 и mutation paths проверяют quarantine.
`completeLocalPurgeTask` CPP887–896 проверяет quarantine **до** использования
`hasLocalPurgeAcknowledgement` и до удаления/ответа. Getters сохраняемой
projection сами по себе не дают разрешения действовать. Startup constructor
синхронный IO этим шагом не исправляется: background readiness/typed protected
adoption остаются обязательными последующими зависимостями custody §5.

## Точные условия согласованной реализации

| Область | Требование к следующему коду / доказательству |
| --- | --- |
| Частный decoder | `bool decodeLedger(std::string_view, bool& legacy)` используется только на fresh local service candidate. Переносится существующий parser, не добавляется второй. Он заполняет только candidate, без IO/root authority/rename/stamp/persist. |
| Формат | Сохраняются существующие поля, grammar, v3/read-v2, optional ACK и server/owner/range/retry semantics. Не вводится новый строгий формат или переименование logical `schema_version` в `schema`. |
| Read bound | До resize/assign проверяются успешные seek/tell и неотрицательная длина≤4194304. Exact read обязан выявлять short/bad read и лишний байт/growth. Неудачный seek/read не означает «пустая очередь»; oversized не обрезается. |
| Whole candidate | Items, deletion operations, purge ACK и document stamp принадлежат одному целиком проверенному документу. Отсутствие ACK в новом валидном документе означает пустой candidate ACK, не сохранение старых. |
| Root check | `AtomicFileStore::isWithinRoot`/проверка package paths остаются в load, после decode, до recovery/persist/adoption. Parsed path не становится authority; existing path validation не удаляется. |
| Recovery | uploading→retry/`upload_interrupted`, v2 stamps и required rewrite выполняются на candidate только после полной проверки. Candidate использует прежние root/writer/clock; установленный тестовый clock не теряется. |
| Принятие | Все три vectors принимаются swaps и stamp присваивается только после всех проверок и успешного required persist. Live writer/root/clock не заменяются whole-object assignment. Writer callback до результата видит прежнюю live projection. |
| Known ledger | Новый `ledgerKnown_=false` становится true после успешного load существующего файла либо успешного persist. Исчезнувший **пустой, stamp0** known ledger — failure, не virgin initialization. Failed load не забывает этот факт. |
| Virgin / quarantine | Успешный missing-file путь допустим лишь для действительно неизвестной, пустой, не quarantined очереди без quarantine sentinel. Известная/nonempty projection или прежний failure не сбрасываются отсутствием файла. Quarantine снимается только после принятого валидного replacement. |
| Failure projection | Любой read/decode/root/recovery/write отказ сохраняет все старые vectors и stamp, устанавливает quarantine и возвращает false. В том числе false/throw writer при v2/uploading rewrite. Retained projection не разрешает network/recycle/purge acknowledgement. |
| Классы ошибки | Существующая quarantine rename применяется к malformed/oversized content; IO/allocation/writer exceptions — false/quarantined без rename. Сам сбой rename не снимает блокировку и не стирает старую projection. |
| Ограничение доказательства | Read cap не доказывает shared64MiB owned peak старой projection+JSON+candidate+serialization, protected two-slot authority, race-free pinned IO или typed durable commit. Их нельзя объявить выполненными по этим тестам. |

Особое обязательное место source review: `numberField` CPP66–80,
`acceptedField` CPP83–103 и stamp parse CPP253–256 сейчас используют
`catch (...)` вокруг allocating conversion/substr. Для согласованного
различения ошибок allocation exception должен дойти до non-renaming fence
load, а не превратиться в malformed JSON. Достаточно минимального уточнения
перехвата существующих helpers; новый parser не требуется. Прочитанный
`DesktopApiClient::jsonObjectFields`/JsonReader не перехватывает allocation
exceptions map/set. Ошибочные числа по прежнему отвергаются как content.

## Обязательная следующая матрица main — НЕ выполнено reviewer

- Повторный load одного ledger с ACK не дублирует/не теряет записи; валидный
  другой ledger с отсутствующим/пустым ACK убирает старые ACK.
- Malformed последний item, deletion operation, ACK или trailing tail не
  публикует ранее разобранные объекты; сохранены старые три vectors и stamp.
- Uploading recovery и read-v2 rewrite: успешный persist принимает весь
  candidate; false/throw writer сохраняет прежнее live состояние. Callback
  непосредственно проверяет старую projection до возврата результата.
- Initial unknown missing без sentinel допустим; missing после known load,
  после persist и после known пустого stamp0 ledger — false/quarantined.
  Повторный missing после неудачи не снимает quarantine; valid replacement
  может восстановить load. Старый malformed quarantine backup сохраняется.
- Exact4MiB / +1 и ошибки seek/read/short/growth/allocation проверяются
  раздельно: oversized допускает прежний quarantine rename, ошибки IO и
  allocation — нет; ни один отказ не заменяет очередь пустой.
- Invalid package root по-прежнему блокируется load; private decode не
  делает проверки/открытия файлов и не выдаёт path или effect authority.
- Quarantined old projection не выбирается для upload/deletion и не приводит
  к recycle или повторному подтверждению purge; existing v2/v3/recovery tests
  сохраняются, новая матрица идёт в существующие targets.

Нужны RED до реализации, затем actual source review, portable и применимые
native Release/Debug/SDK результаты на конечных inputs. Reviewer ничего не
исполнял в VM, не проверял устройства/профиль/installed app. Результаты
Round264 и известные all-native49/50 не являются проверкой ещё не написанного
Round265 кода; legacy AAC RED не отключается и не называется GREEN.

## Инвентарь и неизменяемые anchors

До записи: **124** checklist `.md`: 10 текущих normative файлов, **154 checked /
0 open**; отдельно 114 historical/context отчётов, **256 historical checked /
10 historical open**. Непроверенные historical пункты не переклассифицированы
как новые обязательства. Новый отчёт не содержит checklist checkbox markers.
Tasks: **120 всего /93 done /27 open**; T116–T120 не закрыты. После записи
проверено: hashes всех старых124 совпадают, added только этот файл, итого125.
Tasks и исходные QueueService.h/.cpp совпадают с приведёнными anchors;
`git diff --check` PASS. Новый файл не меняет состояние старых критериев
и не считается одиннадцатым normative checklist.

SHA-256 inventory старых124, sorted basename + пробел + SHA + LF:
`4dc602052267961d69e6c7b549c0281262b0a081d0f0f6daf1d97cf4e84e5126`.

| Прочитанный anchor | SHA-256 |
| --- | --- |
| QueueService.h до Round265 code | `95e62113e29072efb00ddd681cac29902b3e41461cc10660acfa1367e2e83073` |
| QueueService.cpp до Round265 code | `08ea8aac504d6f31d03cfed53b65ff4caed05522e57871a0a34ab376a4c12e5b` |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| custody contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| AGENTS | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| extensions registry | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |

Итог: предложение с уточнённым `ledgerKnown_` и exception fence достаточно
определено для узкого RED/implementation. **GO только REQUIREMENTS этого
среза; никакого full queue/application/release GO и никаких task closures.**
