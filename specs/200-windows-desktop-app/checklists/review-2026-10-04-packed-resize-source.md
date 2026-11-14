# Packed SetSize: независимый ограниченный source review

**Дата**: 2026-10-04
**Владелец**: independent reviewer; main не меняет markers.
**Scope**: worker-only Tree append/replace/SetSize и затронутые TreeTests/OwnerTests. Не full T116/adoption.
**Lane**: high-risk-product; code-reviewer, read-only source inspection.
**Текущий вердикт**: ACCEPTED / bounded source PASS — C0/H0/M0; checked9/unchecked0.
**Runtime**: final17634 + targeted64844 + portable17700 приняты для E999/149036/7039/77b9 с атрибуцией main. Только worker-only SetSize prerequisite; не full T116/app/release. Исторические pending/REQUEST_CHANGES sections ниже сохранены и заменены окончательным вердиктом в конце.

## Собственные критерии source review

- [x] PRZ001 Текущий private API/selected proof и режимы append/replace/resize соответствуют requirements gate, no-op guarded, real resize checked generation+1; арифметика bounded до multiplication.
- [x] PRZ002 Direct range policy и depth3 builder сохраняют разрешённый prefix, EMPTY за EOF, ZERO-only extension без missing-data fallback/materialization; shrink/grow не возвращает discarded bytes.
- [x] PRZ003 Independent disk structural diff аутентифицирует exact BASE и новые records, сопоставляет все64 children по разрешённому диапазону, не принимает caller descriptor/root или самосогласованную подмену sibling.
- [x] PRZ004 Общий publisher сохраняет paired HEAD/base/target, два delta readback, proof allocation до HEAD и retained lease/first-error/notCommitted/ambiguous через существующий Guard/Owner.
- [x] PRZ005 Старые immutable proof/Reader/Clone удерживают тот же Owner; новые roots не изменяют старые bytes/length; no-op и cached reads не обходят observed fault/revoked write.
- [x] PRZ006 Fixed arrays/record caps/append reserve и owned allocator/pin/dirty/job admission не создают flat bitmap/backend/lifecycle; sequential bounds не расширены на resize и обратно.
- [x] PRZ007 Весь decoded plaintext очищается перед фактическим освобождением/reallocation, включая grow boundary и throwing MSVC Debug moves. H1 исправлена в149036…: old/destination раздельно под Wipe; actual before-delete observer в77b9c7…. Main64844 terminal0: targeted Release2/Debug3 cases PASS; точный move-site Debug16 не приписывается.
- [x] PRZ008 Статическая структура новых native normal/boundary/fault/forged-sibling тестов соответствует bounded scope; main entrypoints вызывают их, native assertions не отключены Release; старые режимы остаются в общей fault matrix.
- [x] PRZ009 Exact-final source snapshot имеет terminal native Release/Debug и proportional regression receipts после всех изменений; portable scope отделён. Лично сверены canonical4SHA и Round227 terminal append:17634ReleaseOwner+Tree2/2, DebugTree1/1;64844DebugOwner только --resize-wipe3cases;17700portable39/39. Все EXIT0. Старые45405/78482/21950 не принимают H1 fix.

## H1 — короткий plaintext DATA освобождается без wipe при grow

**Priority**: HIGH / P1. **Место**: `apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp:265–270`, непосредственно строка270.

`load(old, first)` возвращает decoded tail в `CustodyBytes`; codec создаёт body
из точного plaintext диапазона (`ProtectedPackedCustodyCodec.cpp:105`).
В ветке grow `body.value->resize(payload, 0)` может увеличить capacity и
освободить прежнюю allocation с расшифрованным prefix. Scoped `WipeBytes`
обращается к самому vector и срабатывает позже, уже на новой allocation.
`CustodyAllocator::deallocate` не выполняет wipe, а `WipeBytes` очищает только
текущие data/size (`ProtectedCustodyPrimitives.cpp:39–45`). Поэтому исходный
decoded prefix не очищается перед освобождением старого буфера.

