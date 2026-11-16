# Независимый code review: bounded-hash, частичный T116

Дата: 2026-10-02. Итог: **Request Changes — два P1 и один P2**.

Проверяется качество изменения кода, не повторное принятие требований и не полное выполнение T116. Принятый T115 остаётся принятым; нормативный contract не менялся. Этот срез не реализует весь protected custody/encryption. Whole-F200 clock/T119 HIGH не является дефектом bounded-hash и не используется как причина этого решения. Общие release gates сохраняются.

## Границы и свежесть

Единственная рабочая копия: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.

HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.

Полностью прочитаны инструкции `code-reviewer` и `ponytail-review`; просмотрены полный scoped diff `apps/windows`, новый `Sha256Tests.cpp`, все production-вызовы SHA helpers и необходимые границы их обработки. Root/product/risk guidance и accepted custody contract прочитаны в предшествующем независимом requirements review. Это отдельный read-only code review: reviewer создаёт только этот отчёт, не меняет код, требования, задачи, markers, другие отчёты, GitHub или коммиты. Существующие чужие изменения сохранены.

SHA-256 tracked diff (`git diff --binary HEAD -- apps/windows`): `7d6037935e0cbd406db1220a3f3f34312ef22402464265fe7fef53fb0f4a6993`. Новый untracked `Sha256Tests.cpp` в этот diff не входит; его отдельный pin приведён ниже. Pins повторно сверены перед записью отчёта.

## Замечания, препятствующие Approved

### BH-01 — P1: новый отказ CNG выходит из destructor reminder presenter

Источник нового поведения: `apps/windows/RecApp/Storage/Sha256.cpp:161`, особенно исключение на строке 165. Сам запрет подмены identity пустым хешем правильный; проблема в неполной адаптации существующих вызывающих границ.

Конкретная цепочка:

1. `MeetingReminderPresenter.cpp:56`: destructor вызывает `retirePresented()`.
2. При наличии `presented_` `retirePresented():64–70` вызывает `model_.dismiss(event)` и затем `model_.dismissalKey(event)` без обработки исключения.
3. `MeetingReminderModel.cpp:290` → `dismissalKey():287` → `contextKey():284` / `receiptKey():37` вызывают memory `sha256()`.
4. Ошибка любого Open/Create/Hash/Finish CNG приводит к `runtime_error` из нового helper. Исключение выходит из неявно noexcept destructor и вызывает `std::terminate`.

