# Round263 — SOURCE: readonly bootstrap pair

Дата: 2026-10-06. Независимый SOURCE review, lane **high-risk-product**,
T116 / #7444. Canonical:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved.

## Финальное решение

**SCOPED SOURCE GO для `ProtectedCustodyBootstrapPair::read` на exact263c
inputs. C0/H0/M0/L0 новых неустранённых findings в данном компоненте.**
Порог: нет unresolved CRITICAL/HIGH или blocking clarification этой области.
Final Release/Debug/SDK/portable evidence и полный regression/readback учтены
ниже. Общий native прогон **НЕ GREEN:49/50**, legacy AAC RED257/B1 сохранён.
Это не application/admission GO, не закрытие T116 или разрешение выпуска.

Лично прочитаны новый private result/factory и весь новый native test block,
его fixture/fault injection и вызовы из native/portable main. Проверены
реальные Files BOTH validator, allocator/pin/job и strict bootstrap codec.
Использованы `code-reviewer` и `ponytail-review`, инструкции прочитаны полностью.
Принятый REQUIREMENTS263 gate сохранён без изменений, SHA
`eecf32cba1fc531231c10d267c0c40ea44caa6d899972c2abb02b70223259646`.
Никакие тесты/VM/native EXE самим reviewer не запускались.

## Exact source, не прошлый PASS

Текущий frozen map `source-bootstrap-pair-round263c-final.json`, 172 inputs,
SHA `4c0d678954fc2cc6717a397a44c7db624f294c03374fa94d323471f59c8724a7`:
лично JSON parsed и все172 canonical SHA сверены, mismatches0.
JSON exports с UTF-8 BOM прочитаны с удалением BOM только в памяти;
SHA включает исходный BOM. Ни exports, ни product parser не изменены.

| Current file | SHA-256 |
| --- | --- |
| Metadata.h | `7c5cd425b94bba971bad960cd8ee16d87627706ce5a58214e58e2fa71e75f237` |
| Metadata.cpp | `4153506b4fd768869a3f1d2323c232d59bf0ddad786dc9c3733b187afceb8397` |
| FilesTests.cpp | `4edc67b0aaf25826cff259f654289ee9cd2932c96f7507fdc3ac5664f446c707` |

Относительно принятого final262j изменены ровно эти3 inputs, остальные169
неизменны. Дополнительно in-memory удалением только нового class/factory/test
и его main calls восстановлены точные прежние SHA всех трёх файлов:
H `24716202c2a508c7f8b3582d71d7f572059e254b870fc40b4160159b4652c4e5`,
CPP `864eabe04dec416897aa7007e88870d4fc093c0406a35aba0b3502cdcad05f81`,
test `959c8ac3796e3ab87c3bc8c5eaaed4bfd8caa9d74a3c0057459edbb72e6a4bef`.
Файлы не перезаписывались. Старые codec/package/history bodies и тесты не
изменены скрытым образом. 263b map уже не current: два input SHA отличаются.

## Проверка корректности и безопасности

