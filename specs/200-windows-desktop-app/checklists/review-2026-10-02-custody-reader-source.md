# Независимый source-only review protected reader — T116

Дата среза: 2026-10-02 UTC; локальный контекст Europe/Istanbul — 2026-10-03.
Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Branch: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.

## Решение и границы

**Request Changes: один конкретный P2 blocker на указанном freeze.**
Это статический обзор нового read-only IStream, ownership, cache, cancellation,
CopyTo, новых регрессий и регистрации TU. Не повторный полный аудит codec/Files.
После исправления требуется перечитать изменение и привязать решение к новым SHA.
Ни source-only approval, ни synthetic MF adapter не закрывают весь T116.

Полностью прочитаны `code-reviewer` и `ponytail-review`; применены последовательно:
correctness/security, затем отдельно complexity. Прочитаны canonical AGENTS,
guidance index/релевантные правила, новый requirements gate и contract §§5–7.
Normative/guidance SHA совпали с ранее прочитанным контекстом accepted storage.
Lane обзора: read-only investigation + только собственный report;
lane реализации остаётся high-risk-product. Checklist markers не менялись.

## Проверенные source pins

Все пути ниже относительно указанного root; SHA — текущие working-tree bytes,
а не заявление, что новый untracked код уже содержится в HEAD.

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.h | `d1dc47e71865bd09a67cde2fe281e9be24a92fae690a9a8b2ea90f6f8b6a91b4` |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp | `1d6150c7e1e5039e2752c53e205da2dff0497497e717a0db06b49320be8c3009` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | `45a64ba3be3785f00c26ff0cab911794e3e73a63b2439f26431c14914a4bff80` |
| apps/windows/RecApp/GrafWindowsApp.vcxproj | `89d4fb98b1af8ec0ed19ccd4000f45dd55ceca7cdf0dc95459cf378c893a0c55` |
| apps/windows/CMakeLists.txt | `400b57f98d791a6739aa5be0a7140ce9d63f8d114f14cff305a39d8792eb141d` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.h | `ea531e71be71093abfa31f8c023304098a554f1df442946a1c2fef9b0776990c` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `a39ee45d37a7e89837aafb159c3508809e06b2528a66e1cce10bf978815d1625` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `6ac5de213ce896730d87a497d512070dd55a5b496b322c38fdb2c57fa2ed53e6` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp | `148899142a1568f9bc01c47ab63de07f3b5f8854a05faec8ed3b2e2775963fea` |
| apps/windows/RecApp/Storage/ProtectedCustodyMemory.h | `8a0fe8e357935c745f860cc35d30220943410b65300d1c2f9bbb98a4bb5383aa` |

Requirements gate `checklists/review-2026-10-02-custody-reader-gate.md`:
`ef0f98093ad744030f93f5681c8e8741ba7362ef6b54834fac32a61d45ce7b1b`.
Его PASS112/112 — requirements evidence автора gate, не runtime результат reviewer.
Contract `contracts/windows-protected-local-custody.md`:
`630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0`.

## P2 — CopyTo маскирует shared отказ в последнем target callback

Место: `ProtectedCustodyReader.cpp:172–180`; связанные тесты `FilesTests:218–224`.
После успешного `target->Write` код проверяет target HRESULT/количество, но не
повторяет `state_->status()` перед S_OK/S_FALSE. Target callback исполняется вне
global IO lock и может установить cancellation либо вызвать Read на Clone,
который фиксирует shared sticky отказ. На последнем chunk текущий CopyTo затем
возвращает success, хотя отказ уже произошёл; следующий Read обнаружит его.
Это конкретная пропущенная ветка contract §§6–7, а не требование нового dispatcher.

Детерминированный сценарий: свежий reader, CopyTo ровно4 bytes в тестовый target;
его Write принимает4 bytes, устанавливает общий cancellation=true, возвращает
S_OK/sent4. В этом freeze CopyTo возвращает S_OK/read4/written4 вместо отказа.
Для EOF ветки запрос больше length аналогично возвращает S_FALSE.
Вариант с callback Read на Clone доказывает распространение уже записанного
shared failure, даже если cancellation затем сброшен.

Минимальное исправление: проверить shared status после target callback до
успешного возврата/следующего chunk, сохранив фактические read/written counts
и уже переданный target prefix. Ошибку самого target также нельзя скрывать.
Добавить bounded regression для этого callback; прежние проверки EOF,
ACCESSDENIED и scratch allocation не заходят в эту ветку. Reviewer код не менял
и воспроизводящий executable не запускал: сценарий выведен из реальных веток.

## Остальные проверенные свойства

- ReaderState владеет value context, validated index, confined Files и shared
  cancellation; factory не возвращает raw UI/controller/queue reference.
  Checks до open, после open до snapshot validation и после validation явны.
  Account/epoch/package authority дополнительно принадлежит caller job (.h:18–22).
- Pin CAS допускает≤32 живых stream/Clone holders; RAII rollback при factory/
  allocation отказе. Clone держит тот же State и свой cursor. CopyTo удерживает
  source/target COM ownership через callbacks; pin не снимается при возврате factory.
- Read/Seek/Clone сериализованы process-wide cache lock; mutable cursor не
  разделён между Clones. Immutable State+position — ключ exact context/version.
  Last-State release очищает ключ под тем же lock, исключая address reuse.