Конкретный путь уже есть среди normal cases: protected short DATA3 →
`setSize(64GiB)` превращает первый payload в full262144; либо tail3→7 в
`liveResizeBoundaries`. Если payload>capacity, ошибка возникает на успешной
операции, независимо от disk/crypto failure. Выдаваемые bytes могут при этом
быть правильными, поэтому byte equality/owned-memory balance не доказывают wipe.
Это не утверждение об утечке на диск или forensic erase; замечание именно о
владеемой расшифрованной памяти при reallocation в новом grow-пути.

**Минимальное исправление**: не расширять allocation с plaintext prefix через
reallocating resize/reserve. Создать bounded zero-filled destination нужного
размера, скопировать сохранённый prefix, оставить исходный buffer под wipe до
его фактического освобождения; новый buffer также под wipe до append/return.
Сохранить общий builder/publisher, allocator/admission и fail-closed поведение;
не требуется новый framework/allocator/backend. Простой reserve над уже
decoded vector без предварительного сохранения/wipe старой allocation не исправит H1.

**Регрессия**: generated short DATA→larger/full payload должен подтверждать
нулевые bytes старой allocation перед её actual deallocate; проверить отказ
при destination allocation и throwing Debug move, exact prefix/ZERO bytes,
сохранность Owner/lease и baseline budgets. Исполняет main, reviewer VM не запускает.

## Основания статически подтверждённых пунктов

- PRZ001: Tree.h:38–49; Tree.cpp:114–169. `writeReady` раньше input checks;
  index<count проверяется перед index×blockBytes; length≤64GiB, count ceil
  безопасен; same-size проверяет actual heads/guard и возвращает тот же proof,
  включая generation max, без нового candidate.
- PRZ002: Tree.cpp:174–224,259–289. Сначала first>=newCount→EMPTY; ZERO/EMPTY
  становится ZERO только на доступном новом диапазоне, old EMPTY внутри base
  не может быть принятым DATA благодаря established proof и decodeChild.
  Root level3 сохраняет NODE shape при nonempty; shrink0 возвращает EMPTY
  с base extent и без новых records. Exact boundary DATA load/shortening;
  семантика prefix/zero правильна, но очистка grow требует H1.
- PRZ003: Tree.cpp:290–328. Рефы actual сравниваются с прямой range policy
  либо exact internal changed record; все новые bodies читаются через
  envelope SHA/context codec. Новый NODE decodeChild с candidate и prior
  NODE decodeChild с authenticated base; проверяются все siblings. После
  head readback тот же disk diff выполняется второй раз. Изменяемое builder
  body не используется как trusted prior для validator.
- PRZ004: Tree.cpp:127–160,329–365; unchanged Guard/physical publisher прочитан
  адресно в Files.cpp:706–789,1058–1095. Native publisher ловит bad_alloc и
  возвращает ambiguous после actual HEAD attempt; результат сохраняет base
  lease. Exact paired cells/selected base/target проверяются перед ACK.
- PRZ005: immutable heads_/owner_/pin_; no physical truncate/delete/reopen в
  Tree commit; old proof читает свои refs. New tests удерживают старый IStream
  Clone, сравнивают прежние bytes/Stat после двух новых commits; revokeWrites
  запрещает no-op commit, но не здоровый old-root read.
- PRZ006: depth<=3, spans1/64/4096/262144, changed[8], cap4 sequential/cap8
  resize, максимум один DATA на target/boundary и до7 NODE. Guard reserve и
  subtraction-before-bound append limit; только charged CustodyBytes/Tree
  allocations, один Guard/job/mutex/Owner. Physical reserve может быть
  conservative appendLimit+15; фактический append проверяется≤appendLimit.
  Размеры не зависят от count; большие ZERO subtree не разворачиваются.
