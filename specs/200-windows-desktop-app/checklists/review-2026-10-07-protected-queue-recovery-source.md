# Round277 — SOURCE: настоящее восстановление защищённой очереди

**SCOPED SOURCE GO; C0/H0 в проверенной области queue-recovery.**
Это не полный T116, готовность приложения или разрешение эффектов.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.
Risk: high-risk-product, existing T116/#7444. Reviewer применил code-reviewer
и ponytail-review; читал исходники/экспорты на Mac, VM/build/tests не запускал.
Единственная запись reviewer — этот новый отчёт, 0 checkboxes.

## Точная привязка

Frozen `/Users/yshishenya/Documents/graf-f200-recovery277.7yvyAf`;
`source277.json` SHA `61d6e944e0eb10d9a6118004e65d84bac3f9fd8cac288a6ff564ea796b20b110`.
Все207 входов canonical/frozen лично сопоставлены с картой: mismatches0;
source maps Release/Debug/App receipts равны этой карте.
REQ277 SHA `a346c9da7cdb8689f009b64ac7ac251df0cdef163bd76ffa32581b1edc8cc6c8`;
plan1839–1854, custody §5/§8, FR-012/013/014/022 → T116; нормативы не менялись.
Delta против accepted276: CMakeLists.txt, NativeCapture.h, Metadata.h/.cpp,
QueueService.h/.cpp, NativeCaptureStorageIntegrationTests.cpp, QueueV2Tests.cpp.
Основные SHA256 внутри `apps/windows/RecApp`:

| Файл | SHA256 |
|---|---|
| Recording/NativeCapture.h | `2ad9219713dac9d8a27dfb649d29ed00b5f9447883166d83e265963360ee8ce7` |
| Storage/ProtectedCustodyMetadata.h | `95dac817a8428fb48ce5b358784b0cd6513c0d0196b1c7524d51b39d26fc6f5a` |
| Storage/ProtectedCustodyMetadata.cpp | `f138d8a06cc2f10b3fc76c4dcdb456a8548ecd23d87febb11483636e04628620` |
| Upload/DesktopUploadQueueService.h | `b9e2c630702af05142b8790d5d1c3e515a7063de452377bb6f6eef1fed62ff6a` |
| Upload/DesktopUploadQueueService.cpp | `fbb9a3a553aaf60a89c0741449ecc4e37cda0bae2368574f9adeab3077545434` |

## Проверка исходного потока

QueueService.cpp:95 использует один domain loop: needsAuth → retry/auth_recovered,
не меняя owners/identity/accepted ranges/attempts/server truth/operations/purge ACK.
Общий serializer сохраняет logical v3/read-v2 и порядок/escaping полей;
protected строки/три коллекции/scratch/output/control blocks charged, числа через
stack to_chars, лимит4MiB до роста; нет protected filesystem::path conversion.
Decoder/serializer/domain scans проверяют cancellation; прежние64MiB/pin32/job4
не расширены. QueueValue — данные, не native proof или account/effect authority.
ProtectedUploadQueueCandidate::read в QueueService.cpp:1534 удерживает genuine input,
валидирует unselected peer перед selected; любой bad peer отвергает всё.
Metadata.cpp:1039 revalidates BOTH bootstrap/queue/context/current generation
на непрерывных owner leases в том же проходе; нет reopen/path-derived authority.
NativeCapture.h:685–740: revalidate → charged copy → transition → serialize →
один full commit; commit/candidate удерживаются worker до polling ACK либо stop.
Отмена проверяется после read, перед/после copy, в domain loop и перед commit;
ParseCancelled классифицируется ioFailed/ERROR_OPERATION_ABORTED, не malformed.
До ACK private projection старая; stale epoch допускает только физическое adoption,
не effects. No-op — notCommitted/error none/changed false, base=target, без записи.
Ошибка/ambiguous закрывает следующие mutations до свежей owner validation.
Update/shutdown после publication доводит readback/adoption на worker до release;
следующая команда не использует старый generation или незавершённый commit.
Global storageWritable=false; публичные queue_/scheduler/Record/HTTP закрыты.
Ponytail: повторный parser/backend/owner framework не добавлен; безопасных удалений
в этом delta не найдено; `net: -0 lines possible.`

