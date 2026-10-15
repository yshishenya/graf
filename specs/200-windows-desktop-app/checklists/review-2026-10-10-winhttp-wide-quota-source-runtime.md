# T116: независимое ревью charged WinHTTP wide buffers — source/runtime330

Вердикт: **C0 / H0 / P2=0; GO только узкого foundation-среза**. Проверены исходники, внешние драйверы и фактические terminal artifacts. Это не закрытие T116, ALL HTTP quota, scheduler/adoption, T120, полного native regression или installed/release gates.

## Привязка и границы

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`; branch `codex/200-windows-followup`; HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty changes сохранены.

Frozen330: `/Users/yshishenya/Documents/graf-f200-wide330.4Yqmjz`. SHA-256 `source.json`: `83e00f864958650568f0c58897d064705b8cf1ee3621f45e9ac81e988a4b7b1b`. Независимая локальная сверка frozen/canonical: 209/209 entries совпадают с manifest. Против frozen327 изменены ровно семь файлов (четыре production, три test); остальные 202 inputs неизменны.

| Файл относительно `apps/windows/` | SHA-256 source330 |
|---|---|
| `RecApp/Storage/ProtectedCustodyCodec.h` | `7954822ec768a4d7146fb94e34273e92ea5f6d4cbecb2e9989b761c80fdf851c` |
| `RecApp/Upload/DesktopApiClient.cpp` | `99c0d79ecbe82c3cde447fd8244136e8f10162161ad967c473777f552b4c40f0` |
| `RecApp/Upload/DesktopApiClient.h` | `911a03984842bc3c0fdf411b98f2eadc643b274e374edbcec5f0cbab870e7114` |
| `RecApp/Upload/DesktopHttpTransport.cpp` | `827d6cae5823b2caf75f7cb5631b115a835365822bac18a7f046529adc64826a` |
| `Tests/GrafWindowsContractTests/DesktopDeletionProtocolTests.cpp` | `e9619a75f2a96e67ec32b44f17b873c1288c9da1c3f6530a49387d8b9380ac51` |
| `Tests/GrafWindowsContractTests/NativeCalendarJoinTransportTests.cpp` | `552bd6e58b8f55d9e64fb04c26d928716a1d927fd322a8dc9532d8893efbdcf9` |
| `Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp` | `2b3585f39e6b0522c26334c07665c1432b3322446fef2ee37aa433432a3650e5` |

## Source review

`BasicCustodyString<Char>` обобщает существующий helper, сохраняет throwing default/move construction и существующее move assignment; aliases char/wchar используют тот же CustodyAllocator. Wipe учитывает `size()*sizeof(Char)`. Core tests повторно используют существующие проверки фактической capacity, allocation rollback, Debug proxy, move/self-move и wipe для обеих ширин символа.

`scopedAccountHeaders` возвращает allocation-free `optional<array<pair<string_view,string_view>,2>>`. Validation/header constants сохранены; срок жизни views документирован, rvalue overload удалён. Текущие callers используют живые lvalue scopes и views не сохраняют; тест подтверждает адреса borrowed values.

WinHTTP method/path, UTF-8 conversion, URL/host, header assembly и raw Retry-After/auth-expiry scratch используют charged wide strings. Header assembly через append не создаёт прежних owning operator+ temporaries; uint64 offset форматируется stack `to_chars`, positive control проверяет точные 20 цифр максимального значения. UTF-8 guard предотвращает int truncation; exact Unicode и invalid/empty conversion проверены тестом. Endpoint/auth policy/schema не меняются, общий протокол не дублируется.

Quota cuts: давление устанавливается после открытия трёх handles либо после ReceiveResponse на первом size query соответствующего raw header. Caller body сбрасывается; каждый handle close требует живой owner с исходными bytes. После exception проверяются Send/Receive counts, weak expiry, освобождение weak control и точный возврат charged baseline.

Два выявленных P2 исправлены: `installed=true` только после успешного pressure allocation и `usedBytes()==limit`, а после catch installed обязателен до release; Retry quota value содержит 32 ASCII-символа, исключая короткое inline string storage в Release. Positive control `17` сохранён. Исключение самого pressure allocator больше не даёт ложного PASS.

## Внешние драйверы

`validate.ps1` SHA-256: `84d03f0af06513cee1576fa6567bce7536681ed84fcd833593788ef72836541f`.

`run.mjs` SHA-256: `8f6bd2515d494aa274a9edd176a75b09621dbd6854646151124133276b2ea35b`.

GREEN-путь проверен: predecessor terminal/native_completed/stage guard, same-byte hash/parse manifests, idle/source checks до копирования и после выполнения, последовательные три targets в Debug и Release, ровно шесть exit0 результатов и quota markers в обеих конфигурациях. Windows launcher hash проверяет единожды прочитанные script bytes и исполняет те же bytes. Debug PDB обязателен; Release PDB не требуется. Timeout не убивает процесс и не объявляет native_completed/PASS. Неиспользуемая legacy RED-ветка330 этим source GO не покрывается.

## Фактическое native330 evidence

Прочитаны полный `native.json`, configure/build logs, все шесть test logs и их stdout/stderr. Combined test logs побайтно совпадают с stdout+stderr. Receipt связывает harness/source hashes выше; configure_exit=0, build_exit=0, terminal=true, native_completed=true, stage=`wide_quota_green_verified`.

| Target | Debug PID / exit | Release PID / exit |
|---|---|---|
| NativeCalendarJoinTransportTests | 8348 / 0 | 11096 / 0 |
| ProtectedCustodyCodecTests | 8588 / 0 | 2836 / 0 |
| DesktopDeletionProtocolTests | 7204 / 0 | 7728 / 0 |

Все шесть entries completed=true, имеют start identity и EXE hash; Debug entries имеют PDB hash. Нативные EXE/PDB bytes на VM reviewer заново не читает: identity принята из проверенного receipt/harness, без отдельной live-VM аттестации.

Оба Calendar logs содержат `winhttp_wide_quota_before_send=pass`, `headers_quota_after_receive=pass`, `handles_closed_before_body_release=pass`. Debug core log подтверждает proxy=16 и завершение fault/move/cleanup проверок; Release явно отмечает отсутствие allocated proxy, не выдавая SKIP за Debug proof.

| Artifact330 | SHA-256 |
|---|---|
| `native.json` | `fc55c0d4d7c2cda54ea737f352ba8c6e51030048862edb01a0e7ed8708d46d94` |
| `Debug-build.log` | `0ca9c9ac1c33b47d96aaac5291b83a27c78739a7483e58f31522a83ba1b42f33` |
| `Release-build.log` | `0e9057a03a8f311b5a4fc57d2aa1be8b480f9a6d9f1cdb77ca19e88a730a7466` |
| Calendar log, одинаковый Debug/Release | `2d5c3cba31375c381168d02ce14064cff02856a1c98f721b2236a0a018548b64` |
| Debug core log | `e8da249a3559ca71fa6c67c0927568b11ba94c0831b92710ec42d9d9fd94055e` |
| Release core log | `f36bbad3646afc5fdf38d1c517290e9c4c6faeed8b387461d1b2fcf1eaa96cb1` |

## История RED и диагностик

328: `/Users/yshishenya/Documents/graf-f200-wide328.aG0SYP`. Independently read receipt и actual assertion log: configure/build0, test exit3, completed/terminal/native_completed=true, `wide_quota_red_verified`; assertion line289 требует caught/zero Send/Receive/three closes. Manifest `5d8e30baafb65bf728a3156d98e5e8391604433340a21c3a644e00baed2feb6f`; все production RecApp inputs совпадают с frozen327. Receipt SHA `e696e4c5c2c3b4094ded17a70a3199fa6d937f98cdf20b963be257c6db9e4b5e`, assertion log SHA `d76fe16959cf3fe1d757996f93bd505f05a345e44fb05741ababfcb16e86fa1d`. Это ограниченный old-shipping/option-only RED, не RED новых raw-header cuts и не полного ALL quota.

329: `/Users/yshishenya/Documents/graf-f200-wide329.m7Cljf`; receipt SHA `c66ed51928c0501e3ef4b569bbaf5ce12d6db07bb4e1b77e0126a23caedd19aa`, source `83dbbf2d5337492106e199372529edd4acba5c03c69cd121b45fd9c8324f85ed`. Technical PASS/terminal остаётся **unaccepted diagnostic** из-за двух тогда открытых P2; он используется как drained predecessor, не как acceptance foundation-среза. Исторические результаты не переписаны.

## Portable330 — terminal evidence поступило во время ревью

Первоначально PENDING; до записи отчёта independently read `portable.json`, portable driver и test log. Receipt terminal=true, stage=`portable47_verified`, configure/build/test0, bound to exact source330. Проверены hashes всех трёх portable logs; test log содержит 47 уникальных starts и 47 уникальных Passed completions, 47/47 PASS за 25.16s. Driver проверяет frozen/canonical source до и после выполнения.

Receipt SHA `e9e3cf8b213edbf0154a6ef07d582ffa6ece3c5e7f0c0a16af644fb349b304af`; test log SHA `3f0a1ea7d3cbde21574bca6362d498f711d8b52b9f14a6c0fadd511e0b6cf3c3`. Это portable47, не Windows full53 и не installed acceptance.

## Ponytail и обязательные открытые границы

`code-reviewer` и `ponytail-review` прочитаны полностью. Семифайловый diff против frozen327 проверен: обобщение существующего string/helper/test вместо параллельного алгоритма; stdlib array/views/to_chars и native WinHTTP сохранены. Нет нового registry, dependency, protocol fork или speculative framework. Ponytail: **Lean already. Ship.** Отдельных сокращений не предложено; это заключение о форме diff, не разрешение release/full T116.

Открыты все ещё не переведённые request/response/config/DTO/result/hash/serialization allocations и capacities, фактическая scheduler publication/adoption, storage-worker/native-worker fences и полный T116/T120 admission. Не заявляются ALL quota GO, full current native suite, Windows installation, real network/audio, backend/auth-policy изменения или release GO.

Reviewer не запускал jobs/VM/CUA/GitHub и не менял production/tests/normative/tasks/checklist markers. Единственная запись — этот zero-checkbox reviewer-owned report; lane: scoped independent evidence review внутри существующего high-risk F200/T116.
