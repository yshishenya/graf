# Независимый requirements gate metadata commit worker — T116

Дата: **2026-10-03**, Europe/Istanbul.
Canonical root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Branch: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Risk/validation lane: **high-risk-product**, независимая проверка требований
внутри принятого T115/T116, не новая низкорисковая ветка разработки.

## Решение

**PASS для уточнённого последовательного full-value metadata commit worker.
112 checked / 0 unchecked; новых блокирующих пробелов требований: 0.**

Main может начинать регрессии и реализацию именно этого ограниченного слоя.
Существующие нормы достаточны; менять spec/plan/tasks/constitution/JSON schemas
или переосмысливать принятый дизайн для его начала не требуется.

Следующий последовательный шаг реализации logical writer выделен main
implementation agent, не пользователем или владельцем продукта. Пользователь
сохранил полную цель Windows; нового разрешения сократить итоговый объём не было.
Область этого промежуточного gate:

- Полного exact `CustodyBytes` значения только metadata roles: queue,
  bootstrap, package-state, migration-intent, manifest, recovery; role bound
  проверяется до копирования/выделения. Запись chunks ≤256KiB в новые
  immutable block versions, без промежуточной публикации неполного значения.
- Typed terminal result: `committed | not_committed | ambiguous`, context,
  base/target generation, error/native error. Это worker primitive, **не**
  async ticket, adoption протокол или готовый persistence-facing caller.
- Exclusive `createNew`, base=0 только для нового object; update через
  `writeExisting` и полностью verified current generation == expected base.
- Один target index при update; metadata birth — independently protected
  g1/slot0, затем g1/slot1, ACK только после проверки обеих copies/refs.
- Streamed `nextBlockVersion` с сохранением orphans и запретом overwrite/wrap;
  native disk-reserve guard с physical peak/cluster rounding.
- Result владеет actual Files lease, validated index и shared process
  `CustodyPin` до release/передачи владения. Существующий reader Pin переносится
  в общий `Memory.h`; второго независимого счётчика pins не вводится.

Не принимаются writable COM stream/SetSize/seek/rewrite/CopyTo writer, UI
ticket/adoption, JSON semantic authority, producers, ledger/state integration,
GC, migration T117, installed T118 или вся T116. `committed` здесь доказывает
байтовый commit указанного object/generation, не право upload/delete/network,
принятый queue projection или normal package. Эти различия обязательны для
публичного API и будущего обзора кода.

## Основание и свежесть

Применены canonical project-local `speckit-implement` и `speckit-analyze`:
обязательное чтение/проверка checklist gate и consistency analysis, **не**
исполнение implementation tasks. Ограничение пользователя на единственный
report имеет приоритет над шагами skills, меняющими tasks или другие файлы.
Reviewer не делегировал immediate blocker, работал локально.

Git root/branch/HEAD, `.specify/feature.json` и оба read-only prerequisites
(`--json --require-tasks --include-tasks`, `--json --paths-only`) подтверждены.
Они указывают Feature 200/high-risk-product и её текущие artifacts, несмотря
на нормализованное поле BRANCH в ответе prerequisites. Folder name не использован
как источник идентичности. HEAD не является снимком уже имеющихся dirty bytes.

Прочитаны все checklist artifacts в части критериев, заключений и применимых
оснований; все файлы целиком загружены для подсчёта маркеров и SHA-256.
Заново сверены активные spec/plan/tasks, constitution/guidance, storage contract,
data-model, research, quickstart и соответствующие contracts/parity references.
Не заявляется новая приёмка посторонних исторических UI/clock/hardware срезов.
Поэлементное основание полного storage review и его status-only дополнение
сохранены: hashes текущих норм и всех пяти checklist-файлов совпали с
`review-2026-10-02-storage-independent.md`. Во время проверки нормативный
снимок и ранее существовавшие checklist artifacts не изменились.

