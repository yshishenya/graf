# Round267 — REQUIREMENTS: точные поля существующего queue codec

Дата: 2026-10-06. Canonical
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, ветка
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved.
Lane: **high-risk-product**, существующая T116 / #7444.

## Решение

**SCOPED REQUIREMENTS GO к RED и ограниченной реализации Round267.**
CRITICAL=0, HIGH=0, MEDIUM=0, LOW=0 новых неустранённых замечаний в этой
области; blocking clarification=0. Порог scoped storage analyze — отсутствие
неустранённых C/H и блокирующих уточнений — выполнен для предложения.
Это НЕ SOURCE approval, выполненные тесты или принятие всей Feature200.

Согласован только root fix извлечения полей существующего частного ledger
decoder: `DesktopUploadQueueService.cpp` и существующий
`DesktopUploadQueueV2Tests.cpp`. Переиспользуются `jsonObjectFields`,
`jsonArrayValues`, `json_detail::decodeString` и `std::from_chars`;
нет второго parser/DOM, public decode API, класса, схемы, target или зависимости.
Уточнение main о presence-check и переносе настоящего allocation failure
теста с numeric substring на decoded string включено в решение.

## Независимое чтение и нормативная связь

Лично полностью прочитаны canonical project-local навыки `speckit-checklist`
и `speckit-analyze`, AGENTS, guidance index, worktrees/spec-kit-flow/product-gates/
tracker и constitution7.1.0. Для release guidance, PRD/current-status и активных
spec/plan/tasks/quickstart/data-model/contracts проверены относящиеся к этой
области разделы; giant historical validation не использована как текущая норма.
Перечитаны все154 действующих критерия десяти нормативных checklist файлов.
Related Round265 requirements/correction SOURCE и Round266 input requirements
сохранены в прежней области; они не заменяют самостоятельную проверку Round267.

Лично прочитаны actual QueueService helpers/load/decodeLedger/serializer/domain
validators, `DesktopApiClient.cpp` JsonReader и публичные map/array wrappers,
полный `Contracts/JsonString.h`, owner и candidate/OOM/v2 части существующих
V2Tests. Это source trace исходной причины, не новая SOURCE приёмка исправления.

| Норма | Покрытие согласованным предложением |
| --- | --- |
| FR-013; data-model §7 | Immutable local identity, accepted ranges, server/retry fields берутся из точного объекта; logical v3/read-v2 и writer bytes сохраняются. |
| FR-012/013; security CHK013 | Malformed known fields не превращаются в defaults/empty queue; late candidate adoption, quarantine и сохранение прежних трёх vectors/stamp остаются. |
| FR-022; Constitution IV | Deletion operation и purge ACK не могут получить identity/status/receipt из вложенного постороннего объекта. Parsed ACK не является новым proof фактического удаления. |
| Custody §§3,5,8.1; privacy-pause CHK012 | Queue cap4MiB неизменен; §8.1 strict authority-record schema не переносится на старый logical v3/v2. Protected shared quota/owner/adoption остаются отдельной зависимостью. |
| Plan:1501–1597; tasks:568–570; quickstart §12 | Необходимый общий codec prerequisite T116, затем owned logical candidate и полный producer/consumer flow; не новая задача и не приложение. |
| Constitution III/VI; FR-021/SC-006 | Нет egress/секретов/рабочих профилей; metadata-only synthetic evidence, независимый gate до кода. Не заявляется вся bridge/security матрица SC-006. |

Scoped analyze: у всех шести строк есть текущая нормативная связь и existing
owner T116; новых orphan/duplicate tasks, schema conflict или неопределённого
продуктового выбора не обнаружено. Критический незавершённый T116 целиком
этим решением не снимается. Local tasks T116 открыт и связан с #7444;
reviewer не запрашивал live GitHub и не выдаёт прошлый/main tracker snapshot
за собственную свежую проверку. Before implementation main сохраняет его
предложенную fresh OPEN/canon проверку, без нового issue/task.

## Фактическая причина и пригодность reuse

QueueService.cpp:50–110 ищет текстовые markers по всему object через `find`.
CPP:248–289/329–341 вызывает эти helpers даже после успешной map проверки:
сама проверка формы не связывает helper с top-level token. Nested unknown
object может подставить отсутствующее поле либо конкурировать с настоящим
значением. String helper снимает обратный слеш вместо JSON decoding.
Optional helper `nullopt` сейчас также скрывает неверный тип как отсутствие.

