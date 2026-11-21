# Независимый review T114 Phase0: sparse mixed index

Дата: 2026-10-01.

**SOURCE-ONLY RESULT: REQUEST CHANGES к одному P2 в oracle encrypted-invalid g3. Остальных блокирующих ошибок в заявленном узком объёме не обнаружено. Build/runtime receipts и runtime runner ещё не предоставлены и не принимаются. Полный T114: NOT READY.**

## Объём и полномочия

Reviewer лично полностью прочитал `/Users/yshishenya/.agents/skills/code-reviewer/SKILL.md` и применил его проверки correctness, authority/generation, error masking, query arithmetic, resources и достоверности oracle. Полностью прочитаны внешние MixedIndexProof.cpp, IndexProof.cpp, mixed-build.cmd, mixed-build-run.ps1, ContextProof.cpp, ProtectedMfProof.cpp, общий CommitProof.cpp и BlockProof.cpp.

Proof root: `/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/`. Общие helpers находятся в `/Users/yshishenya/Documents/graf-windows-followup-200/f200-dpapi-commit-proof.9xdyLi/CommitProof.cpp` и `/Users/yshishenya/Documents/graf-windows-followup-200/f200-dpapi-block-proof.PRtfBz/BlockProof.cpp`. Формулировка «new CommitProof helper» трактуется как новая редакция именно этого реально включаемого файла; отдельного newCommitProof.cpp в include chain нет.

