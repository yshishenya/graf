# T116 / round403: независимая проверка retained-package metadata ACK

## Решение

Приняты SOURCE GO, selected Release native14/14, portable47/47, SDK Restore/Build и сохранённый postflight main для exact source ниже. В проверенном четырёхфайловом diff нет подтверждённых CRITICAL/HIGH. Это свежий semantic metadata ACK через уже удерживаемую read-only lease; не новая account/playback/delete authority, не пользовательский playback UI и не завершение T116. Global/selective admission не открываются.

Reviewer лично прочитал исходники, receipts, журналы и SDK TLOG, повторно перехешировал frozen/canonical inputs. VM, сборки и тесты reviewer не запускал; guest source/binary/idle сведения принимаются по сохранённому postflight main, а не по независимому обращению reviewer к VM. Единственная запись reviewer — этот новый отчёт; source, нормы, tasks, checklist markers и GitHub не изменены.

## Требования и область source review

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Высокорисковый срез идёт внутри существующего T116 по Spec Kit, не по облегчённому product lane. Переиспользованы прочитанные требования и scoped analyze C0/H0; gate 51af545d0cc8a4dc31c5ea0d65595f08dcb6be2c8a4e2194ee3c3d8da90174e0 и concurrency gate 32728e4b3150071c903f17d1be6363e9a3f8184adfadefdf0415e6e929bf4e8b не пересчитываются в глобальную приёмку. В начале403 лично проверен #7444 OPEN с каноническими метками, owner codex по feature.json; повторный live GitHub запрос при этом closeout не выполнялся.

Перед созданием отчёта повторно просканированы все 190 текущих checklist/report файлов: 29 с пунктами, 420 checked / 0 unchecked. Новый отчёт не содержит чекбоксов: после добавления будет 191 файл при тех же 29 и 420/0. Tasks неизменны: 120, из них 93 checked / 27 open. Сохраняется ранее проверенный объём 22 FR / 10 SC, без объявления их выполненными.

Лично повторно проверены неизменные SHA256 девяти нормативных файлов:

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

Сравнение с frozen402 `graf-f200-player402-green.WcZvxT/source.json` даёт ровно четыре изменённых input: `apps/windows/CMakeLists.txt`, `ProtectedCustodyMetadata.h/.cpp`, существующий `NativeCaptureStorageIntegrationTests.cpp`. Исторический dirty diff вне этого среза не объявляется заново проверенным.

Новая API принимает только retained read-only lease от StoreOwner::readPackage, private provenance и тот же cancellation token. Standalone Pair::read с unique blocked lease и borrowed writer origin не допускаются. Проверяются failed owner, cancellation, trusted root/store identity. Scoped job покрывает owner.validate и освобождается до собственного admission readImpl. Последний читает оба индекса и payload через те же native Files, без release/reopen, share-flag изменения или raw Files getter. Сравниваются selected slot, обе index generation/logicalLength/entries(version/envelopeBytes/flags), затем оба canonical payload существующим writeCustodyPackage. Charged codec buffers очищаются allocator при освобождении. Late cancellation не даёт положительный ACK. Existing sticky fault не сбрасывается; нового безусловного poisoning всего StoreOwner при package error нет.

Ponytail review: Lean already. Использованы существующие codec, allocator, std::equal и native lease; новый framework, dependency или алгоритм сериализации не введён. Избыточная повторная !files после guard не является блокером или причиной менять замороженные байты.

## История RED — без подмены квалификации

Все три исходных попытки сохранили configure/build=0, CTest=8, terminal=true.

LC268h: manifest 29980af62c5ef38b29fe75bf1f95e4bd420e7222b1fee5fa68dc35f8e87d6f18; receipt 4f3cb73526ee04ba1a7d3e3a41dc0c3fb48bd7fdabf10f6850002d0b2144057f; LastTest a8446486cf0f7dc76f34c12ddb54a0d3cbddb4000f22ce380e8c42d85ec952ed. Падение requires_genuine_sealed_inspection до ACK; не qualified ACK RED.

