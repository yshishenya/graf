# Независимый review T114Index Phase0: большой ZERO-only индекс

Дата: 2026-10-01.

**Результат: APPROVED для узкого review исходников, заложенных проверок, обновлённого runner и согласованности Index build/runtime receipts. Блокирующих ошибок в заявленном объёме не обнаружено. Build receipt содержит build_exit=0; итоговая runtime-квитанция содержит exit_code=0, Context child=0 и stderr=0. Это Phase0 ZERO-only metadata; полный T114: NOT READY.**

## Объём и границы работы

Reviewer лично заново прочитал `/Users/yshishenya/.agents/skills/code-reviewer/SKILL.md`. Полностью прочитаны `IndexProof.cpp`, `index-build.cmd`, текущий `ContextProof.cpp`, общие `BlockProof.cpp` и `CommitProof.cpp`; затем дополнительно полностью прочитаны обновлённый `context-run.ps1`, `index-build-run.ps1`, Index build receipt и окончательный runtime receipt. `ProtectedMfProof.cpp` ранее прочитан целиком; его текущий SHA-256 совпал с рассмотренным в resource review.

Основная внешняя папка: `/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/`. Общие helpers: `../f200-dpapi-block-proof.PRtfBz/BlockProof.cpp` и `../f200-dpapi-commit-proof.9xdyLi/CommitProof.cpp` относительно неё.

Сборки, тесты, VM, устройства, приложения и GitHub reviewer не запускал и не менял. Единственная запись — этот новый отчёт; код, существующие документы и отметки чеклистов не изменялись. Путь изменения документа: **Docs-only / mechanical**, проверка чтением Markdown и сверкой SHA-256. Полные продуктовые ворота T114 данным review не принимаются.

## Семантика и безопасность вычислений парсера

`IndexProof.cpp:9-16` использует текущую структуру: четыре little-endian uint64 в заголовке длиной 32 байта и по два uint64 на запись длиной 16 байт. Схема=1; поколение ненулевое и соответствует чётности slot; логическая длина не превышает 64 GiB; число строк равно округлению длины вверх до блока 256 KiB.

Максимальная размерность: **262144 строки × 256 KiB = 68 719 476 736 байт = 64 GiB**. Реальный payload индекса: **32 + 262144×16 = 4 194 336 байт = 4 MiB + 32 байта**. Данные медиа такого объёма не создаются и не читаются. Все строки имеют version=0, cipher=0, flags=1; это явные ZERO-записи той же формы, что и в ProtectedStream, без ссылок на реальные зашифрованные блоки.

Парсер сбрасывает выходное поколение до любой проверки. Размер минимум 32 байта проверяется до get64. Ограничения length≤64 GiB и count≤262144 стоят до округления и `count*16`; благодаря короткому вычислению `||` заведомо недопустимые значения не доходят до этих операций. При допустимых значениях сложение length+blockBytes−1 и расчёт смещений не переполняются. Точная длина payload проверяется до цикла; цикл проверяет каждую из count записей, включая последнюю, через ограниченный get64. Неподдерживаемые flags, ненулевые version/cipher не принимаются.

Памятный парсер допускает и меньшие корректные ZERO-only размерности. Дисковый `indexSnapshot` вызывает unprotect с точным максимальным expectedPayload, поэтому текущий дисковый путь намеренно принимает только payload максимальной длины этого proof. Это не универсальный reader всех размерностей или реализованный reader смешанных ZERO/nonzero индексов.

## Отрицательные проверки: что именно доказывают десять случаев

Положительный случай сначала требует успешного разбора полного массива и generation=1. Каждый отрицательный случай создаёт свою копию этой базы, выставляет выходное поколение 999 и требует одновременно false и generation=0. Счётчик увеличивается только после проверки. Ошибка построения входа, get64 или самого парсера не превращается в ожидаемый отказ: исключение выходит в общий FAIL.

