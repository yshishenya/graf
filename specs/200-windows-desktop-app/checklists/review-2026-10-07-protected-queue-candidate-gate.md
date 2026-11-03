# REQUIREMENTS: неподключённый защищённый logical queue candidate

Дата: 2026-10-07. Область: следующая зависимость существующего T116, не его закрытие.
Risk/validation lane: high-risk-product; независимые speckit-checklist и
speckit-analyze, до RED/реализации. Код и испытания рецензент не менял и не запускал.

## Решение

**SCOPED REQUIREMENTS GO; CRITICAL=0 / HIGH=0 / MEDIUM=0** для конкретного
предложения main вместе с последним уточнением CustodyString/Debug proxies.
Допуск разрешает RED и реализацию одного allocator-aware decoder/candidate.
Это НЕ SOURCE approval, НЕ подтверждение общей квоты реализованного pipeline,
НЕ application/adoption/effect authority и НЕ разрешение commit/install/release.

Обязательная часть принятого предложения — считать Debug proxies и control
block, применять существующий CustodyVector и безопасный CustodyString.
Первоначальный простой alias basic_string с CustodyAllocator сам по себе
этот допуск не получает. Новых продуктовых решений или задач не требуется.

## Снимок и независимость

- Canonical: /Users/yshishenya/Documents/crisp-worktrees/200-windows-followup.
- Branch: codex/200-windows-followup.
- HEAD: b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1; dirty сохранён.
- .specify/feature.json и check-prerequisites --json --require-tasks
  --include-tasks указывают Feature200 и её spec/plan/tasks.
- tasks: 120 всего / 93 закрыто / 27 открыто; T116 открыт.
- До нового отчёта: 135 .md; десять нормативных checklist — 154 checked /
  0 unchecked. Остальные 125 исторических/context reports — 256 checked /
  10 исторических unchecked. Исторические отметки не превращены в новые нормы.
- Хеши всех десяти checklist сверены; действующие критерии перечитаны.
  Полный ранее прочитанный контекст конституции/guidance сохранён; применимые
  разделы дополнительно проверены. Огромный historical validation не пересмотрен.
- Inventory SHA-256 до отчёта: 43f500eb366d6cc21d8fb52ac6bd8e4ece499d2da0f3f0d7c5bb4623e8e30ef5.
  Формат: отсортированные строки SHA256, два пробела, относительный путь, LF.
- Все шесть before/after implement/analyze/checklist hooks: зарегистрирован
  один git.commit, enabled=false; enabled=0, dispatch=0. Не трактовать before
  как отсутствующие. Hooks не запускались.
- Live read-only gh issue view: #7444 OPEN, title
  "[200][P0][storage] T116: Защитить всю локальную цепочку записи без открытых временных копий";
  ровно feature:200, priority:P0, area:storage, gate:pr-blocker, type:hardening.
  Связь Spec tasks:T116 и девять обязательных секций body присутствуют.
  assignees=[]; назначенный человек не придуман. Tracker ownership — существующая
  task-backed issue, не новый дубль и не закрытие задачи.

Issue: https://github.com/yshishenya/graf/issues/7444. GitHub только прочитан.

## Применимые нормы и scoped analyze

| Основание | Что сохраняет этот срез |
|---|---|
| Constitution VI:401–419; spec-kit-flow:180–215 | Независимый gate до кода, reviewer-owned markers, отдельные SOURCE/validation |
| Spec FR-012:459–493, FR-013:494–498 | Не пустая замена ledger, совместимые v3/read-v2, неизменные identity/server truth/ranges |
| Custody §5:186–225 | Общие 64MiB до allocations, worker-only; candidate copy и retained result тоже charged |
| Custody §7:293–308, §8/8.1 | Snapshot/cancel/lifetime; current account/session/epoch и matching durable intent обязательны перед effects |
| Plan:1501–1534; tasks:565–571 | Независимый storage prerequisite разрешён; неподключённый codec не защищает приложение |
| Security CHK012–018, requirements CHK009/012/019/020/022 | Bounded custody, сохранение данных, точная совместимость, safe evidence, shared change не скрыт |
| Calendar-wire CHK002/005 | Извлечение JsonReader обязано сохранить decoded duplicates, Unicode и view lifetime; отдельная календарная приёмка |