Рассмотрены и новые bounded codec/Files/snapshot/resources/reader reports,
включая финальное исправленное заключение reader source от 2026-10-03.
Их source approval/runtime сообщения не переносятся на новый writer. Прочитаны
локальные Files APIs, snapshot resolver, allocator и reader ownership boundary
для проверки совместимости предложенного scope; это не повторный code review.
Mac/UI/hardware исходники для этого слоя не исследовались.

Accepted plan:1376–1409 сохраняет storage analyze CRITICAL=0/HIGH=0,
порядок T116 → T117 → T118 и отдельность clock/calendar gates.
Task mapping: tasks.md:537–561; T116 связан с #7444 и остаётся unchecked.
Main в этом разговоре сообщил свежую live-проверку #7444 OPEN; reviewer сам
GitHub не запрашивал и не менял. Новый общий analyze/issue sync не заявляется.
Здесь заново проверена достаточность норм для предложенного bounded scope.
Configured before/after implement/analyze hooks отключены; никакие hooks,
commits, captures, сборки, установки или runtime tests не выполнялись.

## Checked / unchecked

До записи: **39 Markdown artifacts**, из них пять checklist-файлов и
34 reports без checkbox. После добавления этого report: 40 / 5 / 35.
Отсутствие маркеров в отчёте — не FAIL и не отдельный requirements PASS.
Исторические Request Changes сохраняют историю; позднейшее заключение и
актуальные нормативные bytes проверены отдельно.

| Checklist | Total | Checked | Unchecked | Gate |
| --- | ---: | ---: | ---: | --- |
| advanced-routing.md | 14 | 14 | 0 | PASS |
| audio-capture.md | 24 | 24 | 0 | PASS |
| requirements.md | 22 | 22 | 0 | PASS |
| security.md | 27 | 27 | 0 | PASS |
| ux.md | 25 | 25 | 0 | PASS |
| **Всего** | **112** | **112** | **0** | **PASS требований** |

Custom reviewer-owned: **90/90**; встроенный requirements: **22/22**.
Изменённых/добавленных/снятых markers: **0/0/0**. Новых неподтверждённых
requirements-quality items в этом scope нет. Незавершённая реализация ниже
перечислена текстом, а не маскируется checklist отметками.

Все прочитанные reports без checkbox:

| Артефакт | Checked / unchecked |
| --- | --- |
| analyze-2026-09-27.md | 0 / 0 — report |
| analyze-2026-09-28.md | 0 / 0 — report |
| review-2026-09-26.md | 0 / 0 — report |
| review-2026-09-27.md | 0 / 0 — report |
| review-2026-09-28.md | 0 / 0 — report |
| review-2026-09-30.md | 0 / 0 — report |
| review-2026-10-01-encryption-plan.md | 0 / 0 — report |
| review-2026-10-01-large-index.md | 0 / 0 — report |
| review-2026-10-01-medium-launch.md | 0 / 0 — report |
| review-2026-10-01-mixed-index.md | 0 / 0 — report |
| review-2026-10-01-native-playback.md | 0 / 0 — report |
| review-2026-10-01-package-followup.md | 0 / 0 — report |
| review-2026-10-01-protected-stop.md | 0 / 0 — report |
| review-2026-10-01-protected-stream-proof.md | 0 / 0 — report |
| review-2026-10-01-publish-faults.md | 0 / 0 — report |
| review-2026-10-01-release-custody.md | 0 / 0 — report |
| review-2026-10-01-resources.md | 0 / 0 — report |
| review-2026-10-01-ui-parity.md | 0 / 0 — report |
| review-2026-10-02-bounded-hash.md | 0 / 0 — report |
| review-2026-10-02-calendar-join-design.md | 0 / 0 — report |
| review-2026-10-02-custody-codec-gate.md | 0 / 0 — report |
| review-2026-10-02-custody-codec-source.md | 0 / 0 — report |
| review-2026-10-02-custody-durable-io-gate.md | 0 / 0 — report |
| review-2026-10-02-custody-files-source.md | 0 / 0 — report |
| review-2026-10-02-custody-reader-gate.md | 0 / 0 — report |
| review-2026-10-02-custody-reader-source.md | 0 / 0 — report |
| review-2026-10-02-custody-resources-gate.md | 0 / 0 — report |
| review-2026-10-02-custody-resources-source.md | 0 / 0 — report |
| review-2026-10-02-custody-snapshot-gate.md | 0 / 0 — report |
| review-2026-10-02-custody-snapshot-source.md | 0 / 0 — report |
| review-2026-10-02-native-hash-faults.md | 0 / 0 — report |
| review-2026-10-02-phase0-exit.md | 0 / 0 — report |
| review-2026-10-02-protected-custody-design.md | 0 / 0 — report |
| review-2026-10-02-storage-independent.md | 0 / 0 — report |

