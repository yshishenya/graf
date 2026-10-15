# Независимая проверка Debug321 и final-transfer322 — 2026-10-10

## Решение и разрешённая область

**C0 / H0 / P2=0 в проверенной области evidence. Exact engaged-snapshot
worker error-return criterion закрыт. ALL-checkbox gate: PASS, 420/420.**

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty bytes сохранены.
В рамках обязательного независимого ревью Spec Kit, по поручению основного
агента, reviewer проверил сохранённые source/commands/logs/receipts, изменил
только `[ ]` → `[x]` в tree report:586 и создал этот отдельный отчёт.

Слова «нового receipt нет», прежние counts/STOP и findings в tree report и
`review-2026-10-10-http-all-checklist-gate.md` оставлены как историческое
основание предыдущего cut. Они не означают PASS того снимка. Последующее
закрытие доказано только новым diagnostic322 ниже; direct moves, second rename
и обычный full-suite PASS по-прежнему не заменяют точную ветку.

## Debug321: независимый разбор сохранённого исполнения

Artifact root: `/Users/yshishenya/Documents/graf-f200-progress319-green.gc4KoP`.
Receipt: terminal=true, native_completed=true, stage=full53_debug_verified,
build_exit=0, test_exit=0, completed_tests=53. Полный stdout разобран независимо
от harness и summary prose: 53 starts, 53 уникальных Passed, 106 согласованных
events, IDs1–53, совпадающие имена/порядок, без overlap/repeated/missing events.
В LastTest совпали все53 IDs/имени/durations и команды именно
`C:/Temp/graf-f200-stream292/core-build/Debug/<test>.exe`; все53 Test Passed.
Total time2244.40s; Recovery424.62s, Capture525.65s, Files327.77s.
Build log прочитан как UTF-16LE, compiler error lines не обнаружены.
Capture log содержит actual_transport_bytes=pass, after_ack_allocation=armed,
after_ack_allocation_retains_progress=pass и protected_result_adoption=pending.

Source manifest319 совпал с receipt и всеми209 frozen files; все209 current
canonical files тоже совпали. Проверенный harness имеет explicit `-j1`,
per-test900s/outer7200s, guarded native completion, финальный RequireIdle и
Verify guest/share. Receipt привязан к ctest PID5300, creation UTC
2026-10-10T02:20:47.1625783Z и CMake ctest.exe. Session92578 EXIT0 сообщён main;
reviewer не запускал/не наблюдал этот процесс лично. Post-native idle принимается
из terminal stage проверенного harness и сообщения main, без нового VM query.

| Артефакт321 | Лично пересчитанный SHA-256 |
| --- | --- |
| source319.json | `a71ff9d628da82d874587ae73496f3e58895ed9a0679cc50f08e1f82b25aabd5` |
| native321-debug.json | `210e60017daefb786fa78453fda36db40ada69104095807ae6f6409dfd6d0562` |
| test321-Debug.log | `57e1d16fd4cca3a532ca7f4fde44b51d5f8da70e42d117f73bd4cb09387c0aa5` |
| native321-Debug-LastTest.log | `528d54663db6a86dd886bbdf53571f2b82ded816b1fc06d859add474d6288ad3` |
| validate321-debug.ps1 | `ebf6b69d2e2cea13e735a1c7d32152bde29cbd4b27e65e4767224688173617fe` |
| run321-debug.mjs | `e722875f70a2686fd4f78a356229f2e191dca9d5bbbe36c8a574ac3908ec23ec` |

Это full53 Debug core CTest acceptance, не solution/MSIX/installed/hardware.
Release320 не повторялся; его historical harness exit1 из-за summary regex не
переписан в exit0. Debug321 не выполняет отсутствующий final-transfer cut.

## Diagnostic322: source identity, Debug и точная ветка

Artifact root: `/Users/yshishenya/Documents/graf-f200-metadata-return322.NW3LYN`.
Все210 effective files лично сверены с source322.json. Base319209 совпадает с
canonical209. От base к effective:207 unchanged; CMake только append; внешняя
FilesTests copy только добавляет `return 0` переименованному unused main;
один новый MetadataFinalTransferDiagnostic.cpp. Production bytes unchanged.
Canonical tests не редактировались. Native guest pre/post source verification
принимается по проверенному harness/receipt, отдельно от личной Mac сверки.

Обе actual CL tlog entries относятся к нужным Metadata.cpp и diagnostic TU,
содержат `/MDd /RTC1 /Od /Zi /Ob0 /Zc:nrvo- /std:c++17 /W4 /WX /EHsc`.
Нет `/Ob1–3`, `/O1/O2/Ox`, `/GL`, включающего NRVO override, NDEBUG,
отмены `_DEBUG` или response-file подмены команд. Буквального `/D_DEBUG` нет
и он не добавлен как критерий: TU:9–11 требует `_MSC_VER` и `_DEBUG` через
`#error`, сборка успешна. В included fixture:20–23 NDEBUG снят до `<cassert>`;
assertions не заменены. Real Debug charged proxy виден в квалифицированном
стеке, не выведен только из названия configuration.