DesktopApiClient.cpp:29–155 уже валидирует объект и сохраняет только root
fields; nested values проверяются и пропускаются, raw duplicate keys отвергаются.
Его non-strict map запрещает escaped key names, а не нормализует их в owned
keys; views относятся к исходному документу и не к private reader storage.
Предел отдельного object/array **2MiB**, глубина32, array wrapper limit1024
сохраняются: cap4MiB всего ledger/raw string НЕ означает расширение этих caps.
Нельзя включить strict reader и вернуть dangling views либо менять общий
DesktopApiClient parser ради этой задачи.

Purge loop CPP:389–407 сейчас вообще не строит map. Для него требуется тот
же существующий `jsonObjectFields(object)` перед извлечением трёх полей;
иначе root cause останется в одном из actual consumers. Это reuse validator,
не новый parser и не миграция schema. Unknown unrelated поля разрешены в
существующих item/operation/ACK объектах; это не разрешение новых полей или
произвольного порядка в фиксированном корневом ledger tail.

## Условия следующего кода / SOURCE review

| Область | Точная принятая граница |
| --- | --- |
| Field lookup | Helpers получают per-object map и находят только exact top-level token по key. Нет `object.find` fallback. Required отсутствие/invalid отказывает; nested shadow никогда не восполняет поле. |
| Optional presence | Для `meeting_id`, `media_revision_id`, `upload_session_id`, `server_status`, `processing_status`, `media_revision_status`, item `updated_at_ms`: missing сохраняет нынешнюю совместимость; present + unsuccessful decoding — whole decode false. Valid empty string/zero допускается только как раньше. `null`, object/array/bool/неверный number не означают missing. |
| Strings | Точный quoted token → существующий decodeString, raw bound4194304 до reserve/allocation, allowNul=false, UTF-8/escape/surrogate проверки без blind strip, normalization/trimming. Частичный decoded output никогда не возвращается как успех. |
| Domain validation | После decoding остаются existing identity/reason/path/status/origin predicates, длины и owner pair rules. Правильный `\u0061` в допустимой identity означает `a`; escaped newline не становится `n`, а отклоняется там, где domain запрещает newline. Raw control/invalid UTF-8/surrogate/NUL в известной строке отвергается. Это не обещание новой UTF-8 strict policy всех skipped unknown values. |
| Owner fields | Existing top-level owner_user_id/owner_workspace_id pair и прежняя ASCII/accountId проверка сохраняются; nested owner не устанавливает owner. Не добавляется разрешение escaped owner/key aliases ради исправления других строк. |
| Integers | Один точный integer-token helper с from_chars: unsigned decimal token, successful error code, end==token.end, без sign/fraction/exponent/overflow/coercion. Domain bounds status/attempts/times сохраняются. Не расширять существующий18-digit document-stamp guard и не терять `npos` correction265. |
| Accepted tuple | Existing jsonArrayValues на exact mapped token, ровно3 elements; каждый — тот же integral helper. Отрицательные/строковые/null/вложенные/fraction/exponent/overflow/extra elements/trailing token rejected. Нет нового array scanner. |
| Lifetime | Map/array views используются лишь пока исходный ledger string жив; candidate владеет copied decoded values. Ни public borrowed proof, ни raw view после load не появляется. |
| Error classification | Invalid token возвращает nullopt/false, затем malformed quarantine. Allocation exceptions map/set/vector/string/reserve/emitter не превращаются в nullopt: доходят до load catch, quarantine blocks effects, source остаётся на прежнем имени. No blanket allocating-helper catch. |
| Publication | Existing whole-document validation, root check вне decoder, required recovery/v2 persist и только затем swaps трёх vectors/stamp неизменны. Никаких effects или частичной live adoption внутри helper. |
| Writer/compatibility | serialize/jsonEscape bytes/schema_version/filename неизменны. v2 omission и v3 optional отсутствия принимаются как прежде; повреждённые present known fields не получают compatibility exemption. Не обещается writer support каждого возможного Unicode/control path лишь по decoder тесту. |

## Обязательные следующему main проверки — ещё НЕ результаты

1. Genuine RED до code через actual `load`: nested-only required field и
   nested conflicting value в item; accepted tuple, deletion и purge paths.
   Проверить old projection/quarantine/zero effects, не просто helper boolean.
2. Known optional missing vs present invalid для всех семи полей выше;
   отдельно nested optional без настоящего поля не принимается как значение.
   Valid omissions, empty допустимые строки/zero и v2 upgrade сохраняются.