| Случай | Изменение | Проверяемый отказ |
| --- | --- | --- |
| 0 | schema=2 | неподдерживаемая схема |
| 1 | generation=0 | отсутствие допустимого поколения |
| 2 | generation=2 при slot=1 | несовпадение слота |
| 3 | length=64 GiB+1 | превышение логической длины |
| 4 | count=262145 | превышение числа записей |
| 5 | удалён последний байт | несовпадение точной длины |
| 6 | добавлен байт | превышение максимального payload |
| 7 | flags=2 в первой записи | неканоническая ZERO-запись |
| 8 | version=1 в первой записи | ненулевая версия ZERO-записи |
| 9 | packed=1 в первой записи | flags=0 и cipher=1 вместо ZERO |

**Ограничения покрытия, не блокирующие текущий узкий review:** все мутации полей записей относятся к первой строке. Нет отдельной отрицательной мутации середины/последней строки; receipt этих десяти случаев сам по себе не доказывает обнаружение дефекта преждевременного завершения цикла. Нет отдельного count/length mismatch внутри допустимых диапазонов. Случай 9 одновременно меняет flags и cipher, поэтому не изолирует отказ для cipher≠0 при flags=1. При расширении заявления до покрытия каждого условия достаточно точечных случаев для этих пробелов; текущий исходник соответствующие условия проверяет.

Десять случаев проверяют семантический парсер в памяти. Невалидные семантические payload с корректным DPAPI envelope на диске отдельно не публикуются. Дисковая порча ciphertext проверяет цепочку DPAPI/envelope и выбор индекса, а не десять отдельных семантических отказов через файловый путь.

## Default limits и отдельная компиляция IndexProof

В `BlockProof.cpp:14-17` default `F200_MAXIMUM_PAYLOAD` остаётся **1 MiB**. `IndexProof.cpp:3` задаёт **4 198 400 байт = 4 MiB + 4 KiB** до включения ProtectedMfProof → CommitProof → BlockProof. Override применяется к данной единице компиляции; `index-build.cmd` не задаёт глобальные compiler defines для других программ.

Этот предел больше реального индекса на 4064 байта. `protect` требует непустой payload≤maximumPayload; `validate` проверяет точные context, длину и SHA-256 context/payload; `unprotect` ограничивает ciphertext и expectedPayload до DPAPI. `readCipher` проверяет размер файла до выделения Bytes и ограничивает его maximumPayload+4096. В этом proof все размеры безопасно помещаются в DWORD/ULONG, включая prefix 64 байта и ciphertext allowance.

Обычная компиляция ContextProof и прежних block/commit/resource/publish программ без override сохраняет 1 MiB default. Это утверждение об исходниках и команде Index-сборки, не независимая проверка уже собранных бинарных файлов. Пределы ProtectedStream — 64 MiB потока, 256 записей индекса — не менялись; новый парсер является отдельным исследовательским путём. Он не расширяет продуктовый ProtectedStream до 64 GiB.

Теперь определения общих helpers прочитаны полностью: writeNew использует CREATE_NEW, проверяет handle до записи, требует точный WriteFile, FlushFileBuffers и close; readCipher проверяет reparse/hardlink, тип файла и защищённую DACL до чтения. Контекст зависит от собственного root и вида index-slot; envelope дополнительно сверяет context и digest после DPAPI, так что одного успешного native unprotect недостаточно. Blob очищает native память перед LocalFree. Это усиливает подтверждённый источник доказательства по сравнению с прежним review, где эти определения не входили в разрешённое чтение.

`inspect` проверяет защищённость DACL и число ACE, но не повторно сверяет полное содержимое SID/mask каждой ACE; Security создаёт DACL из user+SYSTEM. Сам CommitProof прямо исключает adversarial-path proof. Защита от произвольной враждебной замены каталога/ACL, полная privacy-приёмка и все исключительные пути очистки plaintext не принимаются этим исследованием синтетических байт.