Остальные действующие checklist проверены на отсутствие изменения capture,
privacy pause, packed writer, UX/доступности, routing и release требований.
Их markers не изменены и не объявлены runtime PASS. Применимые требования имеют
покрытие предлагаемыми проверками ниже; orphan/new task не найден.
Нет несогласованного schema rename, второго parser, нового root/path authority,
новой account policy, скрытой очереди либо изменения численных порогов.

## Фактическая причина и минимальная форма

DesktopApiClient.cpp:29–164 содержит единственный JsonReader, но его
fields/rootKeys/nested keys/array values используют обычные map/set/vector/string.
QueueService.cpp:53–89 и :196–406 затем создают обычные строки и три коллекции.
Заменить только финальные векторы или предварительно оценить размер JSON —
не доказательство учёта этих реальных allocations. Однократное извлечение
существующей грамматики и allocator-параметризация записей — достаточная
минимальная форма; второй DOM/parser или новый controller не нужен.

Принят один generic decodeLedger с target collections/stamp, а не вызов load().
load():119–193 выполняет filesystem containment, recovery/rewrite и persist,
поэтому остаётся только legacy consumer. Новый protected consumer не должен
вызывать его, persist, stamp/retry или quarantine/rename.

## Точный принятый контракт реализации

1. **Одна грамматика.** JsonReader переносится в Contracts/JsonReader.h;
   std wrappers/API остаются совместимыми. Defaults depth32, input2MiB,
   readArray1024 сохраняются; whole ledger4MiB и v3/read-v2 prefix/order тоже.
   strict=false сохраняет нынешние key/unknown/nested правила, strict calendar
   сохраняет decoded-key equality и UTF8/surrogate validation. Не вводить
   closed metadata-schema rules для logical queue. Strict root key views живут
   не дольше своего reader; protected result не хранит views в parser scratch.
2. **Полное allocation ownership.** Allocator распространяется на map nodes,
   set nodes, array scratch, все strings, capacities, proxies, три vectors,
   temporary unselected candidate, retained object и shared control block.
   Rebind обязателен. Никаких скрытых std::string/path conversions в protected
   validators/value_or/record assignment. Constants string_view.
   SSO байты входят в уже charged enclosing owned object/node, не отдельная
   освобождённая от учёта «бесплатная строка». Native memory не выдана за owned.
3. **Записи без нового domain model.** BasicUploadCustodyItem<String,Path>,
   BasicDeletionOperationRecord<String> и BasicLocalPurgeAcknowledgement<String>
   сохраняют порядок полей/defaults и прежние std aliases. Protected path —
   owned UTF8 String, только прежние синтаксические guards, без filesystem::path
   construction, canonicalization, root containment или IO. Числа/accepted
   tuple/optional absent-vs-invalid/owner raw ASCII сохраняются.
   Document stamp from_chars сохраняет старую границу digits/18 и отказ
   truncated stamp; это не ужесточение всей JSON-грамматики.
4. **Debug и очистка.** Protected vectors — CustodyVector. CustodyString
   использует potentially-throwing count0 construction до swap/move, wipes
   valid plaintext на destruction и overwrite move по образцу CustodyBytes.
   Обычный basic_string default/move noexcept не используется как безопасный
   protected transfer. Не расширять это до неподтверждённого обещания очистки
   всего capacity, всех realloc leftovers или native memory. Map/set создаются
   через comparator+allocator; возврат optional/map/array и record/container
   transfer не должны превратить bad_alloc в terminate. Copy/prvalue/throwing
   construction допускаются; peak обеих копий учитывается.
