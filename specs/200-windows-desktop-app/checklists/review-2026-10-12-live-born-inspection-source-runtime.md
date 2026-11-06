# T116 / раунд404: independent source/runtime review live-born inspection

## Решение и способ проверки

Приняты SOURCE GO, selected Release native16/16, portable47/47, Windows SDK Restore/Build и сохранённый postflight main для exact source ниже. Подтверждённых CRITICAL/HIGH в проверенном срезе нет. Исправлен конфликт inspection при живом birth StoreOwner; это не пользовательский playback UI, не открытие admission и не завершение T116.

Reviewer лично прочитал scoped source/test diff, receipts, журналы, postflight script и actual SDK CL tlog; при финальном readback повторно перехешировал все 214 frozen и 214 canonical inputs, расхождений нет. VM, сборки, тесты и очистку reviewer не запускал. Guest source/binary/idle проверки атрибутируются сохранённому postflight main, а не независимому обращению reviewer к VM. Единственная запись reviewer — этот новый отчёт; checkbox markers, задачи, нормы, исходники и GitHub не менялись.

## Requirements / analyze / ownership gate

Canonical: согласованный checkout `200-windows-followup`; branch `codex/200-windows-followup`; HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Проверяется dirty frozen source, не новая commit/CI/release версия. Срез остаётся `high-risk-product` внутри существующего T116. Прочитанные guidance и требования переиспользованы; scoped analyze C0/H0 не означает глобальную приёмку feature. Gate `51af545d0cc8a4dc31c5ea0d65595f08dcb6be2c8a4e2194ee3c3d8da90174e0` и concurrency gate `32728e4b3150071c903f17d1be6363e9a3f8184adfadefdf0415e6e929bf4e8b` сохраняют область применения. Новая политика, схема или задача для этого исправления не нужны.

В начале404 свежим read-only запросом проверен #7444 OPEN с каноническими метками; owner codex по feature.json, GitHub assignees пусты. Финальный closeout повторно GitHub не опрашивал. T116 остаётся открытым.

Перед записью отчёта повторно прочитаны байты всех 191 checklist/report файлов: 29 файлов с пунктами, 420 checked / 0 unchecked. Digest отсортированных filename-NUL-SHA256-newline: `50dddf9e345aa56ea256e342f2ee3bfc8b4cca4b312603e3ccbf66d49b574ef7`. Этот отчёт не добавляет чекбоксов: после него 192 файла при прежних 29 и 420/0. Tasks: 120, из них 93 checked / 27 open; ранее проверенный объём 22 FR / 10 SC не объявляется выполненным.

Повторно вычисленные неизменные SHA256 девяти нормативных файлов:

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

## Source review и минимальность

Baseline403: каталог артефактов `graf-f200-revalidate403-green.OgLS8M`, manifest `610ed57732272189a917a3005a4c4c152506bd5652fe1631d207a342a41cdd21`. Final404: каталог артефактов `graf-f200-live404-green.gKHhxW`, manifest `d105299c997015a60d67545700a48942f417d78a080606cc065356dcae845b02`. Ровно восемь изменённых inputs: Windows CMakeLists.txt, ProtectedCustodyFiles.h/.cpp, ProtectedCustodyMetadata.h, ProtectedCustodyReader.cpp, ProtectedPackedCustodyOwner.h, ProtectedPackedCustodyTree.cpp, существующий NativeCaptureStorageIntegrationTests.cpp. Остальной исторический dirty diff заново не принимается.

Private Files::openPackageMember выводит каталог из genuine held package-state parent и удерживает его root lease. Проверяет readonly/fault/role/store/exact cancellation token, свежую native ancestry, private ACL, object IDs и удержанный store.id; открывает только существующий member identity. Нет store/root reopen, create/discover/repair, публичного raw getter, ослабления sharing/ACL или нового права записи. Cold reader использует этот путь для packed и flat members. Отказ retained пути не переходит в path fallback; прежний standalone fallback допустим только при отсутствии retained lease.

Prepared readExisting packed owner проверяет retained root/context и readonly Files; createNew partial-birth retention сохранён. Read Guard сохраняет native job, owner mutex и проверки, но не берёт общий root write group. Tree commit/checkWrite используют write Guard; writeReady требует владения group lock. Public flush/publishHead берут root group перед owner mutex. Это освобождает общий root для preparation/finalization, не убирая write serialization.