Control failAt0:570 calls, committed snapshot generation1 и retained lease;
cleanup baseline0. Обязательный negative control failAt1:hit, calls1,
commitImpl1581, qualified=0. Final failAt570:hit, calls570, qualified=1.
Лично проверен ordered stack frames13<17<18<19<21<27<28:
CustodyAllocator proxy allocate → CustodyVector<IndexEntry> move:Codec.h30 →
CustodyIndex ctor → CustodySnapshot ctor → optional construction →
CustodyMetadataCommit move:Metadata.h331 → commitImpl final return:Metadata.cpp1649.
Это не ранний candidate ctor1581, не reopen/readback и не snapshot assignment1647. Optional construction
перед MetadataCommit transfer доказывает engaged snapshot. VEH лишь фиксирует
first-chance stack и возвращает EXCEPTION_CONTINUE_SEARCH; символы разрешаются
после отключения allocation hook, без замены unwinding/catch.

Source TU:88–104 и terminal markers подтверждают ambiguous/allocationFailed,
snapshot absent, lease retained, base0/target1; nextBlockVersion(0)writerFailed
при неизменном writerIoCounts. Дополнительно31 pins принимаются, следующая pin
отклоняется; actual id.bin write-open запрещён ERROR_SHARING_VIOLATION.
В production reject:1556 snapshot очищается до повторного return; move ctor
Metadata.h331 готовит snapshot до переноса pin/lease. Исключение final transfer
не вышло наружу: иначе qualifying-fault assertion110 завершила бы test failure.

После окончания WHOLE result/extra pins выполняется cold open/readValidatedSnapshot:
verified generation1, length3, one entry, real readBlock/openBlock и exact
CustodyBytes{7,11,29}. После всех fixture/owner/value lifetimes exact owned
baseline0 восстановлен. Затем RemoveVectoredExceptionHandler/SymCleanup/found
assertions и финальный marker; test_exit0, native_completed=true.
Никакого quota/pin увеличения, catch bypass или реального аудио не было.

Receipt stage diagnostic_verified_pending_independent_review — исторически
корректное имя стадии до этого review, не самодостаточная приёмка. Проверенный
harness связывает receipt с Debug321 receipt SHA, same-byte script/manifest
hashes, новым каталогом, actual compiler commands, EXE/PDB pre/post hashes,
owned PID9168/path/creation UTC2026-10-10T03:24:02.8209109Z и bounded900s exit.
Финальные RequireIdle + Verify guest/share предшествуют этой стадии; timeout
и неполный marker set не могут дать verified exit0. Session89360 EXIT0 сообщён
main. Reviewer сверил экспортированные logs/receipts; EXE/PDB не экспортированы
на Mac и лично не rehashed. Их identity и native idle принимаются на уровне
guest receipt/harness, а не нового live VM наблюдения. Прямой exe не создаёт
дочерних workers; terminal process exit дополняет source lifetime/baseline proof.

| Артефакт322 | SHA-256 |
| --- | --- |
| source322.json, effective210 | `4e13c345260b33800deb7b46eb03632b6068980266ea8f5088dd761f4b21212d` |
| native322-diagnostic.json | `918d4cb546179bc9eb1591ae5f9c2fe66c7bdb7ebf6c3213f3a6ccd21eda3436` |
| test322.log | `ab76ab365034a1d816a2dbd44f5358477c3f1b27e4cfd90a6eedf7dc446a3594` |
| compiler322-common.txt | `d6d90784bccbbaae59cffd7e8cf7c8e369940b148e113ca18adbd9fbbe7f5709` |
| compiler322-diagnostic.txt | `91a237d061b534c1e2213e3f988037b0c1203861ac8f32f688ee1fdc2ecf4e66` |
| validate322-diagnostic.ps1 | `6724fa10c601eb6e4c04b56e6a8058130bd8f44c8657b840905b5c2a894b8c6d` |
| run322-diagnostic.mjs | `ad4fec78829c8fad7b6048f7a89a8f98b3a0ece9a981bd4aa56ba125178f0427` |
| Diagnostic EXE, guest receipt only | `b4d28ae0cd42ca374e12efd4769d86591d4371d3c42dff7c2563a4e34810b555` |
| Diagnostic PDB, guest receipt only | `a3b18fcf47e9c962bf96d6ef49cc804f73b31b57d13e0b365ec354270c60a320` |
| External diagnostic TU | `29868fc59a166181729ea5136f6128c3ba73e8ae0fc86cedd67cc768e3128602` |
| External FilesTests copy | `535037ba403f3e31177cca54cec52b4dc8cac10081306e27e214ecaebf58f09f` |
| External CMake append | `c5c41ab9b1ca17ffefe0946e88e8a003ca7d08fddebe8068b747c08157b7c958` |

## ALL checklist readback

Все172 исходных Markdown полностью просканированы по bytes/markers, все420
checkbox criteria перечитаны без historical exclusions. До записи419/1;
после единственного marker change420/0. Новый отчёт не вводит checkbox:
итог173 Markdown,29 с markers,144 без markers,420 checked/0 unchecked.
Прежние checked criteria сохраняют прежнюю область/основание; это не новое
подтверждение всей реализации. Standalone normative10:154/0; остальные163:266/0.