- PRZ008: latest TreeTests:489–620, main:1450 onward; OwnerTests:241–420,
  main:928–934. Actual Files/Tree TU interposition, не альтернативный backend.
  append/full,append3,tail,interior,shrink,grow,empty используют measured
  read/write/flush ordinals; shared first fault/lease/Owner denial assertions.
  Valid NODE sibling подменяется до REAL seal/checksum/DPAPI/SHA и реально
  decodeChild принимается до structural-diff отказа; shrink/grow включены.
  По completedCounts Read assertions выполняются отдельно и не загрязняют
  ordinals. Metadata/allocation/throw cuts и budget pressure остаются.

## Проверенный source snapshot — SHA-256

| Файл | SHA-256 |
| --- | --- |
| Tree.h | `e99925d665484f864fe63dc305bb3f3ffaff2c025515a4a7994dd10d67f53597` |
| Tree.cpp | `5e860f9a9a0fff3c073050c8adfc3502e6c795d4635eefa6aa3718d974b4c658` |
| TreeTests.cpp | `7039fc7d5cebbd545370617b7f7742448373145b3cf12a81bb586e245525cb30` |
| OwnerTests.cpp | `edd3a0309f073dd77df27e59f8c39f9fd1eb376432ab24da0f1973b518dd763b` |

TreeTests менялся во время первых чтений: промежуточный197337… не является
конечным снимком. Latest7039fc… включает дополнительные max-generation
no-op/real-resize cases и boundary/admission cases, лично перечитанные после
изменения. Три остальных source SHA остаются прежними.

Requirements gate `7a62f7d5345aaa2a8a2d8681f802b851d6d2a7058ef24e65d27dfcbdf66e6747`
14/0 остаётся неизменным, он не является source acceptance.
Packed contract374d8daa…, plan29c396…, quickstart3045f7… сверены с предыдущим
bounded review; constitution d28f8312… и required guidance свежими SHA
подтвердили лично прочитанный неизменённый контекст.

## Execution evidence — только атрибуция main, не принятие

Main сообщил RED50868 build0/test EXIT3 на actual no-op assert и последующий
build55757 C4244, исправленный typed uint8_t без ослабления flags. Reviewer
не запускал и не наблюдал эти процессы. Session78482 ещё выполняется и была
запущена с предыдущим TreeTests snapshot; даже её будущий PASS нельзя назвать
final current TreeTests PASS. Final native packet/Release/Debug/regressions
не получены. PRZ009 unchecked независимо от H1 и текущих тестовых исходников.

## Границы и дальнейший шаг

Сейчас требуется устранить H1, сообщить новый exact source freeze и передать
actual terminal evidence. Старые native receipts нельзя молча перенести на
новый product/test SHA. После этого reviewer адресно перечитает delta и
execution packet; текущий report не разрешает final source acceptance.
Новых нормативных задач/архитектуры не требуется; T116 остаётся open.

Полный T116 writer/partial WriteAt/IStream/adoption, metadata/parser/consumer
integration, migration T117, T120 capture/UI, installed/audio/hardware/cadence
и release не входят. Не изменены код/tests/нормы/tasks/Git/GitHub/VM или старые
checklists. Единственный записанный файл — этот новый reviewer-owned report.
Code-reviewer использован с прямым чтением exact canonical файлов вместо
запрещённых Git diff/preflight/VM commands. Scoped final verdict pending.

## Terminal packet part1 — main, после первоначальной записи report

Main сообщил session78482 terminal EXIT0: Release OwnerTestsedd3… с
Tree.cpp5e86… PASS195.76s, включая новые shrink/grow/empty native cuts,
forged sibling и charged refusal. Tree PASS14.63s в этой session относится
к предыдущему7312… test snapshot, не к current7039….
Portable21950 current fullbuild/rebuild PASS39/39,24.58s,EXIT0; native fixtures
не принимаются portable lane. Main сообщил canonical/mirror4cmp EXIT0.
Final TreeRelease+Debug current4files выполняются последовательно, terminal
receipt ещё не получен. Native DebugOwner не запускался/не заявлен; прежний
native full41 не был повторён. Никакого подразумеваемого Debug/whole-suite PASS.
Reviewer эти проверки не исполнял; сообщение записано с атрибуцией main.
PRZ007/H1 и PRZ009 остаются unchecked; verdict REQUEST_CHANGES,7/2,C0/H1/M0.