## Достаточные нормы и обязательные границы следующего кода

Ниже `C` = `contracts/windows-protected-local-custody.md`; это указатели на
уже принятые нормы и их применение, не новый contract.

| Область | Основание | Что обязательно для bounded primitive |
| --- | --- | --- |
| Worker-only / fixed role | C:24–34, 36–74, 185–194; spec FR-012/013/014/022 | Только fixed confined locations/IDs и шесть metadata roles. JSON не задаёт path; user-only ACL до content write. Ни IO/crypto на UI, ни plaintext AtomicFileStore/legacy fallback. |
| Exact metadata / bounds | C:76–119, 170–177, 199–201 | Manifest ≤4096B, queue ≤4MiB, остальные четыре роли ≤64KiB. Exact full value; unknown role/overflow/oversize — отказ до allocation/write. Полный queue до 16 blocks не равен 16 одновременно dirty blocks. |
| Одна mutation / base | C:123–135, 196–209 | Один writer/candidate под действующим lease. Existing metadata сначала полностью verified; expected base сравнивается с реально выбранной generation, не с caller cache/mtime. Следующий target не wrap/reset. Old base не перезаписывает новый commit. |
| Birth / update authority | C:138–154 | Base0 только exclusive new object. G1 slot0 → independently sealed slot1; оба decoded indices/все refs равны и validated до ACK. Update публикует `(targetGeneration-1)%2`, выбирается largest validated generation. Нет нового adjacency/gap threshold. |
| Immutable versions / orphan | C:123–126, 153–154, 238–246, 497–520 | CREATE_NEW; stream inventory без vector списка; occupied version не overwrite, даже если orphan не decrypts. Номер блока/version не authority и не равен обязательно generation. Overflow/exhaustion — blocked, не wrap/reuse. Orphans сохраняются; GC отсутствует. |
| Commit order / full reopen | C:128–136, 143–148, 199–204 | Все новые blocks полностью written/flushed → encrypted temporary index/flushed → atomic publish → published handle flush → full validated reopen → ACK. Physical `published` не logical `committed`. Одного `readIndex` целевого slot недостаточно: нужны оба slots и все DATA refs, exact target/context/value. |
| Cancellation / ambiguity | C:131–135, 202–223 | До начала publication cancel = not_committed, old projection retained. После начала первого publish, в том числе между двумя birth slots, завершить pair/reopen несмотря на cancel. Любой неразрешённый post-start failure = ambiguous; no next write/effects/GC до reconciliation. |
| Owned memory / dirty | C:170–177, 196–199 | Реальные capacity/copies/cipher/plain/indices/input/results charged в один process64MiB до allocation. Chunks ≤256KiB; одновременно одна dirty группа ≤4blocks/1MiB. Flush её blocks не публикует partial metadata. Native DPAPI memory отдельно, не доказанная owned quota. |
| Pins / result lifetime | C:174–177, 196–209, 276–284; data-model §12 | Reader/Clone и result используют тот же process≤32 admission. Result держит actual Files lease, validated index, pin и charged buffers до release/передачи владения. Перенос Pin не должен изменить reader limits/rollback/cancellation/Clone ownership. |
| Physical reserve | C:225–246; quickstart:420–423 | Reserve=min(10GB,10% actual disk capacity), physical incremental peak целой операции проверен до native writes. Учитывать cluster rounding, все новые blocks/temp/index coexistence и уже занятые orphan/pinned/legacy bytes. Не подменять capacity квотой пользователя, free — logical audio size. |
| Semantic authority отдельно | C:185–218, 401–453, 543–552; data-model:416–460 | Caller сохраняет JSON schema/own target generation/cross-record validation, account/admission leases, UI/result quotas. Verified bytes не означают valid queue/bootstrap/package/intent semantics. Неподключённый primitive не создаёт authority или effects и не меняет v5/v3/v2 schemas. |

