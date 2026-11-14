# T116 / раунд405: независимая source/runtime проверка playback consumer

## Решение и границы проверки

SCOPED GO: приняты текущий source diff, selected Release native20/20,
portable47/47, три последовательных consumer-повтора на том же native EXE,
SDK Restore/Build и сохранённый postflight main. Подтверждённых CRITICAL/HIGH
в проверенном срезе нет. Это подключение защищённого локального consumer,
не завершение T116 и не приёмка установленного пользовательского приложения.

Reviewer лично прочитал scoped production/test diff, primary receipts,
native/portable/repeat журналы, runner/postflight scripts, SDK build log и
actual CL tlog. Все 214 frozen и 214 canonical inputs перехешированы;
расхождений нет. От baseline404 изменены ровно восемь inputs, остальные206
совпадают. VM, процессы приложения, тесты, сборки и очистку reviewer не
запускал. Guest source/binary/idle проверки ниже атрибутируются сохранённому
postflight main, а не независимому обращению reviewer к VM.

Единственная запись reviewer — этот новый отчёт, без новых checkbox.
Исходники, нормы, задачи, markers, GitHub и чужие dirty changes не изменены.
Validation round405 и соответствующий F200 fragment лично прочитаны;
их финальные суммы и ограничения согласованы с primary evidence.

## Requirements / analyze / ownership

Canonical descriptor: checkout `200-windows-followup`, branch
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Проверяется dirty frozen source,
не новый commit/CI/release SHA. Lane остаётся `high-risk-product` внутри
T116/#7444; owner `codex` подтверждён текущим feature.json. Свежая read-only
проверка #7444 OPEN с каноническими метками переиспользуется из requirements
gate405; этот финальный closeout GitHub заново не опрашивал.

Scoped analyze C0/H0 и ранее прочитанные требования/пункты применимы к этому
подключению: native ownership, fresh authority, worker-only IO/last release,
cancel/drain, truthful UI и отсутствие plaintext fallback сохранены.
Hash gate `review-2026-10-10-protected-http-integration-gate.md`:
`51af545d0cc8a4dc31c5ea0d65595f08dcb6be2c8a4e2194ee3c3d8da90174e0`.
Hash concurrency gate `review-2026-10-11-cold-inspection-concurrency-gate.md`:
`32728e4b3150071c903f17d1be6363e9a3f8184adfadefdf0415e6e929bf4e8b`.
Это сохранение scoped gate, не новый полный analyze всей feature и не
повторная приёмка исторических runtime findings.

В этом closeout повторно прочитаны байты всех192 checklist/report файлов.
До отчёта: 29 файлов с пунктами, 420 checked / 0 unchecked.
Digest sorted filename-NUL-SHA256-newline:
`f037d35c1d18084a901039a7a7dd5177d8b4b1d837a56e3f9bbbdf2232953331`.
После добавления этого отчёта: 193 файла, те же29 и 420/0. Ни качество
требований, ни исторические отметки не означают будущую WinUI/runtime приёмку.
Tasks остаются120: 93 checked / 27 open. T116 и полная цель остаются открытыми;
ранее проверенные22 FR / 10 SC не объявлены выполненными.

Лично повторно вычисленные неизменные нормативные SHA256:

| Файл | SHA256 |
| --- | --- |
| spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan.md | 40443131fdafc41aa13ef98058e2fa95608dfdc1f60ae03d2ea6ab3acadb4868 |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| research.md | 901de067501da665dc3d28710c7691665a3d584f7bdcdb8f4f3c1a1ebbf8a774 |
| data-model.md | c24b9d10bf5b935bcf51bb12034a0bb9ccef4a0b3719a138b48a26cbaa0d3bc7 |
| quickstart.md | 6a070377de42113eea427d376f6b39beac5e222ca1dab31a69a85587b68f6dc3 |
| constitution.md | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| windows-protected-local-custody.md | 598223854ea7e614694167c4019ef199e30c82b3ac1c44b33fcefa94fbe27fee |
| windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |

Предложение следующего manual Record/pendingRecord/Stop-before-ACK среза
существует только в ответе reviewer. В405 нормы не менялись; этот отчёт не
разрешает обойти действующий plan admission или начать следующий срез.

## Exact source и проверенные границы