Это конкретный путь аварийного завершения при криптографическом отказе, а не гипотетическая необходимость новой storage-архитектуры. Правила exception specification destructor и завершения при выходе из noexcept подтверждены [C++ draft: exception specifications](https://eel.is/c++draft/except.spec) и [C++ draft: terminate](https://eel.is/c++draft/except.terminate).

Также memory SHA вызывается без локальной обработки при `bind()` → preference load и `reconcile()` → context key. Наличие catch в problem-claim helper не защищает эти отдельные reminder paths.

Минимальное исправление: обработать криптографический отказ на reminder boundary, безопасно убрать pending/presented действие и не предоставлять authority по пустому/общему/default key. Retirement/destructor не должен выпускать это исключение. Не требуется новый протокол или общий hash framework; `noexcept(false)` на destructor и глобальная замена исключения пустой identity не решают задачу.

Нужны регрессии отказа native SHA для retirement с показанной карточкой и для bind/reconcile: нет terminate, чужих receipts/preferences, новой capture authority или сохранения работоспособной карточки с недостоверной identity.

### BH-02 — P1: новый отказ CNG оставляет deletion flight незавершённым

Источник изменения тот же: `Sha256.cpp:165`. Конкретная цепочка:

1. `AppMain.cpp:2205` увеличивает `deletionSelectionsInFlight_` до `planDeletionSelection()`.
2. `DesktopUploadQueueService.cpp:1018–1020` → `requestDeletion():691–701` → `DesktopApiClient::deletionOperationId():845–857` вызывает memory SHA без catch.
3. Исключение покидает `handleDeletionSelection()` до возврата плана и до `finishDeletionSelection()`.
4. `WebView2Host.cpp:1684–1692` ловит и молча поглощает исключение из deletion handler. Ответ выбранному запросу не завершается; единственный decrement этой операции в `AppMain.cpp:2452` не достигнут.
5. `readyForUpdate():3116–3119` требует `deletionSelectionsInFlight_ == 0`; допуск обновления остаётся закрытым в текущем процессе.

Путь существует уже для первой допустимой meeting-target при отказе вычисления её operation ID; не требует предшествующей частичной записи или сетевого сбоя. Проверка `digest.size()` после SHA не обрабатывает исключение.

Минимальное исправление: превратить криптографический отказ в явный отказ планирования/пользовательского запроса на существующей подходящей границе, обеспечить баланс flight и terminal reply. Не производить HTTP/purge под пустым или выдуманным ID. Если более ранние элементы выбора уже durable, не терять и не пересоздавать их при завершении ошибки.

Нужна регрессия native SHA failure при первой валидной deletion target: отсутствуют новая операция/HTTP/purge по недостоверной identity, ответ завершён, flight освобождён, повторная попытка и update admission не зависли.

### BH-03 — P2: пустой manifest hash принимается до возможного создания встречи

`sha256File()` корректно возвращает пустую строку при read/CNG failure, но вызывающая граница допускает её как значение digest:

- `DesktopHttpTransport.cpp:145–182`: `packageTracks()` проверяет media/playback digests и размеры, затем без проверки результата помещает `sha256File(manifestPath)` в manifest track (строка 178).
- Возможен отказ именно этого вычисления после успешных проверок media/playback. Native helper теперь явно возвращает no-hash при CNG failure; read failure также даёт этот результат. `packageTracks()` всё равно возвращает tracks.
- `upload()` может выполнить `POST /api/v1/meetings` на строке 954, прежде чем `uploadSessionRequest(..., tracks[0].sha256)` на строках 968–969 отклонит пустой digest.
- Дополнительно `uploadFile():588` использует только сравнение вычисленного и ожидаемого хеша: два пустых значения при повторном отказе сравниваются равными. Это не доказательство успешной отправки неверных данных: part SHA имеет свой отказ. Это доказательство, что отсутствие хеша не отвергнуто данной integrity-проверкой.

Минимальное исправление: вычислить manifest digest и проверить его existing SHA shape до возврата `packageTracks()` и до сетевых побочных эффектов. В integrity boundary пустой/no-hash результат никогда не считать совпавшим валидным digest. Не требуется менять upload protocol или вводить полный encrypted custody в этот срез.

Нужна регрессия локального read/hash failure только при manifest hashing: invalid package до создания встречи/сессии/PUT; при повторном отказе нет принятия empty == empty. Это integration gap обработки расширенного набора helper failures; существующее поведение file-open failure могло проявлять тот же недостаток раньше.

## Проверенные свойства самого helper и тестов

- Native branch использует CNG, без silent fallback на portable SHA при native failure. Algorithm/hash handles освобождаются; `BCryptHashData` получает chunks не более 64 KiB, поэтому ULONG narrowing безопасен. Output buffer фиксирован, 32 bytes. Memory SHA не возвращает пустую identity, stream/file возвращают no-hash. CNG auto allocation при `pbHashObject == nullptr`, `cbHashObject == 0` поддерживается Windows 7+; обязательное linking `bcrypt.lib` присутствует. См. [BCryptCreateHash](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptcreatehash), [BCryptHashData](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcrypthashdata), [BCryptFinishHash](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptfinishhash).
- Portable branch: 64-byte block, фиксированные state/work arrays, bounded incremental update, checked 64-bit bit-length capacity, big-endian length/digest. Padding после `0x80` создаёт второй block ровно при недостатке места для восьми байт длины. Рассмотрены границы 55/56/63/64/65 bytes и 65536/65537; замечаний к padding не найдено.
- `sha256Stream()` читает от текущего cursor, не делает seek и не материализует весь вход. Рабочий input buffer 64 KiB. Normal EOF и EOF при включённом failbit exception допустимы; badbit/non-EOF failure возвращает no-hash. При read fault после первого успешного chunk не возвращается digest prefix. Начальное failed state отвергается. Это контракт отказов чтения/CNG, не обещание проглатывать любой allocation failure в процессе создания stream/string.
- `sha256File()` перед открытием проверяет `is_regular_file(path, error)`, что устраняет Apple ifstream directory-as-EOF случай. Эта проверка не объявляется same-handle custody proof; обычный file helper остаётся path-based.
- `WindowsTargetDetector.cpp` имеет только comment diff. Executable digest по-прежнему рассчитывается отдельно по открытому handle: регулярный не-reparse объект, размер `0 < bytes <= 256 MiB`, buffer 64 KiB, точный прочитанный размер, тот же handle в `WINTRUST_FILE_INFO.hFile`, удерживается sharing policy без write/delete. Signature/birth checks не заменены file helper или повторным открытием path. Certificate DER bounded 64 KiB; его memory SHA exception в production detection worker передаётся через packaged_task/future и в `AppMain.cpp:2937–2942` превращается в failed snapshot, не в guessed identity.
- `Sha256Tests.cpp` включает fixed empty/abc/million-a vectors, boundary vectors, binary NUL, cursor, initial failed state, throwing EOF, injected stream read fault с/без exception mask, directory rejection и lazy generated `64 MiB + 5` stream без полного input allocation. Assertions включены даже при NDEBUG. CMake регистрирует standalone test; native Core VS project получил bcrypt link. Тесты не проверяют три описанные caller regressions при injected native CNG failure.

## Трассировка всех production SHA callers

| Caller | Использование / граница отказа | Результат review |
| --- | --- | --- |
| `V5LocalRecordingWriter` | canonical retained-prefix hash; final WAV/playback hashes | Пустой digest отклоняется; не принимается нормальный verified результат. |
| `LocalRecordingPackage` | digest совпадает с validated manifest digest и размером | No-hash не равен допустимому 64-hex manifest digest; integrity не valid. |
| `DesktopHttpTransport` | manifest file hash; upload-file recheck; memory part hash перед PUT | BH-03 для manifest. Part exception ловит upload recovery worker и возвращает retryableFailure; текущий part не отправляется без digest. |
| `DesktopApiClient::deletionOperationId` | memory digest → stable scoped UUID | BH-02. Одноимённый private `DesktopApiClient::sha256` — bool format predicate, не hash producer. |
| `MeetingReminderModel` / `NotificationPreferenceStore` | receipt/context/owner keys; incident claim digest | BH-01 для presenter/context/preferences. `updateProblemClaim()` имеет catch и возвращает false: не даёт claim по failed digest. |
| `WindowsTargetDetector::verifiedSigner` | SHA bounded certificate DER после WinVerifyTrust | Production future catch → failed snapshot; authority не выдаётся. Отдельный executable digest остаётся same-handle CNG. |

`sha256Stream()` вызывается production file helper; остальные прямые вызовы нового stream API находятся в tests. Scoped smoke/test вызовы также просмотрены. Это трассировка затронутых callers, не аудит unrelated storage producers.

## Проверки и ограничения доказательств

Независимо выполнены: `git diff --check -- apps/windows` — PASS; повторная SHA freshness — PASS; Node/OpenSSL oracle verification фиксированных семи boundary vectors и lazy `64 MiB + 5` vector — PASS. Последнее проверяет ожидаемые test constants, не исполняет C++ implementation.

Reviewer не запускал C++ сборки/тесты, VM, installed app или внешние side effects. По свежему сообщению main: Mac suite **33/33 PASS**, native Core VS build/run **PASS**; Windows whole CMake build **exit 1**, ErrorsOnly диагностика продолжается, warning flood MSB8064/MSB8065 сам по себе не устанавливает причину. Эти результаты помечены как сообщённые main, не независимо воспроизведённые. Успешный normal-path тест не закрывает статически доказанные failure paths BH-01–03. Historical experiments/candidates не используются как runtime PASS.

Повторный gate для этого среза: локальные исправления BH-01–03, адресные native failure regressions, свежие исходные pins и результаты требуемых scoped build/test lanes. Это не разрешение закрыть весь T116/T117/T118, clock/T119, storage integration или release gates.

## Ponytail-review

Сама bounded реализация уже компактна: reuse существующего `Storage/Sha256.*`, native CNG на Windows, существующий portable algorithm вне Windows, без новых dependencies/frameworks. Безопасных удалений в просмотренном diff не найдено; net 0 строк. Отдельный same-handle executable hash не дублирует безопасно path helper и не должен удаляться ради reuse. Три замечания требуют локальной обработки отказов/регрессий, не нового abstraction layer. Вывод по сложности: Lean already; это не отменяет Request Changes по корректности.

## Exact source pins (SHA-256 текущих bytes)

Пути относительно единственной рабочей копии. Первые семь строк — весь review target; остальные фиксируют использованные caller/build evidence. Accepted contract приведён отдельно от code slice.

| Артефакт | SHA-256 |
| --- | --- |
| `apps/windows/CMakeLists.txt` | `6cbb503c8c899fae4c1c472e3259cfbfc91ffbc35663a76710ac4289a0b02cc6` |
| `apps/windows/RecApp/Storage/Sha256.cpp` | `9d03c560cd7ab124af6034c441a577d30f77649ee096f7be76eee6f3b07d19b7` |
| `apps/windows/RecApp/Storage/Sha256.h` | `06d3f46f37f42cafb12b30f9e6eff25065dbe61e88109035bf91f453aa9045d4` |
| `apps/windows/RecApp/MeetingDetection/WindowsTargetDetector.cpp` | `424eb77232fae271564ae92d7a77918b45fedf8915e8543e8bfc749fa893f860` |
| `apps/windows/Tests/GrafWindowsCoreTests/ContractFixtures.cpp` | `20883ed7b2252084853e87e24c23d39660a050ce006bd7d114ca03357d1f1e55` |
| `apps/windows/Tests/GrafWindowsCoreTests/GrafWindowsCoreTests.vcxproj` | `c53d070bbb0bae3f4262a875e593a56c3ff28847c5dec19e176d87d3e20d5df4` |
| `apps/windows/Tests/GrafWindowsCoreTests/Sha256Tests.cpp` (new/untracked) | `70bf9177f14bf328299ca44ce1d0de2c2853124b228e9f6515744ca2813cebba` |
| `apps/windows/RecApp/Shell/MeetingReminderModel.cpp` | `ad053893499165c639ce41c4a23115ff17a5bb3d775ec568ae311e8f8d4529b7` |
| `apps/windows/RecApp/Shell/MeetingReminderPresenter.cpp` | `dd0bc9dee51329582e227fb164000cf6d4ba7188abd985985998f8dff5a33d56` |
| `apps/windows/RecApp/Shell/MeetingReminderPresenter.h` | `813fac00a83939f27baa71eaa04b6d5773e2a9a0bf7de40115f1247cab831ef4` |
| `apps/windows/RecApp/Shell/RecordingNoticePresenter.cpp` | `44f1b623798c40ad012c41be88cdd6a0bfcdc48eda17166ff9fa90965527ff8f` |
| `apps/windows/RecApp/Upload/DesktopApiClient.cpp` | `84527d7b7457555aac578b7399227a7a0d8b3db589ebcf3e9e78455e329be900` |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.cpp` | `dbd87ca91485b3e9c67c0bb896be1d7c1bcedc91b7e377f8ac4e9bedba2e42d4` |
| `apps/windows/RecApp/Upload/DesktopUploadQueueService.cpp` | `08ea8aac504d6f31d03cfed53b65ff4caed05522e57871a0a34ab376a4c12e5b` |
| `apps/windows/RecApp/Upload/DesktopUploadRecoveryScheduler.cpp` | `e4fdac0709bf03c7b3f18d2629651ebded4f895d24fd3f026cc8bee066d6bf3c` |
| `apps/windows/RecApp/Recording/LocalRecordingPackage.cpp` | `7cfc575282ae03714b52adc219d798121dcbf6d6c4af8a3398f7760de8c30a40` |
| `apps/windows/RecApp/Recording/V5LocalRecordingWriter.cpp` | `b890339cfc0b21d1ef3d6c2840e01e2eb5ecabbdf5444593682279f780c6c453` |
| `apps/windows/RecApp/AppMain.cpp` | `f534c2ef8944120ed535a9a09fbc681b49f391ee6cb68a06fab8d83935391dbd` |
| `apps/windows/RecApp/Web/WebView2Host.cpp` | `39a250d6283c61773786b7f095b0d6afd3c023173310136163841c2144c0e0b3` |
| `apps/windows/RecApp/GrafWindowsApp.vcxproj` | `6f0968254001ddeccea8299094d6b1ce8ebacd26174715565d93cf2daf2ac3db` |
| `apps/windows/Tests/GrafWindowsPackageTests/AutomaticRecordingSmokeTests.cpp` | `ae0664da1157de3daa9891f7bc4551ba7464fbace84535f6c047ca4f62ae8ec5` |
| `specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md` | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |

## Fresh review delta — provider-independent identities / manifest refusal

Дата: 2026-10-02, повторное чтение текущих bytes после исправлений main. Предыдущие выводы выше сохранены как история и относятся к предыдущим pins. **BH-01, BH-02 и BH-03 устранены в текущем коде. Новых code defects в этом delta не найдено. Итоговый gate среза пока Request Changes только по недостающим детерминированным native-failure regressions, не из-за оставшихся причинных цепочек BH-01/02/03.**

Полностью заново прочитаны `code-reviewer` и `ponytail-review`, текущие `Sha256.cpp`, `Sha256.h`, `Sha256Tests.cpp`, CMake; просмотрен весь scoped tracked diff. Повторно проверены transport boundaries и неизменные identity callers. Независимые проверки текущего delta: `git diff --check -- apps/windows` PASS и source SHA freshness PASS. Reviewer не запускал/не писал код или tests. Единственная запись — append этого раздела в собственный отчёт.

### Почему устранены причинные цепочки

- **BH-01 / BH-02:** `Sha256.cpp:159–162` теперь на всех ОС создаёт только `PortableHash`. Ни constructor/update/finish memory helper, ни его fixed-state compressor не обращаются к CNG. Поэтому отказ Open/Create/Hash/Finish больше не может стать исключением SHA в reminder destructor, preference/context keys или deletion operation ID. Это устранение причины в общем primitive, а не обход error handling в callers. Требование изменять reminder/deletion boundaries ради прежнего CNG exception снимается. `length_error` при длине больше `UINT64_MAX/8` не достижим для обычных bounded identity inputs; allocation failure при создании результирующей строки не новый platform-provider отказ, прежний helper также выделял память. Не заявляется безусловный noexcept API.
- Это **не fallback после неудачного native hash**: route выбирается заранее по API. `sha256Stream()` на Windows безусловно использует `NativeHash`, при его отрицательном status возвращает no-hash, не вызывает portable compressor. File API делегирует ему. В accepted contract §6 по-прежнему CNG incremental SHA по logical stream chunks; provider-independent memory identities не отменяют этот контракт, полный logical protected reader ещё не доказан этим срезом.
- **BH-03:** `DesktopHttpTransport.cpp:177–178` проверяет вычисленный manifest digest existing `isSha256()` до возврата tracks. В `upload():896–900` отсутствующие tracks дают invalidPackage **до первого UploadSend**, включая identity GET и создание встречи. `uploadFile():590–591` отдельно требует валидный expected digest; short-circuit отвергает empty/malformed expected, а no-hash при допустимом expected не может сравняться с ним. Empty == empty больше не даёт integrity admission.
- Native stream state/cleanup/buffer/error branches и portable padding сохранены; same-handle signed-executable policy не менялась. Memory API сохраняет digest bytes и provider-independent identity semantics прежней реализации, уменьшая рабочую память. Для сверхдлинного unsupported input новый явный overflow refusal не обсуждается как отдельный ordinary caller defect.

### Самая короткая детерминированная регрессия без системной crypto configuration

Предложение, **не реализация и не выполненный test PASS**: отдельный Windows-only assert executable с test-only wrapper translation unit над текущим `Sha256.cpp`.

1. В test TU сначала включить `windows.h` / `bcrypt.h`, затем определить маленькие wrappers для четырёх операций Open/Create/Hash/Finish. На normal stages wrappers делегируют настоящему BCrypt, на выбранной stage возвращают отрицательный NTSTATUS. Локально подменить имена вызовов macros вокруг `#include ".../Sha256.cpp"`, затем убрать macros. SDK declarations включены до macros; не переопределять импортируемые DLL functions и не менять headers/production API. В executable не линковать второй обычный `Sha256.cpp` object. Никаких DLL hooks, provider registration, registry, global runtime config, admin или нового test framework.
2. Четыре cases: отказ Open, отказ Create, отказ второго HashData после успешно принятого первого 64 KiB, отказ Finish. Для валидного непустого stream и существующего regular synthetic file assert результат пуст; для HashData case не разрешать prefix digest, для Finish case не разрешать полный digest, для Open/Create case не разрешать portable fallback. При real successful Open/Create cleanup остаётся настоящим Destroy/Close. Можно небольшими counters проверить, что partial construction закрывает созданные handles и не вызывает последующие crypto stages после отказа.
3. При включённом Open-failure mode вызвать memory `sha256("abc")` и representative bounded identity bytes: ожидаемые фиксированные hashes и **нулевой счётчик CNG calls**. Это непосредственно доказывает, что прежний CNG trigger BH-01/02 недостижим. Не нужно добавлять криптографическую конфигурацию, API seam или обработчики в reminder/deletion, а также отдельную UI lifecycle инфраструктуру ради удалённой цепочки.
4. Один integration case для BH-03: использовать существующую synthetic valid-package fixture и `DesktopHttpTransport::upload(item, UploadSend)`. Fixture создавать с injection выключенной, затем обнулить call ordinal и отказать только manifest hashing; не ломать более ранние media/playback integrity checks. В текущем inspect порядке два file hashes — media и playback (`LocalRecordingPackage.cpp:157–159`), третий hash — manifest. Можно выбрать третий Open и assert именно три попытки. Expected: `invalidPackage`, **UploadSend calls == 0**. Этот case должен давать RED на прежнем transport: valid owner/session позволяют ему дойти до send. Если fixture/order меняется, обновить явный ordinal/assert, не добавлять глобальный fault framework. Для integration target использовать variant SHA object вместо обычного, остальные production sources оставить настоящими.

Существующая read-fault regression уже покрывает no-prefix при istream failure, но не заменяет эти CNG status cases. Existing boundary vectors проверяют и memory portable branch на Windows, и native stream branch; native failure mode нужен, чтобы детерминированно различить два API routes. Один additional baseline без faults подтверждает, что wrappers реально делегируют CNG и synthetic fixture проходит; отказ стадии не должен маскироваться precondition rejection.

Native return codes и incremental stages сверены с первичными [BCryptOpenAlgorithmProvider](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptopenalgorithmprovider), [BCryptHashData](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcrypthashdata), [BCryptFinishHash](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptfinishhash). Тестовая локальная подмена — рекомендация reviewer, не Microsoft-provided fault-injection facility. Предложенный test target ещё не собран; не заявляется готовым patch.

### Текущие evidence и pins

По новому сообщению main: **native CMake 33/33 PASS**. Plain solution build отдельно не прошёл, main выясняет missing AEC path / verified cache. Reviewer не воспроизводил эти результаты и не устанавливал причину failed build. Whole-solution failure не приписывается SHA без causal evidence; native failure regression пока отсутствует в неизменном `Sha256Tests.cpp`. Требуемые build lanes и точная связь output с текущими bytes остаются отдельным gate.

HEAD остаётся `99b00a579c24b50e320465b69d9a296038bc544d`.

Текущий SHA-256 tracked `git diff --binary HEAD -- apps/windows`: `043d4424c05695b9a43ceb7d9f30c7f79ae2c4a76062ac84ca6d59b6742386c5`; untracked test по-прежнему pinned отдельно.

| Текущий артефакт | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Storage/Sha256.cpp` | `2b0291a3b39f06068433ad4bb32221eacc4b469a4aab26b90215ef1da0d91b2d` |
| `apps/windows/RecApp/Storage/Sha256.h` | `e51b352aa346036708ad30867fed412b67000434b87d88aeb02c45549c43cc60` |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.cpp` | `34bfb5d5359c22c5de26bd790227414974d4804abdd6588e8e63734022e9fce1` |
| `apps/windows/Tests/GrafWindowsCoreTests/Sha256Tests.cpp` | `70bf9177f14bf328299ca44ce1d0de2c2853124b228e9f6515744ca2813cebba` |
| `apps/windows/CMakeLists.txt` | `6cbb503c8c899fae4c1c472e3259cfbfc91ffbc35663a76710ac4289a0b02cc6` |
| `apps/windows/RecApp/Shell/MeetingReminderModel.cpp` | `ad053893499165c639ce41c4a23115ff17a5bb3d775ec568ae311e8f8d4529b7` |
| `apps/windows/RecApp/Shell/MeetingReminderPresenter.cpp` | `dd0bc9dee51329582e227fb164000cf6d4ba7188abd985985998f8dff5a33d56` |
| `apps/windows/RecApp/Upload/DesktopApiClient.cpp` | `84527d7b7457555aac578b7399227a7a0d8b3db589ebcf3e9e78455e329be900` |
| `apps/windows/RecApp/AppMain.cpp` | `f534c2ef8944120ed535a9a09fbc681b49f391ee6cb68a06fab8d83935391dbd` |
| accepted `windows-protected-local-custody.md` | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |

Ponytail delta: разделение существующего portable compressor и native streaming class обосновано различными API semantics, без новых dependencies. Manifest shape guards необходимы и не удаляются. Lean already. Ship. `net: 0 lines possible.` Последняя фраза — вывод только по сложности; gate failure coverage, full T116/storage/encryption и release не закрывается.