## Terminal packet part2 — окончательное выполнение, H1 не исправлена

Main сообщил session45405 terminal EXIT0 после guest actual4SHA check перед
build: E999/5E86/7039/EDD3 совпадают с текущим reviewer snapshot. ReleaseTree
current7039 PASS1/1,20.88s (CTest20.94), RELEASE_TREE_EXIT0; затем serial
DebugTree PASS1/1,27.86s (CTest27.96), DEBUG_TREE_EXIT0. NativeDebugOwner
не выполнялся. ReleaseOwner78482currentedd3+5e86 PASS195.76s и portable21950
39/39PASS24.58s/EXIT0 относятся к этому неизменённому снимку. Main governance
19726 PASS/EXIT0, YAML parse/diffcheck PASS; reviewer этих команд не запускал.
Прежний Tree7312 PASS остаётся историческим и не подменяет final7039.

Reviewer лично повторил4canonical SHA и адресно перечитал Tree.cpp:259–273:
H1 всё ещё присутствует в неизменённом5e86…, `resize(payload,0)` на строке270.
Тестовые bytes/budget/native cuts подтверждены packet, но очистка старой
allocation перед reallocation ими не доказана. PRZ009 отмечен по достаточному
bounded terminal packet; никаких новых unneeded fullDebugOwner/full41/app/VM
gates не добавлено. PRZ007 единственный открытый пункт, C0/H1/M0,8/1.

**Итог: REQUEST_CHANGES, source acceptance НЕ выдана.** Нужно точечное
исправление H1 и подтверждение нового exact snapshot. Initial pending/part1
разделы выше сохранены как история, а не текущий runtime status.

## H1 delta — личное static readback нового снимка

Tree.cpp:265–272 теперь создаёт отдельный zero-filled `resizedBody(payload,0)`;
original decoded body не resize/reserve и остаётся под своим Wipe до scope exit.
Destination сразу получает отдельный Wipe. `copy_n(min(payload,oldSize))`
сохраняет exact prefix; suffix изначально ZERO. Shrink тоже копирует только
разрешённый prefix. Если allocation destination бросает bad_alloc, original
Wipe уже активен; если позже seal/append/throw отказывает, обе completed
allocations очищаются до deallocate. Новый buffer не перемещается между
результатами load; перед appendRecord используется const reference.
Общий Guard/publisher/limits и Owner не изменены. **H1 статически снята.**

OwnerTests:34–59,207–222,275–305,966/1002: наблюдается указатель actual DATA
body из REAL codec openReferenced. Global delete (sized/unsized) проверяет
all bytes ZERO перед std::free, не после освобождения и не копию результата.
Observer активен лишь для выбранного pointer до первого actual free. Все
остальные allocations проходят через malloc/free; producer/custody код
не получил новых allocator hooks. Test-only reuse CodecTests pattern.
Success DATA3→262144 проверяет prefix/ZERO; destination262144 allocation
refusal требует allocationFailed/notCommitted/no snapshot/retained lease
и repeated sticky отказ. _DEBUG после destination allocation ставит отказ
на следующую16B allocation. Это НЕ evidence точного move-site: следующий
proxy может относиться к последующему seal. Такой предел явно сохранён;
existing TreeTests retained move/exact fit случаи остаются отдельно.
Новый test вызывается и --resize-wipe, и обычным Owner main перед baseline
memory assertion. Изменён только test executable, не global product allocator.

Main сообщил RED71170 nativeRelease build0/--resize-wipe EXIT3 на actual
all_of BEFORE delete старой allocation против прежнего product5e86….
Reviewer этот запуск не выполнял. Postfix targeted/full terminal receipts
ещё не получены; статическая корректность fix не превращает ожидаемые runs
в PASS. Новых C/H/M в прочитанной delta нет, PRZ009 pending.

