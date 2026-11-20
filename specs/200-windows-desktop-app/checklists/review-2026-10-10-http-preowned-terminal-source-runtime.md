# T116 — preowned HTTP terminal: независимый source/runtime review

Дата: 2026-10-10. Reviewer: `code-reviewer`. Lane: независимое чтение
high-risk Spec Kit среза и сохранённых focused validation artifacts;
единственная запись reviewer — этот отчёт, без новых checkbox.

Вердикт: **SCOPED IMPLEMENTATION SOURCE GO, C0/H0/P2=0;
FOCUSED DEBUG RUNTIME327 PASS** для заранее созданного result-owner и
сохранения известного ACK progress без позднего terminal allocation.
Это не ALL-quota, scheduler/adoption, full53, installed или release GO.
T116 и issue #7444 остаются OPEN; другие consumer/T120 gates не закрываются.

## Исходники и область

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty changes сохранены.
Artifacts: `/Users/yshishenya/Documents/graf-f200-terminal325.uCD5ip`,
`/Users/yshishenya/Documents/graf-f200-preowned326.GMv7jA` и
`/Users/yshishenya/Documents/graf-f200-preowned327.dfPzKM`.

Reviewer сверил физические 209/209 inputs каждого frozen325/326/327;
canonical 209/209 совпал с327. Против325 — два production-файла и Capture
test; против326 — только две строки Capture test: очистка workspaceId и
удаление избыточного qualified-assert. Остальные208 файлов неизменны.

| Объект | SHA-256 |
| --- | --- |
| source325.json | `bdaeb605fe619a328a1b65654d0fffc32687fbb0f0bd1eff9ecdd55db23cb23e` |
| source326.json | `af5623676be6468efcc117e61d3eba16284e737d097d8c1dce9f3fce4986e0c5` |
| source327.json | `c9ef65a09ccf5f83cf38ea7aa292927e6db3bb2ac3971e5d980450371358311c` |
| DesktopHttpTransport.cpp,326/327 | `3b1a81d82d64afe85d8857d2510730c02f5de676160ec389ad28de8079951781` |
| DesktopHttpTransport.h,326/327 | `35cbf8ffba537340d4f4e2199833085b8333ea10224660abe63304460a117f2b` |
| NativeCaptureStorageIntegrationTests.cpp,325 | `75bd62d88822d956f2be50fa297ed97c8865710897674ed9a0526841fc8d4969` |
| NativeCaptureStorageIntegrationTests.cpp,326 | `11d1ec631b3133ce4fbbc2c80eb1d7adb980ac8228375a7f758049b663eef037` |
| NativeCaptureStorageIntegrationTests.cpp,327 | `527a4dc7e535c52cfd5879c440c3f164b1938bac8bdeaaa5941d4bf2738e2dc8` |

Production paths: `apps/windows/RecApp/Upload/DesktopHttpTransport.{cpp,h}`;
test path: `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`.

## Причина implementation source GO

Protected overload cpp1232–1289 создаёт `allocate_shared` result/control block
через CustodyAllocator, затем engaged truth до config copy, source validation
и account GET. Возвращается тот же `shared_ptr<const DesktopTransportResult>`.
Общий `uploadPrepared` cpp1037–1218 заполняет result&, `uploadFile` cpp645–716
возвращает enum и заполняет result&, `uploadResponse` cpp481–500 работает
in-place. Catch меняет retryable status через nonallocating reset, не создаёт
и не переносит terminal value; известная truth сохраняется. Пустая truth без
meetingExists не публикуется. Ordinary value wrapper остаётся совместимым
существующим API, но не считается protected acceptance.

Протокол общий, без второго потока. Proof/session/directory binding,
protected stream без plaintext fallback, charged body/control, reads ≤256KiB,
body lifetime и ACK/range/hash проверки не ослаблены. Пределы не повышались.

Paired test проверяет nullptr/zero wire при полном owned budget, затем тот же
transport без исчерпания бюджета выполняет spaces → auth/me → sync-state503
и возвращает retryable без truth. ZeroCalls отдельно не доказывает, какое
раннее выделение отказало; вывод о preowned обеспечен также чтением порядка
owner-before-config и поздним cut: hook обязан остаться armed без hit.
Полный exact idle baseline проверяется main после inspection.get(), освобождения
proof/expected/result owners и worker, а не по промежуточному cache baseline.

## Сохранённые RED и FAIL, без переименования истории

323: actual configure0/build0/test3, terminal/native_completed=true,
qualified=false, stage=test. Старый прямой line predicate не доказал точный
RED; **323 не принят как exact RED**. 324 **не запускался**, по истории main;
runtime receipt324 не используется.

325: reviewer прочитал actual receipt и весь log. Configure0/build0/test3,
terminal/native_completed=true, qualified=true,
stage=expected_terminal_allocation_red. После валидного первого PUT ACK и
второго missing-ranges wire throw наблюдён ordered stack: frame6
basic_string::_Construct_empty → frame8 uploadPrepared catch$150, header35 →
frame13 тот же template instance uploadPrepared, cpp1168.
`TERMINAL_ALLOCATION hit=1 qualified=1` подтверждает late terminal ctor
allocation, а не любой предыдущий сбой. Abort не доказывает full owner drain.