Baseline404: artifact basename `graf-f200-live404-green.gKHhxW`, manifest
`d105299c997015a60d67545700a48942f417d78a080606cc065356dcae845b02`.
Final405: `graf-f200-consumer405-green.RLV4Vz`, manifest
`24708b6980866138159ee25bb617f785981729e139d1418712f43a0c900d91bb`.
Восемь изменённых inputs относительно404:

| Путь относительно apps/windows | SHA256 final405 |
| --- | --- |
| CMakeLists.txt | da372b5dbe0c7ad03630fe29a08726d2ac0620a3afaa275b43f88a4305ae4412 |
| RecApp/AppMain.cpp | 6f88f6ca2e8199f6d2060a8c468ad09c4c503760a5db86b891a174521f02dd52 |
| RecApp/Recording/NativeCapture.h | a2f87afd03431308b93fa7d1807015e98b020d0e4dbb79754b7042534c3b706d |
| RecApp/Web/WebView2Host.cpp | f20268733107e87738f5e85027f55af5a3fee08cf8370359ac644847ca6f49c1 |
| RecApp/Web/WebView2Host.h | 13a3ef939a1e7ffa24c8437d06d10560f345dc56ecc697c119253e4ca07d4358 |
| Tests/GrafWindowsContractTests/CalendarJoinHostTests.cpp | 61424170ed541cadaf47a44dc54c6d7d40e759ab37ccf9a7b50b69be975c0e4d |
| Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp | 1dfcfe9cceb91a1339838a9cd9a977565a9e62eb5f6b5d5f0a2bd8a39228793d |
| Tests/GrafWindowsContractTests/WebView2HostLifecycleTests.cpp | 2f4e9282e985030fa0eaf77ff2734f18950385e3d1f6bc7140c1329e7fc1c99a |

UI-held PlaybackWork содержит charged immutable queue snapshot, index,
auth/document generations, cancellation, ограниченные desired commands и
value-only media observation. Pair/inspection/engine не передаются UI.
Worker-only exchange обслуживается единственным storage owner; отдельный
playback executor делает inspection/MediaEngine и actual native release,
не занимая upload executor. Commands/EOS и готовые network/result handshakes
имеют приоритет над запуском/проверкой playback.

Открытие проверяет current account/epoch и настоящую текущую строку;
storage делает fresh queue read и sealed normal/degraded package read.
Перед effects выполняется retained-package revalidation. Play/Seek требуют
ACK соответствующего serial и повторной проверки cancellation/serial;
устаревший ACK не применяется к новой команде. Pause/Close такого ACK не ждут.
Initial engine не начинает Play до отдельного UI authorization.

Pair/proceed/phase публикуются под mutex после storage-local open. Отменённый
initial waiter копирует pair только при proofReady. Executor закрывает engine,
ждёт настоящий reader/Clone drain, освобождает player/proof; storage затем
освобождает exchange pair и только после этого публикует terminal. Ошибка
launch/inspection/validation не даёт playback fallback или преждевременный
drain. Update/shutdown учитывают живой playback; auth change отменяет его.

Host пропускает только принадлежащие текущему аккаунту локальные строки без
meetingId, quarantine или pending deletion. `canOpen` означает право
запросить native проверку, не готовый proof. HTML identity/account/cookie,
document generation и nonce проверяются повторно. Timing не даёт authority.
Send/Delete и глобальные storageWritable/localQueueComplete остаются закрытыми.
Server-bound playback остаётся отдельной неподключённой границей.

AppMain использует одно управляемое окно и одно pending replacement;
replacement ждёт настоящий terminal. Старые callbacks проверяют window
generation, увеличиваемое до Close. Явный Retry допустим только после
ошибки и terminal; автоповтора нет. Wrap/ScrollViewer/Escape/Polite и подписи
проверены по source, не как фактически исполненная доступность WinUI.
Plaintext ShellExecute/meeting-review.m4a content fallback удалён.

## Test-first история и исправление Pause/ACK

История не переписана: M7Q8FO configure0/build1 — missing API compile RED,
не runtime дефект. Pilot7p4ycd native17 PASS при SDK Build1 снят во время
несогласованной UI-правки. 4lnY8r portable47 PASS, Windows /WX build failure
C2220/C4456 исправлен переименованием test locals без ослабления предупреждений.
7MbAwX native20/portable47/SDK0 не покрывал обнаруженный затем Pause/ACK дефект.
Эти промежуточные снимки не подменяют final405.