- Cache — один charged CustodyBytes block≤256KiB, не отдельный cache каждого Clone.
  Replacement сначала SecureZero/actual deallocation, затем новый decode;
  plaintext/native output guards accepted codec сохраняются. CopyTo scratch
  charged≤256KiB и wiped RAII; index/State allocation сохраняют общий allocator.
- Read использует pinned exact DATA version/payload/envelope; tail и ZERO
  вычислены из validated index. При ошибке got0, записанный prefix обнулён,
  cursor не продвинут, ошибка общая и sticky; дальнейшего IO/fallback нет.
  Signed Seek обрабатывает INT64_MIN/overflow, ceiling INT64_MAX accepted gate.
- CopyTo передаёт bounded chunks вне lock, сохраняет source/target errors,
  short target не S_OK; quota failure до Read/Write typed/sticky. Это не rollback
  ранее записанного target prefix. Write/SetSize/unsupported flags запрещены;
  STGC_DEFAULT — read-only no-op/status, не logical commit/ACK.
- Factory сохраняет verified/trustedPrefix и original fault. Files sticky writer
  запрет не мешает чтению validated prefix; никакого повышения package authority.
- Реальные source tests: full/tail/ZERO/EOF/Seek, Clone cursors/cache charge,
  смена текущего index при живом старом snapshot, другой object/role admission,
  process32 и40 concurrent Clone owners с barrier,40 failed factory rollbacks,
  partial native Read failure + shared sticky Clone, cancellation0IO,
  actual Read/CopyTo quota exhaustion и финальный возврат charge к baseline.
- Synthetic MFCreateMFByteStreamOnStream тест проверяет capabilities/length/
  seek/read и release adapter до MFShutdown. Это не AAC/MediaEngine playback
  integration. NDEBUG снят до assert; native fault wrappers остаются TU-local.
- CMake GLOB_RECURSE включает новый reader в common OBJECT; Files/SHA исключены
  для fault-test TU без duplicate symbols. Vcxproj:95 включает product reader.
  Поиск actual callers нашёл только factory и synthetic tests, не UI/producers.

## Ponytail — отдельно

**LeanAlready. Lean already. Ship. net: 0 lines possible.**
COM surface, RAII pin, shared State и один cache/IO lock покрывают реальные
обязательства. Безопасного конкретного сокращения не найдено. P2 выше —
correctness/security finding, не complexity; исправление не автоматизировано.

## Что не доказано и остаётся открытым

Reviewer не выполнял build/tests/VM/install и не проверял runtime mirrors.
Сообщённые main старые35/35 и36/36 относятся к предыдущему test freeze и не
перенесены на этот срез; дальнейшие runtime результаты проверяет main отдельно.
Полный pipeline64MiB/dirty writer/ledger-state/async adoption/account-delete
integration/persistent pin registry/GC roots ещё не принимаются этим слоем.
MF audio decoder/playback, real hash/upload/producers, migration T117,
installed T118, hardware/live capture и release gates открыты; T116 не закрыт.
Изменён только этот новый собственный report через apply_patch.

## Дополнение 2026-10-03 — финальный исправленный freeze

**Approved source only: 0 blockers.** Этот итог заменяет прежний Request Changes
для новых pins; срез 2026-10-02 и первоначальное P2 выше сохранены без изменений.
Root/branch/HEAD прежние; code-reviewer и ponytail-review полностью перечитаны.

| Файл | Финальный SHA-256 |
| --- | --- |
| ProtectedCustodyReader.cpp | `af45e6f5bc2c8450c539c9790adc33ec792493b58df79eaf51292b2f43e545f9` |
| ProtectedCustodyFilesTests.cpp | `07f2b47d51cbb5ef4a2b1ca9f0c02791b56eb896f9ccca60003e3cd0210d8a47` |
| ProtectedCustodyReader.h | `d1dc47e71865bd09a67cde2fe281e9be24a92fae690a9a8b2ea90f6f8b6a91b4` |
| GrafWindowsApp.vcxproj | `89d4fb98b1af8ec0ed19ccd4000f45dd55ceca7cdf0dc95459cf378c893a0c55` |

P2 закрыт: CPP:176 проверяет shared status после target callback до short-write/
успешного возврата; counts уже записаны, target failure не скрыт. CPP:178 также
сохраняет non-S_OK успешный target status. Lock/COM ownership/RAII wipe сохранены.
Tests:158–190 — реальный test-only COM CallbackSink без retained content;
261–285 проверяют last exact4/EOF4of8 cancellation, sticky после сброса сигнала,
reentrant Clone native Read failure и сохранённый target prefix read4/written4.
Tests:290–298 проверяют short2/4, target write-fault2/4, S_FALSE4/4 и реальные
полные CopyTo chunks с maximum256KiB. Новых blocking test holes здесь не найдено.
Files/codec/allocator/CMake/contract/requirements gate pins повторно совпали.
Main сообщил meaningful RED: compile0, старый reader assertion:268,
native0xC0000409/CTest8 за3.03s; reviewer лично этот runtime не запускал.
Финальные native build/tests ещё проверяет main; прежние PASS не перенесены.
Ponytail отдельно: **LeanAlready / Lean already. Ship. net: 0 lines possible.**
Все перечисленные выше whole-T116/consumer/installed/hardware/release gates открыты.
