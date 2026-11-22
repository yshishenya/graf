# T116 — actual RED338 и допуск минимального wipe-исправления

ACTUAL RETIRING-STORAGE RED ACCEPTED; SCOPED PRODUCTION IMPLEMENTATION GO.
Допуск только к ProtectedCustodyMemory.h / ProtectedCustodyCodec.h и existing CodecTests.
Construction blockers C0/H0/M0; это разрешение реализации, НЕ SOURCE/GREEN/runtime приёмка исправления.
Lane high-risk-product прежний; immediate-tail tests записать до source fix, затем RED → GREEN.
Ни T116/ALL, ни Windows/release этим отчётом не закрываются.

## Снимок и сохранённые основания

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` + dirty bytes.
Frozen338 `/Users/yshishenya/Documents/graf-f200-wipe338.mum3VD`; на сверке209 frozen/canonical exact.
source.json `10927910aafdeb641bee40eba9eace1b3101d5a2b82f7f21b781d1422eabf98e`.
От337 изменён только CodecTests: `dcc6c5c579c5fcc80f2ab5e61342d8abffcb19ce64ffd09fd24d7903aab21552`.
Оба production headers unchanged337, normative9 повторно exact; tasks/старые markers не менялись reviewer.
Construction gate `review-2026-10-10-custody-wipe-gate.md` остаётся историческим:
`b91c33e407be84a60dc491113f21d5ba47983fe47eab40130646c979fe5773f5`.
Accepted337 source/runtime report unchanged; wipe не переоткрывает его scoped GO.
Использованы code-reviewer/ponytail-review; прочитаны fixture, harness diff, квитанции и все117 v2 case logs.

## Actual native RED и portable reconciliation

native-v2.json `c4060a14e39b3fa5509b87b9d4b8bf5eaffc6b16ce805e278e123965d6997b68`.
validate-v2.ps1 `a76f1df0778a888fd2585f600db02468914208d5f7ac08cc4c4fae0674c08d0a`.
Terminal/native_completed=true, wipe_red78_verified, configure/build0;78 unique completed cases.
Debug EXE `08a5983988b7aa8f52249967862f87cd017b84562fb76f1c7625b3e9158045a2`;
Debug PDB `4357d62fe1fdfa6bec79082ebee5e781e6384dd1f376af68d9eea0ee643f9e5a`;
Release EXE `a0a70d2dc56d51eb3b564bf7904979f393b29d99b8b78b5d958d0b5487da6079` — receipt evidence main.
Все78 combined logs exact stdout+stderr, каждый RED:exit3/zero0/точный assert:48; controls:exit0/zero1/pass.
SHA sorted78 строк `filename SHA256\n`: `8e13902f60d25fe6c7fcec7485619cf7ce15f83413d19a555ee13df19d7c720a`.

| Исполнение | Случаи | Доказанные RED | Healthy controls |
| --- | --- | --- | --- |
| MSVC Debug | 39 | 29 | 10 |
| MSVC Release | 39 | 29 | 10 |
| Portable libc++, reconciled | 39 | 30 | 9 |

Original native/portable receipts и logs сохранены; исходный harness остановился на неверном char SSO-move ожидании.
V2 меняет expectation SSO-move, имена новых outputs и native prerequisite на terminal первого неудачного harness.
Source/assertion не ослаблены; v2 это полный повтор main, reviewer ничего не запускал из test harness.
portable-v2.json `2995dd0be32375d10a2ffe80686bd44436f8891417477227321af1f432017d63` НЕ PASS:
terminal=true из finally, stage=build, последний wide/sso-move SIGABRT/zero0/bytes12 при expected healthy.
portable-reconciled.json `e1d9787f3fe699d3cbb77c47ec0a5a5ab3d1cf806d5a2eb5a25704869eaa724a` принят:
exact prior/source binding,39 log hashes/signals/assertions, original fields сохранены, только expected classification wide исправлен.
Char SSO-move healthy в обеих средах, MSVC wide healthy; libc++ wide dirty — реальный wipe defect, не skip.
Нового portable rerun для этой классификации не нужно; ни portable GREEN, ни успешный original v2 stage не заявляются.

## R1–R4: принятая конструкция и обязательные условия реализации

R1 — bytes self-range assign исключён, fixture не использует недопустимый vector overlap; новый helper не нужен.
String suffix alias: Base операция читает source до wipe; self copy/move сохраняет значение; исключения не повреждают prefix.
R2 — reviewer разрешённым read-only CLI независимо прочитал installed MSVC14.44.35207/include/xstring:
SHA `9407c290a1d0c6bebc42cf131bd04f09a9892f61b713eecb12827c0f6bbc3045`,161127 bytes.
resize:2386–2393 → append:1537–1546; Count<=res-oldSize использует текущий storage, shrink вызывает _Eos.
Это toolset-specific source proof, НЕ общая C++17 no-allocation гарантия; Debug/Release quota-refusal GREEN ещё обязателен.
R3 — allocator volatile wipes count*sizeof(T) до deallocate/снятия charge; не стирать ещё живые owners/nodes.
Clear/shrink/pop стирают удаляемые live элементы; assign/erase/replace сначала читают возможный alias.
Для tail cleanup допустимо Base expand within retained capacity → volatile wipe live tail → Base shrink.
String destructor охватывает current character storage/SSO/moved-from остатки без allocation; zero-fill не заменяет volatile.
R4 — проверить используемые inherited operator= overloads/chaining; возвращать derived reference где требуется.
Erase iterator восстановить по offset после cleanup; не переносить старый iterator через resize/invalidation.
Не обещать interception произвольного Base&; invalid positions/allocation failure сохраняют прежнюю семантику.

## Immediate-tail oracle и последующая приёмка

Предложенный test-only const volatile unsigned char* oracle принят для заранее initialized allocated storage.
Сразу после mutator проверить removed span до destructor, без resize/записи в test; это не typed data()[outside size].
Перед чтением доказать тот же retained allocation/span: unchanged storage/capacity и отсутствие selected deallocation.
Одна pointer equality недостаточна из-за возможного free/reallocate по тому же адресу; reuse existing delete observation.
SSO span остаётся внутри живого heap owner; никаких freed reads/metadata-zero требований/production hooks.
Основание ограничений: [C++17 lifetime](https://timsong-cpp.github.io/cppwp/n4659/basic.life), [byte access](https://timsong-cpp.github.io/cppwp/n4659/basic.lval).
Добавить immediate checks до fix и сохранить actual RED; их будущие source/runtime evidence здесь НЕ приняты.
GREEN обязан пройти retiring+immediate cases, supported-platform SSO move, quota refusal и прежние proxy/lifetime regressions.
Dependent storage/HTTP/portable regressions и SC-003 cost/full-capacity/double-wipe proof остаются обязательными; caps прежние.
P1 target defect подтверждён RED; исправление ещё не принято. R2 runtime/R3 immediate/R4 source coverage — GREEN obligations.
Existing2headers/oracle достаточны: без нового framework/general container rewrite; net:0 framework lines required.
ALL HTTP/config/request/API/hash/ranges/localtracks/result adoption/scheduler/T116/#7444/global admission/installed/release OPEN.
Единственная запись reviewer — этот новый zero-checkbox report; старые отчёты/norm/tasks/markers/GitHub/source неизменны reviewer.
Только разрешённое VM header-read; VM build/test/jobs/cleanup/state-changing commands/commits не выполнялись reviewer.