Qualified product runtime RED: `graf-f200-consumer405-red.kramP0`, manifest
`8da8f94c09faa6dc5305b575ebeb066b7446a91489bc9619f6eb15ecbe9839c1`.
Receipt `4339a546afd6276e0d4a91b845e71569695124dbafdae209a16291f1126eaf5d`:
terminal=true, configure/build0, CTest8. LastTest SHA256
`84deb20b1f47bf4df944aff875f9b8e2037305b7822c39e739666a5e121a6b3f`;
raw test.log `405238dd1200c6282bc99f17e2331a3193646751c8a2570fc1cb58d60eac298d`.
Лично повторно прочитан именованный assert
`pause_observation_must_publish_before_storage_ack` после failure cleanup.
Реальный успешный queue ReadFile удержан: cut/seek/validation/pause=1,
pause_published_before_ack=0. Это не timeout до достижения нужного среза.

Final fix использует существующий20ms ACK wait. Вне mutex выполняются
настоящие Pause/observe, под mutex публикуется actual Snapshot. Pause failure,
кроме MF_E_NOTACCEPTING, переносится в media.error; failure observation
отменяет операцию и идёт в прежний close/drain. Здесь нет Play/Resume или
оптимистичного fake PAUSED; serial/applied и fresh ACK не ослаблены.
Тест относительно этого RED неизменен, production delta — NativeCapture.h.

Новый consumer проверяет cancellation во время package metadata publication
и настоящего old canonical read; late proof не авторизует закрытый запрос.
Executable-only MF wrapper удерживает настоящий Clone, claim/AddRef/publish
согласованы test mutex с disarm/take, Release выполняется вне mutex.
Logout не даёт terminal до освобождения Clone; настоящая package preparation
завершается до его release. Старый выбранный package не изменяется, shutdown
достигает actual drain и owned-memory baseline. Assertions активны в Release.

При queue-validation cut Pause должен стать наблюдаемым до освобождения ACK;
обратное UI намерение Resume принимается, но actual опубликованное состояние
остаётся paused до ACK. Это не независимый перехват всех native Play calls
и не доказательство отсутствия любого кратковременного audio effect.

## Лично сверенное итоговое evidence

| Артефакт RLV4Vz | SHA256 |
| --- | --- |
| receipt.json | 4b3f528dc6bf096d5cb257b4b56422670dda6da9715f7e3fae8ff0883aaf70c4 |
| validate.ps1 | cf49ce88daf921e68eafda76cb1b78f21a5d3038c65a11e9b448fb2a94e13015 |
| native-LastTest.log | a62237161a135a6f74fa3b7862edf25773439b08dff143484561fde8c70873e7 |
| test.log | 874121512b020111ee280db8da7fa10f1f2144d19f860bac15e310616aff53e4 |
| portable-receipt.json | af58051b8a493384aa06d75c810aeb442af0f2d2844137457c90dd44df17d9b0 |
| portable47-LastTest.log | ecbddd24a89497e798426faf8762ccc42c313f325143095c32a1e5e64978a40a |
| portable-test.log | 39ad9622de324dc46aec2f05fa0c8268ca8d25d59d32819d60f3b907da89e8ec |
| SDK-Restore.log | 32acaa0c124a689e831cfd42806b236b486a95ea498c45264a464b9b801ff3eb |
| SDK-Build.log | d595426e13f5752542306430af95cc352d69c4295da407707c23d5a920acfdf5 |
| SDK-CL.command.1.tlog | 530f85a828952251d67571e69040d9f3158b54218172602913c102c41a010dae |
| postflight.ps1 | 3ee3b6812e90ddca82a2fca9ac4f0201ba0d057ff9c5e76d90b56dcd34c4f583 |
| postflight.json | 57d3d3e62a905f962be360f9ddffad73a9b1aac3f9cc7422993e9f53d8dd6faf |
| repeat-consumer.ps1 | 71774e3f9855d2b600b3e3beef14050f434090ebdb7cefa2887237dbfdcb32ce |
| consumer-repeat-receipt.json | 14e9191a032bead12fd7b7ab0db185dbff8194a94978898c715571087f9573e3 |

Receipt terminal=true, configure/build/test/sdk_Restore/sdk_Build=0.
Native LastTest:20 уникальных ID и имён,20 Passed /0 Failed, Release commands;
summary528.36s. Полные default suites Owner148.71s, Tree21.39s, Files134.41s,
WriteStream2.30s; bridge envelope/lifecycle/calendar host и13 protected
selectors составляют остальные16. Новый consumer11.49s.
Это selected20 из реестра69, не полный69 и не Debug acceptance.

