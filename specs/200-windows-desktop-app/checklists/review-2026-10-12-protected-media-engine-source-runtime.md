# T116 / round402: независимая проверка protected MediaEngine foundation

## Решение и границы

Приняты SOURCE GO, selected Release native13 после контролируемого повторного прогона, portable47, SDK compile/link и сохранённый guest postflight main на exact source ниже. Подтверждённых CRITICAL/HIGH в проверенном source diff нет. Это worker-only playback foundation, не пользовательский player UI, installed/hardware acceptance или завершение T116. Global/selective admission остаются закрытыми.

Reviewer читал исходники и сохранённые свидетельства, не запускал VM/build/tests, не менял source/tasks/GitHub/checklist markers и не выполнял очистку. Создан только этот отчёт.

## Требования и минимальность

Canonical branch codex/200-windows-followup, HEAD b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1. В начале402 независимо подтверждены прежние девять нормативных хешей, bridge contract и scoped analyze gates 51af545d0cc8a4dc31c5ea0d65595f08dcb6be2c8a4e2194ee3c3d8da90174e0 / 32728e4b3150071c903f17d1be6363e9a3f8184adfadefdf0415e6e929bf4e8b. Для данного construction scope C0/H0; это не глобальное заключение о реализации фичи. Live #7444 тогда OPEN с каноническими метками, owner codex по feature.json.

Перед этим отчётом просканированы 189 checklist/report файлов; 29 содержат пункты, 420 checked / 0 unchecked. Новый отчёт не содержит чекбоксов. Повторно посчитаны 22 уникальных FR, 10 уникальных SC, 120 tasks: 93 checked / 27 open. Срез покрывается существующим T116, новой задачи/нормы/схемы не требует. Все FR/SC этим не объявляются выполненными.

Проверены новые ProtectedLocalRecordingPlayback.h/.cpp, private exact-cancellation retention в genuine ProtectedInspection, CMake/SDK inclusion и новый integration selector/oracle; исторический dirty diff вне402 не перепроверялся. Proof не открывает account/delete authority; open допускает genuine sealedNormal/degraded с проверенным playback ref, exact token identity и существующим Reader observer. MF получает свежий Clone через IStream→IMFByteStream и нейтральный label, без plaintext path/URL fallback; autoplay выключен. Callback владеет только charged scalar error state. Shutdown/byte close/clone release precede acquire witness==1, proof release и MF/COM shutdown. Ошибки сохраняют владение; worker destructor не выдаёт timeout за drain.

Ponytail review: Lean already. Ship. Это verdict минимальности, не разрешение commit/release. Ручные COM IQ/refcount и charged allocator повторяют Reader pattern; новый framework не нужен. Borrowed test pointer во время open не делает AddRef: настоящий внешний reference берётся только после успешного open, объявлен после player и освобождается до его destructor, в том числе при исключении.

## Источник и привязка

Evidence root: `/Users/yshishenya/Documents/graf-f200-player402-green.WcZvxT`.

Лично повторно перехешированы все 214 frozen inputs и те же canonical inputs: 214/214 совпадают с source.json, расхождений нет. Manifest SHA256 `e5168843fdd17f4a8872cc896655861ebb72571b75a6dc6773dd790820314892`.

| Сохранённый артефакт | SHA256 |
| --- | --- |
| resume-receipt.json | ca6f6a5bf0708f07be850247a404acb84ccdf3a91ff847904eb0bcd428949d0f |
| postflight.json | de6d7709eee8ed0d8955ab5c28c73b2cb2ef65ca5ddecb7d13e14d2880fc9ee4 |
| CL.command.1.tlog | 78085396c316bfe83fa5ce92becba43ebd128b53681f181a9c6b5fa1e1855f6c |
| native-resume-LastTest.log | 67d88ae939202812ac5f210ecfacdb0f8ef2bb0b4dec247e9cbf87c881dd2b6c |
| test-resume.log | e4dc3e4db99eda1426a3a591068c6fa43c7608114c6dca1d07c23d3ce880aab9 |
| portable-receipt.json | 3a58755f44a2569177b51a66ca06ef3bb3244a7ebef200a29502cf95de772dc8 |
| portable47-LastTest.log | 04a5f0149e53486e6f9d62834e689c502972fb8041ed52f3240dd7be3cc9a94d |
| SDK-Build.log | 2e17e791f739f105e29f514032182ef2cb0b86667883cdb03f28c18c44a8d057 |
| SDK-Restore.log | b3da31a4a24d8859932625104088298155783a7b71b013e1177d813d33106f16 |

## Предыдущие неудачные попытки сохранены

