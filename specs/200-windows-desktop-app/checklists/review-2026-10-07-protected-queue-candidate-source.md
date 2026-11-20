# SOURCE Round271: неподключённый защищённый logical queue candidate

Дата: 2026-10-07. Risk/validation lane: high-risk-product, независимая
проверка исходников и фактических доказательств существующей зависимости T116.

## Решение и границы

**SCOPED SOURCE GO; CRITICAL=0 / HIGH=0 / MEDIUM=0** для исправленного снимка
из 173 входов: allocator-aware общий разборщик и immutable
ProtectedUploadQueueCandidate на настоящем BOTH ProtectedCustodyQueueInput.
Предварительное замечание SRC271-PRE-1 устранено в этом снимке.
Исправленный Base cast и строгая проверка строк без накопления результата приняты.

Это НЕ закрытие T116, НЕ protected queue adoption или account/currentness/intent
authority, НЕ доказательство защищённости приложения целиком и НЕ release GO.
H250, legacy AAC RED257/B1, T116–T120, физическая Windows x64/audio matrix,
установленный интерфейс и producer/consumer integration остаются открытыми.
Не выдавать этот GO за право upload/delete/bootstrap switch или regular queue
fallback. Отдельная app-only сборка по 204 входам в это решение не включена.

Рецензент лично читал исходники, изменения относительно Round270, тесты,
экспортированные квитанции/журналы и scripts проверки. Рецензент НЕ выполнял
VM, сборку, CTest, app/profile/device, GitHub, hooks, commit/install/release.
Единственная запись — этот новый отчёт; старые reports/markers/code/tasks сохранены.

## Идентичность и сохранение прежней работы

- Canonical: /Users/yshishenya/Documents/crisp-worktrees/200-windows-followup.
- Branch: codex/200-windows-followup.
- HEAD: b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1; dirty сохранён.
- .specify/feature.json подтверждает Feature200 и high-risk-product.
- tasks SHA-256: 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f;
  120 всего / 93 закрыто / 27 открыто. T116/#7444 остаётся открытым; новый issue
  или task не создаётся. Свежая внешняя проверка issue сообщена main, рецензент
  GitHub в этом SOURCE-раунде не вызывал.
- REQUIREMENTS gate: review-2026-10-07-protected-queue-candidate-gate.md,
  d98ff03e201969c6192f1ac3029f624efda5c9708ab3f7fd8d35866717d918fd.
  Перечитан полностью, не изменён; это тот же допуск, не новая продуктовая норма.
- Перед записью: 136 .md. Десять текущих нормативных checklist имеют
  154 checked / 0 unchecked. Остальные 126 historical/context reports имеют
  256 checked / 10 historical unchecked; старые findings не переклассифицированы.
- Inventory SHA-256 до отчёта:
  b9f0e909db06c30098bb0dca4d9ee0513bc441291d445871b8f9df31d6be58dd.
  Формат: отсортированные строки SHA256, два пробела, путь от корня, LF.
- Конституция, spec, plan, quickstart и custody contract совпадают с SHA
  принятого REQUIREMENTS gate. Нормативная проверка заново не создаётся.
- Все шесть before/after implement/analyze/checklist hooks имеют по одному
  зарегистрированному git.commit с enabled=false; enabled=0, dispatch=0.
  Не считать before отсутствующими. Рецензент hooks не запускал.

Для Round271-only diff использован сохранённый production baseline
/Users/yshishenya/Documents/graf-f200-recovery-round270.DheA2K/apps/windows,
а не весь dirty diff относительно Git HEAD, содержащий предыдущие раунды.

## Проверка реализации и покрытия требований

