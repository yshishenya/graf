# Независимая проверка требований: packed existing-block rewrite / T116

**Назначение**: полнота, ясность, проверяемость и согласованность требований
к ограниченной замене одного существующего блока до правок кода/тестов.
**Дата**: 2026-10-04.
**Feature**: `specs/200-windows-desktop-app/spec.md`, FR-012/013/014/022;
SC-003/005/006/008; plan packed dependency Step 3, открытая T116.

Чеклист создан с использованием `speckit-checklist`; качество требований
оценивает независимый reviewer. При генерации все пункты оставлены `[ ]`.
Отметка `[X]` после отдельной оценки означает достаточность требований,
не реализацию, тестовый PASS или выполнение T116. Основной агент читает
этот gate, но не меняет reviewer-owned marks.

## Область и состояние проверки

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`.
Лично сверенный HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Risk/validation lane: независимая requirements-quality проверка внутри
активного high-risk-product; собственные изменения только документация review.
Dirty round222 принятого предыдущего этапа сохранён. Старые marks/reports
не изменяются; прежние source PASS не принимают новые ветки.

Предложение main — техническая детализация существующего плана, не новое
решение человека, норма, разрешение на commit/install/audio или exception.
В области: `appendBlock(bytes)` и полная замена одного EXISTING блока через
`replaceBlock(uint64 index, bytes)`, один прежний private commit путь.
Unadopted `replaceTail` удаляется без alias; текущие caller search показывает
только Tree.h/Tree.cpp и два тестовых caller файла, не продуктовую интеграцию.

Не в области: произвольный partial WriteAt, cross-block/dirty-group commits,
SetSize, shrink, большие ZERO ranges, cursor/Clone adapters, MF/producer/
finalizer/hash/upload/playback adoption, metadata/migration/GC lifecycle.
Они остаются обязательными следующими частями T116–T118, не отброшены.
Clock/audio, реальный inventory, установка, физическая x64/60min/AEC,
визуальный паритет, доступность, подпись и выпуск не принимаются этим gate.

## Полнота и ясность ограниченных операций

- [X] CHK001 Определены ли границы one-block rewrite и его связь с открытой Step 3/T116 без объявления полного protected pipeline готовым? [Полнота; Spec FR-012/014; plan Steps 3–7; tasks T116–T118; main proposal]
- [X] CHK002 Однозначно ли сохранён aligned-EOF append размером 1..262144, с index=base.blockCount, count+1, length=base.length+input.size(), и отказом append после short EOF? [Ясность; packed §§3–4; main proposal]
- [X] CHK003 Однозначно ли replacement означает полные caller bytes одного существующего index, а не patch диапазона, caller root/descriptor или сохранение старого префикса без явного input? [Ясность; packed §4; main proposal]
- [X] CHK004 Определены ли index<base.blockCount ДО index×262144, old payload=min(262144,base.length−index×262144), полный размер для full/interior и oldTail..full для last short, без shrink/hole/padding? [Границы; packed §§3–4; main proposal]
- [X] CHK005 Согласованы ли candidate count/length, max64GiB и generation+1 для обеих операций, включая UINT64_MAX index/generation, last full и growth short→full? [Согласованность; packed §§3,5; main proposal]

## Authority, сохранность и ограниченность

- [X] CHK006 Достаточно ли явно задан один общий commit/Guard/job/Owner/mutex путь с optional index и удалением только unadopted replaceTail без alias, нового backend или lifecycle? [Зависимости; packed §§2,6; main proposal]
- [X] CHK007 Сохранён ли приоритет writeReady/первого observed fault/nativeError перед invalid input и admission, с безопасным отказом без публикации и без poison старого reader от обычного неверного input? [Ошибки; packed §§1–2,5–6; main proposal]
- [X] CHK008 Определена ли authority от точного private base proof того же непрерывного owner, exact старой пары/selected base, base+1/target slot и selected-base peer, без stale/caller-descriptor обхода? [Согласованность; packed §§1–2,4–5; main proposal]
- [X] CHK009 Ограничен ли разрешённый structural diff единственным вычисленным index, с exact всеми authenticated unchanged refs и прежним short tail, selectors/version/extent и exact DATA payload/SHA до decode? [Безопасность; packed §§3–4; main proposal]
- [X] CHK010 Сохранены ли ≤1DATA+3NODE/≤290816B, radix64/depth3, исходные owned/cache/dirty/pins/jobs admission и pre-HEAD allocations, без full старого DATA scan/flat index/обещанного native wall-time? [Ограниченность; packed §§2,4,6; quickstart §14; main proposal]
- [X] CHK011 Полностью ли определены append-only actual EOF, первый flush/independent readback, HEAD attempt, второй flush/обе exact heads, повтор records/confinement, и лишь затем candidate proof/ACK; notCommitted vs sticky ambiguous и удержание custody? [Ошибки/восстановление; packed §§2,5; main proposal]
- [X] CHK012 Определены ли immutable старые root/bytes/length и pins после rewrite/HEAD eviction, без ретроактивного роста, и cold обеих-head closure после ownership gap? [Восстановление; packed §§2,4–5; main proposal]

## Проверяемость и покрытие сценариев

- [X] CHK013 Достаточно ли заданы exact-byte критерии first/middle/full-last/short-last rewrite, untouched DATA с обеих сторон и прежний short tail, growth/same-size, pinned old root и cold reopen, включая forged full/partial-tail несовпадение? [Проверяемость; packed §§3–5,7; quickstart §14; main proposal]
- [X] CHK014 Заданы ли компактные radix63/64/4095/4096/last64GiB и empty/indexEOF/UINT64_MAX/size/mode/maxgen/stale/quota отказы с наблюдаемыми bytes/state и без новых write/HEAD effects? [Границы; packed §§3–7; main proposal]
- [X] CHK015 Полны ли требования новой actual-worker native interior-rewrite fault matrix на nonempty base и сохранения append/tail matrices, включая valid non-target NODE sibling под real codec/SHA/DPAPI/decode, first error/custody/admission и pre-HEAD structural-diff отказ? [Ошибки/измеримость; packed §7; main proposal]
- [X] CHK016 Отделены ли RED missing-API → реализация → exact-SHA native Release/Debug и остальные регрессии от portable scope, прежних PASS и будущей source/install/audio/T116 acceptance? [Прослеживаемость; Constitution VI; quickstart §14; main proposal]

## Основания независимой оценки

Это оценка написанных требований, не исполнение будущей матрицы.

| Пункты | Основание достаточности требований |
| --- | --- |
| 001,016 | План Step 3 явно включает persistent-tree update, но далее требует cursor/Clone/shrink/ZERO, измерения и consumers. T116–T118 открыты; proposal исключает закрытие всей задачи. Сначала RED, отдельный source-ready и terminal evidence — не перенос прошлого PASS. |
| 002–005 | Main задаёт режимы и точные формулы. Для private доказанного base count=ceil(length/B), B=262144; index<count проверяется до умножения. Значит index≤262143, offset≤64GiB−B и offset<length: вычитание безопасно. Full input=B сохраняет interior/last-full length; short-last input≥oldTail даёт same/growth без shrink. Replacement count неизменен и согласуется с ceil(new length/B). Aligned append length<64GiB оставляет ≥B, поэтому input≤B не переполняет limit. Generation exhaustion отвергается до +1. |
| 003,006 | Caller даёт index и полный replacement payload, не root/верификационный stamp; это авторизация всей позиции. optional present означает existing rewrite, nullopt append: не смешивается индекс0 и отсутствие индекса. Нынешний replaceTail не adopted; две caller files тестовые. Предложение не требует второго backend/mutex или compatibility alias. |
| 007,008 | Packed §§1–2,5 сохраняют sticky failure, непрерывный owner, exact paired authority и selected base. Proposal явно сохраняет writeReady прежде input/limits/admission и прежний первый error. Invalid input не доказательство порчи; refusal не означает новый proof. Stale base не становится допустимым при совпавшей длине. |
| 009,010 | Единственный разрешённый index ограничивает changed path; неизменный tail не превращается в full DATA при interior rewrite. Exact sibling refs — из authenticated BASE, не caller/writer copies. Current packed wire требует envelope SHA до decode, exact typed context/checksum/payload. ZERO splitting сохраняет существующие explicit ranges, не создаёт hole или тишину. Прежние budget/owner/pin/result bounds применяются ко всем режимам; DPAPI internal allocation и latency не объявляются доказанными. |
| 011,012 | Packed §5 однозначно задаёт два flush/readback этапа, обе heads и selected-base peer. HEAD attempt отделяет notCommitted от ambiguous; ни readback одной cell, ни новые bytes не ACK. Старые records append-only; старые pins/root/length сохраняются, orphan tail не truncate/reuse. Cold reopen full-проверяет обе closures. |
| 013,014 | Main задаёт bytes и length до/после rewrite на first/middle/last, сохранность с обеих сторон/short tail, old pinned и cold snapshots, компактные пограничные деревья без giant allocation. Forged full/short-tail должен отвергаться exact payload/child semantics. Invalid index включает empty/EOF/UINT64_MAX до offset arithmetic; input rules различают full и short; generation/stale/admission/fault priority измеримы. |
| 015 | Новый interior rewrite имеет actual shared worker cuts, nonempty authenticated base и наблюдаемый HEAD attempt. Existing matrices остаются; measured per-mode write/read/flush ordinals не заменяются guessed append ordinals. Non-target sibling negative обязан пройти real framing/hash/DPAPI/typed semantics, чтобы отказ доказывал structural diff, а не ранний codec reject. Outcome/no proof/retained base lease/first native error/no unsafe retry/admission остаются прежними требованиями. |

«Без effects» в refusals означает отсутствие новых records/HEAD writes,
flush publication и candidate proof; не запрещает необходимые confinement/
authority reads. При sticky failure никакой invalid mode/size не скрывает fault.
Полное приложение и полный T116 не являются prerequisite этого bounded gate.

## Прочитанные материалы и привязка снимка

Root AGENTS.md, guidance index, code-reviewer, codex-worktrees, spec-kit-flow,
product-gates и release-and-validation прочитаны. Canonical speckit-checklist
прочитан целиком: он отличается от доступной копии 0309; используется активный
project-local вариант без его изменения. YAML hooks разобран read-only:
before_checklist/after_checklist commit hooks disabled; ничего не исполнялось.
Read-only prerequisite `--json --template checklist-template` подтвердил
canonical FEATURE_DIR и предоставил шаблон. Новых clarification вопросов нет:
scope/actor/timing/режимы/исключения прямо определены запросом.

Полное прежнее личное чтение неизменных spec/plan/tasks/quickstart/constitution,
data-model, local-custody, PRD/current status и пяти нормативных checklists
повторно использовано только после fresh SHA сравнения. Это не заявление
нового полного чтения всех этих больших файлов в данном проходе. Packed
contract перечитан целиком; заново прочитаны FR-012, Constitution VI,
актуальные packed Steps 1–7, T115–T118 и §14 quickstart. Текущий API/начало
commit path и caller search прочитаны только для совместимости proposal,
не как source acceptance ещё не написанного replaceBlock.

Пять неизменных нормативных checklists: requirements22/0, audio24/0,
advanced14/0, security27/0, ux25/0 — исторический baseline112/0.
Прежние tail gate14/0 и source9/0 сохранены как предыдущий ограниченный этап.
Новые блокирующие C/H требования или конфликт product policy не обнаружены;
не вводятся юридические/серверные/аудио prerequisites или новая архитектура.

| Артефакт | Fresh SHA-256 |
| --- | --- |
| spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| tasks.md | `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98` |
| quickstart.md | `2a1c494eafe087b46470de527b4af024970054adcd75bb5df2e1032312bac2f3` |
| constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| windows-protected-local-custody.md | `5c2aad2bbcdee3b47c19df1a80574f9ab03a023f1d7ab59aef6948c1518f2509` |
| data-model.md | `ed7da763ddaa281f7cca2d05b9f4349eca9c9af5293d807008371e6e9a42c16d` |
| docs/prd-voice-layer-final.md | `5c93f6a3a72e639e0cf835518f2ef5e03680b3b500c53734e3478cdd59448212` |
| docs/current-product-status.md | `014243c9fc34ad4a7c77028685c82edcfba8ef8e2a4fcff64ed0479f728d4482` |
| checklists/requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| checklists/audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| checklists/advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| checklists/security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| checklists/ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| checklists/review-2026-10-04-packed-tail-gate.md | `eb341afb826a316b9f547e67dfd4e4de30ec521dfbea8cfd1a1a605d87d7c4ce` |
| checklists/review-2026-10-04-packed-tail-source.md | `9709bf60d815954fc9185a12f35e925fbd0528a0df35459977ea64bdef711169` |

Пути spec/plan/tasks/quickstart/contracts/data-model/checklists в таблице
относительно активного `specs/200-windows-desktop-app/`; constitution —
`.specify/memory/constitution.md`. Нормы и старые отчёты не изменены.
Source review будет отдельным после source-ready в новом
`review-2026-10-04-packed-rewrite-source.md`, заранее не создан и не принят.

## Примечания reviewer

Generation завершена: **0 checked / 16 unchecked**. Ни один пункт не принят
одной генерацией; последующая независимая оценка по основаниям выше запишет
свой итог и отметки. Reviewer изменил только этот NEW gate; VM/tests/GitHub/
code/normative/install/runtime/commit/release действий не выполнял.

## Итог независимой оценки до реализации

**SCOPED REQUIREMENTS APPROVED: 16 checked / 0 unchecked;
CRITICAL=0 / HIGH=0; блокирующих clarification gaps нет.**
Отдельно после generation reviewer оценил каждый CHK001–CHK016 по указанным
нормам и main technical proposal. Основания принятия находятся в таблице
выше; все16 пунктов имеют traceability. Отметки и весь gate перечитаны,
счётчики checked/unchecked сверены. Предыдущие 0/16 описывают только
generation, не текущее состояние review.

Это разрешает основной агенту продолжать именно bounded existing-block
rewrite при остальных действующих gates, сначала RED, затем реализация.
Предложение не требует новых норм или новой human product policy.
Существующий protected authority/ACK/fault/admission путь сохраняется;
шаг3/T116 целиком, установка и приложение не приняты. Предыдущий tail
SOURCE ACCEPTED не перенесён на новые source ветки. Независимый source
report и его критерии появятся только после отдельного source-ready.

Reviewer изменил только этот новый checklist/report, старые marks/reports
и dirty source/docs сохранены. VM, тесты, Git/GitHub mutations, код, нормы,
задачи, install/audio/private inventory/commit/release не затронуты.