## Публикация, восстановление и сохранность файлов

`IndexProof.cpp:27-32,51-60` создаёт собственный случайный каталог на fixed NTFS, публикует generation=1 в index1, затем generation=2 в index0. Каждый временный файл создаётся через writeNew с CREATE_NEW, flush/close, затем MoveFileExW с REPLACE_EXISTING|WRITE_THROUGH, после чего опубликованный файл проходит inspect и FlushFileBuffers/close. Собственная временная запись исчезает посредством rename, а не GC.

selectIndex проверяет оба слота и выбирает максимальное допустимое поколение. Проверки требуют latest=2, затем после побитовой порчи index0 — fallback=1, затем после порчи index1 — false с generation=0. Нет автоматического пустого индекса или успешной пустой авторитетной версии при отказе обоих слотов.

Два начальных поколения заполняют разные слоты: этот proof не проверяет замену уже существующего опубликованного индекса третьим поколением. Нет crash cuts во время большой публикации, многократных попыток, восстановления после оставшегося index-t<generation> или конкурентных writers. Имя временного файла здесь содержит только поколение; для фиксированных 1/2 в новом каталоге оно уникально, но это не принятие стратегии повторной записи после прерванной публикации.

Сохранность ciphertext проверяется хешами обоих файлов до/после инъекции key-unavailable и до/после восстановления при обоих уже испорченных индексах. После всех действий требуется ровно два обычных файла и суммарная длина≤2×(F200_MAXIMUM_PAYLOAD+4096). Поэтому удаления, создания пустой замены или изменения байт этими двумя отказными read-путями не могут пройти соответствующие проверки. Отдельное сравнение байт непосредственно до/после успешного fallback=1 отсутствует; fail-preservation утверждение в proof относится к двум полностью отказным случаям.

## Инъекция key-unavailable и обработка ошибок

`indexSnapshot` сначала успешно читает ciphertext, затем при keyUnavailable увеличивает счётчик, устанавливает NTE_BAD_KEY_STATE через явный `static_cast<DWORD>` и возвращает false **до вызова CryptUnprotectData**. Проверка требует generation=0 и ровно две достигнутые инъекции. Посторонняя ошибка readCipher до границы не может выдать тот же PASS: она либо прерывает proof исключением, либо не увеличивает счётчик до двух.

Это корректная ограниченная проверка отсутствия авторитетного индекса и сохранения ciphertext при введённом отказе двух read boundaries. Она не моделирует реальную потерю DPAPI profile/master keys, отказ native DPAPI с этим кодом, восстановление ключей или пользовательский интерфейс такой ошибки. Сам NTE_BAD_KEY_STATE не проверяется вызывающим кодом и не сохраняется как отдельная классификация ошибки; selectIndex возвращает лишь bool и поколение. `actual_profile_loss=false` в итоговом выводе соответствует этому ограничению.

Неожиданные ошибки handles, файлового доступа, hash и flush не маскируются под ожидаемый parser rejection или успешное восстановление: require/исключение приводит к верхнему FAIL и exit 1. DPAPI/envelope/semantic недействительность возвращает false и допускает явно проверяемый fallback. Все RAII-объекты освобождаются при нормальном выходе и C++ исключении; каталог с синтетическими индексами намеренно сохраняется. IndexProof не инициализирует COM/MF и не выполняет encode/decode, несмотря на включённые определения общего файла.

## Границы запуска и измерений

`ContextProof.cpp:48,53,80,84-90` распознаёт `--index-user-dacl`, выбирает фиксированный sibling IndexProof.exe и передаёт `--medium`. Он создаёт ограниченный medium token, добавляет user ACE только в default DACL этого токена, создаёт дочерний процесс приостановленным и помещает его в собственный Job с KILL_ON_JOB_CLOSE до ResumeThread. IndexProof отдельно проверяет фактическое medium/noadmin. Индексная ветка имеет внутренний watchdog **35 s**; resource сохраняет 60 s, обычный child — 10 s.

