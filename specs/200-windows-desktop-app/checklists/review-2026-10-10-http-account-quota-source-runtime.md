# F200/T116 — Round335: HTTP account parser, source/runtime review

Review accepted / scope GO: только charged account parsing и его отказ по квоте.
CRITICAL 0 / HIGH 0 / MEDIUM 0; LOW/P3 1 — неиспользуемый include, без блокировки.
Полный T116/ALL-HTTP и готовность Windows остаются OPEN; общего GO нет.
Lane: независимое read-only review high-risk-product с единственным docs-only отчётом.
Применены code-reviewer и ponytail-review; новые сборки/тесты reviewer не запускал.

## Точная привязка

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`; branch `codex/200-windows-followup`.
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` + dirty bytes.
Frozen335 `/Users/yshishenya/Documents/graf-f200-account335.QIr9I1`;334 `/Users/yshishenya/Documents/graf-f200-account334.oJJrWC`.
Независимо пересчитаны все209 файлов обоих frozen;335 также209/209 равен canonical.
Diff334→335: ровно DesktopHttpTransport.cpp и два теста ниже; public header прежний.

| Артефакт | SHA-256, пересчитан reviewer |
| --- | --- |
| 335 source.json | `7650cde0080a792d01aa8d6cf9fd250a93d631694a7d284e89ee51b500d50c5d` |
| 335 native.json | `8b0c129a327bb1375082bfe30a7d02c6bc26e3010d95479b28a693f7e23b3e59` |
| 335 portable.json | `46f83c41794d2cd5a5ec384ec357372f78f14f129f0cb34399e48fa14926c72a` |
| 335 validate.ps1 | `98941d2eb51f3475449692aa54dd44e16bfee35866a74b8065cfadfe3367ba47` |
| 334 native.json | `3cc3ea66ae003badc67c70ebc4cd3ba030186f7a1a53e725e1699cc04008a4bd` |
| DesktopHttpTransport.cpp | `7ba6b02bd7973ac79c1fb4c0ae452e0c9359004ddb9a2abe0978431919d83036` |
| DesktopHttpTransport.h | `9cecf3d432f47e50889404db3ff37d2533cc172121a2f148fefe201b494f38a3` |
| NativeCalendarJoinTransportTests.cpp | `e6381d91b5374d95ed095fe5fe73a32338acf848898e22a4bc0020569e1807b3` |
| NativeCaptureStorageIntegrationTests.cpp | `b83da663ae34fcd10a6af4771dcc7a1698c6272bc46c65c609c544162cd43d8f` |

## Source и различающая проверка

DesktopHttpTransport.cpp:768–873,1120–1124: общий resolveAccountIdentityUsing<Reader,Get>; protected Response прямо от send к charged JsonReader.
accountField/RawKeys держат views внутри живого response; decode завершается до его разрушения.
Наружу выходят владеющие std::string/identity, висячих views не обнаружено.
Raw root-only parser прежний: accountId проверяет UUID; nested authority/escaped keys/duplicate keys/ID,
несколько active, неверные bool, trailing/depth/size отклоняются.
IdentityGet{} проверяется после snapshot; валидный snapshot даёт zero GET, mismatch запрещён.
Отмена проверяется до resolution и до/после GET; status mapping и deviceId.clear сохранены.
Прерывание внутри account parser этим срезом не добавлено и отдельно runtime не доказано.
DesktopUploadRecoveryTests:28–254,1155–1205 покрывает совместимые правила; asserts активны в Debug/Release.
Snapshot с пустым getter оценён по исходному порядку, отдельного теста нет.
NativeCalendarJoinTransportTests:310–332: живой charged body до давления; entry constructor+read и prebuilt reader.read
ловят bad_alloc, сохраняют body и возвращают charged baseline.
Это не утверждение о constructor-only allocation в Release без Debug iterator proxies.
NativeCaptureStorageIntegrationTests:930–976: known_workspace0/1, первый reply реально возвращён;
ReturnProbe исключает отказ при его создании/возврате, allowance учитывает move proxy.
Обе ветки требуют calls1/retryable1/noTruth/неизменный disk snapshot, запрещают следующие auth/me либо sync-state/mutations; healthy control есть.
RED334: native exit3, returned1/calls2/retryable0/truth0, driver принимает именно ожидаемый RED.
GREEN335: те же два endpoint пути дают returned1/calls1/retryable1/truth0 в обеих конфигурациях.