| Область | Actual source / результат |
| --- | --- |
| Independent identity | CPP540/550: только bootstrap role, non-null cancellation, fixed empty package argument; own context проверяет прежний Files.open. Queue ID только independent expected value strict codec, не JSON-derived path/owner. |
| BOTH и выбор | CPP554/561–575: прежний readValidatedMetadataPair проверяет обе physical copies; затем оба DATA заново читаются/decrypt/parse с generation своего индекса. Current выбирается прежним physical validator, не новым эвристическим scanner. |
| Bounds | CPP564: positive logicalLength≤65536, entries exactly1, flags DATA0; cast выполняется после ограничения. Нет empty/ZERO/oversize JSON success. Codec остаётся closed nine-field schema, без aliases/fallback. |
| Failure | Ошибки Files и codec передаются с typed cause/native code; null result при любом отказе, включая lower peer. Нет partial/default bootstrap success или fallback к plaintext. |
| Cancel | CPP545/553/562/569/572/577: pre-open, after fixed-ID compound open, around physical pair/slot IO/decrypt и before result construction. Отмена не force-frees синхронный native call; post-open ordinal1 regression требует reads==2, без последующего index scan. |
| Admission | CPP546–549: native job≤4 и pin≤32 до IO. Job локальный, удержан до actual factory cleanup; pin передаётся в результат до последней owning shared reference. No job-timeout shortcut. |
| Private lease | CPP550/578: writeExisting применяется только как native identity exclusion lease, после проверки blockWrites. H95–113: private ctor и private Files, только const slots/indices/current наружу. Нет writable handle/capability. |
| Constructor exceptions | CPP522–527: throwing indices move заканчивается, пока caller ещё владеет lease/pin; только затем noexcept transfers. Placement constructor failure deallocates raw block. Shared_ptr control-block constructor использует deleter для уже созданного raw object на allocation failure. |
| Release order | H108–111: pin объявлен раньше lease; reverse destruction закрывает actual Files прежде pin admission release. CPP528–532 очищает retained semantic values до разрушения членов. Job объявлен до native owners, освобождается после них на factory exits. |
| Memory / wipe | Object и shared control block используют CustodyAllocator; indices/cipher/plain прежние charged owners. WipeValues очищает locals на всех exits, parsed accepted value очищается после копирования; retained values очищаются destructor. Не обещается wipe каждой register/parser stack копии или включение native/path allocations в shared charge. |
| Effects | Pair доказывает только собственные BOTH bootstrap payloads под удержанной lease. Mode protected/migrating, queue ID и transaction не являются queue/account/migration/GC/upload/delete/playback authority. Worker-only usage/release заявлены, app caller adoption здесь отсутствует. |

Проверка shared_ptr exception cleanup — SOURCE reasoning по обычному
shared_ptr(raw, deleter, allocator) pattern, а не заявление о специально
выполненном control-block allocation fault. Новых runtime policy knobs нет.

## Фактическое покрытие нового test block

FilesTests1510–1640 использует настоящий existing DACL/root fixture,
DPAPI и commitProtectedCustodyMetadata, а не fabricated public Pair.

- Все3 формы bootstrap: protected, migrating queue, migrating package;
  padded exactly65536 bytes, equal g1 и subsequent actual g3/g2/g4,
  разрешённый mode switch между поколениями. Очередь намеренно отсутствует:
  это доказательство отсутствия queue authority, не успешной готовности queue.
- Identity writer exclusion при живой первой ссылке и её owning копии;
  после last reset writer open снова разрешён. IO counters/artifact inventory
  не показывают writes/rename/flush/scan в factory.
- Native read errors ordinals1..8 с ERROR_READ_FAULT; cancel ordinals1/6/7/8,
  pre-cancel без opens, typed hash/allocation faults, job4/pin32 exhaustion,
  shared memory pressure, retry и final usedBytes baseline.
- Independent expected queue mismatch, own store/object mismatch, wrong role,
  null cancellation до IO. Genuine DPAPI-authenticated malformed LOWER payload
  при здоровом higher: syntax/generation/schema/queue mismatch; missing lower
  либо higher index и lower DATA. Empty и ZERO metadata отвергаются.
- Прежние physical conflict/placement/unsafe-file и strict shape/bounds tests
  используются как регрессии общих слоёв. Новые формы не создают второй
  decoder/schema или special bootstrap exception к BOTH rules.

Честные пределы: новый block не имеет адресной инъекции allocation отказа
именно raw result/control block, не отменяет DPAPI посреди native вызова,
не представляет exhaustive bootstrap-specific higher-DATA tampering/64KiB+1
матрицу. Их нельзя подписывать как специально исполненные новые cases.
Общее pressure assertion может завершаться раньше final allocation.
Debug existing proxy regression проверяет общий throwing-move механизм,
не отдельный final BootstrapPair constructor fault. В этих местах SOURCE
cleanup/общий unchanged validator рассмотрены отдельно от runtime assertions;
конкретного дефекта нового кода не выявлено. No new product requirements.

## Лично проверенная текущая execution evidence

