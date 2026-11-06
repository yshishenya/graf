# Независимый review T114 Phase0: protected Stop

Дата: 2026-10-01.

**Результат: REQUEST CHANGES только к проверке mode=3 — один P2 допускает поглощение ошибки FIFO как ожидаемого исключения sink. Ошибок controller в исполненном узком пути не обнаружено. Build/runtime receipts согласованы: build_exit=0, runtime exit_code=0, пять маркеров, Context child=0, stderr=0. Остальные наблюдения принимаются в указанном ниже исследовательском объёме; безусловное APPROVED для всей пятислучайной проверки пока не выдано. Полный T114: NOT READY.**

## Объём и полномочия

Reviewer лично заново прочитал `/Users/yshishenya/.agents/skills/code-reviewer/SKILL.md` и применил его проверки correctness, error handling, oracle, concurrency/lifetime и границ. Сборки, тесты, VM, устройства и приложения reviewer не запускал. Запись выполнена только в этот новый отчёт через apply_patch; исходники, прежние документы, tasks/checkboxes, GitHub и чужие изменения не изменялись.

Путь проверки — read-only investigation; добавление отчёта — Docs-only / mechanical, без изменения продуктового поведения. Активная `.specify/feature.json` указывает `specs/200-windows-desktop-app`, ветку `codex/200-windows-followup` и high-risk lane самой Feature 200. Прочитанный HEAD canonical: `99b00a579c24b50e320465b69d9a296038bc544d`. Разрешение на отчёт не является разрешением на реализацию или закрытие T114.

Полностью прочитаны внешние `StopProof.cpp`, `stop-build.cmd`, `ContextProof.cpp`, `stop-run.ps1`, `stop-build-run.ps1`, успешный build receipt и итоговый runtime receipt. Проверены используемые определения ProtectedStream, encode, cipher inventory и medium-token verification в `ProtectedMfProof.cpp`; его SHA совпал с ранее полностью рассмотренным файлом. Общие BlockProof/CommitProof ранее прочитаны полностью; текущие SHA совпали с manifest финальной квитанции.