5. **Настоящий BOTH input.** Private ctor, read только genuine
   ProtectedCustodyQueueInput; null input/cancel — invalidInput.
   Input/context/indices/physical generation удерживаются до конца проверки
   и жизни результата. Unselected полностью проверяется charged temporary,
   затем освобождается; selected разбирается в retained result. Неправильный
   любой peer отвергает весь candidate. Все бросающие storage/result/control
   allocations выполняются при живом владельце input и NativeJob; ошибка
   construction/transfer освобождает своё, не caller input/last projection.
6. **Отмена и ошибки.** Nonnull shared cancellation, NativeJob через синхронный
   parse. Проверки before parse, bounded syntax/whitespace/digits/objectEnd/
   string-emission/duplicate scans и после создания результата до publication.
   Internal cancellation tag не ловится как malformed или allocation failure:
   protected boundary возвращает ERROR_OPERATION_ABORTED отдельно от
   allocationFailed/invalidContent. Legacy default traversal без cancellation
   сохраняет прежнюю source-vs-malformed классификацию load().
7. **Никаких полномочий.** Getter даёт immutable decoded snapshot + input/context/
   physical generation/legacy flag, не готовность очереди. V2 flag не вызывает
   rewrite; uploading не становится retry. Нет network/rename/quarantine/
   mutation/delete/bootstrap switch. Ни owner fields, ни decrypt/parse success
   не доказывают account epoch/currentness/matching intent/root admission.
   Эти проверки обязательны следующим реальным consumer до любого effect.

## Проверка MSVC: проект допустим, фактический отказ ещё не доказан