Inspection preparation: actual_prepared=1 при удержанном cut, wire0.
ActiveStop: both_eos_finalize_serviced=1, wire0, adoption/restart5 pass.
Display: quota/logout/stale-cut/drain/disk/memory=1, upload_calls0;
owner quota package/queue modes recovered/queue_readable/future_created=1.
MediaEngine: actual muted ready/progress/pause/seek/resume, held MF Clone,
close_pending/release_drained и disk/memory=1. Это конкретные generated
регрессии, не универсальная latency или concurrency гарантия.

Во всех final consumer журналах metadata_before_publication_cut=1,
queue_validation_cut=1, seek/validation/pause/pause_published/resume=1,
resumed_without_ack=0 и финальный marker
`protected_playback_consumer=passed generated_muted=1 UI_acceptance=0`.
Последовательные повторы:10.69s,10.69s,11.12s, каждый CTest exit0;
receipt содержит iteration1/2/3 exit0 и тот же native EXE SHA.
LastTest hashes по итерациям:
`e30b061f37ee877e85c075e2c769e1fa732b162d36e0688460e2961260d116ca`,
`e30b061f37ee877e85c075e2c769e1fa732b162d36e0688460e2961260d116ca`,
`1aea29395e0a844c97d56520d4c1813607d34255860dd47a26b8de6284f857d9`.
Отдельные repeat stdout hashes:
`919170c72c565ac74b54d7896202334bca975e147d12a118b9126deca7313d49`,
`edaa5826e96a2eff680b8a5ed86cd44672fcc94dd4450a91cf095e88ab588f2f`,
`275a482908133b358e8c2b81168e77bf5370fbba3259585e93060d59ff75512a`.
Ранний Parallels Invalid argument до запуска repeat loader не считается
четвёртым тестом или product failure; новых прогонов reviewer не делал.

Portable: terminal=true, configure/compile/test0;47 уникальных ID1..47
и имён,47 Passed /0 Failed,23.25s. Windows-only capture/MF пути portable
не исполняет. Calendar host tests исполняют permission/document/account
матрицу; lifecycle test проверяет source wiring, не настоящий WinUI callback.

SDK Restore/Build0 и обычный compile/link подтверждены primary logs;
AEC3 source/license guard verified846fe90a289f58b7c9303a635142aa2c7caa93e5.
Лично прочитанный UTF16LE CL tlog содержит actual compile records AppMain.cpp,
Web/WebView2Host.cpp и Recording/ProtectedLocalRecordingPlayback.cpp.
Postflight main сообщает source_matches214, production_sources_compiled3,
active_jobs0 и следующие binary hashes:

- SDK app: `c2b4860f02de3b034e42b793939133a420deaacc7aa8e1f3487b7011f66ef2df`.
- Native integration: `dafbacf6886da85123344899c9d02a520631e993e40210469f83699da47ee083`.

Reviewer сверил сохранённые bytes/hash/scripts, не перечитывал guest EXE
напрямую. Reported OSArchitecture Arm64: x64 target в Parallels, не физический
x64 компьютер. Сборка приложения не означает его запуск или установку.

## Ponytail и оставшиеся gates

Ponytail-review ограничен восемью inputs405, не всем историческим dirty diff.
Lean already. Повторное использование existing MediaEngine/inspection/
retained revalidation, одного storage owner и value-only exchange достаточно;
нового framework, codec, протокола или зависимости нет. Удалять cancellation,
serial/document fences, clone drain или проверочные срезы ради сокращения
нельзя. Дополнительных безопасных обязательных сокращений не найдено.

Не приняты: настоящий WinUI window/button/keyboard/focus/text-scale/a11y
runtime; установленный пакет и профильная изоляция запуска UI; server-bound
доступ; полный native69/Debug/performance/hardware; вся конкуренция
display/playback/recording и starvation при общем native-job quota.
Display на этом source не отменяется автоматически при initial playback
handoff; same-package contention может отказать, а overlap требует отдельной
проверки. Успех preparation при удержанном MF Clone не доказывает всю такую
матрицу. Ошибка/занятость допускает явный Retry после actual terminal,
но не fallback или принудительное освобождение proof.

Общий admission, ordinary Record, Send/Delete, T120 и full Windows parity
остаются незавершёнными. Ни критерии следующего manual Record среза,
ни будущий WinUI harness не приняты этим scoped report. Commit/push/PR/
merge/release/deploy и изменение tasks/checklist markers не разрешались.
