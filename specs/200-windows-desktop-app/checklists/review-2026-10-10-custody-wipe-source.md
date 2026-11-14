# T116 — независимое SOURCE review wipe341

SCOPED SOURCE GO для минимального wipe-среза; runtime341 НЕ принят этим отчётом.
Текущих блокирующих SOURCE findings P0/P1/P2: 0; high-risk-product lane сохранён.
Проверены frozen341, diff339→340→341, actual callers, RED339 receipts/logs и static harness.
Использованы code-reviewer и ponytail-review; новые production abstractions не требуются.

## Точный источник и границы

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch `codex/200-windows-followup`.
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` + dirty bytes; injected0309 не использован.
Frozen `/Users/yshishenya/Documents/graf-f200-wipe341.WiXPp2`.
source.json SHA256 `9aa96c5c9a1acfba681d06d5a6ea7543c95d90677ca1a8a93984653134ec88e6`.
Все209 frozen файлов independently rehashed; canonical209 exact на проверке.
От339 изменены только ProtectedCustodyMemory.h / ProtectedCustodyCodec.h / existing CodecTests.
Memory SHA256 `c365ae6ff2fe15565f3db991cc589e05bb0f22dfad8de65911482d39b3a3f2b1`.
Codec SHA256 `3d7f63903a7a0daa9432c55fa90fe90735a7f42a06ba3bdb61e2276a7dcc3406`.
Tests SHA256 `5a02a0382a5a4ca895f74ba1a6995ffcf021c9d7a548a88dac833afb12538686`.
От340 только explicit Bytes assign/SFINAE и завершающий budget baseline assert.
Normative9 exact относительно таблицы accepted owned-data gate; tasks120/93done/27open неизменны.
До этого отчёта checklists182md/29marked/420checked/0unchecked; старые markers не тронуты.

## Основание RED и отказ superseded340

339 source.json `497e6b6e0dae41229d7fe685a702e1bf177385c421456ab4f55370c27b402589` exact209.
native339.json `056d1847996baf966226b94f5d402d934cf02b8223e9f0ad2697739d794cb21a`:
terminal/native_completed=true, tail_red78_verified, configure/build0; Debug/Release по29RED/10controls.
Прочитаны78 logs, exact stdout+stderr; RED exit3/zero0/assert, controls exit0/WIPE_CASE=pass.
portable-fixed.json `d3aae030cdc828d3ad74d3fbfe570e0ae7de824b6e9b1d6b47e2cf103008a66b`:
terminal=true, wipe_red39_verified, configure/build0;30RED SIGABRT/9controls0; все39 log hashes exact.
Immediate zero0 виден в52 native и27 portable случаях; growth использует retiring oracle.
SHA sorted117 строк filename+space+SHA256+LF: `47281b47da5eb303e529d55a81221753936bc14d603c6d177896a6746a94575e`.
Original portable339 configure_exit1/cases0 сохранён; не считается успешным исполнением тестов.
Native340 terminal/build_exit1/tests0: C2220/C4244 в variadic Bytes assign; runtime168 не состоялся.
341 explicit assign(size_t,uint8_t) конвертирует literal в месте вызова; !integral iterator overload убирает ambiguity.
Это SOURCE устранение причины C4244, не подтверждение успешной native341 сборки.
Portable340 terminal stage portable47_plus_wipe78_verified относится только к superseded340, не к341/Windows.

## R1–R4: correctness, lifetime и actual caller audit

R1: string assign/replace сначала выполняют Base operation, затем wipe tail: own suffix прочитан до стирания.
Self copy/move защищены identity check; bytes self-range assign по-прежнему недопустим и не добавлен.
Bytes count/iterator/init-list overloads покрывают Writer:149/157/163 и Metadata:1609 без нового overlap helper.
R2: string full-capacity wipe вызывает Base resize(capacity), volatile wipe включая terminator, затем restore size.
No-allocation утверждение ограничено поддержанным STL/toolset; не универсальная гарантия C++17.
Installed MSVC14.44.35207 xstring proof сохранён в accepted production gate; runtime full-quota341 ещё обязателен.
Default/move constructors остаются potentially throwing; новые noexcept на allocating construction не введены.
R3: allocator стирает count*sizeof(T) volatile unsigned char до std deallocate и снятия charge.
Bounded allocate исключает overflow для соответствующего deallocate; caps64MiB/32pins/4jobs не изменены.
Это распространяется на rebound map/set/proxy/control-block storage и owners, не только char/bytes.
Проверенные manual deleters Tree:27–28, Files:1353/1404 вызывают destructor до deallocate;
Reader/Stream/Writer operator delete и allocate_shared используют тот же lifetime порядок освобождения.
Живые members/owners не стираются allocator; отдельная память их полей освобождается обычными destructors.
Bytes clear/shrink/pop стирают удаляемые live элементы; destructor теперь опирается на full-allocation deallocate.
Assign/erase/replace cleanup временно расширяет размер внутри retained capacity, стирает live tail и сужает обратно.
Никакой production записи за size через data()[index] нет; reallocated retiring storage покрыт allocator.
String destructor охватывает heap capacity+terminator и SSO; embedded NUL не ограничивает span.
Move ctor swap и guarded move assignment отдельно wipe moved-from storage, не storage нового владельца.
R4: erase сохраняет числовой offset до Base erase и заново вычисляет begin()+offset после cleanup resize.
Не возвращается исходный invalidated iterator; budget fixture содержит erase suffix→новый end для обоих configurations.
HTTP:397/420/466 shrink, :503/504 clear, :604/:1161 assign идут через concrete/templated CustodyString.
JsonReader:64 использует String += char; HTTP markers:38–39 и headers:346–348 используют append.
Account/sync/result/truth aggregate copy/move используют derived assignment; ordinary std aliases unchanged.
Protected Reader:25–26 clear/shrink_to_fit и Bytes swap-release в Tree/Files сохраняют lifetime/charge.
Actual caller Base& shrink/chained cleanup bypass не найден; произвольный Base& interception НЕ обещается.
Invalid-position erase бросает до wipe; failed reserve сохраняет value/storage; реальные iterator sources не throwing input adapters.
Не заявляется новая strong guarantee для всех произвольных throwing iterator/custom conversion overloads.

## Тестовый источник, минимальность и незакрытые ворота

Immediate oracle читает volatile raw bytes до destructor: same pointer/capacity и !wipeObserved обязательны.
SSO span внутри live heap owner; заранее initialized spans; no freed reads/test resize/production hook.
Budget CLI покрывает shrinking/aliases/initializer/chaining/refusal/invalid erase/destructor под полной квотой.
341 final baseline assert закрывает continue в destroy cut; прежние proxy/move/allocator tests сохранены.
Static native harness341 передаёт @(('--memory-'+testMode),type,cut); ожидает156matrix+2budget+10dependent=168.
Ponytail: existing2headers + existing test oracle достаточны, framework/dependencies/second pipeline:0.
append/+= forwarding сохраняют derived return; текущие callers результат не chain: возможный optional trim −6lines, не blocker.
Двойной wipe с existing WipeBytes не скрыт; SC-003 cost/полный acceptance этим SOURCE review не доказаны.
GREEN341 logs/receipts, actual binary/source postflight и cleanup acceptance — отдельный runtime review после terminal.
ALL config/request/API/hash/ranges/localtracks/result adoption/scheduler/T116/#7444/global admission остаются OPEN.
Installed/hardware/SC-003/full Windows/release OPEN; accepted337 узкий slice не переоткрыт и не расширен.
Reviewer создал только этот zero-checkbox report; source/norm/tasks/старые reports/GitHub/VM/jobs/commits не менял.