Два конкретных риска первоначального diff исправлены до GREEN: packed member open получил scoped native admission до IO с освобождением перед отдельным openImpl admission; flat/packed member opener получил свежую проверку удерживаемых ancestor handles/ACL/object IDs/store.id без reopen или чтения shared cursor. Нового лимита, исключения из quota, framework или зависимости нет. Ponytail review: Lean already; private helper и существующие loaders достаточны.

Final integration CPP SHA256 `b3bd6b301511b96d99ae002a08bb8df5b7b62b1c865d9cee2b918c4277f5cfd9`; Files.cpp `b4ab2d5e1260a5f25696703bfc624396a719e5699c5c88b8ebfc9bb92bee6f5f`; Reader.cpp `2bf35e4b9390f7c5f2dc3915fe43a72bd83a0dcf4a270dda309532415393cd3f`.

## RED и конструкция GREEN

Qualified RED: каталог артефактов `graf-f200-live404-red.eFwVkX`, source manifest `60d250ad139936cb5e316d3a9e051561b777941619f725ef0cc8ea55628c67d7`; receipt SHA256 `042f2815d35d0638e804a45b672917f3e82965c7f7aabe790b521c63756ef9ba`; LastTest `eb9a7d14e3af07279fd0532dfb9382984f468ad772a63065c93f14c0b69b0dcf`. Configure/build=0, CTest=8. Оба genuine normal/degraded пакета sealed/firstRead/ACK=1 при удержанном birth StoreOwner; inspection ioFailed6/native32, queue/disk/encrypted-only/memory проверки успешны. Exact assertion `protected_live_born_owner_must_allow_genuine_inspection` падает после cleanup. Это квалифицированный product RED, не ранний fixture failure. Исторические неквалифицированные попытки403 и его cold-only приёмка не переписываются.

GREEN test расширен относительно RED: четыре занятых native jobs дают allocationFailed10/native1816; после освобождения выполняется genuine retry. При удержанном успешном nonempty old canonical packed read cut новая package birth на том же StoreOwner завершается до cut release. Cut освобождается до ожидания futures и при failure cleanup; asserts выполняются после worker/native/memory cleanup. Byte identity проверяется для старого пакета, а не для всего root, где намеренно создан новый пакет.

Direct live-born package preparation не называется actual controller Prepared/Stop. Последние проверены отдельными существующими vertical cases на reopened scheduled root; новый retained opener связывает reader с этим же root. Отдельный actual-controller Stop именно на birth root не исполнен. Renderer cancelled-token fixture теперь сначала получает genuine pair/inspection с тем же отменяемым token; ранний opener refusal не принимается за renderer rejection. RED/GREEN whole test sources не идентичны.

## Лично проверенное runtime evidence

| Артефакт final404 | SHA256 |
| --- | --- |
| receipt.json | df41d1a6d585dc1912db59b2b142d41c701f142c28598327a85b922b49c5fbeb |
| native-LastTest.log | ddc69395f0e5e0878081c8b1fb744447bcbb10500d1887b5d3e3a311efca1c12 |
| test.log | 619274692510bab65458aeb70e59c823777731d3071097367439f619310337e6 |
| portable-receipt.json | 478ef4d39c21efd752246bff5dda935e3d1e6d34ec9c1aa5fe10b9cddce0f113 |
| portable47-LastTest.log | 5786bbdd290cfd83ab3a50c20482e76d4a86dc3998e6a2acb607dc064b2f3940 |
| portable-test.log | e1699d8478d608e7aa2f6774e57229900c375a243b093b9133811e7721b8482e |
| SDK-Restore.log | c257bc7751f59e79945c03832908ec4e039663f0bff120febb484d1e292cafad |
| SDK-Build.log | d000b1593eefb1b1a49e16d8397ffd3cc23f9bcc90d8946db1aa52183f5de5cb |
| SDK-CL.command.1.tlog | 486055708fa53d2fdd3463b7981827f69f0987df46bd3c7e14e372615cd6bd4f |
| postflight.ps1 | 80d25cbf562e512f79054c180f0edf0f7404f62248af13da8afbc705319f33f1 |
| postflight.json | 1eea0b0885d825f8f673bab6a18d16c1a9d1c808fccd5411e9566368cf34ca9c |

Final receipt terminal=true, configure/build/test/sdk_Restore/sdk_Build=0. Native LastTest: 16 уникальных ID и имён, 16 Passed / 0 Failed, Release commands; test.log (UTF16LE BOM) подтверждает CTest553.40s. Это selected16 из registry68, не full68 и не Debug. Полные default suites: PackedOwner202.48s, PackedTree21.58s, Files136.42s, WriteStream2.27s. Остальные12: InspectionPreparation45.12s, InspectionActiveStop89.87s, ReadModel2.49s, AccountProblems0.32s, DisplayTiming2.52s, DisplayOwnerQuota0.39s, MetadataReadAdmission0.25s, OwnerCancellation0.50s, ReaderReleaseDrain0.17s, MediaEngine8.54s, PackageRevalidation29.34s, LiveBornInspection10.96s. Времена не используются как performance/hardware acceptance.