Новый personally hashed source snapshot:

| Файл | SHA-256 |
| --- | --- |
| Tree.h, unchanged | `e99925d665484f864fe63dc305bb3f3ffaff2c025515a4a7994dd10d67f53597` |
| Tree.cpp, H1 fix | `1490364c1c68fb34c70acd598b241318520883a3f8d8efdbdd95dac838f6f8f8` |
| TreeTests, unchanged | `7039fc7d5cebbd545370617b7f7742448373145b3cf12a81bb586e245525cb30` |
| OwnerTests, wipe regression | `0a05aea1821fde7b5c36ebd5e616d5bced1679077567d1ad6a3ea023963e2391` |

Requirements gate7a62f7… и три normative SHA374d8daa/29c396/3045f7 сверены
неизменными. Ранее описанные H1/REQUEST_CHANGES/old terminal sections сохранены
как история. Current static C0/H0/M0,8/1; source acceptance PENDING_RUNTIME.
Для нового product149036… старые native/portable receipts не принимаются.

### Последний test-only delta во время readback

OwnerTests SHA теперь `cb1804bf64e277db7c67753bd756eef7811533159324715c5a06e2211de3fcd6`.
Лично перечитаны observer/new/delete/codec capture/resizePlainWipe/main
entrypoints после изменения: добавлена metadata-only fprintf case/freed/
watched/pending/state/error перед assertion, без plaintext/private data.
Observer и success/refusal assertions сохранены. Intermediate0a05… выше
сохранён как снимок первого чтения, не final runtime identity. Product149036…,
Tree.hE999… и TreeTests7039… неизменны. Current static C0/H0/M0,8/1;
PRZ009 остаётся pending на latest149036/cb1804 snapshot.

### Финальный test matcher и H1 targeted terminal64844

OwnerTests latest SHA `77b9c7d0c65cbc1ed0dae1e0961ae58d7567c0121ab76c427a26e8c6c381d474`
лично сверён; operator new:47–58 и resizePlainWipe:278–310 перечитаны.
При pending logical destination262144 отказ теперь учитывает actual operator
new размер[262144,262208] под watchedPlain, включая MSVC alignment overhead;
Debug16 injection остаётся exact. Разница не меняет product allocator/caps.
В этой цепочке после capture old DATA3 первая allocation в указанном диапазоне
относится к destination; codec/header buffers имеют другой размер. Это scoped
test injection, не production size acceptance. Все observer/refusal assertions
остались, metadata fprintf не содержит payload.

Main сообщил64844 terminal EXIT0 на product149036…/OwnerTests77b9c7…:
Release --resize-wipe2cases PASS, Debug3cases PASS; success и allocation
refusals наблюдают actual old DATA allocation wiped перед delete, freed1,
pending0; refusal error10/allocationFailed. Debug16 отказ происходит после
destination allocation, но не доказывает конкретный move-site. RED71170
против old product5e86… остаётся доказательством чувствительности observer.
11724 failure относился к старому exact262144 test matcher, не новым product
bytes; история не переписана. Partial portable94492/old snapshot не принимается.

H1 закрыта source+targeted evidence; C0/H0/M0,8/1. Main serial final native
ReleaseOwner+Tree/DebugTree и current portable39 ещё RUNNING; PRZ009 не отмечен
и final acceptance не выдана. Snapshot current: Tree.hE999…/Tree.cpp149036…/
TreeTests7039…/OwnerTests77b9c7…. Reviewer не запускал VM/тесты и не расширяет
bounded acceptance новыми gates.

## Окончательное независимое readback / PRZ009 — 2026-10-04

Reviewer лично перечитал source report целиком, current canonical4SHA,
неизменённый requirements gate14/0 и modified normative3SHA. Адресно прочитан
main validation `validation-2026-10-02.md:6935–6975`, в частности Round227
terminal packet:6956–6975. Pending snapshots в предыдущих append sections
не считаются текущим статусом; старые5e86/edd3 runs не перенесены на H1 fix.