1. **Один codec, совместимая грамматика.** JsonReader извлечён из
   DesktopApiClient.cpp, прежний std consumer использует alias JsonReader<>.
   Defaults depth32/input2MiB/readArray1024 и whole ledger4MiB сохранены.
   decodeQueueLedger в QueueService.cpp:206–449 — один общий путь для std и
   protected allocator. Сохраняются v3/read-v2 prefix/order, optional omission
   vs present-invalid, accepted tuple, owner raw-ASCII, server truth, deletion
   receipt/phase и purge duplicates. Writer/schema/load recovery не заменены.
   Root containment остаётся только в legacy load; protected path — UTF8 text.
2. **Фактические allocations.** JsonReader.h:24–54,150–171 использует
   rebind allocator для map/set/array scratch; root/nested keys учитываются.
   Возврат optional Fields/Values копирует lvalue в потенциально бросающем
   контексте, обе копии charged. Comparator+allocator constructors не спрятаны
   в noexcept transfer. Protected fields/records/три vectors используют
   CustodyString/CustodyVector; std::filesystem::path создаётся только std веткой.
   В protected body не найдено обычных heap strings/path conversions вместо
   charged ownership. SSO в owned records входит в charged object/vector/node;
   ограниченные локальные временные объекты не объявлены heap allocations.
3. **Debug proxy и перенос строк.** Codec.h:61–79 использует потенциально
   бросающий count0 constructor до swap/move. Move assignment:70 передаёт
   std::move(static_cast<Base&>(other)); это устраняет выбор template assignment
   через string_view и дополнительный allocation внутри noexcept.
   CodecTests:81–166 проверяет charge/capacity, copy/reserve refusal, overwrite
   wipe, self-move, proxy default/move/optional failure и retry при реальной квоте.
   Доказательство очистки ограничено valid plaintext на destruction/overwrite;
   не обещается wipe всего capacity, realloc leftovers или native allocations.
4. **BOTH и lifetime.** Candidate::read:1415–1455 принимает только настоящий
   private-ctor QueueInput, null input/token отвергает. NativeJob объявлен до
   held input, удерживается во время разбора и cleanup. Unselected разбирается
   в charged temporary и освобождается; selected — в retained result.
   Объект placement-new и shared control block charged; constructor failure
   deallocates object, control-block failure вызывает owning deleter.
   Header:135–141 объявляет input до parsed storage: при уничтожении storage
   освобождается раньше input/leases. Scratch views не сохраняются в результате.
   Нет раннего освобождения input при отказе, частичного publication или path cache.
5. **Отмена и типы ошибок.** ParseCancelled отделён от bad_alloc/malformed:
   protected boundary возвращает ioFailed/995, allocationFailed или invalidContent.
   Проверки before parse, между слотами и перед возвратом после transfer input
   присутствуют. Whitespace/digits/objectEnd продвигаются по одному байту,
   duplicate scan проверяется каждые 256 записей; decoded emission — каждые
   4096 выходных байтов. Это bounded synchronous traversal, не обещание hard latency.
6. **SRC271-PRE-1 исправлено.** JsonReader.h:84–88 сравнивает cursor-lastChecked
   с 4096 и обновляет lastChecked. Экранирование больше не позволяет бесконечно
   перескакивать выровненные позиции проверки. Одна итерация raw scanner consumes
   максимум 6 байтов: максимум 4101 исходный байт между проверками этого прохода.
   JsonReader.h:95–97 выполняет strict value validation через discard emitter,
   без временной owned decoded строки. UTF8/surrogate/allowNul семантика сохранена.
   Здесь polling считается по decoded output, не по raw bytes; предел 4101
   не переносится на второй проход. Owned decoded strings нужны только ключам.
7. **Общие потребители.** Calendar strict readers DesktopApiClient.cpp:393/411/
   428/452 живут до обработки fields: key views не выходят за owner lifetime.
   MeetingReminderModel.h меняет только forward declaration на тот же std alias;
   NativeSettingsBridge.cpp переименовывает private quoted в quoteJson против
   ADL-конфликта, не меняя escaping/payload. Calendar и settings targets входят
   в оба нативных прогона. Нет нового parser/DOM/dependency/controller.

