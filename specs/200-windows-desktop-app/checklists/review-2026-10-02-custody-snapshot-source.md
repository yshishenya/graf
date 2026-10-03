# Независимый source-only review: validated custody snapshot

Дата среза: **2026-10-02 UTC**; локальная дата Europe/Istanbul — 3 октября.
Решение: **Approved source only — 0 blocking findings** для нового
`readValidatedSnapshot`, typed codec failure propagation и связанных тестов/
CMake регистраций на четырёх SHA-256 ниже. Whole T116 не закрыт.

Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Ветка: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Это review текущих локальных рабочих байтов, включая untracked исходники,
не утверждение их наличия в HEAD или установленном приложении.

## Объём, инструкции и pins

Полностью прочитаны `code-reviewer` и `ponytail-review` SKILL; применены
последовательно: correctness/security, затем отдельно сложность. Использованы
root AGENTS и применимые guidance; risk lane остаётся high-risk-product.
Accepted physical Files/codec baseline из прежнего review повторно не
аудировался. Прочитаны новый snapshot requirements gate и относящиеся к
selection/error/bounds положения accepted contract §§3–5; дополнение владельца
о классификации manifest/recovery и playback согласуется с этими границами.
Посторонний dirty diff не включался в review.

| Файл от root | SHA-256 проверенных байтов |
| --- | --- |
| `apps/windows/RecApp/Storage/ProtectedCustodyFiles.h` | `ea531e71be71093abfa31f8c023304098a554f1df442946a1c2fef9b0776990c` |
| `apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp` | `60770764df0f3e625b9040c6744e07a7891cfa98d9c8a37ccfb37e3d0792d44e` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp` | `3353b599c626fe7892b449b6141f82f23cc97a4087364aba036e742eae3ad384` |
| `apps/windows/CMakeLists.txt` | `400b57f98d791a6739aa5be0a7140ce9d63f8d114f14cff305a39d8792eb141d` |

Все четыре pins совпали с freeze владельца и повторно проверены перед записью.
Нормативный contract неизменен:
`630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0`.
Прочитанный `review-2026-10-02-custody-snapshot-gate.md`:
`2c50e60558ccbdc15ef5c8abc25b6864e994f85010fcd9197bc34e3dd439e5b4`.
Его PASS112/112 — вывод отдельного requirements reviewer, не повторная
поэлементная проверка markers этим source reviewer и не runtime PASS.

## Correctness/security — основания решения

Строки CPP далее относятся к текущему `ProtectedCustodyFiles.cpp`, строки
тестов — к `ProtectedCustodyFilesTests.cpp` из таблицы.

**Typed failure сохранён.** CPP23–31 больше не объединяет всё в
invalidContent: codec hashFailed остаётся hashFailed, nativeFailed и неизвестный
codec reason становятся protectionFailed, nativeError сохраняется. Только
invalidEnvelope/invalidPlaintext классифицируются как invalidContent;
invalidInput/unsupportedPlatform остаются отдельными отказами. Mapping
применён в readBlock305, writeBlock320, readIndex346, publishIndex360 и
resolver436. Проверены call sites, а не повторно вся реализация codec/hash.

CPP455–460 допускает продолжение поиска альтернативы только для установленной
invalidContent либо ERROR_FILE_NOT_FOUND. Иные IO, unsafe path/file, protection,
hash, allocation и неизвестные причины немедленно дают typed failure без
snapshot и через reject420–422 ставят failed. bad_alloc из самой snapshot
операции также ловится488–490 с sticky allocationFailed. Успешный второй slot
не может подавить такую инфраструктурную ошибку первого; ошибка второго также
не превращается в успех первого.

**Проверка до выбора.** CPP429–461 читает каждый slot с его действительным
slot context и accepted codec bound. После успешного index decode442–450
каждый DATA проверяется через readBlock по ordinal position, entry version,
exact envelope size и full-block/exact-tail payload. Кандидат принимается
только после прохождения всех DATA; первый отказ достаточен для его invalidity,
он не превращается в частичный valid index. Только затем478–482 выполняется
selection. Ранний выход при запрещённой ошибке — отказ всей операции, не
выбор ещё не проверенного кандидата.

**Missing slot не missing DATA.** missingSlot432 устанавливается только при
неудачном открытии/чтении самого ожидаемого index с ioFailed/FILE_NOT_FOUND.
Отказ referenced DATA сохраняется в candidate446, не меняет missingSlot.
Поэтому verified branch481 не принимает broken DATA за отсутствующий второй
index. PATH_NOT_FOUND/read/access/confinement error не считаются missing.
Temp/orphan не сканируется, не становится authority и не удаляется.

| Роли и ситуация | Реальный результат CPP |
| --- | --- |
| Metadata: manifest4, recovery5, queue6, packageState7, bootstrap8, migrationIntent9; singleton или любой invalid slot/DATA | Отказ474–476, failed. Настоящий missing slot даёт recoveryRequired, не empty ledger и не автоматическую достройку пары. |
| Metadata, обе fully validated copies одного g1 | Допускается только при равенстве logicalLength, count и каждого version/envelopeBytes/flags462–468. Общие IDs/role, фиксированные headers/reserved и checksum уже проверены codec; вместе с generation это равенство decoded index, не ciphertext. |
| Две fully validated различные generations | Выбирается наибольшая478–482. Non-g1 parity проверяется accepted codec. Нет придуманного adjacency/gap threshold. Equal non-g1 не допускается. |
| Audio: canonical1/media2/playback3; правильный g1/slot0 и действительно missing slot1 | Verified byte snapshot, не metadata pair/history proof/normal package/ACK/upload. G1/slot1 audio не пользуется metadata исключением470–472; equal audio g1 pair — conflict465. |
| Canonical/media, полностью validated альтернатива и известная invalidity другого кандидата, включая missing DATA | Только trustedPrefix484–486 с исходным recoveryError/nativeError; failed запрещает дальнейшую запись. Не normal success/effects. |
| Playback с invalid существующим slot/DATA | Отказ483. Для playback разрешён verified byte checkpoint, но не canonical/media fallback. |
| Нет ни одного valid кандидата | Typed отказ474–476, не успешный пустой snapshot. |

Сравнение g1 не требует равенства DPAPI ciphertext: две copies имеют разные
slot entropy. Невалидный кандидат не даёт достоверного поколения, поэтому
helper не заявляет, что альтернатива — последний или точно предыдущий commit.

**Bounds и lifetime.** remaining начинается из codec-validated logicalLength;
entry count совпадает с ceil(length/blockBytes), поэтому min/subtraction и
position increment442–450 не выходят за длину. DATA не читается целиком как
logical object: один bounded block за итерацию. ZERO только из валидированной
entry flags1/version0/size0 и не вызывает readBlock. Size/exact/role checks
existing read205–220 и readBlock296–305 сохраняют bound-before-allocation и
IO chunks≤256KiB. Кандидаты — два bounded index, временные decoded/cipher
buffers не накапливаются по числу DATA; выбор перемещает index, не копирует
whole media bytes. Нет необоснованного утверждения global64MiB quota.

Header36–39/59–64 требует caller reservation до allocation и удержание object,
snapshot pins/ownership во время использования. Result содержит index/state/
reason, не автоматические pins или право открыть произвольное поколение позднее.
Этот caller precondition обязателен, а не уже доказанная integration. Любой
trustedPrefix/terminal fault оставляет failed; повторный snapshot возвращает
writerFailed419, запись уже блокируется existing failed guards. Fresh instance
для reconciliation — не скрытое восстановление authority.

## Тесты: что действительно проверяют исходники

NDEBUG снимается11–14 до cassert. Тесты154–287 вызывают настоящий resolver:

- Все шесть metadata roles: singleton recoveryRequired, запрет автодостройки,
  fresh reopen, независимо sealed g1 pair, затем missing DATA при existing
  slot; проверяется сохранение обоих index files155–175.
- Orphan с двумя missing indices; конфликт разных decoded g1 refs; valid
  newer metadata не маскирует broken older DATA177–195.
- Canonical/media verified singleton; missing DATA во втором existing slot
  даёт trustedPrefix с ioFailed/FILE_NOT_FOUND, а следующий publish запрещён;
  неверный audio g1 slot и equal audio g1 pair197–220.
- Различные fully validated generations без искусственного gap limit223–227;
  playback singleton допустим, playback fallback запрещён255–259.
- Повреждённое outer framing даёт явный invalidContent prefix262–269;
  full block плюс4B tail проходит, а reuse старого short tail как full после
  расширения даёт invalidContent prefix271–285.
- Максимальный ZERO index64GiB/262144 entries проходит новый resolver430–432.
  Это тест bounded структуры, не64GiB plaintext allocation или DATA throughput.

Faults75–84 компилируют **реальный Sha256.cpp** с TU-local CNG open wrapper;
85–95 компилируют real Files.cpp с прежними локальными IO wrappers. Codec
использует реальный sha256Stream/NativeHash, а не подменённый результат digest.
Fault ordinal1–4 в229–243 соответствует index0/hash-or-read, DATA0,
index1, DATA1 после inject reset. Hash open failure, ReadFile FALSE с
ERROR_READ_FAULT и throw bad_alloc каждый обязаны дать !ok и свой typed
reason; после снятия fault повторный resolver обязан дать writerFailed.
Throw расположен до stream-read catch, в реальном NativeHash constructor;
это проверка propagation allocation failure, не измерение всех allocation.

Wrong slot entropy test245–252 сохраняет valid physical ACL/framing, но
использует реальные DPAPI bytes другого slot: требуется protectionFailed с
ненулевым nativeError, не degraded success. Digest mismatch и native hash
failure не смешиваются в mapping; mock success другого index не используется.

CMake79–84 исключает отдельно compiled hash и Files object именно для Windows
ProtectedCustodyFilesTests, где реальные CPP уже включены в TU. Остальные
тесты получают обычные objects; non-Windows получает их вместе с
unsupportedPlatform поведением. Нет duplicate definitions, production knobs
или новой зависимости. Предыдущая baseline fault/physical матрица не
переутверждается этим обзором.

## Ponytail — отдельный результат

**LeanAlready. Lean already. Ship.** **net: 0 lines possible**: конкретного
безопасного сокращения не найдено. Два bounded candidates, missingSlot отдельно
от DATA error и явная классификация roles/errors необходимы для разных
accepted outcomes. Resolver переиспользует codec/readBlock/physical read и
existing failed guard; fault seams ограничены тестовым TU. Ponytail не снижает
security/risk lane и не разрешает удалить проверки ради краткости.

## Runtime и остающиеся gates

Reviewer не запускал builds/tests/VM, не читал VM logs, не делал install.
Владелец сообщил test-before-code RED: C2039 missing method/exit1 и initial
implementation focused native PASS/exit0. Эти сообщения — отдельные данные,
не лично подтверждённое reviewer execution. Latest extension full-runtime
rerun для этого freeze ещё ожидается по сообщению владельца. Round20636/36
принадлежит прежнему physical Files срезу и не записывается как PASS resolver.

Открыты whole T116: logical read/seek/write/commit, metadata birth ACK,
global owned budget/pins/cache accounting, async UI tickets/adoption, полный
producer/consumer pipeline и storage integration. Snapshot не даёт normal
package, account/upload/delete authority. Migration/GC T117, full storage/
installed T118, hardware/audio/60min/AEC, clock/calendar и общие release gates
остаются открытыми. No power-loss/history guarantees добавлено не было.

Единственное изменение reviewer — этот собственный отчёт через apply_patch.
Код, нормативные документы, markers, tasks/plan, прежние отчёты, чужие рабочие
изменения и GitHub/commits сохранены. Approval относится только к указанным
четырём source pins; при их изменении нужна новая привязка review.