Свободное место проверяется до записи: минимум 64 MiB. Реально создаются только два индекса приблизительно по 4 MiB плюс служебный overhead. На успешном пути финальный обход ограничен двумя объектами; размеры каждого читаемого ciphertext ограничены общим helper. Память parserGuards ограничена базой и одной копией на отрицательный случай; файл/metadata loops имеют фиксированный максимум. Большие значения заголовка не ведут к выделению медиа или неограниченному обходу.

`publish_two_us` включает построение двух ZERO-массивов, защиту и две публикации с барьерами; это не время одной атомарной публикации. `reopen_two_us` включает чтение, DPAPI/envelope и семантическую проверку обоих индексов. Lifetime memory peaks относятся ко всей жизни IndexProof, включая parser negatives и инъекционные проверки. Итоговые значения приведены ниже; критериев производительности или SC-003 код не проверяет.

`index-build.cmd` собирает только IndexProof.exe с x64 MSVC `/std:c++17 /EHsc /MT /O2 /W4 /WX`, возвращая exit cl. Изменённый ContextProof требует отдельной актуальной сборки. Main сообщил её terminal exit 0 и новый Context EXE hash; этот hash сверён со значением обновлённого runner. Самостоятельный Context build receipt reviewer не предоставлен.

## Исправление сборки и Index build receipt

Main сообщил первый build_exit=2 при `/WX` из-за неявного signed HRESULT → DWORD в SetLastError, затем ошибку получения результата Prl и отсутствие Index EXE по ограниченной инвентаризации. Эти промежуточные сообщения не используются как доказательство готовой сборки.

Текущий `IndexProof.cpp:37` содержит `SetLastError(static_cast<DWORD>(NTE_BAD_KEY_STATE))`. Явное приведение устраняет неявное преобразование к типу параметра SetLastError и сохраняет введённый код ошибки без изменения read-boundary сценария. Исправленный файл повторно прочитан целиком; SHA-256=`1eccae197bcda610e9d33c001254e4c27be14ede461c44dd683a7b0a24b7fa97`. Остальные ранее рассмотренные source hashes не изменились.

`index-build-run.ps1` вызывает index-build.cmd, немедленно сохраняет LASTEXITCODE в собственный buildExit, формирует JSON schema=1 с build_exit/source_sha256/exe_sha256 и возвращает именно сохранённый buildExit. EXE hash записывается только при buildExit=0; отсутствие доступного EXE на этом пути приводит к ошибке Get-FileHash, а не к успешному receipt с null-хешом.

Полностью прочитан `index-build-result-1e39e643-0baf-4fb7-8902-fcf4cbf4dd25.json`:

```text
schema=1
build_exit=0
source_sha256=1eccae197bcda610e9d33c001254e4c27be14ede461c44dd683a7b0a24b7fa97
exe_sha256=0ef7d9af91c3697934cdb14d4a13b2e33721a8b19b797006a3f94df324443c15
```

Source hash совпал с независимо вычисленным текущим хешем; EXE hash совпал с переданным Main и закреплённым в runtime runner. SHA-256 самой build-квитанции=`a245d9988f44aaeef2c9f7e7e24444aaa4a38fd41b9c5490e4bce5e1e41eb092`.

Это согласованная metadata-квитанция завершения команды сборки. Wrapper хеширует единственный IndexProof.cpp после сборки: он не фиксирует source до запуска, транзитивные includes, compiler version или build flags в JSON и не является атомарной аттестацией binary↔всех source. Reviewer отдельно фиксирует хеши helpers и команды сборки в этом отчёте, но не воспроизводит сборку и не хеширует байты EXE самостоятельно.

## Проверка обновлённого runtime runner