## Реальные проверки и границы свидетельств

Actual-class tests используют genuine worker seed/commit g2, public recover,
pre-start/coalesced intent, no-ACK view, stale epoch adoption g3, duplicate no-op,
restart и update/destructor drain. Owners/ranges и две другие коллекции сохранены.
Executable-local native hooks: flush failure → notCommitted/restart g2;
rename completed + failed IO status → ambiguous/restart g3; cancel после flush
до publication → g2, после rename/readback → committed g3. Production knob нет.
Native memory-pressure case может отказать ещё в owner read: это не доказательство
отказа именно на copy. Pure Value tests отдельно проверяют copy/serialize refusal,
retry и baseline restoration. Ordinal cases не доказывают каждый scanner callsite.
Unknown-root fixture подтверждает сохранность/default-closed, не отдельную ветку
private-ACL unknown inventory. Полная owner/finalizer fault matrix остаётся pending.
Ранний reported RED277 был compile failure отсутствующих backend API, не runtime RED.

Лично прочитаны полные native test logs, parsed receipts/readbacks и App build log;
JSON BOM/UTF16 build log декодированы только в памяти, экспортные байты не менялись.
Release: build0/test0, selected8/8,111.18s; Debug: build0/test0,8/8,279.56s,
Files252.00s. Timeout360 задан с начала, не post-failure retry. Portable46/46,27.76s.
В raw actual-class log PASS summary после assertions, не отдельные строки всех cases.

| Экспорт | SHA256 |
|---|---|
| native277-release.json | `0221ce58eca0dbe4abbf13e9125b7fad9e517b1b2d929a4fc4973362bc36e718` |
| native277-release-test.log | `a644f52fc4e1a3460ca6280ba6cd1bb1c810936950a3663324edef524d40bd4b` |
| native277-debug.json | `bc57e2a34c56cd5b084bd71adb4bd88d463b89ae4c8d2c57062d73174caba793` |
| native277-debug-test.log | `dc08e2955d928a3d6052b16de3bba3ad63f13c1ca3f99304f9af3d6d6a4221d1` |
| portable277-test.log | `f20441a737a0350a6817a79f5dd862ae5c0e65e981ca5ac269bd29fa7dee3f7c` |
| native-readback277.json | `6842d2a97b44c498c3e8bd4815e456b381580f81b534b50b9cf714388ec1f3cc` |
| app277.json | `77534ef48740453457439bfdec18a32504915d16de004cd6202d77f0084ac1f6` |
| app277-build.log | `1f4a8929979b13e0b4313234ebb35841fa45609f8f5fbbb9e2a7c755c78629bd` |
| app-readback277.json | `2b19866f8afb2fdcaadb5ee74531a237f9ffbe8342dba88f42942790208c5a36` |

Main executed readback: source207/receipts/16 native EXEs SHA+PE0x8664 MATCH,
owned_jobs0; reviewer проверил экспорт/скрипт, не исполнял Windows readback.
App SDK Release/x64 build0, build-only-no-install; отдельный readback207 MATCH,
EXE `c5b7b70a3968a940958fbe41aeb62a6cef4249a5a4d7312e4e10a606f92e5d89`, PE0x8664.
AEC identity846fe90a289f58b7c9303a635142aa2c7caa93e5 verified; D9025/C4100
сохранены: не zero-warning, не vulnerability audit, не install/launch proof.

## Сохранность и итоговые ограничения

Предыдущие163 Markdown byte-identical; после добавления164:10 current normative
checklists154 checked/0 open и154 historical Markdown отдельно. Старые markers
не менялись. Tasks120/93/27 SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
T116 остаётся OPEN; high-risk lane не закрыт. Нет full52, A11y/hardware/MF60min,
finalizer/protected V5/HTTP/playback/delete integration, H250 или release GO.
Legacy AAC RED не исправлен/не исключён из требований; admission не открывается.