326: actual configure0/build0/test3, terminal/native_completed=true, stage=test.
Лог падает на ожидании первого spaces path, до late cut. Причина fixture:
confirmedIdentity был сброшен, но workspaceId оставался заполнен, поэтому
реальный resolver cpp820 пропускал spaces GET. Reviewer ранее пропустил это
условие. В327 workspaceId очищен до создания preparing; production не менялся.
**326 остаётся FAIL**, его post-test source/idle checks не были достигнуты.

| Evidence | SHA-256 |
| --- | --- |
| native325.json | `22b3327bbfdef3819f02e01cd16f2ccad340db3c7edbf771fc90db33405d67f3` |
| test325.log | `ac93a48f4169d777103daf24f38216c5f6ead6938baadd1e2df79b0876248a55` |
| native326.json | `f27f65ee8d7ac7cbdacb8607aa21eea1f36d0c8b3532f075208a1c72a97be240` |

## Actual focused native327 GREEN

Reviewer прочитал actual native327.json и полный test327.log, независимо
посчитал их hashes. Receipt: configure_exit=0/build_exit=0/test_exit=0,
terminal=true/native_completed=true, stage=preowned_terminal_verified;
source identity совпадает с приведённым327 manifest.

Owned PID2272, creation UTC `2026-10-10T04:16:36.8876436Z`,
Debug NativeCaptureStorageIntegrationTests.exe, argument `--protected-upload`.
EXE SHA из receipt: `9b44ccc4e5dd28a33ffa67d9b73de557964ae4dde10df7fc50a67a9c8ad37b19`.
PDB SHA из receipt: `21819b784b5acee0270d6ea0a238284c5b537961ef648c45e18b92f1dd04df88`.
Reviewer сам guest EXE/PDB bytes не читал и процесс не запускал.

Полный log содержит frames_3000/finalized/cold_read, actual_transport_bytes=pass
с protected_result_adoption=pending, preowned_admission_zero_wire_including_account=pass,
два after_ack_allocation=armed, cancel_range_quota_ack_allocation=pass,
after_ack_allocation_retains_progress=pass, preowned_terminal_no_late_allocation=pass,
затем cold_read_verified/done. Ни одного TERMINAL_ALLOCATION hit нет.
qualified=false здесь корректен: GREEN требует отсутствия allocation hit,
не RED qualification. Baseline=0, empty_proxy=16; test exit0 после обязательного
exact idle assertion подтверждает завершение этого oracle. Receipt fixture_files пуст.

| Evidence | SHA-256 |
| --- | --- |
| native327.json | `1420cd2638b799fe89883943a1cfbe0134de0c611fef44624c8ce5457ddbabfe` |
| test327.log | `eb827a32cde0bae9e78b625d677bbdbc4c91798206d2506565e6bf5336e9d187` |
| validate327.ps1 | `40e4344504fa1eef0de587704bf993dbe8d3fe7fff8a59b1e267b8dca9082148` |
| run327.mjs | `2e9bf04f46529312b463f58b6c3c8699154c152dccfb140440228ac6011f68f4` |

Harness source review C0/H0/P2=0: script hash/decode и JSON hash/parse same-byte;
pinned terminal FAIL326 receipt, native idle и все209 old326 inputs проверяются
до единственного test copy. GREEN требует exit0/всех markers/no hit, затем
idle и Verify native/share209 до verified stage. Таймаут не убивает процесс,
не означает native_completed и не может дать GREEN. Выполнение guest postchecks
подтверждается receipt stage и прочитанным harness, не отдельным VM-запросом reviewer.

## Portable и оставшиеся обязательные gates

Portable326 receipt/log независимо прочитаны: configure0/build0/test0,
terminal=true, stage=portable47_verified, 47/47 PASS, 29.14s. Все три log hashes
совпали с receipt. Это source326 portable evidence; production327 тот же,
но native-only test delta327 не считается отдельным portable327 прогоном.

Portable receipt SHA: `16f2454a9bf5ed71f1c24646ffd5ceb654f61d9e5db537d6d7aac529e9e98b81`.
Portable test log SHA: `4acce88361186b002bb1f4621af93b2a0355d96394806c8722c5aa1110534d7b`.
Это не updated full53 Release/Debug: прежнее full evidence не переносится
на новые cpp/h автоматически. Installed/live/server/audio acceptance отсутствует.

ALL request/response/hash/serialization/config/DTO/result internal string/vector
capacity/control/Debug allocations под общей квотой ещё OPEN: здесь charged
result struct/control и body, не все внутренние allocations. Scheduler full
prepare commit/adoption → worker proof/network → fresh-current single result
commit/adoption, stale/publish/lost-poll fences, owner-worker last release и
shutdown continuation остаются OPEN. Global storageWritable/localQueueComplete
не разрешаются этим direct transport test; pending adoption marker сохранён.

Reviewer не запускал jobs/build/test/VM/CUA/GitHub, не выполнял cleanup и не
менял code/norms/tasks/checklist markers/другие reports. Разрешённое main
последующее удаление только test-temp323/325/326/327 этим отчётом не заявляется
выполненным; receipts/logs/source и native build должны сохраниться.