### Final exact source identity

| Файл | SHA-256 |
| --- | --- |
| Tree.h | `e99925d665484f864fe63dc305bb3f3ffaff2c025515a4a7994dd10d67f53597` |
| Tree.cpp | `1490364c1c68fb34c70acd598b241318520883a3f8d8efdbdd95dac838f6f8f8` |
| TreeTests.cpp | `7039fc7d5cebbd545370617b7f7742448373145b3cf12a81bb586e245525cb30` |
| OwnerTests.cpp | `77b9c7d0c65cbc1ed0dae1e0961ae58d7567c0121ab76c427a26e8c6c381d474` |

Guest4 identity до final build подтверждена main; current canonical4 identity
после terminal повторно проверена reviewer и совпала. Canonical/mirror delta2
сравнения main EXIT0; остальные2 immutable после прежней сверки. Git HEAD
не перепроверялся/не менялся; feature snapshot b1eb… не является SHA dirty code.

### Достаточный terminal packet, main execution / reviewer readback

| Receipt | Подтверждённый объём | Результат |
| --- | --- | --- |
| 17634 Release | target build0, full Owner + Tree для final4source | 2/2 PASS206.32s; Owner186.77s, Tree19.41s; FINAL_RELEASE_EXIT0; commandEXIT0 |
| 17634 Debug | serial Tree build0 + full Tree target | 1/1 PASS24.08s, CTest24.16s; FINAL_DEBUG_TREE_EXIT0 |
| 64844 H1 targeted | --resize-wipe Release2/Debug3cases на149036/77b9 | PASS/EXIT0; actual old allocation wiped before delete на success/destination failure/Debug16 после destination |
| 17700 portable | final source rebuild0, без Win32 fixtures | 39/39PASS11.34s/EXIT0 |
| 86109 governance | current H1 docs, YAML и diffcheck | PASS/EXIT0 |

Owner full Release включает прежние и новые mode cuts/structural sibling
forgery/pressure/retained Owner плюс интегрированный wipe regression; Tree
Release/Debug включает current boundary/pinned/cold/admission/maxgen/retained
move cases. DebugOwner FULL MATRIX не выполнялась: только64844 targeted3cases.
Final native full41/all-app rebuild/MSIX/install не заявлены, не подменены
старым выполнением и не добавлены как новые gates этого bounded acceptance.
Длительности не являются cadence/5s Stop/full hardware performance proof.
Reviewer сам не запускал VM/tests; execution attribution main сохранена.

H1 закрыта по source и чувствительной actual-allocation RED→GREEN регрессии:
RED71170/old5e86 EXIT3 перед actual delete, новый149036/77b9 targeted PASS.
Matcher diagnostic11724 и intermediate94492 не используются как final PASS.
Debug16 evidence не приписывается точному move-site, ранее установленные
retained-move tests отдельно присутствуют в принятом DebugTree прогоне.

**Окончательный вердикт: ACCEPTED,9 checked / 0 unchecked,C0/H0/M0.**
PRZ009 отмечен только после actual terminal receipt и exact identity readback;
новых unneeded gates/задач/требований не введено. Requirements gate7a62f7…
14/0 остаётся отдельным immutable proof требований, не реализацией.

Принят только bounded worker Tree SetSize/shrink/ZERO + общий append/replace
transition/publisher regression на final source выше. Partial WriteAt/staged
writer/IStream adapter, package.v2/v5 parser/consumer/MF/hash/upload integration,
T117 migration, T120 pause, real audio/E2E/physical x64, installed app/design,
accessibility/install/update/signing/release и полная Windows цель НЕ приняты.
T116/T117/T118/T120 и соответствующие дальнейшие gates остаются open.
Не изменены source/tests/нормы/tasks/old reports/Git/GitHub/VM. Reviewer
редактировал только этот source report; конечные markers/счётчики перечитаны.