В обоих live-born случаях inspection/ACK=1, error/native0, duration5000, jobs_held=1 с отказом10/1816, nonempty_read_cut=1, prepared_before_release=1; queue/private old-disk/encrypted-only/memory=1. Normal decodedFrames240640. Degraded decodedFrames0, trustedFrames500: проверен genuine trusted recovery prefix, не AAC decode этого degraded случая.

Actual preparation: cut_held=1, actual_prepared=1, wire0, затем cancel/drain pass. ActiveStop: cut_held=1, both_eos_finalize_serviced=1, wire0, запись state1/base3/target4/error0/native0 и adoption/restart5 pass. Это конкретные generated concurrency cases, не универсальная latency гарантия.

MediaEngine: cancelled_token/negative_drain/ready/muted/progress/pause/seek/resume=1; held_mf_clone/close_pending/release_drained/closed/repeated_close/commands_closed/disk/memory=1. Genuine MF-held clone удерживает закрытие до actual release. Duration5.013, positions0.101 → pause0.101 → seek2.507 → resume2.625. PackageRevalidation regression Passed; ресурсные отказы не ослаблялись ради нового opener.

Portable receipt terminal=true, configure/compile/test=0. LastTest: 47 уникальных ID1..47 и имён, 47 Passed / 0 Failed; summary23.20s. Portable не исполняет Windows-only native/MF path.

SDK logs подтверждают Restore и обычный compile/link GrafWindowsApp.exe. Лично прочитанный UTF16LE CL tlog содержит actual compile records для ProtectedCustodyMetadata.cpp, ProtectedCustodyFiles.cpp, ProtectedCustodyReader.cpp и ProtectedPackedCustodyTree.cpp из exact404 guest tree. Его raw SHA совпадает с postflight. SDK EXE по receipt/postflight `eb3734b2669b34f29d6959651f4debb3bcfb0440e117c46ea861c2a8424cc983`; native Integration EXE по postflight `faacf43845e62728ddb226d1c18f39d8a1d455808a58f9fec3da1e0623ffa0dd`.

Saved main postflight terminal=true, source_matches214, production_sources_compiled4, active_jobs0. Reviewer лично проверил shared/frozen и canonical байты, но гостевые EXE/live idle независимо не наблюдал. Скрипт отдельно хеширует и читает manifest/TLOG: same-captured-bytes атомарность всех его чтений не заявляется. SDK warnings не объявляются отсутствующими. Приложение не устанавливалось и не запускалось как пользовательский UI.

## Документирование, очистка и оставшиеся границы

Лично прочитаны новые round404 записи validation-2026-10-02.md и changes/unreleased/F200.yaml. На момент чтения SHA256 файлов соответственно `4e5e9dad422efd3edfbec2e0f199b56c1cd75325fb153ab7429a18aedf45a698` и `5db79e4de6b14cab1d53181874cb2a79c0d4dd3a36393feb5db02d6dc2cd9b7d`. Историческое pending сохранено с последующим terminal addendum; нет ложного full68/Debug/installed/UI/performance утверждения. Подтверждённых блокирующих расхождений с прочитанными свидетельствами нет.

Cleanup main подтверждён сохранёнными receipts: Windows logical843073701bytes (`9b1fee8012ed1bb3c5564581099cfcbff6965cecf883b0ed18f443302be1053f`) и Mac95848278bytes (`b9f192ade8bfeb94af64152b6340df86f84fc2ea7e50563ef93dae761fa4aab0`). Указаны только завершённые generated403 build/out,404 RED build и portable404 build; active404 validation сохранён. Reviewer ничего не удалял; сжатие VM image или независимый guest filesystem inventory не заявляются.

Fresh ancestor ACL rejection подтверждён source review; отдельного ACL-mutation runtime cut нет. Следующая работа — actual protected playback consumer с fresh account/epoch/queue/row/delete/document fences, worker-owned UI lifecycle, отменой и actual last-release drain. Global storageWritable/localQueueComplete и canOpen/send/delete не открываются. Нет installed UI, hardware/accessibility, полной Debug/native68 матрицы, migration T117, полной T118/Windows parity, commit/merge/release authority. T116/#7444 и полная пользовательская цель остаются открытыми.
