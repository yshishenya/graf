# T116 / round401: независимая проверка Reader drain foundation

Проверка только чтением сохранённых исходников и свидетельств. Этот новый reviewer-owned отчёт не меняет checklist markers, нормы, tasks или GitHub. T116 остаётся открытым; глобальный admission не открывается.

## Решение и нормативные границы

SOURCE GO и принятие результатов selected Release native12 + portable47 в указанном ниже объёме. Ранее проверенный gate401 переиспользован: девять нормативных документов и применимый bridge contract неизменны, scoped analyze C0/H0; 420 checked / 0 unchecked в 29 checklist-файлах, всего просмотрено 188 checklist/report файлов; tasks 93/120, 27 открыты; T116 / #7444 OPEN, owner codex. Эти governance сведения относятся к предыдущей проверке401, а не к новому live-запросу GitHub при составлении отчёта.

Новый counter — отдельный charged atomic control block, не alias native state. Конструктор Reader увеличивает его последней невыбрасывающей операцией. Последний Release сохраняет counter, удаляет Reader вместе с native state/pin/charged allocation и лишь затем делает release-decrement. Все три места создания Reader присваивают weak observer; Clone разделяет counter через ReaderState. Read/Seek, admission limits и прежние quota assertions не ослаблены. Ponytail: лишних абстракций или зависимостей не найдено.

## Источники и соответствие

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Frozen GREEN: `/Users/yshishenya/Documents/graf-f200-reader401-green.YXZQYK`.

Лично проверены 212 frozen файлов по source.json и те же 212 canonical файлов: расхождений нет. Ранее проверенный frozen RED отличается от GREEN только ProtectedCustodyReader.cpp; тест, header и регистрация не подменены после RED.

Контрольные суммы SHA256:

| Артефакт | SHA256 |
| --- | --- |
| GREEN source.json | f7116c4ecb9a90e08bb3f74420baf0678ca5240f372d53955a279ff8efe67e28 |
| GREEN native-LastTest.log | 5a519507696413ec8d6a43188e6a658059ae9f1ce4deab2572e500019102455b |
| GREEN test.log | ba41518f14d3cc223201fdb72e94df1131056eeb2c0b81db5272b156eb64a7ac |
| GREEN build.log | 635232db147cd97834d2bcfceb7cd9a9a8f61a14534cfc1eeabb6e329120ff22 |
| GREEN validate.ps1 | 8f1afe63df7dc5dd45665d970519c1ef40d2279b21e7fe6f932ea05f45c0ed2d |
| portable-receipt.json | 4229715a04fe7ad493620a2fb1a8d576f7f6708b4077b186fd3b361e9c38d6e3 |
| portable47-LastTest.log | f670559b27b14c3d037a1d8c3bc53f0edfe99be090c6761a09121fd5d6692c5c |
| portable-test.log | a8d536aa7ce8d878d945c3d2724989a6aa208ebda72cc5c129cf054b4b4a1394 |

## Фактические результаты

RED `/Users/yshishenya/Documents/graf-f200-reader401-red.hMm0g2`: receipt terminal true, configure/build 0, CTest 8; отдельный процессный exit3 этим receipt не заявляется. Точный assert `reader_release_drain_requires_actual_instance_observer`, observed=0 при owner_released/pins_released/memory_released=1. RED source SHA dce62d01e8eff996d538b57029eb71a0beeb86312b9ee558baf521cc877f71b2; receipt dbd8f6acd3da475995416f1998980b091bac4ecbd91752e9c74d33e01a23bc77; LastTest 934ea34bfa66a764fb4daec6c487b541ea25853c6cae855c2f9f6769e6eb4d3e.

GREEN native: LastTest содержит 12 уникальных ID/имён и 12 Passed, 0 Failed; test.log подтверждает 12/12, 332.84 s. Все команды Release. Три default suite: PackedOwner, PackedTree, WriteStream; девять selectors: inspection preparation, activeStop, readmodel, account problems, display timing, display owner quota, metadata read admission, owner cancellation, новый reader release drain.

Drain в default PackedTree и отдельном selector: observed/cloned/addref_unchanged/cancelled_still_live/external_released/all_released/owner_released/pins_released/memory_released=1. Selector также вызывает прежний packedReaderAdmission с full-quota и pin-limit отказами; его assertions сохранены.

ActiveStop: actual old packed-read cut, both_eos_finalize_serviced=1, wire=0; recording result state=1 base=3 target=4; sealed adoption/restart5=pass. Inspection preparation: actual_prepared=1, wire=0, cancel/drain=pass. Display timing: timing/current account/exact queue/quota/logout/stale/native cut/disk/drain/memory положительны, upload_calls=0. Обе owner quota формы возвращают allocation10 под давлением, затем recovery/queue_readable/future_created/disk/memory=1. Нижние 5 и owner 4 negative/positive cases сохраняют sticky physical/semantic fault и отличают отмену от физического995.