## Лично проверенные испытания и предел их доказательств

Existing FilesTests.cpp:1551–1932 строит реальные bootstrap/queue DPAPI fixtures,
не fabricated input. Проверены g1/g2/g3 и оба selected slots, различающиеся bytes,
неправильный selected или unselected v2/v3 peer при валидной физической упаковке,
три коллекции, Unicode/path guards, optional fields, numeric limits/duplicates,
v2/v3 parity со std consumer и отсутствие protected rewrite/retry.
Caller input и ранее опубликованный candidate сохраняются после отказов.
Leases действительно исключают writeExisting до последнего result owner.

FilesTests:1830–1932 использует non-SSO строки/nested key sets/array scratch и
growth всех трёх vectors. Реальная reservation почти64MiB вызывает typed отказ;
baseline измеряется с живым BOTH input, после снятия давления доступен retry.
Каждый фактически наблюдённый operator-new ordinal fixture последовательно
отвергается, проверяются allocationFailed, baseline, leases, job release,
previous projection, retry, отсутствие writes и неизменность artifacts.

- Release: **889** actual allocation cuts. proxy=0, соответствующие proxy-only
  доказательства явно SKIP, не PASS фиктивного allocation.
- Debug: **1594** actual allocation cuts; entries/index/snapshot proxy=16,
  charged-proxy paths и caught default/move failures реально выполнены.
  Tests asserts активны в Release (NDEBUG снимается перед cassert).
- Это все allocations выбранного fixture/read path, НЕ все формы ledger,
  НЕ весь pipeline, НЕ классификация каждого ordinal по конкретному месту кода.
- Runtime cancel — pre-cancel и first/middle/last actual allocation. Это НЕ
  отдельная deterministic runtime injection в whitespace/digits/objectEnd/
  duplicate scan или точно на final publication instruction. Эти polling и
  ordering проверены SOURCE; тестовый журнал сам явно сообщает это ограничение.
  Quota/resource/owner correctness принимается совместно с SOURCE proof,
  а не подменяется тремя cancel ordinals.

## Замороженные доказательства

Внешний каталог: /Users/yshishenya/Documents/graf-f200-queue-final271.ZFwyvZ.
JSON прочитан без изменения файлов; UTF8 BOM квитанции удаляется только в памяти.
SHA ниже вычислены по исходным байтам, включая BOM при его наличии.

| Артефакт | Лично вычисленный SHA-256 |
|---|---|
| source-final271.json, 173 входа | f699d67824ad22ea04a3ddf606ef32d2a8c6221eaa16756ca8a7e75f9e9e9a0a |
| final-round271-release.json | 31fa094ee9e39f33f52b014f55ec07122e8a122777d085c0828fa562606bc679 |
| final-round271-release-test.log | 3d04ef48ec69e0c67daa87bb6f3e293f80f165b60fa903c7f508e424ef26abd7 |
| final-round271-debug.json | 2c2cbc737d2a36f5f8df0cb973d236efc15dffb5cb237a2e1ca68bee234d91c0 |
| final-round271-debug-test.log | 6962417a3a687870c0f0a60a798c82d623ab3fc75326c93d1b46c727581acd32 |
| portable-final271-test.log | 11859f5aee24a3c17e3b973f5f1cd18a69952dfabee768e0e1395bc39bb0cd37 |

Обе native receipt terminal=true/build_exit=0/test_exit=0, architecture=x64.
Release и Debug лично разобраны; обе source maps равны final173 map.
Все 173 current canonical files совпадают с map; Release/Debug содержат по 18
EXE hashes с PE machine34404 (0x8664). Raw logs лично прочитаны полностью:
18 Test Passed/0 Failed каждый, команды указывают правильные Release/Debug
каталоги исправленного ZFwyvZ. Files target32.83s/51.53s соответственно.
Main terminal40450/chunk1b14df сообщает totals52.63s/77.48s; totals не придуманы
как отдельное поле receipt. Portable log лично проверен:46 Passed/0 Failed,
total30.77s сообщён main; Windows-native ветки portable не подтверждает.

