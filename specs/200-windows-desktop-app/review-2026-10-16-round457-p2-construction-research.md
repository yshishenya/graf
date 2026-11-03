# Round457 — P2: продолжение завершённых outputs перед final seal

## Граница исследования

Read-only source/design research, не requirements/analyze/runtime GO. Authoritative branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` проверены. Current216/216 совпадает с frozen456 GREEN3 manifest `a6774514da8a14b6ef5726970194537a5402ee8e6c17bf6fa37a4500ef87af94`. Прочитаны current AGENTS/router/product-gates/spec-kit-flow, construction B plan:2316–2375, finite P2/E1 audit453, source и actual456 cuts. Frozen456 не изменён. Единственная запись reviewer — этот новый report457; code/spec/plan/tasks/checklists/VM/Git/index/cleanup не менялись. Никакие scripts/tests не исполнялись.

## Короткий вывод

**Положительное продолжение данного layout конструктивно возможно без нового формата, ledger, UUID, dispatcher или повторного кодирования. Это не готовая композиция существующих public API.** Минимальная операция — private проверка уже завершённых пяти members под genuine StoreOwner/package ownership, затем **один existing package-state generation+1 commit → sealedDegraded**, после него обычная полная sealed inspection. Не повторять recover/retainPrefix как есть и не поднимать prefix/parsed descriptor до authority.

«Без перезаписи metadata» требует точного смысла: manifest/recovery/index history и все audio bytes остаются неизменными, но **новая публикация package-state обязательна**. Вообще без durable package-state publication завершение finalizing в sealedDegraded невозможно. Нельзя выдавать один read-only proof или внутренне изменённый phase за эту публикацию.

## Что реально оставляет before-final-seal

Основание — GREEN3 case role5/op2/after_event23 с actual native c000007f и cold finalizing; source цепочка:

1. `V5LocalRecordingWriter.cpp:638–665 retainPrefix`: finalizing ACK, canonical sealed ref только во временном writer state, writeWav/writePlayback с checkpoint/decode, sealMetadata(manifest), sealMetadata(recovery), затем final package commit.
2. `ProtectedCustodyMetadata.cpp:1836–1873 commitMetadata`: bound manifest rollover сначала сохраняет предыдущий package ref, затем пишет metadata и публикует package с новым manifest ref. **Это не публикует временные media/playback/canonical-sealed/recovery refs writer State.**
3. Значит selected finalizing package после fault уже связывает новый degraded/artifact manifest, но canonical ещё live; завершённые media/playback и recovery могут физически существовать **без final package refs**. Их отсутствие в refs не доказывает unused, а наличие валидного JSON не доказывает происхождение/authority.
4. Existing `openUnfinished` (`Metadata.cpp:1643–1758`) намеренно допускает только live canonical и bound manifest из BOTH slots; другие refs/started role inventory отвергаются. Для manifest selected generation обязан совпасть с bound ref. Для unused derived roles используются новые container IDs, поэтому эту ветку нельзя применять к существующим outputs.

Это точный positive P2 slice: **полностью записанный terminal layout, не arbitrary partial output continuation**. Byte-partial/DATA-only/head singleton/orphan manifest/bad peer сохраняются и здесь не ремонтируются.

## Минимальные private дополнения и reuse

### 1. StoreOwner acquisition: отдельная terminal-completion ветка, не ослабление unused guard

Переиспользовать existing-only package root/state/role discovery и identity/collision checks из openUnfinished. Выбор completion layout делается внутри genuine worker acquisition из actual BOTH package-state и native inventory, не из caller bool/JSON/synthetic V5 result. Удерживать тот же root/package/role leases до final release.

Для выбранного случая требовать selected finalizing, live canonical container ID согласован в BOTH, selected **bound** manifest generation/hash/length действительно присутствует и является current selected metadata. Manifest должен быть именно complete degraded/artifacts/session layout. Старый live/no-artifacts manifest плюс произвольные started outputs не является этим случаем и остаётся отказом. Все старые refs BOTH package slots должны продолжать разрешаться и полностью проверяться; нельзя проверить только selected и забыть peer.

Acquire package-state для existing mutation, а canonical/media/playback/manifest/recovery — без content/metadata write capability для этой ветки. Существующий `ProtectedPackedCustodyOwner::openImpl` в `ProtectedCustodyFiles.cpp:1415–1520` умеет **переносить** prepared readonly role lease в readonly packed owner, не reopen content через caller path. Но он требует уже известный container ID и сам открывает content. Container ID media/playback здесь отсутствует в package refs: см. следующее звено. Не снимать глобальный check prepared writable/readExisting, не делать readonly→writer upgrade.

Практически минимально — private completion variant существующего acquisition, общий helper для неизменной identity-discovery части при необходимости. Не второй StoreOwner, не новый background service и не попытка пустить started outputs через CREATE_NEW. Отдельный runtime mode inside existing terminal writer допустим как выбор алгоритма; **сам mode не proof**.

### 2. Packed discovery — реальный недостающий API, не prefix-as-authority

`ProtectedPackedCustodyFormat.cpp:34–53`: container ID есть в prefix bytes48–63. `prefixMatches` лишь сравнивает wire bytes с ожидаемым context. Публичного безопасного cold discovery из unknown container ID сейчас нет: `Owner::openImpl` требует context заранее, а `Tree::verify` проверяет prefix относительно уже установленного owner context.

Нужен узкий **private existing-only factory** в существующем physical owner/file layer: context store/object/role берётся независимо из genuine acquired role identity; content открывается один раз и остаётся удержанным; только candidate container ID читается из prefix на ЭТОМ handle, проверяются полный prefix/структура/непустой ID/collisions. После этого existing `ProtectedPackedCustodyTree::verify` (`Tree.cpp:32–151`) обязан decrypt/authenticate **оба HEAD, все edges/records обеих closures**, а не только selected descriptor. До этого candidate ID не возвращается как proof/permission. Затем hash/semantic binding связывают bytes с bound manifest.

Не читать prefix отдельным std::ifstream/CreateFile с последующим release/reopen, не принимать произвольный PackedCustodyContext снаружи и не генерировать новый container ID. Кандидат из prefix сам по себе не является authority; доказательство получается из continuous native identity + authenticated BOTH trees + exact bound manifest/artifact semantics. Partial birth/one bad HEAD не допускают fallback на второй HEAD.

### 3. Full terminal semantic preflight без поддельного sealed Pair

Current `LocalRecordingPackage.cpp:569–620` намеренно не даёт ProtectedInspection для finalizing. `unfinishedHistory:538–561` требует live normal/no-artifacts (`RecordingJson::manifest(...unfinished=true)`), поэтому тоже не подходит degraded output manifest. **Не менять public phase guards и не изготовлять in-memory sealed pair ради reuse.**

Минимальный reuse — private phase-specific validator рядом с existing closed RecordingJson/protected metadata/stream helpers, вызываемый только для genuine acquired completion package. Можно выделить общую closed semantic часть sealed inspector; внешние public sealed guards остаются прежними. Результат живёт только в existing terminal writer/package state под retained proofs, не публичный boolean/snapshot/authority.

Он проверяет:

- Selected bound manifest и все связанные BOTH history snapshots: exact session, privacy IDs/OPEN/CLOSE/границы и присутствие/отсутствие временных полей без синтеза recovery wall-clock. Старый normal/no-artifacts snapshot допустим только как валидная история соответствующего peer, не как выбранный terminal manifest. Новая terminal история не должна стирать или выдумывать предыдущую.
- Canonical actual verified tree, весь logical hash/length и finite complete480 prefix, включая сохранённый incomplete tail вне playable prefix. Exact frames/duration берутся из проверенных canonical/recovery согласований, не physical file size.
- Media/playback — existing read-only BOTH tree proofs, реальные selected descriptor/hash/length, точное совпадение с artifact bytes/SHA **bound** manifest; WAV canonical header/duration и actual full AAC decode/EOF/duration через existing helpers. Никакого re-AEC/padding/re-encode.
- Recovery metadata — BOTH valid indices/payloads, exact closed recovery shape, reason/frames/canonical bytes/SHA согласованы с genuine canonical и bound terminal manifest. Не «любая выбранная newer metadata». Для первого узкого случая можно требовать именно однозначную existing recovery birth pair/generation; arbitrary unbound newer generations остаются отказом. Это **именованное подтверждение уже завершённого terminal record**, а не разрешение принимать unknown orphan вообще.
- BOTH-union references, contexts/container IDs/retained roots/generations/length/hash, отсутствие конфликтующих extra native children и invalid peers. `openProtectedCustodyReaders` проверяет **refs**, но сам не достраивает недостающие unbound output refs: необходима указанная private verified discovery/closure, не один вызов существующего group reader.

Все отказы до preflight completion не пишут. При memory/jobs/pins shortage — сохранённый отказ с точной ошибкой, без увеличения лимитов/нового pool. Streaming/decoder не должны одновременно удерживать лишнюю полную группу клонов: известный cap32 сохраняется.

### 4. Только package-state publish, затем реальный sealed inspector

Из реальных tree descriptors/хешей и проверенных metadata indices собрать **private** refs в существующем writer State. `sealAudio(role,false)` (`V5.cpp:504–534`) уже умеет получить sealed reference из retained readonly snapshot и stream hash **без checkpoint**, writer не нужен. Для metadata не вызывать `sealMetadata/commitMetadata`: existing generation/length/hash берутся из actual validated pair и bound/checked bytes. Прежние metadata bytes/index generations остаются нетронутыми.

Existing `commitState(sealedDegraded,reason)` + `ProtectedCustodyRecordingPackage::commitImpl` (`Metadata.cpp:1943–2014`) дают generation fencing, validateRefs, package codec, настоящий rename/flush/paired readback и сохранение ambiguous truth. Before mutation свежепроверить current BOTH package generation и ранее проверенные exact roots/indices под удерживаемыми leases; cancellation до эффекта запрещает запись. Reason берётся из согласованного terminal record/manifest, не новый current-account вывод.

Не вызывать current `retainPrefix(playable=true)`: он снова запишет media/playback, manifest и recovery. Не добавлять Writer::open к media/playback/canonical. Единственный allowed effect этого completion — package-state generation+1 publication. Existing package commit после effect уже использует fresh noncancelled readback token; эту границу не ослаблять. Ambiguous не означает «не записалось» и не разрешает replay на failed lease.

После actual committed ACK отпустить временные write-only/snapshot ресурсы как existing seal boundary и вызвать **настоящий** `inspectProtected` для теперь durable sealedDegraded. Только его actual full result даёт semanticVerified/trustedPrefixRetained; не выставлять flags по preflight alone. Если поздний inspect отказал/отменён, returned error сохраняется, а cold read всё ещё может подтвердить состоявшийся seal (как456). Никакого deletion/GC/repair при ошибке.

## Native consumer — reuse без новой workflow

`NativeCapture.h:2248–2276` уже получает fresh queue/exact row, readPackage и для capturing/finalizing вызывает private `prepareRecovery`; `1717–1754 inspectRecovery` завершает writer на existing executor. Acquisition остаётся на storage owner thread, BOTH hashes/AAC и final seal — на existing recovery executor. На storage thread нельзя перенести полную проверку outputs ради удобного factory.

`inspectRecovery` не превращает результат writer branch в recoveryProof и не публикует очередь. Это **сохранить**: даже после положительного P2 package остаётся degraded, исходная quarantine/owner reservation не меняется, HTTP/normal promotion нет. Existing post-B display проверяет package заново и применяет original-owner/deletion gates. Start/Stop, cancellation token, commandReconciliation/purge actual drain и proof/writer retirement before recoveryDone не должны получать новую ветку ожидания/dispatcher. Не задерживать финализатор другой записи за UI ACK данного completion.

## Конкретные blockers против слишком короткой реализации

1. Снятие `unusedPackageRole`/новые random containers или generic Writer reopen не продолжат existing outputs безопасно и могут разрушить provenance. Нужна private discovered-and-verified readonly adoption существующих containers.
2. Prefix/parsed root/manifest JSON либо caller-provided refs не являются завершённым доказательством. Existing inspector guards не поддерживают finalizing preflight; нужен узкий common semantic reuse без fake sealed pair.
3. Existing finalizing package **не содержит final output refs**. Просто сменить phase, взять текущие refs или вызвать retainPrefix заново недостаточно. Нужно privately сформировать полные5 refs из genuine retained closures и сделать настоящий package commit.
4. Unknown orphan/partial/singleton/invalid peer не имеют этой однозначной terminal chain. Не обещать их продолжение в этом первом положительном подшаге и не маскировать их отказом complete all P2.

## Что следует явно записать в scoped plan перед quality gate

Один положительный layout: bound degraded-artifact manifest + intact existing media/playback BOTH + exact matching recovery + valid finalizing BOTH package/history. Private container discovery на same handle; preflight без записи; только package-state effect; actual final full inspection; Native no queue/normal authority. Различить этот завершённый terminal record и unknown orphan, а также сохранить old unused-output branch и остальные started-layout refusals. Это construction внутри прежней T116, **но current B план прямо оставляет started continuation открытым**: необходим запланированный main scoped append и независимый quality/analyze review до source edits, не молчаливое расширение старого GO.

Минимальное положительное доказательство позже — fresh cold continuation именно actual before-final-seal layout с generation+1, неизменными canonical/media/playback/manifest/recovery и всеми IDs, cold full AAC/историей и no queue change; повторный cold recover уже sealed не переписывает outputs. Это описание результата конструкции, не новая программа negative tests и не выполненный runtime.

Итог research: нет необходимости нового persistent формата/authority/account decision. Есть три конкретных missing private звена — existing completed-layout acquisition/container discovery, full phase-aware semantic preflight и package-only seal continuation. Рекомендован первый положительный narrow completion вместо общего механизма resume/repair произвольных output. P2/T116 remain open, runtime GO не выдан. Frozen456/report456 не изменены.
