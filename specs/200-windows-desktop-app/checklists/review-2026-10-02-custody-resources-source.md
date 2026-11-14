# Независимый source review: custody allocation

Дата среза: 2026-10-02 UTC; локальный контекст Europe/Istanbul — 3 октября.
**Approved source only: 0 blocking findings.** Прежний test portability blocker
закрыт в финальном freeze; native/host результаты для него ещё не утверждены.
Решение привязано к шести рабочим SHA-256 ниже, не committed/installed evidence.
Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Branch: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.

## Объём и pins

Полностью прочитаны code-reviewer и ponytail-review SKILL. Correctness/security
рассмотрены первыми; сложность отдельно. Risk lane — high-risk-product.
Baseline physical/snapshot/wire review не повторялся; проверены allocation
sites, ownership, новые catches/mapping и regressions этого ограниченного этапа.
Requirements gate PASS112/112 — отдельное заключение requirements reviewer,
не новая поэлементная проверка markers и не source/runtime PASS этим reviewer.

| Файл от root | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Storage/ProtectedCustodyMemory.h` | `8a0fe8e357935c745f860cc35d30220943410b65300d1c2f9bbb98a4bb5383aa` |
| `apps/windows/RecApp/Storage/ProtectedCustodyCodec.h` | `6ac5de213ce896730d87a497d512070dd55a5b496b322c38fdb2c57fa2ed53e6` |
| `apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp` | `148899142a1568f9bc01c47ab63de07f3b5f8854a05faec8ed3b2e2775963fea` |
| `apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp` | `a39ee45d37a7e89837aafb159c3508809e06b2528a66e1cce10bf978815d1625` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp` | `6209b8735fb4fa4d31871d52451832732ec60cfbee7e3041d886f650c710e948` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp` | `4919f3a68586779a70ceaebfc1e6b3b07e5ce0e571e87833d7e31c3ea091709d` |

Прочитанный `review-2026-10-02-custody-resources-gate.md` совпал с pin:
`172904d20b14785f8572456a203cc560ab1c38b0583e3954ee62d99aaa4ee2d9`.
Accepted contract неизменен:
`630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0`.

## Закрытое замечание P1: MSVC fault-size portability

В первоначальном freeze `ProtectedCustodyCodecTests.cpp:23–25,78–81` test arms
`failAllocationBytes=4096`, вызывал `CustodyBytes::reserve(4096)` и требовал,
чтобы underlying operator-new fault был consumed и charge вернулся в0.
Но Microsoft STL для x86/x64 allocation≥4096 использует manual vector
alignment: `std::allocator::allocate` передаёт запрос через `_Allocate`,
который добавляет `_Non_user_size` до вызова scalar operator new. Поэтому
ordinary x64 Release запрос —4135 bytes, Debug —4143, не4096.

CAS по точному размеру не срабатывал; allocation succeeds, `rejected=false`,
assert81 падает. Владелец подтвердил native failure на старом test. Это не
rollback-дефект production allocator: тест не достигал его catch. Прежний
host PASS такую переносимость не подтверждал.

Исправление финального freeze проверено: test80–84 использует fail1024 и
reserve1024 ниже threshold. Настоящий CustodyAllocator резервирует1024 до
std allocator, wrapper throws bad_alloc, catch43 откатывает charge; assert83
требует consumed fault/used0, а повторный reserve84 проверяет дальнейшую
работу. Quota, production allocator и assert не ослаблены. Memory.h7 добавил
direct type_traits для std::true_type; другой логики в этом изменении нет.
Все шесть финальных pins перепроверены. Native rerun остаётся у main.

Первичный источник: [Microsoft STL xmemory](https://github.com/microsoft/STL/blob/main/stl/inc/xmemory),
`allocator::allocate`, `_Allocate`, `_Big_allocation_threshold`,
`_Allocate_manually_vector_aligned` и `_Non_user_size`. Проверены текущие
официальные исходники; installed SDK/VM headers reviewer не инспектировал.

## Что проверено в production

- Memory.h18/23: один64MiB counter, inline static atomic не является template
  member, поэтому все CustodyAllocator<T> instances/types/TU одной программы
  используют один charge. usedBytes20 только наблюдает, не принимает admission.
- Memory.h36–41: count≤limit/sizeof(T) проверяется до multiplication;
  limit−bytes и CAS проверяют суммарную reservation до underlying allocation.
  Relaxed достаточно для атомарного numeric admission; ownership передаётся
  контейнером, не публикацией данных через counter. Oversubscription не найден.
- Memory.h42–47: std allocator вызывается после reservation, любой throw
  откатывает ровно её bytes; успешный charge снимается только при deallocate.
  Для корректных allocator callers count совпадает с прежним allocation,
  multiplication в release bounded; underflow пути в контейнерах не найден.
- Codec.h13/32 реально меняет CustodyBytes и index.entries на общий allocator.
  Codec entropy/native-output copy/plain/envelope/payload-result и decoded
  entries используют эти типы; Files disk-read bytes, candidates и возвращаемые
  results также их сохраняют. Это не unused standalone counter.
- Capacity, а не size, задаётся count allocation. clear не освобождает charge;
  reallocation сначала резервирует весь new buffer при ещё живом old buffer.
  Copies отдельно charged; equal/stateless allocator и is_always_equal
  позволяют move/swap передавать storage без двойного charge. Destination old
  storage освобождается std::vector, result/optional удерживает charge до
  уничтожения allocation, не только до выхода функции. ABI aliases требуют
  согласованной сборки всех TU; partial binary mixing не одобряется.
- Codec.cpp194–195/213–214/233–234/266–267 ловит bad_alloc всех четырёх API и
  возвращает allocationFailed без value. Budget exhaustion и underlying
  allocator failure используют одну разрешённую typed категорию.
- NativeOutput123–128 очищает native bytes даже при отказе app-owned copy135.
  Plain WipeBytes188/203/220/243 остаётся активным при exception unwind и
  отказе entries/result allocation; успешный payload result не стирается до
  передачи caller. Files WipePlain/error guards не ослаблены.
- Files.cpp29 передаёт codec allocationFailed без flattening. Snapshot459–461
  не допускает такую ошибку к fallback и ставит failed через reject; outer
  bad_alloc также sticky. Prevalidation отказ write/publish не выполняет IO
  и не объявляется commit; прежние post-publication ambiguous/retention guards
  сохранены. Глобальный allocator не исправляет context/snapshot authority.

## Тестовые доказательства и ограничения

CodecTests39–97 проверяет capacity across bytes/entries, copy/move/optional/
clear/swap,40+48MiB old+new refusal с сохранением old data, exact64MiB,
overflow, deallocation и12-thread admission с четырьмя живыми16MiB buffers.
Rollback test78–84 исправлен и перепроверен по исходникам. NDEBUG снимается.
Replacement scalar new/delete/sized-delete локален этому executable, malloc/
free пары не смешаны; fault теперь не зависит от big-allocation alignment.

CodecTests98–109 удерживает реальные payload/cipher/index/results и заполняет
остаток бюджета; четыре codec API должны вернуть allocationFailed с полным
charge. Это cross-TU counter проверка, не только allocation в test TU.
FilesTests155–174 аналогично заполняет остаток: readBlock/readIndex/writeBlock/
publish/snapshot отказывают с0reads/0writes; после release snapshot-induced
failed запрещает publish и повторный snapshot. Native/hash fault guards
прежнего resolver остаются подключены. Эти assertions прочитаны, не запускались.

## Ponytail и остающиеся gates

**LeanAlready. Lean already. Ship. net: 0 lines possible.** Безопасного точного
сокращения не найдено;53-line stateless allocator использует std::allocator,
без нового owner registry или speculative manager. Исправление fault seam —
correctness/portability, не отдельное замечание о сложности.

Это ещё не whole-pipeline64MiB: other JSON/string/hash/upload/CopyTo/job owned
buffers, cache2MiB, dirty4blocks/1MiB, pins32/process registry, async ownership/
UI/native IO, MF internal peaks, migration/GC и ordered logical ACK открыты.
Whole T116/T117/T118, hardware/audio/clock/calendar/installed/release не приняты.
Владелец сообщил host35/35 PASS старого freeze, first native Files PASS и
Codec failure старого fault на line81. Final host/native/build reruns pending;
эти прежние результаты не перенесены на финальный allocation freeze.
Installed MSVC header read-only confirmation reviewer не делал, публичный
STL source не подменяет такую локальную проверку. Round207 также не PASS этапа.
Reviewer не запускал build/VM/install и не менял код/нормы/markers/старые отчёты/
tasks/GitHub/commits. Единственная запись — этот отчёт через apply_patch.