thj9vY: manifest d6cc2496080c57032460a22ffec96f35a2b333c954fe133f8271a10613e02761; receipt a31c6918c87e5797e787c893896268b66e56d4da4b1d45fbf2647f35a7bb6542; LastTest 08f1ea5d6ff0970e419fb3b64549ca8d054e2d7357450d140e0211342e707f6f. Все три inspection error=6/ioFailed, native=32, duration/frames=0; то же падение до ACK. Это второй неквалифицированный RED, не доказательство нужной ACK-границы.

Причина live-born пути сохранена отдельно: birth StoreOwner удерживает store.id с read/write access и FILE_SHARE_READ; холодный packed reader пытается открыть READ/shareREAD, несовместимое с существующим WRITE access. В тесте403 writer и birth owner реально освобождены, затем выполнен настоящий StoreOwner::open с тем же token, reopened owner удерживается через inspection/ACK. Share flags и Files policy не ослаблены. Live-born inspection этим НЕ исправлен и остаётся работой T116.

h4OvsS: manifest e348aabe20c16ea81d46c47db450077018de61dff1ac68cd4c33bbe0e172bb55; receipt 9257052163898d9cf74f35f4caa6335b12c62ad295be0f208cc4c2afd11a5311; LastTest 9eab852aa49a889d6f56c433190e0856e06f8a371aff14fd61aadb6d072850c8. Все три genuine inspection error/native=0, duration5000, decodedFrames240640; second open и guarded stub ACK дают ioFailed/native32. Exact assertion protected_package_revalidation_must_ack_retained_readonly_lease падает после disk_unchanged/memory_released=1. Этот RED квалифицирован. Позднее GREEN добавил четвёртый semantic case и усилил index/sticky assertions; идентичность всего RED/GREEN теста не заявляется.

## Exact GREEN evidence

Root: `/Users/yshishenya/Documents/graf-f200-revalidate403-green.OgLS8M`.
Manifest SHA256 `610ed57732272189a917a3005a4c4c152506bd5652fe1631d207a342a41cdd21`. Лично перехешированы 214/214 frozen и 214/214 canonical inputs: расхождений нет. Integration test SHA256 `a8bc3e32eeb32592404915af39a9d0cb8417273f83ba12b176792f2a0f1a0d6e`.

| Артефакт | Лично вычисленный SHA256 |
| --- | --- |
| receipt.json | 978fe7237ed97e05899be871741f853623e50e65f61f97a1c842caa757ed16df |
| native-LastTest.log | f9df6b2bc80302f2bb2fb2657c906eec8ff183606a8608197405fd84127e7dc4 |
| test.log | 75539de1d1a1ca0152cacec7113bd611d92c4841a7d5d04ffb5de8276173af95 |
| portable-receipt.json | a6ea37b34a41ff848d1d6d373fa2a142161a759e1acafdef1afab5802a900fd7 |
| portable47-LastTest.log | 3979b079106a5176bc9495258031c8f5e65e08d108b0b1104def9991d8d40017 |
| SDK-Restore.log | 20df6b940bb4f41fd442bc88059542ff6b98560d4d68f88dab0851b99ad3f8c3 |
| SDK-Build.log | f91b4f7a3462407af60ea2c65ad55452c30bc49933ef62ea90c171424cf15c50 |
| SDK-CL.command.1.tlog | ca9bee252609934ef1205c2567feaf7cc896765c019a662d67a47bc0193dc0f0 |
| postflight.ps1 | 57b954a7ddd8d99882f1c6ac038c2e7b636848c0afe11f95725fa7d020c06d54 |
| postflight.json | 3985224bfcdcccc570c8fa6d4cd8df9fbb50ceb87cf7892cbcb8bd20c154295c |

