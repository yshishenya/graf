# T116 — construction gate стирания owned memory

SCOPED GO к подготовке корректного RED; production GO пока НЕ ВЫДАН.
Область: два existing headers и existing ProtectedCustodyCodecTests pre-free oracle.
Это продолжение T116, high-risk-product; новых task IDs/норм/HTTP pipeline не требуется.
Фактический новый fixture/manifest/RED ещё не представлены и здесь не приняты.

## Основание и снимок

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` + dirty bytes.
На проверке209 source hashes exact frozen337; normative9 совпадают с действующим construction gate.
ProtectedCustodyMemory.h SHA `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad`.
ProtectedCustodyCodec.h SHA `7954822ec768a4d7146fb94e34273e92ea5f6d4cbecb2e9989b761c80fdf851c`.
ProtectedCustodyCodecTests.cpp SHA `2b3585f39e6b0522c26334c07665c1432b3322446fef2ee37aa433432a3650e5`.
Plan:2075–2089: body lifetime/last-release wipe/charged capacity; quickstart:704–705 запрещает unwiped retiring serializer buffer.
Existing implementation: allocator deallocate:102 без wipe; Bytes/String destruction стирает лишь current size.
Existing oracle: tests:39–46 проверяет выбранные bytes до free; tests:95–120 покрывает destruction/move overwrite,
не growth/shrink/clear/SSO. Использованы code-reviewer и ponytail-review; новые процессы не запускались.

## Принятая минимальная основа

Allocator стирает ровно count*sizeof(T) через volatile unsigned char до std deallocate и снятия charge;
только retiring allocation после завершения object lifetime, не живые nodes/control blocks/borrowed body.
Это закрывает heap reallocation/free; String/Bytes mutators отдельно закрывают хвост и SSO.
Clear/shrink/pop: стирать удаляемые live элементы до уменьшения size; сохранять prefix/terminator/charge.
Assign/erase/replace с возможным alias: сначала корректная исходная операция, затем только прежний удалённый tail.
Временное расширение до oldSize допустимо как доступ через standard API, если storage для него удержан;
после расширения нужен volatile wipe хвоста, затем Base shrink. Одного zero-fill через resize недостаточно для secure-wipe proof.
Destructor String может обработать current capacity через live расширение и volatile wipe, но no-allocation требует proof ниже.
Не вводить новый secure container/framework/production hook; не переписывать CustodyVector для произвольных T.

## Обязательные уточнения до production

P1/R1 — byte self-range нельзя молча передавать Base::assign(first,last): C++17 запрещает iterators into destination.
Если bytes alias входит в обещание, нужен конкретный byte-specific безопасный overlapping copy/shrink путь;
иначе такой тест не является корректным RED. String alias и self-copy/move — отдельные случаи, не общее правило vector.
Основание: [C++17 sequence requirements](https://timsong-cpp.github.io/cppwp/n4659/sequence.reqmts), assign preconditions.
P1/R2 — resize≤capacity не объявлять универсальной C++17 no-allocation гарантией для basic_string.
Общие non-const операции могут инвалидировать views/iterators; cleanup после успешного Base действия не должен бросать,
особенно destructor/clear/noexcept move. Нужны source inspection используемой STL и allocation-refusal Debug/Release proof.
Current upstream MSVC resize→append имеет capacity fast path, но upstream main не идентифицирует установленный toolset.
Основание: [C++17 string capacity](https://timsong-cpp.github.io/cppwp/n4659/string.capacity),
[string requirements](https://timsong-cpp.github.io/cppwp/n4659/string.require), [MSVC xstring](https://github.com/microsoft/STL/blob/main/stl/inc/xstring).
P2/R3 — volatile wipe должен реально выполняться пока очищаемый tail live; resize zero-fill не заменяет этот шаг.
P2/R4 — inherited operator= и возврат Base& могут обойти derived assign/clear; проверить используемые overloads/chaining,
не считать методы virtual overrides. Erase iterator вернуть заново по offset после cleanup, не сохранять iterator через resize.
Проверки invalid positions/failed allocation сохраняют исходное значение; alias не стирается до чтения; self assignment безопасен.
Public Base reference по-прежнему возможен: проверить actual callers и не обещать перехват любых внешних Base mutations.

## Требования к будущему RED и GREEN

Generated char/wchar_t/bytes: forced reserve growth, destruction с прежним tail, clear, shrink, shorter assign,
erase/pop/replace, supported overlap, self copy/move; exact retained prefix и zero removed bytes.
Heap oracle наблюдает весь выбранный allocation до реального free, включая capacity; никаких чтений после free.
SSO не имеет отдельного delete: наблюдать inline character span в тестовом heap owner до его free,
используя тот же test-only oracle; не требовать нулей во всём object representation/metadata.
Отдельно moved-from SSO, short→heap→short, alias к собственному suffix, embedded NUL и wchar_t byte counts.
Под полной quota cleanup не делает allocation: прежние proxy/default/move/refusal/rollback/self-move tests остаются.
RED обязан падать по конкретному wipe oracle, не UB/ошибке setup/compiler; будущий fixture читается до production gate.
После исправления — targeted Debug/Release, прежние allocator/codec и зависимые storage/HTTP regressions;
двойной wipe/полная capacity стоимость измеряется в прежних SC-003/owned64MiB/cache2MiB/pins32/jobs4, caps не увеличиваются.

## Предел решения

Требований existing T116 достаточно; R1–R4 и actual RED являются prerequisites, не разрешением ослабить gates.
Минимальность: existing allocator/wrappers/oracle достаточны; speculative layer не нужен, net:0 framework lines required.
SOURCE337 не переутверждается и не меняется; portable/native337 runtime в этой проверке не принимался.
ALL HTTP/request/config/API/hash/ranges/localtracks/result adoption/scheduler/global admission/installed/release OPEN.
Reviewer создал только этот zero-checkbox report; source/tests/norms/tasks/старые markers/GitHub/VM/jobs не менял.