Покрытие требований: FR-012 → C §§1–6; FR-013 → §§4/5/8;
FR-014 → §6 и unchanged logical bytes; FR-022 → §§5/7/8 и отсутствие effects;
SC-003 → §5 bounds; SC-005 → §§4/5/8 restart/cuts;
SC-006 → §§1–3/7 safe boundaries; SC-008 → §8 preservation.
Все восемь имеют task coverage T116–T118; этот gate не закрывает ни одно из них.
Constitution II/III/IV/VI сохранены; внутренних противоречий или новых
CRITICAL/HIGH requirements findings в указанном объёме не обнаружено.

## Конкретные подводные камни

1. **Нельзя лечить singleton.** `createNew` отказ на существующую directory
   не превращается в update/birth repair. Update не разрешён на g1 singleton,
   two missing indices при known object, invalid older slot или broken DATA
   даже при valid newer slot. Нет rollback/empty queue/автодостройки.
2. **Version allocation не recovery selection.** Streamed scan нужен только
   для свободного monotonic номера соответствующей позиции. Проверять numeric
   parse/overflow, окончания enumeration и ошибки, не собирать full inventory.
   Файл с занятым canonical именем остаётся occupied независимо от содержимого;
   неизвестные объекты сохраняются, а не становятся trusted/пустыми.
   Collision остаётся typed отказом/безопасным bounded выбором, не overwrite.
3. **Одна публикация полного значения.** Queue4MiB может обрабатываться
   последовательными dirty groups, но index получает весь финальный entry set
   только после flush всех DATA. Никаких intermediate JSON generations.
   Старые block versions нужны обоим slots и живым snapshots, включая shrink.
4. **ACK точного target.** Reopen обязан доказать именно target generation,
   length/entries/context, не просто вернуть какой-нибудь verified snapshot.
   Две g1 copies имеют равные decoded bytes, не обязаны иметь равный ciphertext.
   Родившийся slot0 без ACK не допускает effects; после publication failed
   результат нельзя называть доказанным отсутствием commit или безопасным retry.
5. **Error categories сохраняются.** Native protect/hash/allocation/ACL/IO
   failure не превращается в corruption/missing и не вызывает fallback.
   `not_committed` до publication не означает, что не осталось новых blocks/
   temp/id/directory; artifacts и исходный checkpoint сохраняются.
6. **Result — не голое число поколения.** Подтверждённый snapshot и Files lease
   живут вместе с pin/result. Передача владельцу следующего шага не равна UI
   callback; нельзя освобождать lease по timeout или разрывать его ради нового
   conflicting open. При stale account committed bytes не откатываются, но
   future UI/network continuation пока не реализован и полномочий не получает.
7. **Общий Pin, не новый лимит 32+32.** Совместные reader/Clone/result holders
   используют один admission; failed factory/result allocation возвращает pin
   и память. Move/actual release не удваивают счётчик. Сам pin без будущего
   persistent roots/GC integration не разрешает удаление block versions.