Native LastTest содержит 14 уникальных ID/имён, 14 Passed / 0 Failed; test.log подтверждает CTest384.00s. Это Release selected14 из registry67, НЕ full67 и НЕ Debug. Полные default suites: PackedOwner156.37s, PackedTree20.93s, WriteStream2.27s. Остальные11: inspection preparation, activeStop, readmodel, account problems, display timing, display owner quota, metadata admission, owner cancellation, reader drain, MediaEngine, package revalidation.

Новый selector37.76s: во всех четырёх случаях sealed/first_read/inspected/ACK/disk_unchanged/memory_released=1, exception0; genuine duration5000/frames240640. Независимый повторный open по-прежнему ioFailed/native32 — положительный ACK не получен ослаблением sharing. Control отвергает writer/null/token/foreign/cancel случаи; native-job quota10/native1816 и memory quota10 восстанавливаются до ACK1 после освобождения pressure. Index.0 и index.1 усечены в отдельных roots: fresh invalidContent7/native0, повторный writerFailed9; quota10 не стирает fault, после quota writerFailed9. Четвёртый случай меняет только существующий encrypted block с корректным размером/shape и неизменными индексами/поколением; semantic_changed=1, conflict8, cached_unchanged=1. Он проверяет canonical comparison выбранного slot; отдельная semantic mutation невыбранного slot не исполнена. Сравнение обоих slots подтверждено source review, но ACK не утверждает raw-byte identity произвольного исходного JSON или повторную AAC/member-integrity inspection.

MediaEngine10.87s сохраняет реальный playback regression: ready/muted/progress/pause/seek/resume=1, held_mf_clone/close_pending/release_drained=1, disk/memory=1. ActiveStop101.60s Passed; это конкретный generated concurrency case, не универсальная hardware/latency гарантия.

Portable receipt terminal=true, configure/compile/test=0. LastTest: 47 уникальных ID1..47 и имён, 47 Passed / 0 Failed. Main сообщил CTest25.01s; этот timing не используется как performance gate. Portable не исполняет Windows-only retained-lease/MF path.

Final receipt terminal=true, configure/build/test/sdk_Restore/sdk_Build=0. SDK logs подтверждают Restore и compile/link GrafWindowsApp.exe; сохранённый UTF16LE CL.command TLOG содержит actual ProtectedCustodyMetadata.cpp из exact OgLS8M guest tree. SDK app SHA256 по receipt/postflight `15643c728a785eb5046e4d6f03180fc64eeb1f9c9e355b7b7670b99614805322`. Приложение не установлено и не запущено.

Первый postflight launcher закончился Parallels255/PrlJob_GetRetCode invalid argument до guest receipt, не был принят. Main сообщил успешный повтор того же loader SHA без повторного исполнения тестов. Сохранённые postflight.ps1/json лично прочитаны: terminal=true, source_matches214, metadata_compiled=true, active_jobs0; native Integration EXE SHA256 `297c381e5a1bd6024c2b6391a2ae70e2f865fe2c1de22d73bdfbb5b28d3e77c5`, SDK TLOG hash совпадает с лично перехешированным файлом. Это readback доказательств main: postflight script отдельно хеширует/читает manifest и TLOG, поэтому атомарная same-captured-bytes привязка всех его чтений не заявляется. Reviewer не перехешировал гостевые EXE и не наблюдал live idle самостоятельно.

## Оставшиеся границы

Принят именно cold retained-package metadata ACK foundation. Не исправлен live-born StoreOwner inspection conflict; standalone Pair::read и borrowed writer не поддерживаются этим API. Свежие account/epoch/current queue/deletion/document fences и полномочия будущего пользовательского playback остаются обязанностью consumer, а не результатом bool ACK. Нового UI consumer пока нет. Нет installed app, hardware, полного native67, новой Debug matrix, release/commit authority или full Windows parity acceptance. T116/#7444 остаются открытыми; следующий UI/readback срез требует собственного test-first source/runtime review.
