# T116: независимое source/runtime review response foundation 333

Дата: 2026-10-10. Reviewer-owned, без новых checkbox/marker updates.
Вердикт: **C0 / H0 / P2=0; принят только узкий response foundation**.
T116, ALL HTTP quota, scheduler/result adoption и общие продуктовые ворота OPEN.
Risk lane: high-risk-product; выполнено независимое чтение исходников и уже
полученных доказательств, не самостоятельный запуск проверок.

## Идентичность и область

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` плюс dirty bytes, не новый commit SHA.
Артефакты: `/Users/yshishenya/Documents/graf-f200-response333.viwQeu`.
Независимо пересчитаны все 209 frozen и canonical inputs: несовпадений нет.
Относительно принятого frozen330 изменены только четыре файла ниже; относительно
332 — только `before` → `chargedBefore` в строках 928–929 Integration test.
Предупреждения не отключались; production332/333 идентичен.

| Файл относительно canonical | SHA-256 333 |
| --- | --- |
| apps/windows/RecApp/Upload/DesktopHttpTransport.cpp | adbb32aae07b3cab181f1ce901c7abaaef8e79d54bcd137da4bd5c8151abd453 |
| apps/windows/RecApp/Upload/DesktopHttpTransport.h | 9cecf3d432f47e50889404db3ff37d2533cc172121a2f148fefe201b494f38a3 |
| apps/windows/Tests/GrafWindowsContractTests/NativeCalendarJoinTransportTests.cpp | 49601905bcb850a30088684d8d72fd550442e8e280ced8be14442a8251015e09 |
| apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp | 27b7c312920ab7e5bf07f8aec77620a93377c7cc589a672c9ed0b792cbc7429f |

## Исходники и сохранённые ограничения

Перечитаны четыре изменения относительно frozen330, текущие native request,
protected entry/common protocol и существенные проверки обоих native tests.
`BasicUploadResponse<String>` сохраняет обычный std::string alias и добавляет
protected CustodyString alias. В единственном request/sendUploadRequest алгоритме
body/retryAfter/authExpiresAt, capacity и MSVC Debug proxies protected response
учитываются существующим CustodyAllocator. `resize` до WinHttpReadData находится
в DesktopHttpTransport.cpp:445–450; headers используют charged raw wide scratch.
ProtectedSend передаётся const reference, native default — прямой указатель на
`sendUploadRequest<ProtectedUploadResponse>`; прежнего условного std::function
copy/wrapper нет. Один loadTracks передаётся в одну из двух ветвей того же
uploadPrepared, протокол не дублирован. Ordinary/calendar/deletion aliases и
поведение сохранены. Новых зависимостей или реестра реализаций нет.

Тестовый ответ создаётся непосредственно в CustodyString, числа — stack to_chars,
а не через уже выделенную std::string. CopyProbe проверяет отсутствие копий после
создания callable. Старый request-body quota cut сохранён: missing-ranges response
подготовлен до pressure, measured three-proxy allowance допускает ровно явный
return move без зависимости от NRVO, ReturnProbe подтверждает успешный возврат.
После освобождения transport temporaries available=303 Debug / 159 Release меньше
manifest body=617, PUT=0; известный server truth не finalized. Это доказательство
конкретной одно-блочной fixture, не общий вывод для произвольных reader failures.
Weak owner/control release, полный idle baseline после proof/cache/worker release,
точные bytes/hash/ranges/JSON oracle и неизменность диска не ослаблены.
Native wrapper удерживает body до закрытия всех handles, включая exceptions/cancel.
Assertions активны и в Release: tests снимают NDEBUG перед cassert.

`ponytail-review` четырёхфайлового изменения: **Lean already. Ship.**
Это только отсутствие найденной лишней сложности, не merge/release/full-T116 GO.

## RED331 и неуспешная сборка332

Лично прочитаны receipts, журналы и harness, пересчитаны их hashes.
331: `/Users/yshishenya/Documents/graf-f200-response331.z6CxAa`;
все 209 frozen inputs совпали с manifest, единственная дельта к330 — Calendar test,
production остаётся330. Configure/build=0, PID8520,
start `2026-10-10T07:01:30.2292362Z`, test exit3, completed/terminal/native_completed=true,
stage=response_quota_red_verified. Actual log: `installed=1 caught=0 sends=1
receives=1 reads=1 closes=3`, assertion reads=0 провалился на строке339.
Это доказанный RED, не GREEN.

| Объект | SHA-256 |
| --- | --- |
| 331 source.json | 9b744762836f784fa00b70a970889a913d9d3132293dcd6850d8c11c334dd927 |
| 331 native.json | 345cbec6eb17069c1ffa1e4ab66ee9fb526297aac91c809df338f81bea5ca5cf |
| 331 NativeCalendarJoinTransportTests.log | 635cd835ed048d4846b545d8d6b4684fd88136790f7a48e04325b6912f537e71 |
| 331 EXE, из receipt | 1da17d0e43294ab030489c88f4797152c9eed9f4dbaf8e963f99ca96befedc05 |
| 331 PDB, из receipt | 888e11c6c9fdcb044ac766f6032fb5aace06d5a8d05ee90830a89b6c40c153e2 |
| 332 source.json | 70564b94f6624365284309b38bb5eae01570d109213d45769dc6e4dd70e36a8d |
| 332 native.json | b90325639fc9368d899a4c519326563a6580af3638622a8d2dab0c2413fa8b8e |
| 332 Debug-build.log | 89bf41187e3293e65e0f89cbf7b50575c090eebf1cf199fc44210d7ed1d099f4 |

332: `/Users/yshishenya/Documents/graf-f200-response332.xUWpFI`.
Terminal=true, native_completed=false, stage=build, configure0/build1/tests[].
Actual MSVC C4456/C2220: local `before` на928 скрывает outer `before` на772.
Ни один native test332 не начинался; portable332 не превращает его в native PASS.

## GREEN333: фактические receipts, журналы и процессная идентичность

Прочитаны native.json/portable.json, configure/build logs, все восемь native logs
и их stdout/stderr, portable configure/build/test logs. Каждый combined native
log побайтно равен stdout+stderr. Portable receipt hashes совпали с actual logs;
47 уникальных start и 47 уникальных Passed с совпадающими ID, 29.76s.
Native: terminal/native_completed=true, stage=response_quota_green_verified,
configure/build=0; все восемь completed=true/exit0. Portable: terminal=true,
stage=portable47_verified, configure/build/test=0. Main executor sessions52616/78842
reported terminal0; независимая приёмка опирается на прочитанные receipts/logs.

| Объект333 | SHA-256 |
| --- | --- |
| source.json | 756aa889ecbcd0a5e65da3afda3fc6ae27806e86e1fc322d97253d4f7be77186 |
| validate.ps1 | 423fa86e254e78c73bdb56f7ff0653fc7d18ab2bf32efb022b0be92889fba458 |
| run.mjs | 3f94454cf4ecbca8ec34538139ee317f88a9458d6ebc7ab7f75f8d5e46d49989 |
| portable.mjs | 9618772e71484ed6b85b8c7cabb9780f5af19e959f8614a4091a8aa042b88481 |
| native.json | 1e979214d9edbf615b079093c9f78285158c18a84589983fb4057c5842a1f72a |
| portable.json | 831c6f86be7ea9d68804c652479521afb6afa2749531e627ea02fbdbab8f6451 |
| configure.log | b693656bb0555d15bfc091e63d182a2f1d28675483d06469c7e566c3b6d07c00 |
| Debug-build.log | e31a7e15641917e692df67be7688da8d7af9b2e76ff5c205ec4364c797f2c969 |
| Release-build.log | de426eb9a67eea0b6601459e8334ac04cb96f03eb0fc53358cc44f77cef74389 |
| portable-configure.log | cf593a92c5cc15eb17cd3e40ee47d55339d1534924a771f26294917d3a3ba15f |
| portable-build.log | 1206a8e5773a47e74d4fc0df4efdfd9277bef78be8c5d7e176c3a267af3191e0 |
| portable-test.log | 593af96a65f1b3a06f92cec57bbd183dbd5b85e168de1a2f91f2e3a92d092b4c |

В следующей таблице время — UTC 2026-10-10; EXE/PDB hashes независимо прочитаны
из receipt и сверены с способом их получения в actual harness. Он запускает
точный EXE из `C:\Temp\graf-f200-stream292\core-build\<configuration>`, сохраняет
настоящий process handle/PID/StartTime, вычисляет EXE hash и Debug PDB hash,
ждёт этот процесс до следующего запуска. Windows EXE/PDB отдельно на Mac не
экспортированы: повторное хеширование их текущих Windows bytes не выполнялось,
VM не запускалась. Release PDB=null ожидаем по harness, не пропущенная Debug proof.

| Config / target | PID / start UTC | EXE SHA-256 | Debug PDB SHA-256 |
| --- | --- | --- | --- |
| Debug Calendar | 8016 / 11:50:59.4016583Z | 236001f7beda07de0f2d9e325e225f0d50242145ab205f8985091ea4078e0e31 | a86276548d35d66488092743c3740d06825ca7afa503107197fc027807406c52 |
| Debug Codec | 2284 / 11:50:59.8909546Z | 54cc84d0dd8f99695aa3e59d54d9859bab78dfbe99266c4d30b2a97054c69492 | 1d7eeab4ac6d2143201f2945766d3cef353cff2ba9bc720fb0ec5ef4ef1b8005 |
| Debug Deletion | 6768 / 11:51:02.9720210Z | 6c5f18a0c02e28d9f0697e594d58eb8590a8ad3bb69156c94c121b660aa8192b | 57a5f9ce11fe585fc58c06b5d6b2444efe4bf4a52767ea6c3d99fcdd21bdb1a4 |
| Debug Capture | 5252 / 11:51:03.2590444Z | 5df6d0d96b60f11215f29662975e79dbd7ea48beddfc49569757bbcadadf3a8c | 2eb7829c4cad885c7605b00e2b6e9384afaa6b89ff3883c750d9d44594921cb9 |
| Release Calendar | 8196 / 11:52:48.8684636Z | 96b2a2e1b545930ec345be8768dfbfe74ca02460879ca8db30d1c9f081099323 | null |
| Release Codec | 5088 / 11:52:48.9884698Z | ad2a439770e72cce3a0529b6109d6e7381b67e8eda70de9d8705ef1269846655 | null |
| Release Deletion | 4344 / 11:52:50.9327549Z | fa0ece8971ee0a4eaeccab591706b89dc388e1ad9322b05fba434add8386367c | null |
| Release Capture | 7512 / 11:52:51.0329887Z | bcf8202aa7301ae043738d5178465061e69460aae304975e6767ad5389b4ebef | null |

Calendar=NativeCalendarJoinTransportTests; Codec=ProtectedCustodyCodecTests;
Deletion=DesktopDeletionProtocolTests; Capture=NativeCaptureStorageIntegrationTests
с `--protected-upload`. Это четыре выбранных target × две конфигурации, не full53.

| Native log | SHA-256 |
| --- | --- |
| Debug-NativeCalendarJoinTransportTests.log | 847348a9a17826c2ab22f2aec3d0fbcdc6189d7cc46594b4281b82c51e147c71 |
| Release-NativeCalendarJoinTransportTests.log | 847348a9a17826c2ab22f2aec3d0fbcdc6189d7cc46594b4281b82c51e147c71 |
| Debug-ProtectedCustodyCodecTests.log | e8da249a3559ca71fa6c67c0927568b11ba94c0831b92710ec42d9d9fd94055e |
| Release-ProtectedCustodyCodecTests.log | f36bbad3646afc5fdf38d1c517290e9c4c6faeed8b387461d1b2fcf1eaa96cb1 |
| Debug-DesktopDeletionProtocolTests.log | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| Release-DesktopDeletionProtocolTests.log | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| Debug-NativeCaptureStorageIntegrationTests.log | 14ba156c95673a913ca8c4d50db4a56276858332ed3e5ad4f47caf393967763a |
| Release-NativeCaptureStorageIntegrationTests.log | c0de76c1bb2f1b9b6dbcaa7d018f979d527ed20dc3bcc37246474a17da3f6f9d |

Calendar в обоих режимах: RESPONSE_QUOTA installed1/caught1/sends1/receives1/
reads0/closes3; wide-before-send, headers-after-receive, body-through-close и
protected-response-before-read PASS. Positive4096 body/headers/exact charge
проверены assertions до markers. Integration в обоих: frames3000, finalized,
cold_read; direct charged wire/callback_not_copied, actual_transport_bytes,
preowned zero wire including account, request quota reply returned, six negative
cuts/known ACK progress, cold_read_verified/done PASS. Debug дополнительно
preowned_terminal_no_late_allocation PASS; unexpected TERMINAL allocation hit
не наблюдается. Baseline=0, empty_proxy=16 Debug / 0 Release; полный post-release
idle проверен тестом. Codec Debug выполняет proxy-fault proof; Release честно
SKIP только проверки выделяемых proxies, которых в этой STL конфигурации нет.
Deletion logs пусты; приёмка этого target опирается на completed/exit0, не на
выдуманные markers.

Harness связывает verified same bytes source/previous receipt и ScriptBlock,
требует точный terminal BUILDFAIL332, idle до изменения native tree и после
проверок, проверяет source до/после, использует уникальные TEMP по конфигурации.
900s timeout не убивает процесс и не выдаёт native_completed/verified PASS.
Verified stage достижим только после всех восьми exit0 и обязательных markers;
неуспешный/неполный результат не принимается. Это статическая проверка guard
плюс actual receipt, не отдельный текущий CIM/VM audit reviewer.

## Явно OPEN и что не изменено

Account owning bridge DesktopHttpTransport.cpp:1096–1102 всё ещё копирует charged
body в std::string; resolveAccountIdentity:820–848 копирует config/body/identity,
decodeAccountIdentity/decodeActiveWorkspace:763–796 используют обычные parser
containers/decoded strings. Эти seams OPEN. Также OPEN все оставшиеся owning
request/config/LocalTrack/DTO/JSON map-vector-set/hash/serialization/result string
и Debug/control allocations, скрытые allocation до invocation, полноценный
ALL-before-allocation proof. Response foundation не закрывает их.

OPEN actual scheduler/storage-worker prepare full commit/adoption, отдельный
network executor с worker-owned proof/last release, fresh-current single result
commit/adoption, stale/effect/stop fences. OPEN playback/delete/T120, migration
T117, whole-pipeline/100cycles T118, hardware/accessibility/installed MSIX/auth E2E,
macOS parity, exact-SHA CI/PR/merge/release. Ни endpoint/schema/auth policy, ни
лимиты64MiB/256KiB, ни plaintext-temp policy этим срезом не меняются.
ReadinessInputs.storageWritable=false (WindowsReadinessGate.h:16);
NativeCapture.h:753 меняет только local readiness copy;
localQueueComplete:452 использует readiness_. Global admission не открыт.

Девять normative SHA независимо пересчитаны и прежние; tasks SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`,
120 unique /93 done /27 open. До этого отчёта:175 Markdown,29 с checkbox,
420 checked/0 unchecked; этот файл добавляет ноль checkbox. Нормативные документы,
tasks и прежние reviewer markers не изменены. #7444/T116 не закрывались; нового
GitHub чтения/изменения в этом review нет. Validation/changelog append основного
агента не выдаётся за независимое runtime evidence.

Reviewer не запускал jobs/VM/CUA/GitHub, не правил code/norms/tasks/другие reports.
Единственная запись — этот отчёт. Очистку не выполнял и не фиксирует выполненной:
временные build каталоги остаются в ведении main после принятия отчёта;
frozen sources/logs/receipts/native core-build сохраняются.