3. Valid escaped ASCII/quote/backslash/slash/Unicode и whitespace в value tokens
   читаются по JSON смыслу; invalid escape/UTF-8/surrogate/NUL, raw newline и
   decoded newline в запрещённой identity/path — refuse. Writer roundtrip на
   реально допустимых field/path values, без изменения serializer.
4. UInt64 boundary/overflow, negative/fraction/exponent/string/bool/null,
   exact3 accepted tuple, wrong types/length/trailing; сохранить domain bounds.
   Purge map также проверяет duplicate/malformed objects до ACK adoption.
5. Huge numeric synthetic rejection больше не allocation test: from_chars
   не создаёт substring. Hook должен остаться неиспользованным и корректно
   сбрасываться; malformed bytes изолируются. Genuine OOM перенесён на
   decoding raw safe_reason>1KiB с существующим test operator-new interception:
   hook реально срабатывает до domain отказа, старые projection/source retained,
   нет quarantine rename; после снятия fault successful retry. Нет prod seam.
6. Existing candidate partial-object/tail/stamp/root, v2/upload recovery,
   repeated/omitted ACK, known-missing, exact4MiB/+1 и writer failure tests
   сохраняются; exception-vs-content assertions соответствуют новой причине.

После RED/implementation нужны самостоятельный SOURCE review и свежие
применимые portable/native Release/Debug/SDK доказательства конечных inputs.
Reviewer не исполнял tests/VM/EXE/hooks/GitHub, не запускал app/микрофон/профиль.
Предыдущий all-native49/50 с legacy AAC RED257/B1 НЕ GREEN; его нельзя
переименовать в PASS, отключить или выдать за проверку нового Round267.

## Инвентарь и anchors

До записи130 `.md`:10 текущих нормативных — **154 checked /0 open**;
отдельно120 historical/context — **256 historical checked /10 historical open**.
Исторические unchecked не становятся новыми нормативными обязательствами.
Разбивка нормативных: requirements22, security27, ux25, audio24, routing14,
calendar-launcher5, calendar-operation8, calendar-wire5, packed-writer12,
privacy-pause12; все0open. Маркеры не меняются. Новый report без checkbox
markers; после записи131 файлов. Лично сверено: hashes всех прежних130
совпадают с до-write inventory, added только этот report; old mismatches0.
QueueService.cpp, V2Tests и tasks также повторно совпали с anchors ниже.
`git diff --check` PASS; это проверка текста, не запуск продуктовых тестов.

Tasks **120/93/27**, SHA ниже, без закрытия T116–T120. Inventory130 SHA-256,
sorted basename + пробел + SHA + LF:
`f2470151abe2e4818a2418ce1c012013659c52b08fd75dbfa60a1d08f4d3fe41`.

| Anchor до Round267 implementation | SHA-256 |
| --- | --- |
| QueueService.cpp | `8d1384c54e6295d141d4ffd6d7902efd386e8b7748c8ea9a6389392e962aa50b` |
| QueueService.h | `b3de437363e7e85adb19c649221408dd6f6ff0081932c51e69a46c634399fc6f` |
| V2Tests.cpp | `1c4143cbdecdbd7b1ab7f2adfb14f386cd836eded84e72b6d9c2d01379eab8d7` |
| DesktopApiClient.cpp | `a2442981a1113c985d8d9307e897161149a43e9c6895e6cc035e668b2e6373dd` |
| Contracts/JsonString.h | `e07cecc28815e8803d69b07e99f5bc9ca195e0aa1d1c30f6866a92c8d27389ac` |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| Base custody contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| Constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| Extensions registry | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |

Каждая из шести before/after implement/analyze/checklist стадий содержит
1registered git.commit disabled; enabled0/dispatch0. Поддерживаемые prerequisite
команды вернули active200; checklist-template прочитан. Skill analyze требует
unsupported `--require-spec`: установленный --help проверен, использован
`--require-tasks --include-tasks`, наличие spec проверено отдельно. Это
tooling discrepancy, не обход spec check или запуск hook.

**Итог: GO только требованиям точного shared legacy-codec root fix.**
Новые protected logical decoder, shared64MiB scratch/results accounting,
matching intent/current queue/account/epoch, typed mutation/admission/startup,
full writer/upload/playback/delete wiring, T117 migration, H250 и полная
T118/installed/hardware/release приёмка остаются открытыми. Physical input
Round266 не превращается в semantic/effect authority по этому решению.