validate-final271.ps1 и readback-final271.ps1 лично прочитаны: x64 configure,
одна solution build18targets на config, serial CTest regex subset, правильные
EXE folders, post-test source verify и CreateNew immutable export.
Main execution9640/chunk9f7431 exit0 отдельно сообщает независимое native/share
сопоставление173 inputs и36 EXE hashes/PE, равенство native/export receipts.
Это main execution evidence, НЕ выполнение или личное чтение NTFS рецензентом.

Old pre-correction Release/Debug173 и первое compile failure не принимаются
за current proof. Genuine RED271b configure/build0/test8 на positive assertion
сообщён main; новый GO основан на personally read final code/green receipts,
не на выдаче compile failure за runtime RED. Новый all50 не выполнен этими
subset scripts: исторический legacy AAC failure остаётся открытым, не skipped/fixed.

## SHA-256 предмета SOURCE-проверки

| Путь от apps/windows | SHA-256 |
|---|---|
| RecApp/Contracts/JsonReader.h | 98d28c22bf3e447cd77b36d4fda2c2fcd59fb467b9f910ecd73fddf9c96f637d |
| RecApp/Storage/ProtectedCustodyCodec.h | ef725ea1bc07c6a6905f801dcf63d94f7827b4e630ca301d69ec4f6dabcc906b |
| RecApp/Upload/DesktopUploadQueueService.h | 1eb0b10ef3b2beee6ef833dcc8bfb767accbeec6dd61ce9bf77ded6c0d01754f |
| RecApp/Upload/DesktopUploadQueueService.cpp | 9bd86e5dd5e4f075889337bc239f4f476e4444e36fb1d8eef51d50d1c53e6463 |
| RecApp/Upload/DesktopApiClient.cpp | b3f1f9fed3bcae794aa5b6a7e128d1e06622b96d1237c4f7aade8183e2743365 |
| RecApp/Shell/MeetingReminderModel.h | 370b59af8517eb881974a5b3b300fb7b8bec2b72225a5b8a6c068b96afc05ade |
| RecApp/Web/NativeSettingsBridge.cpp | bc667b52197b9ae0c7b3163e3d83963d131326ebbefda7abd7cbc4cf48073845 |
| Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp | acf47b798f63a8d49e9f9f0675e608fd1f8b3c7690ffccb23bfe68c57cc373b3 |
| Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | 1b58a9448461983b76b4608392ba7bbeac2163e0117a64618814f59f4ddce9d0 |

## Ponytail и итоговая передача

Применены code-reviewer и ponytail-review; skills прочитаны рецензентом.
Общий allocator-aware codec устраняет дублирование, без второго domain model,
нового target/parser/framework. Безопасных дополнительных удалений не найдено.
Ponytail: **Lean already. Ship.** net: -0 lines possible.
Эта формула — только оценка сложности, не разрешение выпуска.

Итог: принята исходная корректность и приложенные scoped execution evidence
неподключённого компонента. До effects обязательны matching intent, account/
epoch/currentness, root/queue admission, typed durable mutations и реальная
интеграция startup/writer/consumer. Их выполнение этим отчётом не заявлено.

После записи отчёт полностью перечитан. Независимая повторная сверка:
все 136 прежних .md byte-identical, добавлен только этот SOURCE report;
все 173 canonical input hashes совпадают с final map, tasks и REQUIREMENTS
gate сохранили исходные SHA. Нормативные markers остались154/0, tasks120/93/27.
Сообщённая позднее успешная app-only204 сборка не расширяет это решение;
NU1900/D9025/external WebRTC warnings не объявлены zero-warning/security audit.
App-only receipt/readback/install/runtime требуют своей отдельной фиксации.