`context-run.ps1` добавляет отдельный `-Index`. Он запрещает смешивание Index со Spawn/UserDacl/NativeArm64/Mf/Playback/Publish/Resource и выбирает фиксированный sibling IndexProof.exe через `--index-user-dacl`. PlaybackFault сначала включает Playback и также попадает под запрет смешанных режимов.

Закреплённые EXE hashes:

```text
0ef7d9af91c3697934cdb14d4a13b2e33721a8b19b797006a3f94df324443c15  IndexProof.exe
83ce6724332dd291f1b1ce385a953253cb10ac585d952e771018b5fa71cae148  ContextProof.exe
```

Context EXE проверяется до и после запуска; Index EXE — до запуска Index-режима и после завершения. Для Index задан внешний watchdog 45 s при внутреннем Context child guard 35 s. Resource сохраняет 70 s/60 s, обычный контекст — 15 s/10 s. Старые MF/playback/publish guards остаются 45 s/35 s.

Runner считывает stdout/stderr асинхронно, проверяет их длину после завершения, сохраняет output/exit/stderr в JSON и возвращает exit ContextProof. Index поля добавляются к ordered metadata явно: index, index_sha256; spawn и user_dacl дополнительно включают Index. В текущем receipt подтверждены index=true, spawn=true, user_dacl=true при выключенных остальных proof-режимах.

Проверка длины stdout≤4096/stderr≤1024 символа выполняется после чтения и не является жёстким пределом памяти во время чтения. Runner не разбирает полноту PASS-маркеров; наличие JSON не означает успешный запуск при exit≠0. Полнота маркеров и успешный exit проверены reviewer по окончательному receipt.

## Окончательный runtime receipt: Round138

Main обозначает этот результат Round138. Полностью прочитан `context-result-fda8c038-fbf7-46b4-907d-cd74dc66da11.json` из внешней папки. SHA-256 самой квитанции: `75095009e16d2b889238c04c34b344cc7bba92e78f401e8329f568c6d13005d2`.

Согласованность metadata подтверждена:

- schema=1; index=true, spawn=true, user_dacl=true;
- MF/playback/publish/resource=false, хеши этих выключенных proof-режимов=null;
- index_sha256 совпадает с EXE hash в build receipt и закреплённым Index hash runner;
- exe_sha256 совпадает с новым Context hash runner;
- exit_code=0, stderr_bytes=0; CHILD_RESULT exit=0x0 и medium_nonadmin_verified=true;
- CONTEXT_RESULT: medium_integrity=8192, restricted_admin=false, identity_restored=true, global_acl_changed=false; доступ к window station/desktop успешен;
- присутствуют INDEX_PARSER_PASS, INDEX_DISK_PASS и завершающий INDEX_PROOF; FAIL в сохранённом output отсутствует.

Terminal exit 0 и отдельные проверки EXE после запуска сообщены Main. Reviewer непосредственно проверил exit_code=0 в JSON, код возврата runner, его before/after hash checks и повторно вычислил все source/runner/receipt hashes. Byte-level hashes самих EXE reviewer отдельно не вычислял.

| Поле квитанции | Проверенное значение |
| --- | ---: |
| entries | 262144 |
| logical_dimension | 68 719 476 736 байт |
| rejection_cases | 10 |
| payload_bytes каждого индекса | 4 194 336 |
| objects | 2 |
| disk_file_bytes двух ciphertext | 8 389 260 |
| publish_two_us | 609295 |
| reopen_two_us | 550852 |
| lifetime_peak_commit | 27 152 384 байт |
| lifetime_peak_resident | 39 804 928 байт |

Значения длины payload, числа строк, файлов и суммарной длины ciphertext согласованы с проверками источника и пределами helper. INDEX_DISK_PASS подтверждает latest=2, fallback=1, both_invalid_rejected=true, key_read_injections=2 и failures_preserve_bytes=true. Эти маркеры печатаются только после соответствующих require; успешный конечный exit исключает принятие только промежуточного parser PASS.