8. **Disk query — не резервирование пространства.** `GetDiskSpaceInformationW`
   возвращает HRESULT, не BOOL; geometry/overflow/query failure должны дать
   отказ, не нулевую capacity или успех. `ActualTotalAllocationUnits` задаёт
   actual capacity, `ActualAvailableAllocationUnits` — physical free, а
   `CallerAvailableAllocationUnits` отдельно ограничивает доступную запись.
   API принимает root path фактического volume, не custody subdirectory.
   Не использовать CallerTotal как процентную базу. Rounding blocks/index/temp
   вверх до cluster и арифметика peak/reserve проверяются до IO. Уже занятые
   orphans учитываются actual free, их не надо одновременно вычитать вторично.
   Не рассчитывать на освобождение старого target/GC до ACK. Caller admission
   сериализует этот bounded шаг; query не защищает от внешнего расхода диска,
   поэтому actual write/flush failure всё равно terminal/ambiguous по фазе.

API fact-check сделан по официальным страницам Microsoft для
`GetDiskSpaceInformationW` и `DISK_SPACE_INFORMATION`: HRESULT и раздельные
Actual/Caller units/geometry подтверждены. Указанный минимум Windows10 build
17763 укладывается в FR-001 Windows10 22H2/build19045. Это не runtime proof
доступности API в каждой редакции и не разрешение ослабить support matrix.
Источник: `https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdiskspaceinformationw`
и `https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-disk_space_information`.

## Проверки следующего implementation шага

Использовать существующие synthetic Windows Core/Contract/fault-test пути,
не захват устройств/реальный inventory. Минимальное содержательное покрытие:

- Exact role caps, один полный256KiB block+tail и queue из нескольких dirty
  groups: читается только полный target, без промежуточного JSON ACK.
- Birth g1 pair; cancellation до publication и между birth slots; update g2;
  lost slot1 после ACK g2/delete-intent и partial birth после restart — blocked.
- Expected-base mismatch, occupied orphan versions, enumeration/parse failure,
  version/generation exhaustion: no overwrite/wrap/new authority.
- Native write/flush/publish/reopen cuts: correct committed/not_committed/
  ambiguous и sticky отказ следующей записи, artifacts/checkpoint retained.
- Реальные charged allocations и result lifetime при budget/pin exhaustion;
  совместные reader/Clone/commit results ограничены единым32, release/move и
  failed allocation не оставляют charge/pin и не снимают чужое владение.
- Reserve arithmetic/cluster rounding, exact-threshold/under-threshold,
  actual-vs-caller quota, query failure и actual disk-write failure без
  логирования content/private paths. Не объявлять mocked arithmetic power-loss proof.

Это план обязательной проверки main после кода, а не выполненные reviewer
тесты. Последующий source review, focused native checks и полный protected
pipeline остаются обязательными. Writable stream, producers/ledger/state,
async ticket/adoption, GC roots, T117/T118, Windows общая/аппаратная приёмка,
install/update/rollback и release gates остаются открытыми.

## Хеши текущего локального снимка

Пути от feature directory, если явно не обозначен root. Это SHA-256 dirty
локальных bytes, **не** SHA committed tree, сборки, installed EXE или runtime.

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f` |
| plan.md | `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc` |
| tasks.md | `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287` |
| contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |
| data-model.md | `b494c57fa6cff34c0128d674677f5fca09e647aabbf60aea15c2a53603c43848` |
| quickstart.md | `9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59` |
| root .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| root AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| security.md | `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9` |
| ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| review-2026-10-02-storage-independent.md | `4d6a6c32a6513f7a4ab796490ab6cfb173d1faaa3cca0bca7142bd64e4d90d94` |

## Границы изменения reviewer

Создан только этот отдельный report через apply_patch. Existing checklist
markers/отчёты, нормы, tasks, код, Git state и чужие dirty/untracked изменения
не редактировались и не отменялись. Никаких issues/PR/commit/push, записи звука,
установки, миграции, GC или выпуска. Допуск относится только к названному
worker primitive при сохранении перечисленных уже действующих норм.