По первичному Microsoft STL xstring ordinary default/move constructors
используют noexcept и proxy allocation; count/character construction
потенциально бросает. Это подтверждает необходимость CustodyString, но не
подтверждает ещё не написанный wrapper на установленном SDK.
Источник: [Microsoft STL xstring](https://github.com/microsoft/STL/blob/main/stl/inc/xstring).

Map/set comparator+allocator constructors и их tree implementation allocate
sentinel/proxy; upstream move constructors map/set потенциально бросают, а не
обязательно noexcept. Поэтому нет blanket-утверждения «любой STL move unsafe»:
проверяется каждая фактическая цепочка optional/record/result.
Источники: [map](https://github.com/microsoft/STL/blob/main/stl/inc/map),
[set](https://github.com/microsoft/STL/blob/main/stl/inc/set),
[xtree](https://github.com/microsoft/STL/blob/main/stl/inc/xtree).

Это upstream source reading, НЕ чтение установленного VM STL или Debug execution.
Фактическая установленная версия и Release/Debug budget refusal нужны на SOURCE.

## Минимальная обязательная проверка на искусственных данных

- **Parity:** существующий V2Tests fixture со всеми тремя коллекциями,
  optional fields/server truth/accepted tuple/Unicode/path controls/duplicates/
  malformed document stamp; v2 и v3 дают те же данные через оба allocator пути.
  Legacy load/rewrite/quarantine/OOM classification и aggregate initializers
  не меняют поведения. Calendar strict escaped duplicate keys, invalid UTF8/
  surrogate, depth/size/array bounds и root-key lifetime после извлечения parser.
- **BOTH:** настоящий native QueueInput с разными g1/g2 logical JSON;
  оба варианта selected slot; valid selected + malformed unselected при верных
  physical SHA, и наоборот. Peer никогда не пропускается по legacy/schema.
  Caller input остаётся пригоден и retained после отказа candidate.
- **Вложенная квота:** долгие non-SSO строки, множество nested unknown keys/
  map/set nodes, array scratch и все три result vectors при реально зарезервированном
  почти64MiB. Отдельные отказы construction/proxy, string reserve, node/array,
  vector growth, object/control block и transfer. No terminate в Debug,
  typed allocationFailed; после освобождения temporary — baseline/retry.
  Baseline измеряется с живым BOTH input, не ошибочное требование usedBytes=0.
- **Отмена:** pre-cancel; mid whitespace/objectEnd/digits/string decode/duplicate
  traversal и final publication checkpoint. Typed cancelled, не malformed;
  ни частичной projection, ни записи/rename/network. Точное место наблюдения
  должно следовать из source/test, не из недетерминированного thread sleep.
- **Lifetime:** reset caller bootstrap/input при живом result не снимает leases;
  release только после последнего владельца. Quota/cancel/error не выпускает
  admission/input раньше фактического синхронного completion.
  Existing generated native fixture/targets переиспользуются; новые targets,
  публичный forged-input ctor и production fault flags не нужны.

Это перечень критериев будущей SOURCE/validation, не сообщение об их PASS.
Рецензент не выполнял VM, CTest, сборку, app/profile/device или частные данные.

## Непринятые этим gate области

Protected queue logical adoption/shared projection, durable typed mutation,
startup/account/session/epoch/currentness, migrating intent validation и
producer/consumer wiring остаются обязательными последующими шагами T116.
T117/T118/T119/T120, H250 и legacy AAC RED257/B1 не закрыты.
Сообщённые main результаты Round270 не использованы как independent evidence
нового ещё не написанного candidate; прежний Recovery deadline не назван исправленным.
Нет application/native-all50/install/parity/release GO.

## SHA-256 исходного снимка

| Файл | SHA-256 |
|---|---|
| .specify/feature.json | d4be889d623986959cc6b11beeb6227a4a33d0a1d9b2052e782db105439ba882 |
| .specify/memory/constitution.md | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| .specify/extensions.yml | ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c |
| specs/200-windows-desktop-app/spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| specs/200-windows-desktop-app/plan.md | 527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c |
| specs/200-windows-desktop-app/tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| specs/200-windows-desktop-app/quickstart.md | fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e |
| specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md | ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a |
| apps/windows/RecApp/Upload/DesktopApiClient.cpp | a2442981a1113c985d8d9307e897161149a43e9c6895e6cc035e668b2e6373dd |
| apps/windows/RecApp/Upload/DesktopUploadQueueService.h | b3de437363e7e85adb19c649221408dd6f6ff0081932c51e69a46c634399fc6f |
| apps/windows/RecApp/Upload/DesktopUploadQueueService.cpp | bdc76ef8cf30d83c53a75f83e844386285f2bad6dc6beb93bf2f77f276a66613 |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h | 524a040b07a3264369406d7bdbcd9e9bcb90417b471f4f3455ced9109f02b615 |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | 6b9566e55edb24e6880d971777cb0d2b852e04cafb28831530395c161dcefba1 |
| apps/windows/RecApp/Storage/ProtectedCustodyMemory.h | a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | 669f287ec7643339a93fbc91c72f92210bef542e639fe605151e7d0e96798396 |
| apps/windows/RecApp/Contracts/JsonString.h | e07cecc28815e8803d69b07e99f5bc9ca195e0aa1d1c30f6866a92c8d27389ac |
| apps/windows/Tests/GrafWindowsCoreTests/DesktopUploadQueueV2Tests.cpp | d49d2bd6a0d512d171522645c28d3950c23c49248c53d49c5ae2fa0b9a24c7e4 |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | dfccb4b9f27cdc78435b69c6f7bf58ad4316dd0839c6ba233df58cc40ca9f7f1 |

После записи и полного перечитывания отчёта повторная SHA-сверка подтвердила:
все 135 прежних reports/checklists byte-identical, все 18 перечисленных
normative/source/test inputs byte-identical; добавлен только этот отчёт.
Нормативные markers остались 154/0, tasks — 120/93/27. Реализация не начата
рецензентом; код/tests/GitHub/VM/hooks/commit не изменены и не выполнялись.