| Checklist | Total | Checked | Unchecked | Status |
| --- | ---: | ---: | ---: | --- |
| advanced-routing.md | 14 | 14 | 0 | PASS |
| audio-capture.md | 24 | 24 | 0 | PASS |
| calendar-launcher.md | 5 | 5 | 0 | PASS |
| calendar-operation.md | 8 | 8 | 0 | PASS |
| calendar-wire.md | 5 | 5 | 0 | PASS |
| packed-writer.md | 12 | 12 | 0 | PASS |
| privacy-pause.md | 12 | 12 | 0 | PASS |
| requirements.md | 22 | 22 | 0 | PASS |
| review-2026-10-03-packed-tree-source.md | 38 | 38 | 0 | PASS |
| review-2026-10-04-calendar-join-gate.md | 12 | 12 | 0 | PASS |
| review-2026-10-04-calendar-resolver-gate.md | 12 | 12 | 0 | PASS |
| review-2026-10-04-calendar-url-gate.md | 12 | 12 | 0 | PASS |
| review-2026-10-04-manifest-cap-source.md | 9 | 9 | 0 | PASS |
| review-2026-10-04-packed-cadence-gate.md | 12 | 12 | 0 | PASS |
| review-2026-10-04-packed-cadence-source.md | 18 | 18 | 0 | PASS |
| review-2026-10-04-packed-live-writer-gate.md | 14 | 14 | 0 | PASS |
| review-2026-10-04-packed-live-writer-source.md | 9 | 9 | 0 | PASS |
| review-2026-10-04-packed-package-gate.md | 12 | 12 | 0 | PASS |
| review-2026-10-04-packed-reader-gate.md | 20 | 20 | 0 | PASS |
| review-2026-10-04-packed-reader-source.md | 9 | 9 | 0 | PASS |
| review-2026-10-04-packed-resize-gate.md | 14 | 14 | 0 | PASS |
| review-2026-10-04-packed-resize-source.md | 9 | 9 | 0 | PASS |
| review-2026-10-04-packed-rewrite-gate.md | 16 | 16 | 0 | PASS |
| review-2026-10-04-packed-rewrite-source.md | 9 | 9 | 0 | PASS |
| review-2026-10-04-packed-tail-gate.md | 14 | 14 | 0 | PASS |
| review-2026-10-04-packed-tail-source.md | 9 | 9 | 0 | PASS |
| review-2026-10-04-packed-writer-source.md | 18 | 18 | 0 | PASS |
| security.md | 27 | 27 | 0 | PASS |
| ux.md | 25 | 25 | 0 | PASS |
| Остальные144 Markdown без checkbox, включая этот report | 0 | 0 | 0 | PASS |
| **Итого173 Markdown** | **420** | **420** | **0** | **PASS** |

Tree report до изменения SHA
`8810e2dbfdc8099c92d0a43402343a14187c5bed6ab14419f4450c25a4bb961d`;
после изменения SHA
`8057d9a09f9b39d4ef054c63e5318d8bf3fd3ad9ea69cc03e52ae55c709aa4dd`.
Старый ALL gate SHA
`9046fad30dca6aced77b9ba62aae54164e3e2a34cd9abb265874dafa5a62bdf3`
оставлен неизменным. Остальные171 исходных checklist Markdown не изменены.

## Нормативная identity и оставшиеся границы

Принятые9 normative hashes повторно совпали с предыдущим reviewer gate:

| Артефакт | Current SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `9cdc5200419b6264d8e0c6a8c01aca5956b225661e674bba49acecbc4b90cf21` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| research.md | `4a7a1f9d8f7606a106b68e5b6194a0de8d75243508232c191f945f0fc0faa90e` |
| data-model.md | `c24b9d10bf5b935bcf51bb12034a0bb9ccef4a0b3719a138b48a26cbaa0d3bc7` |
| quickstart.md | `44c93c6558e8564aefe15a2180fd22d117f6368307d865b02253f9e0dffdf0b9` |
| contracts/windows-protected-local-custody.md | `598223854ea7e614694167c4019ef199e30c82b3ac1c44b33fcefa94fbe27fee` |
| contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Снят только этот ALL-checkbox blocker. Остальные implement prerequisites,
актуальность analyze/issue ownership и разрешение конкретной следующей работы
проверяются отдельно; GitHub сейчас не читался/не изменялся. T116/T120 OPEN,
ALL HTTP control-buffer quota/preowned terminal и actual scheduler/result
commit/adoption не реализованы/не приняты этим отчётом. Global admission false;
нет whole-feature/full application/installed/hardware/release GO.

`code-reviewer` использован для source/exception/lifetime/evidence проверки;
`speckit-implement` — только для независимого reviewer-owned ALL-checkbox gate,
не запуска implementation. Norms/tasks/code/другие reports не редактировались;
jobs/builds/tests/VM/CUA/GitHub не запускались.

EOF — независимый ограниченный reviewer report.