Portable: receipt terminal true, configure/compile/test=0; LastTest содержит ровно 47 уникальных ID 1..47 и 47 уникальных имён, 47 Passed, 0 Failed; CTest 23.70 s. Это не выполнение Windows-only путей на Mac и не показатель пользовательской задержки Stop.

## Отдельный MediaEngine capability probe

`/Users/yshishenya/Documents/graf-f200-mediaengine401.YR94ws`: receipt terminal true, build/run=0. Лично проверены probe.cpp/vcxproj против source hashes receipt. Фактически AUDIOONLY + FORCEMUTE + DISABLE_LOCAL_PLUGINS, источника нет; COM/MF/factory/create/shutdown/MF close S_OK, callbacks=0, notify_destroyed=1. Receipt SHA 06382751e7fedba5adf20763996596ac2168aa3a2ce357c5529e04c50c24f374; probe.log SHA 379bab861c6d50f7bba7025fe2ccf9bd767b4fa3dcafdc347da0b546046b70c3. Это создание и закрытие MediaEngine, не playback proof.

## Непроверенное и оставшиеся этапы

На момент чтения общий GREEN receipt.json отсутствует: validate.ps1 сохраняет его после SDK Restore/Build, получения app hash и окончательной native source проверки. SDK и этот финальный postflight не принимаются данным отчётом. Reviewer не запускал VM и не перечитывал guest EXE/PDB; текущие guest artifact hashes, process exit каждого теста и native idle не подтверждаются независимым VM readback. Native12 принято по сохранённым CTest/LastTest, а не как завершённый общий SDK run.

Нет actual MediaEngine source input, SetSourceFromByteStream/play/pause/seek, callback-drain proof, player UI, installed/hardware acceptance, Debug native run или full65 execution. Counter наблюдает завершение Reader instances, не всех MF callbacks. Будущий consumer должен удерживать base Reader, передавать MF только Clone, исключить новые clones перед acquire-проверкой, считать missing/expired observer и count!=1 незавершённым drain. Нельзя освобождать proof по таймауту. Account/logout/delete authority, worker-only native last release и закрытый global readiness сохраняются.

## Дополнение: финальный SDK receipt и guest postflight401

Добавлено после предыдущего чтения; историческое pending выше сохранено. Лично прочитаны финальные receipt/logs и сохранённый postflight, без обращения к VM и без новых запусков.

GREEN receipt SHA256 `63b34bb5dc0e7bbec6fbdb4f9d1ed50338ebf3016ca01626b92dd6ef645eca52`: terminal=true, stage=green, тот же manifest f7116c4e…, configure/build/test/sdk_Restore/sdk_Build=0. App EXE SHA256 `994b9f09abbe4a018e782379900a1b046fc9e22afb4ac361e3de37ae7a9823dc`. SDK-Restore.log SHA256 `477b0e9936150041f696dbb884fdf6451d79e85ba53a4a3f90bfa152e5178394`; SDK-Build.log `88b0ab318a7e37bc008cf4f6fe0e78272c3bfb3f9951707fc53b8646066414c0`. Корректно декодированный UTF16LE build log подтверждает AppMain.cpp, verified AEC3 identity 846fe90a289f58b7c9303a635142aa2c7caa93e5 и успешный выход GrafWindowsApp.vcxproj в Release EXE. Принимается SDK compile/link, не запуск приложения.

postflight.json SHA256 `df89c55c2cecf962f18c1207fb32f99f63acbd9c92eb51ff933d1db126fdce34`: sources=212, source_match=true, idle=true, тот же app EXE hash. Скопированный CL.command.1.tlog лично перехеширован: `00f34c3a56cd5b4891065938d756cb4e3ee8fe2637632096ad059514f09b3476`, совпадает с postflight. postflight.ps1 SHA256 `5fd4eb314d54f8d545b3db32f8a0c0537d81effc8ec6afbe0dc3555893f0a526`; путь out/obj/GrafWindowsApp/x64/Release согласуется с IntDir в Directory.Build.props. Предыдущий TLOG_MISSING по неверному helper path — сообщённый main collector failure, не product/test failure и не повторное выполнение тестов.

Guest source/EXE/idle readback принят по сохранённому свидетельству main, не как независимое VM-наблюдение reviewer. Фильтр idle в helper проверяет ctest/MSBuild/cl/link/probe, не объявляется всеобщей инвентаризацией процессов. Postflight не содержит hashes всех test EXE/PDB и не даёт новых доказательств MediaEngine playback. Все прежние ограничения, отсутствие installed/UI/hardware/Debug/full65 acceptance и открытый T116 сохраняются. Очистку выполняет и документирует main; reviewer ничего не удалял.