Две публикации заняли 609,295 ms, чтение и семантическая проверка двух индексов — 550,852 ms в одном запуске. Это измерение ZERO-only metadata, без расшифровки и чтения 64 GiB media blocks. Его нельзя переносить на восстановление большого смешанного/nonzero индекса или использовать вместо ранее измеренного resource reopen 9,44 s при 64 MiB реальных сгенерированных блоков: пути проверяют разные объекты.

Итоговый INDEX_PROOF сохраняет zero_only=true, media_allocated=false, actual_profile_loss=false, power_loss=false и product_changed=false. Получен узкий runtime результат: максимальный ZERO-only payload публикуется, оба индекса проходят DPAPI/envelope и семантику, latest/fallback работают, два отказных read-пути сохраняют ciphertext. Производительность продукта или полный T114 этим не приняты.

## Что остаётся открытым

**T114 NOT READY:** Stop и fence, фактическая потеря/недоступность DPAPI profile keys, большой индекс с nonzero ссылками и реальным чтением блоков, полная матрица файловых сценариев остаются открытыми. Также данный proof не принимает crash/power-loss durability большой публикации, повторную запись после оставшегося временного индекса, SC-003 или пользовательскую приёмку восстановления. Текущие parser coverage ограничения сохраняются после успешного run.

Build wrapper хеширует только главный source после сборки; транзитивные includes отдельно привязаны хешами в этом отчёте, а не в build/runtime JSON. Квитанции — сохранённые metadata; независимое воспроизведение сборки binary↔всех source и подписанная аттестация не выполнялись. Одобрение относится к явно заявленному Phase0 объёму и согласованности текущих доказательств.

## Привязка к исходникам

SHA-256 просмотренных файлов:

```text
1eccae197bcda610e9d33c001254e4c27be14ede461c44dd683a7b0a24b7fa97  f200-protected-mf-proof.jADm92/IndexProof.cpp
96c07c22b48152989efabc2e145e67b929d4b228b56dd411b722776ea7ae1030  f200-protected-mf-proof.jADm92/index-build.cmd
e60f1ba74a25aab5e2e0e23aa006bc93ac09437a6cfdf20b40f80930cce47f55  f200-protected-mf-proof.jADm92/ContextProof.cpp
6d09fa40dbc7b77eef34235dced9eccb247d008de08ea4564eb9f1e394acf29f  f200-protected-mf-proof.jADm92/ProtectedMfProof.cpp
462b4658dc7c2577119fbcc89c40d075c85e6e758a4372d45790590ee5c73daa  f200-dpapi-block-proof.PRtfBz/BlockProof.cpp
ced3982c08668428390f32983b1e7a374f9aec1fedbdfa928290af1de1d9b387  f200-dpapi-commit-proof.9xdyLi/CommitProof.cpp
5ba7c738a098ffa9bc35de252d0cd3190e89dfd69d7e65f51655e4d574c447eb  f200-protected-mf-proof.jADm92/context-run.ps1
b0a72aa89f360c34a180662a97b779b1c15f390b2dfbfdc3358df99e0efb4e6d  f200-protected-mf-proof.jADm92/index-build-run.ps1
a245d9988f44aaeef2c9f7e7e24444aaa4a38fd41b9c5490e4bce5e1e41eb092  f200-protected-mf-proof.jADm92/index-build-result-1e39e643-0baf-4fb7-8902-fcf4cbf4dd25.json
75095009e16d2b889238c04c34b344cc7bba92e78f401e8329f568c6d13005d2  f200-protected-mf-proof.jADm92/context-result-fda8c038-fbf7-46b4-907d-cd74dc66da11.json
```

Это узкое одобрение исходников, runner и согласованности окончательных build/runtime receipts. Все source/runner hashes при итоговой сверке совпали. Reviewer изменил только этот разрешённый отчёт; tasks/checkboxes и другие документы остались без изменений. Полный T114: NOT READY.