Canonical root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp/apps/windows/RecApp/`. Прочитаны controller, WindowsDesktopSession, CaptureReasonMapping, WindowsReadinessGate, RecordingIndicator, WasapiCaptureWorker, WasapiEndpointEnumerator, AudioNormalizer, ClockMapper — `.cpp` и `.h`; также AudioTypes.h и WindowsDesktopContracts.h. Все эти **20 используемых файлов** побайтно сопоставлены через cmp с внешним mirror `/Users/yshishenya/Documents/graf-windows-followup-200/apps/windows/RecApp/`: различий нет. Это ограниченное сравнение используемых исходников, не заявление об отсутствии любых различий во всём mirror.

Внешняя папка proof и receipts: `/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/`.

## Findings

### [P2] Ошибка проверочного условия FIFO может выдать ожидаемый PASS в mode=3

Место: [StopProof.cpp:70](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/StopProof.cpp:70), особенно строки 71–73; связанная проверка результата — строки 125–129. Обработка исключения: [WindowsCaptureSessionController.cpp:409](/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp/apps/windows/RecApp/Capture/WindowsCaptureSessionController.cpp:409).

`require(...,"fifo-order")` бросает std::runtime_error внутри BatchSink, до намеренного `introduced-sink-exception`. Реальный `processBatch` ловит любое исключение sink и фиксирует `finalizationFailed`. Для mode=3 именно эта причина ожидается, но proof не отличает введённое исключение от падения собственного проверочного условия.

Конкретный путь ложного PASS при нарушении порядка: sink успешно сохраняет sequence 0,1,2; четвёртым получает не sequence 3, а sequence 4. Счётчик calls уже равен 4; `fifo-order` бросает до строки введённого исключения. Controller фиксирует ожидаемый `finalizationFailed`, прекращает последующие вызовы sink, но пропускает оба EOS. В prefix остаются правильные три блока, поэтому проверки delivered.size=3, calls=4, full raw identity, EOS=3, terminal failed и trustedPrefixRetained проходят. Независимый AAC также создаётся для этих трёх блоков. Следовательно, строка `STOP_CASE_PASS mode=3 ... fifo_exact=true` возможна без достижения предусмотренного места инъекции и при падении FIFO oracle.

Это дефект достоверности проверки, **не обнаруженный reorder в текущем controller и не доказательство ложного результата фактически проведённого запуска**. Нормальный и overflow режимы дополнительно проверяют полный порядок 255 сохранённых блоков; эти результаты не аннулируются данным finding. Но заявленное отдельное принятие exception/FIFO case=3 требует отличать ожидаемую инъекцию от проверки, сломанной внутри обрабатываемого callback.

Минимальное условие закрытия: отдельно фиксировать достижение введённого исключения и проверять его после завершения dispatcher вне BatchSink; нарушения собственных oracle должны независимо приводить к FAIL. Например, marker непосредственно перед введённым throw после FIFO require, с обязательной внешней проверкой для mode=3, устраняет приведённый путь. Это изменение только исследовательского proof; изменения canonical controller или расширение матрицы не требуются. Reviewer код не исправлял и повторный запуск не выполнял.

Других блокирующих findings в разрешённом узком объёме не обнаружено. Ограничения ниже не превращаются в дополнительные требования к этому proof.

## Реальный FIFO/EOS/Stop путь

`CaptureSessionTestPeer::begin` использует настоящую WindowsDesktopSession и её переходы readiness → ready → starting → recording, затем включает acceptingBatches и запускает настоящий dispatchLoop. Это новый controller в каждом режиме; заводские значения очереди/flags соответствуют свежему объекту. `record`, readiness inputs, start guard, запуск и завершение WASAPI workers обходятся: оба worker pointers остаются null.

Первый sink вызов удерживается gate. Ещё 254 AudioBatch помещаются в очередь; pending=254 проверяется до Stop. В mode=1 попытка 255-го queued item отвергается, фиксируя queueOverflow. У controller maxPending=256 и maxData=254: два места зарезервированы для типизированных EOS. После Stop proof требует pending=256. Поздний enqueue возвращает true по контракту «молча отбросить после fence», но pending остаётся 256 — true здесь не означает сохранённый batch.

Настоящий Stop закрывает acceptingBatches, однократно фиксирует stopReason, ставит deadline=5s, добавляет render/microphone EOS через тот же mutex очереди, запрашивает остановку dispatcher и вызывает неблокирующий finishStop. Очередь читается через front/pop_front. Уже принятые данные продолжают проходить sink после Stop. После false/exception sinkFailed запрещает последующие audio calls, но не пропуск EOS. Сначала processBatch фиксирует исходную ошибку, затем дополнительный latch clockDiscontinuity не может заменить первый fault: compare_exchange из none.

finishStop требует dispatchFinished acquire, проверяет EOS mask=3, join выполняет только после опубликованного завершения. Пустая очередь сама по себе не является разрешением финализации. Последующая попытка захватить captureMutex использует try_to_lock, не заставляя Stop ждать удерживаемый sink. В proof обязательны stopping до releaseSink, оба EOS до UI poll и отсутствие раннего finalizer job. Реальные worker completion/COM teardown fences присутствуют в source, но здесь не исполняются и не принимаются.

В mode=4 текущий поток удерживает sink до stopBegin+5100ms и опрашивает controller, пока dispatcher ещё занят. Требуются stopping и отсутствие finalizer. Timeout не создаёт terminal state до завершения dispatcher и не освобождает владение. После releaseSink поздний completion всё равно ведёт к finalizationFailed: controller имеет отдельный sticky drainTimedOut и учитывает реальные sink/dispatcher completion timestamps. Proof не подменяет этот случай искусственным enum.

## Pending finalizer, причина остановки и владение

Finalizer вызывается только UI-owner потоком. Первый вызов после EOS создаёт один исследовательский std::thread и возвращает nullopt; следующий poll, пока job удерживается gate, снова должен вернуть finalizing без второго job. Другой WindowsDesktopSession не может получить process-wide active lease в этом промежутке. После готового job finalizer присоединяет поток и возвращает `{savedLocal=true, reason=none, trustedPrefixRetained=true}`.

Controller не принимает этот успешный результат за обычное сохранение при capture error или drain timeout: savedLocal сбрасывается, итог — failed с ожидаемой причиной. Для mode=0 результат savedLocal; для mode=1 queueOverflow, mode=2 clockDiscontinuity, mode=3/4 finalizationFailed. Повторный stop(interruption) до финализации не заменяет исходный userRequested. Повторные terminal poll/stop не создают второй job. Только после terminal перехода другой session получает lease; это процессный запрет второй сессии, не межпроцессная блокировка каталога.

Проверки finalizer-after-eos, sticky reason и jobOk также расположены внутри callback, где controller ловит исключения. Однако при их падении в текущем proof не выполняется совокупность внешних требований finalizing/one job/trustedPrefixRetained: обработчик controller создаёт `{false,finalizationFailed}` с trustedPrefixRetained=false. Приведённый P2 относится именно к sink/FIFO condition на четвёртом вызове mode=3, где все внешние условия могут совпасть.

## Конкурентность, время жизни и cleanup

Controller commands/session/indicator/finalizerStarts остаются на одном управляющем потоке. Dispatcher записывает delivered и canonical; управляющий поток и finalizer thread получают доступ к завершённым данным только после dispatchFinished acquire и join. Результаты jobOk/pcmBytes/jobUs публикуются через jobFinished release, читаются после acquire и join. В показанном порядке доступа незакрытых data races не обнаружено.

`Unwind` объявлен после controller, поэтому при C++ исключении сначала открывает оба gate и присоединяет finalizerJob, затем деструктор controller присоединяет dispatcher. Захваченные переменные и canonical объявлены раньше controller и живут до окончания этих joins. Существующий current pointer назначается до запуска dispatcher/финализации. Объекты MF reader/writer и media освобождаются в COM apartment job; CoUninitialize вызывается после выхода внутренних объектов, включая путь C++ исключения. Ошибка job не является успешной финализацией: jobOk=false затем требует FAIL и не даёт trustedPrefixRetained=true.

Join при аварийном unwind не имеет собственного предельного времени, а блокирующий native MF вызов не отменяется этим кодом. Общую границу исследовательского процесса задаёт Context own Job. Это не доказательство ограниченного по времени деструктора или очистки native workers. Финальный MFShutdown вызывается, но его HRESULT не проверяется; receipt не подтверждает успешность каждого глобального shutdown вызова. Синтетические каталоги намеренно оставлены; удаления/GC/миграции нет.

## Что именно проверяет защищённое содержимое

Canonical stream получает реальные raw float samples из BatchSink: 480 float на batch, 1920 байт, значение каждого sample — sequence/256. Эти значения точно представимы в float. Проверка после закрытия и reopen требует точную длину и каждый sample каждого сохранённого batch в порядке sequence 0…N−1. Полные prefix размеры: 489600 байт для 255 batches и 5760 байт для трёх. Это не WAV и не canonical timeline/v5 package; ptsFrames здесь искусственный порядковый номер, а не корректная продуктовая временная шкала с шагом 480.

Job выполняет tail Commit raw canonical, затем создаёт **независимый** AAC из generated PCM16 zeros, по 10ms на сохранённый batch. Он не читает и не преобразует сохранённые float samples. Media закрывается, переоткрывается и полностью декодируется до EOS с максимумом blocks+1024 итераций. Длина PCM должна лежать в диапазоне blocks×960 … blocks×960+4096; это ограниченная проверка длительности с допуском codec padding, не byte identity AAC↔raw и не sample-exact decoded duration. Фактический PCM output format отдельно не запрашивается/не сверяется после SetCurrentMediaType. Измеренный PCM byte count не расширяет эту границу.

После raw reopen вызывается verifyCipherFiles для обоих storage roots: все найденные обычные объекты, максимум 1024 на root, читаются через bounded helper и проходят DPAPI/context/digest envelope validation. Неожиданное имя или оставшийся temp отвергается. Receipt показывает шесть объектов в длинных случаях и четыре в коротких. Криптографическая проверка inventory не является отдельным semantic parser для всех исторических индексов; действующий raw snapshot и full identity проверены отдельно.

Используется прежний ProtectedStream: 64MiB fixture limit, 256KiB cache/immutable blocks, два индекса максимум 256 entries; default helper payload limit остаётся 1MiB. StopProof не включает IndexProof override и не объявляет принятие большого nonzero индекса. Own fixed NTFS random root и минимум 64MiB free space проверяются; DACL создаётся user+SYSTEM. Общий inspect проверяет protected DACL/число ACE, но не полное повторное сравнение SID/mask; adversarial path/ACL proof и полная memory-zeroization при исключениях вне этого принятия.

## Launcher, runner и build wrapper

ContextProof распознаёт `--stop-user-dacl`, выбирает только fixed sibling StopProof.exe и передаёт `--medium`. Restricted token получает integrity 8192 и отключённый admin group; user ACE добавляется только в default DACL собственного токена. Глобальные ACL не изменяются. Child создаётся suspended, помещается в собственный Job с KILL_ON_JOB_CLOSE до ResumeThread. Stop child guard=35s; внешний stop-run=45s. StopProof самостоятельно требует actual medium/noadmin. Resource guard остаётся 60s, общий MF guard 35s, обычный context child 10s.

stop-run проверяет закреплённые два EXE hash до/после, записывает и сопоставляет before/after hashes **27 inputs**: семь proof/helper/build файлов и 20 используемых RecApp cpp/h. stdout/stderr читаются асинхронно; accepted требует exit=0, stderr пустой, пять STOP_CASE_PASS mode=[0-4] маркеров, STOP_PROOF и CHILD_RESULT с zero exit. Текущая квитанция действительно содержит по одному mode 0,1,2,3,4. Сам runner считает общее число, не уникальность каждого mode; с рассмотренным StopProof фиксированный цикл mode<5 закрывает это без отдельного blocker. Bound stdout=4096/stderr=1024 применяется после ReadToEndAsync и выражен в .NET characters, не жёсткий memory/byte limit во время чтения; stderr_bytes также является Length строки. Здесь stdout Length=1805, stderr Length=0.

stop-build.cmd содержит x64 MSVC `/std:c++17 /EHsc /MT /O2 /W4 /WX /utf-8`, компилирует mirror controller/dependencies и возвращает сохранённый exit cl. stop-build-run сохраняет собственный LASTEXITCODE сразу после команды, проверяет SHA StopProof.cpp до/после сборки и записывает EXE SHA только при build_exit=0. Это согласованная build metadata-квитанция, не воспроизведённая reviewer сборка и не атомарная аттестация EXE↔всех транзитивных source/compiler inputs. Полный 27-input manifest относится к стабильности runtime окна, не всего build окна. Отдельного Context build receipt в этой проверке нет: terminal0 сообщён Main, текущие Context source/EXE hashes независимо проверены.

## Итоговые квитанции и согласованность

Лично полностью прочитаны:

- [stop-build-result-65d9ed40-a9fd-4e96-8780-4b3ad7f5d489.json](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/stop-build-result-65d9ed40-a9fd-4e96-8780-4b3ad7f5d489.json): schema=1, build_exit=0, source/exe hashes совпадают с текущими байтами.
- [stop-result-0393f785-c37b-41c7-81aa-1d1a347e8b1b.json](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/stop-result-0393f785-c37b-41c7-81aa-1d1a347e8b1b.json): schema=1, exit_code=0, stderr_bytes=0, pass_markers=5, accepted=true, CHILD_RESULT exit=0x0 medium_nonadmin_verified=true.

Reviewer отдельно пересчитал SHA-256 каждого из 27 inputs и обоих EXE: расхождений с runtime receipt нет. Пять modes уникальны и полны. Source hashes совпадают между current/read source и receipt; Stop source/EXE также совпадают с успешным build receipt. Runner before/after checks подтверждаются successful-path accepted receipt; reviewer не наблюдал выполнение Windows процесса и не выдаёт независимо воспроизведённый run.

| Артефакт | SHA-256 текущих байт |
|---|---|
| StopProof.cpp | `2a7987064de4648042944ad22ca2c7308f6355f091bad25fd6488380cb3a8ffa` |
| StopProof.exe | `5bde468d0ca00b43e4cf5e023a0c15eaf269de9c20ae1fa780d3d6af9e5d8912` |
| ContextProof.cpp | `38edcc4f88e1e44f6d668c2fa4b74f497f6baf6bec3caef00b32ec1b0f4243e4` |
| ContextProof.exe | `ebc73774df9b89e442f6d1f516b9bbeeb4bd1012b8ad9ea1503a29cdc1e22980` |
| ProtectedMfProof.cpp | `6d09fa40dbc7b77eef34235dced9eccb247d008de08ea4564eb9f1e394acf29f` |
| stop-run.ps1 | `85e77144d1589d6fc11d9c7ac90ce9d68c2e1a8aa3e0f7657d0d1f7189908ef1` |
| stop-build-run.ps1 | `8cfa36c05870a57d49c83bba0ffa03b4c11c6e4fd06ef8eadc35d0060e6939c4` |
| Успешный build receipt | `c7f52888652f2817475b86e08265726ac0ba23c7456e4b5ca276159b9f0619a0` |
| Итоговый runtime receipt | `fe5e0916cdc6072e8688ee903385186cf9c5d5e65c6488d1a362c00efee0380c` |

Полный 27-input manifest сохранён в runtime receipt; его RecApp hashes относятся и к побайтно совпавшим canonical файлам. Ранее неуспешный build receipt e4f89010 содержит build_exit=2, иной source SHA и null EXE hash; он прочитан как история, но не используется как текущая build evidence.

| Mode | Сценарий | Сохранено batches / sink calls | Stop, us | Protected job, us | PCM bytes | Cipher objects | Terminal |
|---|---|---:|---:|---:|---:|---:|---|
| 0 | normal | 255 / 255 | 680 | 560248 | 245760 | 6 | savedLocal, none |
| 1 | queue overflow | 255 / 255 | 21 | 246829 | 245760 | 6 | failed, queueOverflow |
| 2 | sink false | 3 / 4 | 29 | 111548 | 4096 | 4 | failed, clockDiscontinuity |
| 3 | sink exception, с P2 выше | 3 / 4 | 37 | 82119 | 4096 | 4 | failed, finalizationFailed |
| 4 | held sink >5s | 255 / 255 | 11 | 218577 | 245760 | 6 | failed, finalizationFailed |

Все пять строк сообщают eos_mask=3, fifo_exact=true, pending_lease=true. `accepted_batches` в output означает сохранённые sink batches, а не число принятых в очередь: в mode=2/3 до ошибки enqueue принял 255 batches, сохранено только три. Предел nonblocking-stop в proof — 500000us; текущий максимум 680us меньше него. Это один синтетический запуск без driver/worker Stop, не продуктовый latency SLA.

`protected_job_us` измеряет job целиком: COM initialization, возможное ожидание releaseFinalizer, canonical Commit, полный independent AAC encode/Finalize/Commit, reopen/full decode и освобождение объектов/COM. Максимум 560248us не является отдельным MF Finalize временем или временем возврата UI Stop. Reopen raw identity и финальная проверка всех cipher objects выполняются позже управляющим потоком и в job time не входят. SC-003/CPU/resident/dispatcher performance этим измерением не принимаются.

## Заключение и границы принятия

Подтверждены source↔current receipt consistency, идентичность используемых mirror/canonical файлов и реалистичный путь настоящего dispatcher/controller для generated raw float storage. Нормальная остановка, reserve/EOS при overflow, sink false, held-sink drain timeout, pending finalizer/lease и terminal error truth имеют соответствующие внешние проверки. Для mode=3 найден ровно один локальный дефект oracle, блокирующий безусловное принятие его exception/FIFO утверждения; исправление controller не требуется и не разрешалось.

Не принимаются: реальная acquisition/worker cleanup, native driver cancellation, concurrent producer-vs-Stop stress, timeline/mixing/AEC, v5 bytes/manifest/short-recording policy, conversion raw→AAC, account/delete/shutdown/pinned-reader fences, crash/power-loss/GC, native key-loss failure, nonzero large index/full file matrix, SC-003 или полная encrypted-at-rest продуктовая реализация. Это согласованные границы, не новая расширенная задача. Указанные Main следующие native-key-failure/nonzero-large-index исследования данным отчётом не рассмотрены.

**T114/Phase0 остаётся открытой, T114 NOT READY; разрешение на T115–T118 или product implementation не выдано. Checklist/task checkbox state не менялся.**

## Дополнение: повторная проверка исправления P2 — 2026-10-01

Это append-only дополнение: исходное finding, прежний REQUEST CHANGES, таблицы хешей и квитанции выше сохранены как история рассмотренной ревизии. Текущий статус определяется этим дополнением; свежие build/runtime receipts исправленной ревизии на момент его записи ещё не предоставлены.

Reviewer снова лично прочитал code-reviewer SKILL и полностью текущий внешний StopProof.cpp. SHA-256 исправленного source: `d6e9a131335954832896c8978ccfde9b90b4101a35c5f40383f4e6b38e0e6522`; прежний рассмотренный source SHA `2a7987064de4648042944ad22ca2c7308f6355f091bad25fd6488380cb3a8ffa` относится только к первой ревизии/первым квитанциям.

В [StopProof.cpp:63](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/StopProof.cpp:63) marker injectedThrowReached — отдельный atomic_bool, первоначально false для каждого runStopCase. В строке 73 его store(true) расположен только в ветке mode=3/ptsFrames=3, непосредственно перед введённым throw и после FIFO require. В [StopProof.cpp:121](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/StopProof.cpp:121) обязательный `require(injectedThrowReached.load()==(mode==3),"exact-introduced-throw-reached")` находится вне controller callbacks, после dispatchFinished acquire и EOS check, до первого запуска finalizer.

Приведённый в P2 путь теперь отвергается: если четвёртым приходит sequence 4 вместо 3, FIFO require бросает раньше store(true); controller может по-прежнему классифицировать это как finalizationFailed, но marker остаётся false, и внешний require прерывает proof с FAIL/exit=1 до финализации и STOP_CASE_PASS. Другие sink/gate/storage исключения до предусмотренного места инъекции также не могут выполнить эту обязательную проверку mode=3. Для остальных modes требуется marker=false. Atomic операции по умолчанию seq_cst и существующий dispatch completion acquire дают корректный межпоточный доступ; время жизни marker покрывает dispatcher join существующим Unwind/controller порядком.

**P2 закрыт на уровне повторного чтения исправленных исходников. SOURCE REVIEW: APPROVED NARROW; новых блокирующих findings в исправлении не обнаружено. Финальная согласованность свежих source/EXE/runner/build/runtime receipts пока PENDING, поэтому первая успешная квитанция не объявляется подтверждением исправленной ревизии.**

Сборки, дополнительные runs/тесты, VM и изменения кода reviewer не выполнял. Запись — только это дополнение в прежний разрешённый отчёт; checklist/task отметки не менялись. Объём принятия и все ограничения предыдущего review сохраняются. **Полный T114: NOT READY.**

## Финальное дополнение: исправленная ревизия и свежие квитанции — 2026-10-01

**Окончательный актуальный вердикт: APPROVED NARROW для protected Stop proof, исправления P2 и согласованности предоставленных финальных build/runtime receipts. P2 CLOSED. Блокирующих findings в рассмотренном узком объёме больше нет. Полный T114: NOT READY.** Это дополнение заменяет прежние текущие статусы REQUEST CHANGES/PENDING только для исправленной ревизии; весь предшествующий текст, finding и история хешей/измерений остаются неизменными.

Reviewer лично снова прочитал code-reviewer SKILL, обновлённый stop-run.ps1 целиком, участок StopProof.cpp с marker и обоими callbacks, а также обе новые квитанции целиком:

- [stop-build-result-c03f952c-5b0e-4de1-a351-b5e6e82268cf.json](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/stop-build-result-c03f952c-5b0e-4de1-a351-b5e6e82268cf.json): schema=1, build_exit=0; source/exe SHA совпадают с текущими файлами и runtime receipt.
- [stop-result-44343e83-e74f-4915-9dd0-b9e3e3162ef3.json](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/stop-result-44343e83-e74f-4915-9dd0-b9e3e3162ef3.json): schema=1, exit_code=0, stderr_bytes=0, pass_markers=5, accepted=true, CHILD_RESULT exit=0x0 medium_nonadmin_verified=true.

Независимое повторное вычисление SHA-256 подтвердило все 27 manifest inputs и оба текущих EXE: расхождений с финальным receipt нет. Также повторно проверены 20 canonical RecApp cpp/h против manifest mirror: все совпали. Между первой и исправленной runtime квитанциями изменился ровно один из 27 input hashes — StopProof.cpp; Context, ProtectedMfProof, общие helpers, build commands и все используемые RecApp source hashes прежние. Runtime runner прочитан с закреплённым новым Stop EXE hash; логика 45s guard, before/after checks и acceptance conditions сохранена. Context EXE и build wrapper не изменились.

| Артефакт исправленной ревизии | Независимо вычисленный SHA-256 |
|---|---|
| StopProof.cpp | `d6e9a131335954832896c8978ccfde9b90b4101a35c5f40383f4e6b38e0e6522` |
| StopProof.exe | `3f393a310b4a5a0f7fd5e1ee986d6d8efc27af392fc3bc4ae3e2043156a1d34a` |
| stop-run.ps1 | `97c17b9cf1f27323ca7bca5d5a0f10743772f08ee42114c2addadeefd27a2292` |
| ContextProof.exe, прежний | `ebc73774df9b89e442f6d1f516b9bbeeb4bd1012b8ad9ea1503a29cdc1e22980` |
| Новый build receipt | `92ca81f56cb4e298cf54b00b3a3b058f1f36dd51f82dae382cf6e0fa66d0a1ba` |
| Новый runtime receipt | `fe61c7c664401962e98fc38fcffc7efe76c22af0dd8d16a153fb529bb43dc345` |

### Закрытие P2 и предел доказательства

Исправленная source цепочка по-прежнему содержит false-init marker на case, store(true) только непосредственно перед mode=3/sequence=3 introduced throw после FIFO require и обязательный внешний require после dispatchFinished/EOS до finalizer. Этот source SHA совпадает с успешной build-квитанцией и финальным runtime manifest. Успешный путь всех пяти cases теперь включает обязательную проверку marker==(mode==3), хотя marker отдельно не печатается в JSON/output.

Прежний контрпример sequence 4 вместо 3 отвергается по прочитанной source цепочке: FIFO throw предшествует marker store, поэтому внешний require выдаёт FAIL. **Отдельного отрицательного запуска с такой перестановкой не было; runtime reproduction этого контрпримера не заявляется.** Исправление закрывает конкретный P2 без изменения controller, новых сценариев или расширения scope. Оговорка об отсутствии атомарной/hermetic аттестации всех compiler inputs сохраняется: reviewer подтвердил согласованность предоставленных квитанций и текущих файлов, а не самостоятельно воспроизведённую сборку/исполнение.

### Финальный повтор: пять случаев

В receipt по одному mode 0,1,2,3,4; прежние counts сохранены. Каждая строка сообщает eos_mask=3, fifo_exact=true и pending_lease=true; normal имеет terminal_error=false, остальные — true.

| Mode | Сохранено batches / sink calls | Stop, us | Protected job, us | PCM bytes | Cipher objects |
|---|---:|---:|---:|---:|---:|
| 0 | 255 / 255 | 357 | 122478 | 245760 | 6 |
| 1 | 255 / 255 | 7 | 89167 | 245760 | 6 |
| 2 | 3 / 4 | 5 | 27791 | 4096 | 4 |
| 3 | 3 / 4 | 4 | 33447 | 4096 | 4 |
| 4 | 255 / 255 | 5 | 83113 | 245760 | 6 |

Stop диапазон 4–357us, protected job 27791–122478us. В mode=4 код сохраняет реальное удержание sink до stopBegin+5100ms и проверку stopping/no finalizer до release; успешная квитанция включает этот путь, но отдельно elapsed held duration в output не измеряется. Terminal причины и savedLocal/trustedPrefix проверки остаются обязательными перед PASS. Это наблюдения одного свежего синтетического повтора; меньшие времена относительно первого запуска не объявляются доказательством оптимизации или новым SLA.

Protected job по-прежнему включает canonical tail Commit, independent generated-zeros AAC encode/Finalize/Commit и reopen/full decode, а также ожидание gate/COM lifecycle. Raw float prefix проверяется полностью после reopen; generated AAC не является его преобразованием. Нет acquisition, timeline/v5, native worker cleanup или SC-003 acceptance. Последующие native key failure/nonzero large index исследования остаются вне этого review.

Итоговый PENDING по свежим квитанциям снят. Reviewer не выполнял никаких дополнительных запусков, сборок, тестов, VM-действий или code edits. Единственная запись — это append-only дополнение в тот же разрешённый отчёт; task/checklist checkbox state и прочие документы не менялись. **APPROVED NARROW; P2 CLOSED; T114/Phase0 остаётся открытой, T114 NOT READY.**