Readonly parsed receipts и raw logs; фактическое исполнение — main, не reviewer.
Каждый receipt source_hashes точно совпал со своим named frozen172 map.

| Run | Actual evidence |
| --- | --- |
| Genuine RED263a | configure0/build0/test8, Files result.ok assertion1535; остальные3 focused targets PASS. Не masqueraded decoder/device error. |
| Historical GREEN263b | configure0/build0/test0, focused4/4; не final guarded source. |
| Final Release263c | configure0/build0/test0, focused4/4, raw Release commands; Files23.77s. Main total25.85s, не вычислено из rounded raw durations. |
| Final Debug263d | configure0/build0/test0, focused4/4, raw Debug commands; Files32.22s. Helper лично прочитан: build config / exe_hashes folder / ctest все Debug. Main total35.38s. |
| Portable263c | Read raw log:46 commands/46 Test Passed/0failed; unsupported-platform branch не выполняет Windows factory. Build0/total23.01s предоставлены main. |
| SDK263e | Readonly parsed terminal passed receipt, restore0/build0; named179 map полностью canonical MATCH, receipt source_hashes equal. Actual app EXE SHA ниже; приложение не запускалось. |
| Full263f | Лично parsed terminal failed receipt: configure0/buildALL0/test8; source_hashes equal final172. Raw log содержит все50 Release commands,49PASS/1FAIL, только #47 NativeHashFailureTests assertion395. Main total261.96s. Не filtered4/4 и не GREEN. |
| Readback263g | Main фактически исполнил после full263f, toolchunk e56474/exit0: Release263c и Debug263d MIRROR_NTFS_SOURCE_AND_EXE_MATCH; SDK179_MIRROR_NTFS_SOURCE_AND_EXE_MATCH; ROUND263G_READONLY_EXIT=0. Reviewer лично прочитал/хешировал script и canonical maps; не выполнял VM, не утверждает личное наблюдение NTFS bytes. Отдельного stdout export нет. |

Сохранённые checksum exports (outside Git):

| Artifact | SHA-256 |
| --- | --- |
| RED263a receipt | `fcca1b47b8b468f8939695b0dc3f62bbc1815d6243baf90d6ea99ffeb720a3ef` |
| RED263a raw | `f819e1d418b7d58d0f691fb6fb534946f941f7bf287557571f79a5b7cd245f24` |
| RED263a map | `48877336b25c6dd8e8040321c4298e593fa9e5729c3ebc0ffb762a2e3c60225f` |
| Release263c receipt | `8674fd94bd4ef51fff225583d03821bf8b23f515110ced264a6476d0edebd341` |
| Release263c raw | `f6ea5e14e5653229d09e6b84fd76c4a4fe59080a3f7cea3474c3bf93ba51546b` |
| Debug263d receipt | `3d8e023594d9e49a1380bd8e65e848b72ccbe776e1176ad3a1c8b36ada6205f6` |
| Debug263d raw | `d9787a18e79d13eab44ea38c301613f74e64b2a83bbfa0ddcef03faa38498513` |
| Portable raw | `a29f08c5dd59b69a930b3ede8a722629c620dfc61677e18e5c0c6746468459f5` |
| SDK263e map179 | `8d49dcf99938dea156089548b84f3fa75f9989cc0f5bb325fde1d7adb47d5e5d` |
| SDK263e receipt | `675433ac25bcf7d38383bac9b53891b2a706b1c2038f4dc3446d9f98e5d6f684` |
| SDK263e app EXE (receipt) | `64e5c49dda6d72751f00fba9f200f1dcae879ed344f7cd8803726a0c900891bf` |
| Full263f receipt | `4308d2a4ae40815064c80a3a7b6e0d8c299c2f0e1defe579441d9dd21f701ad2` |
| Full263f raw | `78cade802bbd37d8cb6deb785495de273ef25484dfb6c40c5218ab777d694081` |
| Readback263g script | `d274abf29d9c26a9ea6854af4c7b79d35cc6e52096d5ec4d1eaae2e998167d92` |