RED root `/Users/yshishenya/Documents/graf-f200-player402-red.KtWScQ`: configure/build=0, CTest=8, genuine sealed/inspected/negative/disk/memory=1, opened=0; named assert protected_media_engine_must_play_pause_seek_and_drain. Receipt SHA 089e4ac9111e684637e551025e58e4142b294a77f84c7a6cc2ee192460b46d98, LastTest ad86e9db83b4851de9355cacb56fa6e0b04b9f81b2f3f3782e257e4f0fce1d4e. Это намеренное отсутствие реализации в runtime RED stub, не доказанный дефект финального CPP. Этот первый oracle ещё не содержал последующее усиление held-MF-Clone; идентичность всех тестов RED→final GREEN не заявляется.

Первая WcZvxT попытка: 12 Passed / 1 Failed, PackedOwner timeout179.97s при внешнем пределе180s, общий CTest371.96s. Оригинальный receipt terminal=true/test=8 сохранён (SHA3963ba2fecb4c71b1e8ce6f28e1b0f5c3ea7305e5b027914a788cbd9771fa9dd); оригинальный LastTest SHA0358b5d05121f07c77d26493acc1b3583777761a504e14236c714603d2812809. Причина превышения не установлена; оно не объявляется ни product assertion RED, ни безвредным environmental failure. Старый yAUu3F без нового held-Clone oracle не используется вместо final proof.

## Фактический final runtime

На тех же frozen214 без правки product/test source повторно исполнены все13 последовательно с явным внешним CTest timeout300; resume script не перестраивает native CMake targets перед тестами. Новый LastTest содержит 13 уникальных ID/имён, 13 Passed, 0 Failed; CTest335.25s, PackedOwner145.05s. Три полных default suite: PackedOwner, PackedTree, WriteStream. Остальные десять selectors: inspection preparation, activeStop, readmodel, account problems, display timing, display owner quota, metadata read admission, owner cancellation, reader drain и MediaEngine. Это selected13 из registry66, не full66 и не Debug.

MediaEngine9.74s: sealed/inspected/opened/ready/muted/invalid_seek/progress/paused/sought/resumed=1, error/open_error/native=0. Фактическая duration5.013s, position0.111→pause0.111→seek2.507→resume2.625. held_mf_clone=1, close_pending=1, release_drained=1: внешний COM reference именно MF input Clone препятствует drain; после реального Release тот же player закрывается. closed/repeated_close/commands_closed/disk_unchanged/memory=1. Missing proof/token, wrong token и заранее cancelled token отвергнуты; это не проверка всех возможных гонок/отказов.

Прежние native regression cases также Passed: activeStop обслуживает оба EOS/finalize при old packed-read cut, wire0 и sealed adoption/restart5; Reader drain/pin/full-quota assertions сохранены; owner quota recovery, metadata physical/semantic sticky faults, cancellation и display stale-account cases не заменены слабее.

Portable receipt terminal=true/configure=compile=test=0; LastTest содержит 47 уникальных ID1..47 и имён, 47 Passed, 0 Failed; CTest45.95s. Portable PASS не исполняет Windows-only MediaEngine path и не доказывает hardware/Stop latency.

Resume receipt terminal=true/test=sdk_Restore=sdk_Build=0. SDK log подтверждает обычный production ProtectedLocalRecordingPlayback.cpp, verified AEC3 identity846fe90a289f58b7c9303a635142aa2c7caa93e5 и Release GrafWindowsApp.exe. Лично прочитан UTF16LE CL tlog: запись production playback CPP из frozen WcZvxT и следующая compile command; tlog hash совпадает с postflight. Это SDK compile/link обычного CPP, не execution SDK app.

App EXE SHA256 `5ab211848455528b440a9fa21bb4ab0d986f067cee15ad2f33e8cc900cfbc38c`. Postflight terminal=true, source_matches=214, playback_compiled=true, active_jobs=0 и тот же EXE hash. Guest source/EXE/idle приняты по сохранённому main readback, не как независимый VM-запуск reviewer; helper фильтрует ctest/MSBuild/cl/link/*Tests. Отдельные test EXE/PDB hashes этим postflight не предоставлены.

## Оставшиеся границы

Повторный PASS не объясняет первый timeout и не принимает производительность/SC-003. Нет player UI/fresh UI authorization, audible/hardware proof (тест FORCEMUTE), installed app, Debug/full66/full T116 или release acceptance. Native MF internal allocations не объявляются полностью charged. Нет исчерпывающего codec fault/partial initialization/quota/Shutdown failure matrix, degraded-playback runtime или доказательства завершения всех callback objects; Reader witness доказывает завершение Reader instances, не всех MF callbacks.

Следующее подключение сохраняет account/epoch/current-row/delete fences и worker-only native last release; retained-package ACK требует собственного test-first source/runtime gate. Нельзя ослаблять share flags, выводить authority из generic proof или открывать global/selective admission по foundation PASS. T116/T117/T118 и прочие незавершённые задачи остаются открытыми. Cleanup main — отдельное действие и журнал; reviewer не удалял builds и не принимает cleanup по факту этого runtime отчёта.