## Runtime artifacts и harness

Native receipt: terminal/native_completed=true, account_parser_green_verified, configure/build0; уникальные5 targets × Debug/Release:10 completed/exit0,5 Debug PDB SHA.
Capture запускается с --protected-upload: generated3000/cold read/direct transport, не весь EXE suite.
Все10 logs прочитаны и равны stdout+stderr. C=NativeCalendarJoinTransportTests; K=ProtectedCustodyCodecTests;
D=DesktopDeletionProtocolTests; U=DesktopUploadRecoveryTests; I=NativeCaptureStorageIntegrationTests.

| Log | SHA-256 |
| --- | --- |
| Debug-C / Release-C | `8fc7a31f8753d750f0a399f61caf414cef4ae90b3f3e5020bf3d6f5fe65b3073` |
| Debug-K | `e8da249a3559ca71fa6c67c0927568b11ba94c0831b92710ec42d9d9fd94055e` |
| Release-K | `f36bbad3646afc5fdf38d1c517290e9c4c6faeed8b387461d1b2fcf1eaa96cb1` |
| Debug-D/U / Release-D/U, каждый пуст | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Debug-I | `96a98dddbea3cec6232fce436b242d14d9b429b31db65efa6ca046792cf5c184` |
| Release-I | `2fa5b572b4776e120d0164941b063f73d7ed3633984de3d69f8629fc329961b9` |

C сохраняет WinHTTP quota/close markers; I — preowned admission, request quota и ACK progress;
Debug дополнительно terminal no-late-allocation. K Release честно SKIP только proxy-fault cases.
Пустые D/U приняты по completed/exit0 и активным assertions, без придуманных markers.
run.mjs/validate.ps1 связывают source/harness/RED receipt, проверяют209 до/после и idle;
verified stage требует10 exit0 и точные markers. Timeout900s не убивает job и не даёт verified PASS.
Portable receipt и три log hashes сверены:47/47 PASS,0 failed; это отдельная portable область.
Main actual postflight-v2.json SHA `139b0e948f3f4246e3b107f5ea4f402ae859ab50a326148e5cac79c0c52542c0`:
terminal/idle=true, source_checks209,10 EXE/5 PDB rehash; source/native receipt hashes совпали.
postflight-v2.ps1 SHA `1214b13222dd1e26f643f5a6c10fa5803a9cbe1286fe3f1c1a637dbd8d5c401a` прочитан:
полные source/EXE/PDB/idle проверки повторяются; diff к v1 — только @(...).Count и имя receipt.
Старый postflight.json сохранён; его array209ones не принимается как численная метрика.
VM execution — main (сообщён session2032 exit0/PASS); reviewer проверил artifacts, собственного VM/CIM audit нет.
TEMP335 оба пусты; RED33427files/7970508B сохранены.

## Findings и оставшиеся границы

P3 DesktopHttpTransport.cpp:L16: delete: unused <set>; replacement nothing; net: -1 line possible. Не изменён; typed reuse оправдан двумя allocator/body путями.
OPEN owning config/request/DTO/result strings, serialization/hash и остальные ALL-HTTP allocations;
OPEN scheduler/storage-worker prepare/result commit/adoption, stale/stop/effect fences, T116/#7444,
global admission, playback/delete/T120, migration/whole-pipeline, installed/hardware/CI/release.
storageWritable=false/localQueueComplete guard сохранены. Нормативные9 SHA прежние;120 unique tasks/93done/27open.
tasks SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
До отчёта176 Markdown/29 checkbox files/420checked/0unchecked; отчёт добавляет0 markers, после177 Markdown.
Единственная запись reviewer — этот файл; code/norms/tasks/старые markers/GitHub/VM/jobs/commit/release не менялись.
Cleanup scripts не исполнялись reviewer; очистка main на момент review ещё не выполнена.
