# Независимая проверка требований: packed short tail / T116

Дата: 2026-10-04. Отметки принадлежат независимому reviewer.
Область проверки: техническое предложение основного агента для следующего
worker-only этапа, а не новое решение владельца или изменение норм.

## Решение и границы

**SCOPED REQUIREMENTS APPROVED: CRITICAL=0 / HIGH=0;
14 checked / 0 unchecked.** Действующий контракт и предложение достаточно
точно определяют этот ограниченный этап. Блокирующих уточнений требований
не найдено. Это не проверка будущих исходников, не runtime PASS и не закрытие
полной Step 3/T116. Analyze, остальные применимые gates и отдельная проверка
готовых исходников сохраняются.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`.
Лично сверенный HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Незакоммиченные round221 source/docs сохранены. Иной checkout не использован.
Risk lane: requirements review внутри активного high-risk-product;
собственная запись — только документация независимой проверки.

Допуск: короткий блок при выровненном EOF и явная полная замена последнего
короткого блока; один прежний commit/Guard/Owner путь. Не допускает произвольный
writeAt, SetSize, shrink, много блоков за commit, большие ZERO ranges,
cursor/Clone adapters, producer/finalizer/MF/hash/upload интеграцию,
metadata roots/migration/GC, использование реального inventory или установку.
Все эти обязательные следующие части T116–T118 остаются открытыми.
Audio/clock, физический x64, визуальный паритет, доступность, подпись,
install/update/rollback и выпуск не принимаются данным отчётом.

## Прочитанные материалы и актуальность

Root AGENTS, guidance index, code-reviewer, codex-worktrees и применимые
spec-kit-flow/product-gates/release guidance прочитаны. Из унаследованной
истории повторно использовано полное чтение неизменных active spec/plan/tasks/
quickstart/constitution и продуктовой базы; текущие полные SHA сверены ниже.
Это reuse прежнего чтения по идентичности, не заявление нового полного
построчного чтения всей продуктовой документации в этом проходе.

Packed contract прочитан целиком заново; повторно проверены FR-012,
актуальный независимый storage-порядок и packed dependency Steps 1–7 в plan,
T115–T118 и §14 quickstart; применимые §§5–6 local-custody contract.
Текущие Tree.h/commit path Tree.cpp прочитаны для оценки совместимости
предложения. Их нынешний FULL-only API не выдан за будущую tail реализацию.

Пять нормативных checklists перечитаны: requirements **22/0**, audio **24/0**,
advanced **14/0**, security **27/0**, ux **25/0**, всего **112/0**.
Ни их отметки, ни исторические отчёты не изменены. Исторические требования
юридических условий читаются с явным уточнением Constitution 7; они не
возвращаются в prerequisites записи. Requirements PASS не означает UI PASS.

Последние live-writer reports прочитаны: requirements **14/0**,
source **9/0**, окончательный scoped C0/H0/M0. Сохранена история M1 и его
последующего устранения, без повторного открытия закрытого full-block finding.
Все семь current source SHA совпали с окончательным source report.
Его native/portable receipts атрибутированы основному агенту; reviewer здесь
ничего не исполнял. Эти результаты не принимают ещё не написанные tail ветки.

## Reviewer-owned критерии качества требований

`[X]` ниже означает достаточную полноту, ясность, проверяемость и согласованность
требования, а не результат будущего теста. Предложение — main technical
proposal; не новое разрешение человека, не exception и не самостоятельная норма.

- [X] PTG001 Определена ли область двух worker-only операций и её связь с открытой T116, без принятия всей Step 3 или приложения? Доказательства: FR-012; plan packed Steps 3–7; tasks T116–T118; предложение. Tail checkpoint требуется local-custody §5, но интеграция Flush/Pause/Stop этим prerequisite не закрывается.
- [X] PTG002 Однозначно ли `appendBlock(bytes)` принимает 1..262144 bytes только при aligned logical EOF; block index=base.blockCount, candidate length=base.length+input.size(), count=base.blockCount+1? Доказательства: packed §§3–4, descriptor/tail; предложение. Короткий commit создаёт точный EOF без padding; следующий append до заполнения tail отвергается, не скрыто переводится в replacement.
- [X] PTG003 Однозначно ли `replaceTail(bytes)` требует nonempty unaligned base и полную caller replacement последнего блока размером oldTail..262144; index=base.blockCount−1, count неизменен, length=index×262144+input.size()? Доказательства: packed §4, local-custody §6; предложение. Это разрешённая полная правка last block, не обещание автоматически сохранить его старый префикс. Same size допускает rewrite, рост до full делает EOF aligned; implicit shrink запрещён.
- [X] PTG004 Определены ли empty/oversize/wrong mode, short base для append, aligned/empty base для replacement, shrink, 64GiB и generation exhaustion как отказ до append/HEAD effects? Доказательства: packed §§3,5; предложение. Checked arithmetic не wrap; stale selected base/exact pair правила остаются действующими. «Без I/O effects» не запрещает необходимые confinement/metadata проверки и проверочные reads; означает отсутствие записи/flush публикации и нового proof.
- [X] PTG005 Сохраняется ли первый fault и его nativeError до проверки пользовательского режима/размера и quota refusal, под тем же Guard; не становится ли invalid-input способом скрыть observed sticky failure? Доказательства: packed §§1–2,5–6; current writeReady/reject/result path; предложение. Обычный неверный вызов не доказывает corruption и не должен сам лишать старый snapshot чтения.
- [X] PTG006 Сведены ли оба API к одному private `commitBlock(bytes,bool replaceTail)`, без legacy alias, второго IO backend, mutex или lifecycle? Доказательства: packed §6 reuse; нынешний immutable private Tree/Guard путь; предложение. `appendFullBlock` пока не adopted; переименование существующих двух тестовых caller files не требует compatibility alias. Ссылки исторических receipts не выдаются за active API.
- [X] PTG007 Получает ли операция authority только от private Tree proof того же continuous Owner, с exact предыдущей парой, selected base+1/slot formula и selected-base peer; caller передаёт bytes, не descriptor/root/verified flag? Доказательства: packed §§1–2,4–5; прежний LW002/004/005/008; предложение. Decode/новый pathname не переносит proof через ownership gap.
- [X] PTG008 Ограничен ли authorized structural diff одной вычисленной позицией, с точным сохранением всех прочих authenticated Ref64, правильными selectors/levels/version/extent и exact short/full DATA payload? Доказательства: packed §§3–4; прежний LW006/007; предложение. Изменённая длина tail не разрешает заменить соседний subtree. ZERO splitting наследует прежние явные zero ranges, не создаёт тишину вместо отсутствующих данных.
- [X] PTG009 Сохранены ли пределы ≤1DATA+3NODE и прежний ≤290816B append span, depth3/radix64, отсутствие full old-DATA scan/flat index, включая radix64/4096 и последний блок у64GiB? Доказательства: packed §§3–4,6; quickstart §14 Live delta; предложение. Short/replacement не требуют новый physical record budget; native latency не объявляется ограниченной wall-time.
- [X] PTG010 Сохраняются ли один admitted job/State mutex/strong Owner через append, оба flush и independent disk readbacks, catch и return; reservation/pin/dirty/owned budget до acceptance и потенциальные allocations proof/result до HEAD publication? Доказательства: packed §§2,5–6; local-custody §5; прежний LW003/009/012; предложение. Native allocations не принимаются за доказанный owned64MiB bound. Borrowed caller input не заменяет independent readback.
- [X] PTG011 Определён ли полный paired ACK: actual append-only EOF, первый flush/проверка всех новых records, HEAD attempt boundary, второй flush, обе exact cells/candidate+selected base, повтор records/confinement, и лишь затем выдача prospective proof? Доказательства: packed §5; прежний LW007/008/013; предложение. До HEAD notCommitted, после начала HEAD I/O любой отказ ambiguous/sticky; одна успешно прочитанная cell не ACK, orphan tail не truncate/reuse.
- [X] PTG012 Сохраняют ли старые short/full snapshots свои bytes/length/root и actual custody после замены/growth, вытеснения из обеих heads и release caller, без ретроактивного роста или padding; cold reopen требует полную обеих-head closure? Доказательства: packed §§2,4–5; local-custody §6; предложение. Старый pinned reader не становится новым writable base, observed failure не обходится старым root.
- [X] PTG013 Достаточно ли определены exact-byte/length/generation success и refusal/admission проверки, RED→implementation, без giant fixture/production switch и переноса прежнего FULL PASS на tail? Доказательства: packed §7; quickstart §14; матрица ниже; предложение. Проверки проводят main на generated data, source acceptance отдельно.
- [X] PTG014 Есть ли обязательные actual-worker native cuts для каждого нового режима и valid unchanged-sibling negative, с проверкой outcome по фактической HEAD attempt, no snapshot/retained custody/first error/no unsafe retry; не подменяется ли semantic diff отказ порчей framing/SHA? Доказательства: packed §7; прежний закрытый M1; предложение и матрица ниже. Existing FULL fault matrix остаётся регрессией shared path, но не самостоятельным доказательством новых веток.

## Ограниченная проверочная матрица для следующего source review

Это критерии будущих доказательств main, не выполненные reviewer проверки.

| Группа | Конкретное необходимое доказательство |
| --- | --- |
| Размер/байты | Aligned append1/3/262143/full, exact logical length и возвращённые bytes; cold reopen обеих heads без padding. Replacement same size с отличающимися bytes, рост short→short и short→full; после full следующий append. |
| Tail immutability | Short checkpoint→несколько replacements/append, старый short root вытеснен из обеих cells, но pinned reader выдаёт только прежний короткий tail. Новый root не раскрывает старые отрезанные/лишние bytes. |
| Диапазоны | Компактная base на переходах radix64/4096 и последний возможный short/full блок у64GiB; replacement count неизменен, append count+1, next append сверх лимита отказ. Не создавать64GiB DATA fixture/flat arrays. |
| Refusals | Пустой/oversize input; append на short EOF; replacement empty/aligned base/короче oldTail; generation max. Нет append/head writes и нового snapshot, old readable там, где нет observed storage fault. Sticky fault имеет прежний exact error/nativeError даже с неверным input; admission32/4/dirty/owned сохранена. |
| Publication cuts | Existing FULL matrix регрессии плюс measured native write/read/flush/exception cuts actual `appendBlock(short)` и actual `replaceTail`. Считать boundary по реальной HEAD attempt, не guessed ordinal. Before-head notCommitted/post-head ambiguous, retained base lease/first error, повтор без unsafe native IO. |
| Unchanged sibling | Новый append/replacement с существующим соседним DATA; подмена отличающегося, но structurally valid Ref64 при согласованных envelope SHA/DPAPI/inner checksum. Actual shared worker отказывает именно structural diff до HEAD; отказ framing/hash или подмена HEAD peer не заменяет этот case. |
| Identity/исполнение | Exact source/test hashes и terminal native receipts новых веток, отдельно portable/non-Win32 scope; Release assertions активны. Старый FULL report не source acceptance нового diff. Reviewer не исполняет VM/tests и ожидает source-ready. |

Произвольный Write/SetSize/shrink/ZERO ranges/cursor/Clone и общий stream adapter
не являются prerequisite этого bounded gate, но не исключены из полной T116.
Отдельно остаются generated cadence/Stop измерения, protected metadata refs,
MF/hash/upload/playback adoption, migration и T118 installed acceptance.
Нет основания требовать новую архитектуру или весь T116 для этих двух операций.

## SHA-256 нормативного и исходного снимка

`spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, `contracts/` и `checklists/`
относятся к `specs/200-windows-desktop-app/`; остальные пути — к canonical.
Старые документы не изменялись. Source report
идентифицирует семь лично сверенных pre-tail source files; их hashes совпали.

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| tasks.md | `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98` |
| quickstart.md | `2a1c494eafe087b46470de527b4af024970054adcd75bb5df2e1032312bac2f3` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| contracts/windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| contracts/windows-protected-local-custody.md | `5c2aad2bbcdee3b47c19df1a80574f9ab03a023f1d7ab59aef6948c1518f2509` |
| docs/prd-voice-layer-final.md | `5c93f6a3a72e639e0cf835518f2ef5e03680b3b500c53734e3478cdd59448212` |
| docs/current-product-status.md | `014243c9fc34ad4a7c77028685c82edcfba8ef8e2a4fcff64ed0479f728d4482` |
| checklists/requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| checklists/audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| checklists/advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| checklists/security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| checklists/ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| checklists/review-2026-10-04-packed-live-writer-gate.md | `7fb4f75180745620091241fd569e47677efeda113080f3b452155bca84181a5f` |
| checklists/review-2026-10-04-packed-live-writer-source.md | `dbc28796fb37629f6a3bf5f283fbf88946f319e1ed1a901b63b3300abcc46edd` |

Reviewer изменил только этот NEW файл. Code/spec/plan/tasks/старые checklists/
reports/Git/GitHub/VM/runtime/commit/install/release не изменял и не исполнял.
Исходники tail будут проверяться после отдельного source-ready сигнала в
`review-2026-10-04-packed-tail-source.md`; заранее source acceptance не выдан.
После записи перечитаны критерии и счётчики: **14 checked / 0 unchecked**.