Активная `.specify/feature.json` canonical worktree указывает Feature 200, `specs/200-windows-desktop-app` и ветку `codex/200-windows-followup`. Прочитанный HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`. Пользовательский объём — только disposable generated-data Phase0, не product implementation. Путь проверки: read-only investigation; добавление отчёта: Docs-only / mechanical.

Сборки, runs, тесты, VM, устройства и GitHub reviewer не запускал и не менял. Единственная запись — этот новый файл через apply_patch. Код, старые отчёты, tasks, checkbox state и чужие изменения не менялись. Указанные ниже expected results — условия прочитанного source, не результаты проведённого reviewer эксперимента.

## Finding

### [P2] Fallback=2 не доказывает достигнутый semantic rejection валидного envelope g3

Место: [MixedIndexProof.cpp:113](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/MixedIndexProof.cpp:113); ранний отказ — [MixedIndexProof.cpp:56](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/MixedIndexProof.cpp:56).

После `publishMixed(root,3,security,true)` проверяется только успешный selectMixed с generation=2 и identity прежней g2. Но mixedSnapshot одинаково возвращает false при CryptUnprotectData failure, envelope validation failure и parseMixed rejection. Отдельного обязательного подтверждения «g3 успешно открыт native DPAPI, envelope/context/digest/length валидны, после этого семантический parser отверг именно g3» нет.

Конкретный путь ложного принятия заявленного сценария: если после публикации ciphertext index1/g3 не открывается DPAPI или не проходит envelope, mixedSnapshot возвращает false до parseMixed. Правильный index0/g2 всё равно даёт generation=2, range/full-block checks проходят. После порчи последнего блока v2 index0 также становится недействительным, index1 остаётся crypto-invalid; both-invalid и сравнение всех шести ciphertext hashes до/после отказного read тоже проходят. Возможен полный PASS без фактически проверенного чтения **валидно зашифрованного, но семантически неверного** payload. Native wrong-entropy счётчик здесь не помогает: он относится к отдельному более раннему шагу.

publishMixed по прочитанному коду действительно строит invalid payload до protect с правильным slot context, а прямые parser negatives проверяют соответствующее недопустимое поле в памяти. Finding не утверждает, что этот source сейчас генерирует неправильный ciphertext или что native DPAPI фактически откажет. Он относится к недостаточности отдельного oracle для заявленного encrypted semantic rejection: правильный общий fallback не различает нужную и постороннюю причину отказа.

Минимальное закрытие в рамках того же proof: перед/в ходе g3 fallback обязательно подтвердить успешный DPAPI+envelope roundtrip опубликованного g3 и достигнутый parseMixed rejection с generation=0. Это можно сделать явной проверкой открытого g3 payload или отдельным marker/counter соответствующей стадии snapshot с внешним require. Более ранний crypto/envelope отказ должен приводить к FAIL этого сценария. Product implementation, реальная key loss, новая матрица или дополнительные VM runs reviewer не требуются и не выполнялись.

Других blocking findings в разрешённом source-only объёме не обнаружено. Ограничения покрытия ниже не являются расширением задачи.

## Размерность, layout и reuse

Mixed include chain: MixedIndexProof → IndexProof → ProtectedMfProof → CommitProof → BlockProof. Новый F200_INDEX_MAIN переименовывает старый Index entrypoint в priorMixedIndexMain для reuse; самостоятельный IndexProof без override сохраняет wmain. Mixed не вызывает этот старый entrypoint: прежние десять ZERO-only negatives и Index read-boundary injection не исполняются данным Mixed wmain. Также не вызываются старые MF encode/decode/playback/commit-crash entrypoints из включённых файлов.

Индекс содержит четыре little-endian uint64 в заголовке 32B и 262144 записи по 16B: **payload 4 194 336B = 4MiB+32B**. Логическая длина mixedLength — **68 719 476 613B = 64GiB−123B**. Число блоков ceil(length/262144)=262144. Последний блок имеет 262021B, не полный 256KiB.

Три реальные ссылки расположены в rows 0,131072,262143. Создаются версии b0-1, b131072-1, b262143-1 и b262143-2. Суммарный plaintext четырёх версий — **1 048 330B = 1MiB−246B**; в одном snapshot три referenced payloads занимают 786309B. Остальные 262141 rows — explicit ZERO без media objects. Это sparse maximum-dimension metadata experiment, не запись/полное чтение 64GiB media.

Index compile-time F200_MAXIMUM_PAYLOAD=4096+262144×16=4198400B действует только в Index/Mixed translation unit. BlockProof default под #ifndef остаётся 1MiB. Включённый ProtectedStream не получает увеличенную stream размерность: его собственные fixtureLimit=64MiB, index≤256 entries и version-inventory bounds остаются прежними; Mixed использует отдельные parse/query helpers, а не ProtectedStream для 64GiB. Увеличенная metadata cap не принимается как продуктовый формат или новый стандартный block limit.

## readCipher: предел до allocation

[CommitProof.cpp:68](/Users/yshishenya/Documents/graf-windows-followup-200/f200-dpapi-commit-proof.9xdyLi/CommitProof.cpp:68) добавляет optional byteLimit с прежним default maximumPayload+4096. Positive byteLimit и его верхняя граница проверяются до открытия; GetFileSizeEx и сравнение с byteLimit стоят до bytes.resize/ReadFile. Missing file возвращает false только при ERROR_FILE_NOT_FOUND; остальные open/inspect/read failures бросают и прерывают proof, не дают ожидаемый fallback PASS.

Все Mixed block reads — построение reference size, parseMixed, mixedRange, full-block oracle и mixedDigests — передают **blockBytes+4096=266240B**. Поэтому большой Index compile cap не позволяет случайно выделить около 4MiB ciphertext buffer для block file. Index reads используют default **4202496B** в этой translation unit. Все текущие размеры безопасны для DWORD/ULONG/LONGLONG conversion. Default callers в прежних helpers/ProtectedMf сохраняют свои прежние default limits соответствующей compilation unit.

Этот source review подтверждает порядок bounds checks, но не содержит runtime oversized-file rejection case. bytes на false path не очищается helper автоматически; текущие Mixed callers создают новый Bytes и проверяют bool до использования, поэтому stale-buffer false authority здесь не возникает. Native DPAPI allocation принадлежит API; envelope validation проверяет точный expected plaintext до копирования в payload vector. Это не независимое измерение или строгая квота внутренних native allocations.

## Парсер и поколение authority

parseMixed сбрасывает generation=0 до любых проверок и требует точную максимальную длину payload до get64/copy/loop. Ровно 262144 entries проходят ограниченный обход. ZERO допустим только как version=0,cipher=0,flags=1. Nonzero допустим при flags=0, version>0, 0<cipher≤266240 и не более трёх references. Четвёртая nonzero reference отвергается; после обхода обязательно used==3. Это намеренный ceiling fixture, не общий parser произвольного nonzero index.

Для reuse parseZeroIndex делает bounded копию normalized: три nonzero rows заменены ZERO, заголовок сохранён. Старый parser требует schema=1, g>0, g%2==slot, length≤64GiB, count≤262144, согласованный ceil(length/blockBytes) и точную длину. Дополнительно Mixed требует length==64GiB−123. Недопустимые huge length/count short-circuit отвергаются до потенциального overflow. Все row offsets находятся внутри заранее проверенных 4194336B. Общий обход выполняется до проверки header, но остаётся O(262144), без media-sized allocation.

После header validation каждый из трёх references читается с local block cap, exact ciphertext size и DPAPI context root/kind/index/version; expected payload length определяется mixedBytes(i), включая укороченный tail. Generation присваивается только после проверки всех references. Парсер допускает любые три допустимые позиции, а не только locations; в этом fixture существуют файлы лишь для трёх известных позиций. Полная shape/integrity validation и fixed generated-content oracle — отдельные проверки.

mixedSnapshot на входе сбрасывает generation и plain. При правильной entropy успешный native DPAPI ещё недостаточен: обязателен validate exact payload/context/SHA digest, затем parseMixed. selectMixed сбрасывает общий результат, рассматривает оба slots и выбирает максимальное полностью валидное поколение. При обоих отказах возвращает false, generation=0, selected.empty(); это отсутствие authority, не успешный пустой snapshot/ledger.

## Публикация, fallback и сохранность шести файлов

Own случайный root создаётся на fixed NTFS после проверки минимум 64MiB free space, с DACL user+SYSTEM до записи content. Block versions создаются через CREATE_NEW. Index temp mixed-t<g> также CREATE_NEW, write/flush/close; MoveFileEx(REPLACE_EXISTING|WRITE_THROUGH) публикует g%2, затем published handle inspect/flush/close.

G1 в slot1 с tail v1, g2 в slot0 с tail v2; оба используют неизменённые первые/middle block v1. Latest требует generation=2, восемь queries и три whole-block identity checks. Wrong-entropy отказ требует отсутствия authority и hashes всех шести файлов без изменений. После flip byte100 только в tail v2 требуется fallback=1, ranges/full referenced-block identity g1 и сохранность всех шести уже частично испорченных ciphertext files после read.

Повторный XOR того же tail byte восстанавливает ciphertext; требуется совпадение полного шестифайлового digest vector с исходным baseline и снова generation=2. Это исследовательская repair инъекции, не re-encryption, key recovery или принятая продуктовая «починка повреждений».

G3 заменяет slot1/g1: payload имеет invalid middle packed field, но передаётся в protect до write. Ожидается fallback=2, не принятие g3; недостаток отдельного semantic oracle описан в P2. После нового flip tail v2 slot0 невалиден по referenced block, slot1 невалиден по payload; требуются both-invalid rejection/reset и сохранность всех шести файлов между digest before/after этого отказного read. Старый g1 index уже заменён g3, поэтому fallback=1 на этом шаге не ожидается.

Preservation сравнивает SHA(context-zero+cipher bytes) для двух текущих indexes и всех четырёх block versions, включая unreferenced old tail. Отдельного before/after hash сравнения непосредственно для semantic fallback g3→g2 нет; его нельзя объявлять общим preservation proof всех успешных read путей. Crash cuts, restart retries/temp collision strategy, concurrent writers, pinning, GC и power-loss здесь не проверяются. mixed-t<g> безопасно уникален для текущих 1/2/3 в fresh root, но не принят как restart-safe naming contract.

## Query arithmetic и content oracle

mixedRange принимает offset≤mixedLength и requested≤8192; выделяет min(requested,length−offset) bytes, первоначально нулевых. Это исключает underflow и offset+requested overflow до расчёта range. При каждой итерации offset+done<length, i<262144, within<262144; n=min(remaining,blockBytes−within)>0. EOF clipping гарантирует within+n≤mixedBytes(i), в том числе при коротком last block. offset==length создаёт пустой result и не читает row/data. Умножения i×blockBytes и mixedByte arithmetic для текущего диапазона не переполняют uint64.

На валидированном selected payload ZERO оставляет initialized zeros; nonzero читает конкретные index version/size/context и копирует ограниченный участок decrypted block. mixedRange сам не повторяет все semantic checks для ZERO/неизвестных flags: безопасный контракт здесь — только ранее validated snapshot из selectMixed. Он не универсальный reader untrusted index.

Восемь fixed offsets с requested=4096 покрывают начало, nonzero→ZERO после first block, ZERO→middle, внутренний middle, middle→ZERO, ZERO→last, последние 17B и точный EOF. Expected query bytes рассчитываются по fixed locations/generation, не считываются из query result/index references; tail v1/v2 различается в oracle. После latest g2, fallback g1 и g3 fallback g2 вызываются те же восемь queries.

Три whole-block checks отдельно читают файлы известных locations/versions, требуют native envelope/exact length и сравнивают весь decrypted payload с mixedPayload. Это полная identity трёх физически referenced blocks, **не whole-stream 64GiB identity** и не проверка каждого byte через mixedRange: range reader проверяется указанными восемью запросами. Непосредственный запрос только из середины большого ZERO interval, invalid query bounds и requested=8192 не входят в executed source cases; соответствующие branches inspected, не runtime-accepted.

## Шесть parser negatives и native wrong entropy

Отрицательные payloads копируются из selected g2 после подтверждённого восстановления всех ciphertext hashes и успешной повторной validation. Каждый case требует !parseMixed и rejected generation=0, предварительно выставленный в 999. Посторонние file/hash/allocation exceptions не засчитываются: они достигают верхнего FAIL/exit=1.

| Case | Изменение | Проверяемый отказ |
|---|---|---|
| 0 | middle row packed=2<<32 | недопустимые flags; одновременно cipher становится 0 |
| 1 | last row version=0 | nonzero reference без версии |
| 2 | last row cipher=blockBytes+4097 | metadata cipher превышает local block cap |
| 3 | header count=maxEntries−1 | count не соответствует length и payload |
| 4 | header length=64GiB+1 | превышение logical limit |
| 5 | payload.pop_back | нарушена точная длина до чтения entries |

Case0 не изолирует только flags, а case2 не создаёт физический oversized block: его metadata bound проверяется до чтения, helper preallocation bound отдельно inspected по source. Положительный baseline не позволяет всем negatives пройти просто из-за заведомо непригодного исходного payload.

Wrong entropy — отдельный реальный native read experiment на уже успешно validated indexes. context[0] XOR 0x80 изменяется только для передаваемой entropy; непосредственно перед CryptUnprotectData устанавливается ERROR_SUCCESS, сразу после native call сохраняется GetLastError без промежуточных API calls. Обязательны !opened и error!=ERROR_SUCCESS; counter увеличивается только после этой проверки и ограничен двумя. Внешний require требует nativeFailures==2, отсутствие authority/selected bytes и сохранение всех ciphertext hashes. Early read failure/exception не может выдать тот же PASS или довести counter до двух.

Это **два actual CryptUnprotectData failures с wrong entropy**, не SetLastError-only injection. Но token/user/profile остаются теми же. Не принимаются реальная profile/master-key loss, другая identity, ключи недоступного пользователя, конкретный NTE_BAD_KEY_STATE или восстановление ключей. Source намеренно требует только nonzero native error и печатает фактические два DWORD; численные значения ещё неизвестны без receipt. Semantic parse/digest failures не должны заменять required native FALSE на этом этапе.

## Ресурсы, ошибки и cleanup

Payload/normalized/bad indexes копируются целиком несколькими bounded vectors, около 4MiB каждый; parser performs whole-index scans. Block plaintext/cipher ограничены одной текущей 256KiB reference на iteration, range output≤8192. Средства full-media allocation отсутствуют. Поэтому исследование bounded по размерам, но не доказывает маленький product cache, инкрементальный startup или SC-003.

Финальный inventory требует ровно шесть regular files и file_bytes<16MiB; seventh object сразу отвергается. Размеры содержимого ранее ограничены readCipher. Это sum logical file sizes, не NTFS allocation/temporary high-water/общая disk-quota measurement. PeakPagefileUsage/PeakWorkingSetSize — lifetime process peaks всей жизни Mixed executable, включая setup, большой parser/negatives и verification; не stage deltas или managed memory.

elapsed_us начинается после создания четырёх block versions, перед публикацией g1/g2, и включает дальнейшие selects/native failures/hashes/corruption/repair/negatives/g3/inventory/memory query. Он не является временем одной публикации, reopen или полного запуска: initial DPAPI block creation и часть setup исключены. CPU/process IO/dispatcher/Stop не измеряются. Численных resource results и принятия performance gates на source-only этапе нет.

Top-level std::exception приводит к FAIL/exit=1. Blob zeroizes/LocalFree native plaintext, explicit success-path payloads zeroize; Handle/Security RAII освобождают ресурсы. Однако normalized early-rejection copies, discarded vector storage после clear и некоторые exception paths не имеют полного plaintext scrubbing. Это не полная memory-privacy acceptance. inspect отвергает reparse/hardlink/file kind и требует protected DACL с двумя ACE, но не повторно сравнивает все SID/mask; adversarial path/ACL proof не принимается. Fixture намеренно остаётся на диске, delete/GC не заявлены.

## Context и build scripts

ContextProof добавляет только fixed `--mixed-user-dacl` branch с sibling MixedIndexProof.exe и `--medium`. Ограниченный token имеет medium integrity 8192, admin group disabled и user ACE только в собственном default DACL. Child suspended, own Job KILL_ON_JOB_CLOSE назначается до ResumeThread. Mixed использует прежний mf guard35s; resource60s/обычный child10s сохраняются. Mixed wmain отдельно требует actual medium/noadmin. Несмотря на имя общей mf ветки и linked MF imports, Mixed не инициализирует COM/MF и не запускает encode/decode/devices.

mixed-build.cmd описывает x64 MSVC `/std:c++17 /EHsc /MT /O2 /W4 /WX /utf-8`, компилирует только MixedIndexProof TU и возвращает сохранённый exit cl. mixed-build-run.ps1 фиксирует before/after SHA шести прямых source/build/helper inputs, немедленно сохраняет LASTEXITCODE, записывает build_exit/source_hashes/exe_sha256 и возвращает именно buildExit. EXE hash — только при build_exit=0; недоступный EXE вызывает ошибку, не успешную null-квитанцию. Wrapper сам, system headers/compiler/version/env не входят в шесть hashes; это не hermetic compiler attestation. Новый Context source требует отдельного актуального EXE.

Runtime runner и build/runtime receipts пока не предоставлены: обновлённый EXE, runner hash/guard/acceptance markers, actual medium/noadmin result, native error values и source/exe before/after consistency остаются PENDING. Старые Index/Context receipts или другие proof EXE не являются evidence этой ревизии.

## Привязка рассмотренных исходников

Независимо вычисленные SHA-256:

| Файл | SHA-256 |
|---|---|
| MixedIndexProof.cpp | `d8bd348386c4094ddd19dbf2a5e90a97d8c682cebf476e143aa3b423d14315b8` |
| IndexProof.cpp | `3a9bda2eb030e7e7da6b30df7a49887e55d0acaab0ab80ce037b6e1fcf731391` |
| mixed-build.cmd | `59a16bd157985b9f0f6365c70a50a07c436f35cfcdcc8370e79c254a10055e93` |
| mixed-build-run.ps1 | `7437b3a1f6bf4fdb9289b87bab2152756e51b0c56a282811615163ec839fab73` |
| ContextProof.cpp | `1cc6fbb9ffd1aba02cd8e0d16bd328b6a0f3c177ce9be12466f441fcdbaf7d70` |
| ProtectedMfProof.cpp | `6d09fa40dbc7b77eef34235dced9eccb247d008de08ea4564eb9f1e394acf29f` |
| CommitProof.cpp | `f42b7820bfb04187c32d773fbb49d269e7cce831d6a8a3ab1c6aacf9e9f79ef1` |
| BlockProof.cpp | `462b4658dc7c2577119fbcc89c40d075c85e6e758a4372d45790590ee5c73daa` |

Эти hashes привязывают только source review. Изменённые Index/Commit/Context hashes не следует смешивать с предыдущими ZERO-only/Stop receipts; старые отчёты сохранены без изменений и относятся к своим ревизиям.

## Заключение

В source подтверждены bounded sparse layout, безопасная арифметика известных ranges, проверка всех трёх ссылок до authority, generation reset/maximum selection, mid/last negatives, правильные intended fallback transitions и реальные wrong-entropy native failure guards. Обнаружен один локальный P2, не позволяющий безусловно принять утверждение о достигнутом encrypted semantic rejection g3; запрошенное изменение ограничено oracle исследовательского proof.

**REQUEST CHANGES для указанного P2; build/runtime acceptance PENDING; T114/Phase0 NOT READY.** Не принимаются full64GiB/nonzero stream implementation, full-file read matrix, actual profile/key/identity loss, продуктовые Stop/account/delete/shutdown fences, migration/GC/power-loss, privacy/SC-003 gates или разрешение на T115–T118. Scope не расширен, code/old reports/tasks/checkboxes не изменены.

## Дополнение 2026-10-02: узкая повторная проверка P2 и свежих квитанций

**Текущий итог: APPROVED в узком объёме исправленного mixed-index proof; P2 CLOSED. Полный T114/Phase0: NOT READY.** Предыдущий REQUEST CHANGES, finding и исходные hashes выше сохранены как история первой ревизии, а не как итог исправленного source. Общий audit T114 временно отложен по уточнению приоритета основным агентом; это дополнение не разрешает переход к T115 и не меняет никакие gates.

Reviewer повторно лично прочитал code-reviewer SKILL и полностью текущие MixedIndexProof.cpp, mixed-run.ps1 и обе указанные fresh receipts; проверил реально вызываемые unprotect/validate/require в BlockProof, build wrapper и fixed Mixed child/guard/Job branch ContextProof. Никаких сборок, тестов, запуска proof, VM или дополнительной negative injection reviewer не выполнял. Единственная запись — append этого раздела; прежний текст не редактировался.

### Исправление и прежний ранний crypto/envelope контрпример

В [MixedIndexProof.cpp:114](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/MixedIndexProof.cpp:114), сразу после publishMixed g3 и **до** selectMixed/fallback, теперь обязателен успешный read опубликованного index1 и unprotect с правильным contextFor(root,13), точным payload size 32+262144×16 = 4194336B и возвратом plaintext. В реально включённом helper успех unprotect требует native CryptUnprotectData TRUE, затем validate точной envelope length, context и SHA-256 digest. Только после этого plaintext копируется в возвращаемый vector. Это не проверка одного API TRUE или условный путь, который можно пропустить при false.

Следующий внешний require подтверждает generation=3 и точное invalid middle packed=uint64_t(2)<<32. Затем rejected предварительно равен 999, и обязательный прямой parseMixed(root,plain,1,rejected) должен вернуть false со сбросом generation в 0. У данного middle row flags=2 не подходят ни ZERO flags=1, ни nonzero flags=0; возврат false достигается при разборе entries, без попытки принять authority. Plaintext после успешной проверки явно zeroized. Существующее ограничение scrubbing на exception/early-return путях остаётся, но это не новый full memory-privacy proof.

Прежний контрпример теперь приводит к FAIL: если опубликованный g3 не читается, не открывается native DPAPI или не проходит envelope/context/digest/length, require `mixed-invalid-envelope-opened` бросает std::runtime_error. Верхний catch печатает FAIL и возвращает 1 **раньше** fallback=2 и всех PASS markers. Правильный g2 больше не может замаскировать такой ранний отказ. Неверные g3/packed field или неожиданное принятие parser также дают внешний FAIL, не засчитываются как ожидаемый отказ. Проверки стоят непосредственно в wmain, вне локального перехвата, который мог бы превратить ошибку в ожидаемый invalid snapshot.

После прямого semantic rejection остаются прежние selectMixed generation=2, восемь range queries и полная identity трёх referenced blocks; затем оба invalid indexes требуют отказа/reset/empty result и preservation шести ciphertext hashes. Новый `authenticated_semantic_rejections=1` печатается только после обязательных проверок, а свежий runner дополнительно требует этот marker при accepted. Значение 1 — literal на достигнутом обязательном пути, не самостоятельный динамический счётчик и не единственное основание принятия.

Таким образом, P2 закрыт по source и подтверждён свежим успешным run этой ревизии. Отдельный запуск с намеренно ранним crypto/envelope отказом после g3 не проводился: его FAIL-путь установлен чтением require/throw/catch chain, а не выдан за runtime negative test. В узком повторно рассмотренном изменении новых blocking findings не обнаружено.

### Fresh build/run и независимая сверка hashes

Полностью прочитаны [mixed-build-result-d9bda888-217d-4570-bdc2-8d0bfe2f207f.json](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/mixed-build-result-d9bda888-217d-4570-bdc2-8d0bfe2f207f.json) и [mixed-result-852974e5-90ed-4ee8-ac4f-c3f7ab68efb8.json](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/mixed-result-852974e5-90ed-4ee8-ac4f-c3f7ab68efb8.json). SHA вычислены непосредственно по текущим локальным bytes, а не только переписаны из сообщения Main.

| Объект | Независимо вычисленный SHA-256 |
|---|---|
| Исправленный MixedIndexProof.cpp | `ab7b52d2930649f089dd436a4e94394435f294c59443880f610685949a112226` |
| MixedIndexProof.exe | `c232fa7550119298490ee3e0b39ffe4cb66c5d8a98512427e6221b6e2c208c68` |
| ContextProof.exe | `52455eb60f76ad3e0f65f176c9fd761012b51380b60bdcd5f0d502c209101b91` |
| mixed-run.ps1 | `acc0776e2857ca61f13033a3e6ba5f133385aa23ce9c09d691b48066d3a0ab31` |
| Fresh build receipt d9bda888 | `a7402b1451fcce6538a0da9f0418c167ebd08adc8a5644f88f83b7172e2b9b0d` |
| Fresh run receipt 852974e5 | `0263e8972073b1918e10602a20d4f8c882cc81f5900083334d450d1758128530` |

Все шесть source/build/helper hashes fresh build receipt совпали с локальными файлами и с теми же полями run receipt. Build receipt содержит build_exit=0 и Mixed EXE hash c232…; он совпал с локальным EXE, fixed runner constant и run mixed_sha256. Все десять source/build/runner/helper inputs run receipt независимо пересчитаны и совпали. Неизменённые Index, ProtectedMf, Commit, Block, Context, mixed-build.cmd и mixed-build-run.ps1 hashes соответствуют значениям первой source review выше; дополнительный context-build.cmd hash — `941809fd29f686295999de9f1efb3bfb342d565ca5d2b1627c7f9381d6483ae3`. Локальный Context EXE совпал с run receipt и runner constant. Fresh Mixed build receipt не является новой квитанцией сборки Context и не приписывается ей.

Runner по source проверяет десять inputs до/после и оба fixed EXE hashes до запуска и после завершения; несовпадение бросает до accepted/receipt. Receipt хранит исходный manifest, не две отдельные копии before/after: неизменность следует из достигнутого пути проверенного runner. Это согласованная цепочка предоставленных metadata/source/EXE, не независимый повтор reviewer и не hermetic compiler attestation.

Runner запускает fixed Context с `--mixed-user-dacl`, имеет внешний guard45s; Context выбирает sibling MixedIndexProof.exe с `--medium`, собственный Job KILL_ON_JOB_CLOSE назначает suspended child до ResumeThread и сохраняет внутренний guard35s. Runner после завершения требует exit0, пустой stderr, четыре PASS markers, новый authenticated marker, synthetic-only marker и CHILD_RESULT exit0/medium_nonadmin_verified. Его regex считает четыре markers суммарно, не гарантирует уникальность каждого типа сам по себе; reviewer отдельно проверил **по одной** записи INDEX_PASS, NATIVE_FAILURE_PASS, RESOURCES и PROOF в этой квитанции. stdout имеет 1384 символа, меньше установленного 4096; проверка длины выполняется после ReadToEndAsync и не доказывает потоковую allocation quota.

### Что именно подтверждено fresh receipt

Fresh run содержит exit_code=0, stderr_bytes=0, pass_markers=4, accepted=true; CHILD_RESULT exit=0x0 medium_nonadmin_verified=true, medium_integrity=8192 и restricted_admin=false. Это собственный medium child текущего пользователя, не доказательство отдельного standard-user account, другой identity или потери профиля.

INDEX_PASS подтверждает 262144 entries, logical_bytes=68719476613, четыре физические block versions, три nonzero references, шесть parser negatives, восемь range queries на snapshot, три whole-block oracles и **authenticated_semantic_rejections=1**. Переходы latest=2, corrupted-tail fallback=1, semantic-invalid g3 fallback=2 и both-invalid rejection сохранены.

NATIVE_FAILURE_PASS содержит actual_calls=2, errors=13,13, wrong_entropy=true, identity_changed=false, profile_loss=false и preservation всех ciphertext bytes. Эти два native FALSE относятся к отдельным wrong-optional-entropy calls; они не заменяют новый прямой semantic rejection правильно открытого g3 и не принимаются как actual profile/master-key loss.

RESOURCES: шесть файлов, file_bytes=9438756, elapsed_us=8086200, lifetime_peak_commit=32649216B и lifetime_peak_resident=44769280B. Время включает общий timed сценарий после создания четырёх blocks и дополнительное прямое g3 открытие/разбор; это **не** отдельное время reopen, publication или Stop. Пики — lifetime всего Mixed process, не app CPU/dispatcher/cache acceptance. PROOF явно сохраняет full_media_allocated=false, full_stream=false, product_changed=false, power_loss=false, fixture_retained=true.

Первый round140 build a2bdb287/run b4b5c738 относится к прежнему source d8bd… и EXE4a2e… без обязательной прямой semantic проверки. Он остаётся историческим и не использован для закрытия P2. Fresh evidence — только d9bda888/852974e5, исправленный source ab7b… и EXE c232…; старые hashes и finding выше намеренно сохранены.

### Итог повторной проверки

**APPROVED — только исправление P2 и достоверность узкого sparse mixed-index proof по двум fresh receipts. P2 CLOSED; новых blocking findings в повторно рассмотренном объёме нет. T114/Phase0 NOT READY; полного exit audit сейчас нет и переход к T115 не одобрен.** Все прежние ограничения покрытия сохраняются: не full64GiB media/whole-stream identity, не произвольный nonzero index, не actual profile/key/identity loss, не product pipeline/installed acceptance, не SC-003, power-loss, migration/GC или product lifetime/fences. Код, другие отчёты, tasks и checkbox state не менялись; VM/build/run не запускались.