SDK263e helper и readback263g script лично полностью прочитаны, не исполнены
reviewer. Readback использует Release для263c, Debug для263d и отдельный SDK
NTFS tree; script existence не считается actual readback PASS. Фактический
PASS принят только вместе с отдельным сообщением main об execution263g.

Полный263f helper лично прочитан: build ALL без target filter, CTest без -R;
receipt содержит EXE hashes только4 component targets, не всех50 executable
identities. Reviewer не расширяет эту запись до independent50EXE rehash.
Raw parsed/read по всем50 command/status/time records и failure output;
новых failures нет. Exact unchanged counterexample в #47:
`original_frames=48128 corrupt_decode_complete=1 corrupt_frames=0
explicit_root_normal=1 explicit_root_playback=1 default_root_normal=1
invalid_package=0 synthetic_sends=1`, assert malformed/playback395.
Это EOS с нулём decoded frames и старое ложное принятие AAC, не универсальная
decoder/HRESULT ошибка. Native process0xc0000409 и total261.96s предоставлены
main execution; raw LastTest.log лично подтверждает assertion395/FAIL/2.55s,
но сам не содержит этого process exit code или суммарного wall time.
Known RED не отключён и не заменён успешным BootstrapPair тестом.

После263f/g лично повторены canonical172/179 hashes: mismatches0, все три
current source SHA остались прежними. Main подтвердил отсутствие дальнейших
source изменений и terminal VM sessions; reviewer не проверял процессы VM.

## Ponytail и последующая интеграция

Отдельная complexity проверка: **Lean already. Ship.** Это только отсутствие
безопасных сокращений, не разрешение выпуска. Existing PackagePair ownership
pattern и strict codec reused; никаких новых dependencies/targets/controllers.
Два похожих bounded factory не оправдывают generic authority abstraction;
удаление повторного semantic BOTH parse/wipe/guards нарушило бы контракт.

Protected queue owner/pair, matching durable intent/history, fixed old-name
conflicts/tombstone-only recovery, root inventory/GC и account/epoch admission
остаются следующими реальными зависимостями. App startup/queue/writer adoption
не сделаны. Legacy RED257/B1 и прежние known49/50 не закрыты bootstrap wrapper.
Это не installed app/UI/hardware parity либо полный T116/релиз GO.

## Инвентарь и authority

До этого отчёта121 `.md`:10 normative154 checked/0open;
отдельно111 historical/context256 checked/10historical open. Старые10 unchecked
не переклассифицированы как новые требования. Current requirements gate
сохраняется, новых checkbox markers в данном SOURCE report0.

SHA sorted basename + space + SHA + LF прежних121 reports:
`571e26afaa3edc7a20b4773b210cd78839f55bd0161e6927c0efd32d633a10e2`.
Tasks120/93/27, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
T116 #7444 остаётся OPEN по main; reviewer remote tracker не запрашивал.
Registered6 hooks: before/after implement/analyze/checklist EACH1
git/speckit.git.commit enabledfalse; enabled0, dispatch0. Governance unchanged.
Reviewer writes ONLY this new report; no VM/tests/GitHub/code/task/old-report
mutations. До final update прежние121 reports побайтно unchanged; в дереве
122 `.md`, новый SOURCE report без checkbox markers. Tasks SHA и Extensions
SHA `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c`
лично перепроверены. Main append-only validation/changelog не принимаются
за изменение frozen product inputs. T116–118/119/120 и H250 остаются OPEN
по main; никакие tracker/task markers reviewer не менял.

## Итоговая граница принятия

Принят только bounded readonly consumer собственных BOTH bootstrap payloads:
genuine identity lease, strict per-slot semantics, independent expected queue
ID match, retained lifetime и fail-closed cleanup. Цель следующего реального
шага остаётся прежней: independent fixed-ID discovery/reservation, queue BOTH
semantics/owner, matching intent и actual app adoption с account/currentness.
Ни структурная mode, ни этот новый Pair не подменяют эти полномочия.
Исторические reports/нормативные criteria не переоткрывались/не закрывались.
Не выдан whole-app, installed/hardware, release или legacy-consumer GO.
