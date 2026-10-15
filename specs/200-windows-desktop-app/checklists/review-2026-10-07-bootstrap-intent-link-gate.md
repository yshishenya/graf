# Round274 — REQUIREMENTS gate: bootstrap → own migration intent

Дата: 2026-10-07. Reviewer-owned, 0 checkbox. Lane: high-risk-product,
existing T116 / #7444. Это независимая проверка требований ДО RED/code.

## Решение

**SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** для последнего объединённого
предложения: `ProtectedCustodyMigrationPair::read(retainedBootstrap, cancellation)`,
БЕЗ caller `root`. Допуск ограничен связыванием genuine discovery-created
bootstrap с genuine own MigrationPair. Main может выполнять RED и реализацию
этой границы в существующих Files.h/.cpp и Metadata.h/.cpp; worker — проверки
в существующем ProtectedCustodyFilesTests. Новый parser/owner/backend/target
не требуется. Это НЕ SOURCE GO, НЕ выполненные испытания и НЕ startup admission.

Возвращаемая пара подтверждает собственные два intent-слота/direct Birth и их
связь с удерживаемым migrating bootstrap/fixed queue ID. Она НЕ подтверждает
готовность queue destination, actual logical queue snapshot, source freshness,
account/epoch, recovery completion, отсутствие/conflict-free tombstone, GC,
switch или разрешение обычных эффектов.

## Identity и неизменность

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`; HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.

Предыдущие 155 Markdown byte-identical инвентарю после supplemental SOURCE273.
Sorted basename<TAB>SHA256<LF> SHA-256 inventory до этого нового отчёта:
`6b361ff97863bc093172ec8fad83c69047860b8e963e0d5c3f850229d8a229fc`.

Из них 10 — текущие нормативные checklists, 145 — прочие/исторические отчёты.
В исторических файлах 256 checked / 10 unchecked: это не 10 новых критериев
данного gate и не переотметка прошлого. Исторические findings не объявлены
закрытыми этим решением. Все текущие нормативные пункты лично прочитаны.

| Текущий нормативный checklist | Checked | Open |
| --- | ---: | ---: |
| advanced-routing.md | 14 | 0 |
| audio-capture.md | 24 | 0 |
| calendar-launcher.md | 5 | 0 |
| calendar-operation.md | 8 | 0 |
| calendar-wire.md | 5 | 0 |
| packed-writer.md | 12 | 0 |
| privacy-pause.md | 12 | 0 |
| requirements.md | 22 | 0 |
| security.md | 27 | 0 |
| ux.md | 25 | 0 |
| Итого | 154 | 0 |

Markers означают качество требований, не готовность продукта. Они не менялись.
Tasks: 120 / 93 checked / 27 open; T116 CRITICAL остаётся открытой.
#7444 OPEN/canonical — свежая проверка main, сообщённая в запросе;
reviewer не выполнял GitHub audit или mutation. Новая задача не нужна.

Применены `speckit-checklist` и `speckit-analyze`; полные инструкции прочитаны.
Вместо генерации новых markers создан только разрешённый 0-checkbox report.
Прочитанные ранее feature/guidance нормы переиспользованы с текущей проверкой
SHA; релевантные constitution, spec/plan/tasks/model/quickstart, контракты и
реальные Files/Bootstrap/MigrationPair потоки перечитаны. Большая validation
история и все исторические отчёты подряд не перечитывались.

Prerequisites `--json --require-tasks --include-tasks` и
`--json --template checklist-template` подтверждают активную F200.
Установленный script не поддерживает `--require-spec`; существование spec
проверено непосредственно, script не менялся.
Реестр YAML: before/after checklist/analyze/implement — каждый registered1,
enabled0; dispatched0. Hooks, commit, GitHub и VM не запускались.

## Нормативная трассируемость и scoped analyze

| Источник | Требование этой границы |
| --- | --- |
| Constitution II/IV/VI; guidance spec-kit-flow и product-gates | Native storage, правдивые пределы результата, independent high-risk gate; не выдавать retained metadata за эффекты |
| Spec FR-012/013/014/022; tasks:568–570 | Сохранность ciphertext, no empty/default queue, прежние logical codecs и owner T116; T117/T118 отдельно |
| Base custody §2:43–79 | Confined root/actual handles, exact16B store/object IDs, fixed bootstrap/queue/root/package intent locations, без JSON path |
| Base §4:155–172 | BOTH physical validation/selection; invalid peer/singleton блокирует, g1 equality по существующему validator |
| Base §7:293–317 | Current account/epoch/source fences нужны до эффектов; данная пара их не заменяет |
| Base §8:328–362 | Reserved queue без indices — допустимый закрывающий prepared fence; invalid/mismatching records не дают legacy/empty/effects |
| Base §8.1:415–464,481–559 | Strict own/tuple/schema, fixed queue ID, per-slot generation, immutable receipts/barrier/Birth; этапная authority отдельно |
| Packed §6.1:295–364 | Migration v1/v2, packed representation/stamp сохраняются; structural stamps не full closure/retained-root authority |
| Model:533–578; plan:1565–1597; quickstart:509–532 | Single lifecycle, versioned metadata, bounded storage и будущая полная native/installed приёмка |
| Files.cpp:257–350; Files.h:108–120 | Уже существующие private discovery/openImpl и exclusive IDs; допустимо узкое расширение role/package и private trustedRoot accessor |
| Metadata.cpp:469–568,679–779; Metadata.h:73–153 | Один existing BOTH MigrationPair алгоритм и реальный immutable bootstrap с retained queueLease; не второй scanner |

Проверены полнота входов, согласованность schema/location/stages, измеримость
отказов, зависимости и покрытие задачей. Не найдено constitution violation,
C/H ambiguity или требование нового product decision внутри этой границы.
Общий analyze приложения этим решением не принят: открытые integration/AAC/
H250 findings остаются вне области и не превращаются в C/H0 всего T116.

## Принятая закрытая форма

1. **Вход и root binding.** Только genuine shared const BootstrapPair и non-null
   shared cancellation. Обязателен его retained discovery queueLease; старый
   explicit-context bootstrap без неё — invalidInput. Корень берётся как const
   reference из trustedRoot уже удерживаемого Files через PRIVATE friend-only
   accessor. Никакого публичного root/HANDLE/getter и caller root argument.
   Parent удерживается во время всего открытия и до последнего intent owner:
   rootA bootstrap нельзя сочетать с rootB, даже если IDs побайтно одинаковы.
2. **Tuple и mode.** Selected bootstrap строго migrating; protected selected
   отвергается, даже если другой slot migrating. Transaction/subject/directory
   задаются только authenticated selected value. Нельзя достраивать отсутствующие
   ожидания из intent. Каждый migrating bootstrap peer обязан иметь тот же tuple;
   другой transaction/subject/directory — отказ. Старый protected peer со своими
   null полями сам по себе не отвергается: это не вывод completed transition.
   Queue object ID обоих bootstrap slots уже exact fixed queue ID по codec.
3. **Private native discovery.** Допускается только прежний bootstrap/queue и
   migrationIntent с queue empty directory либо валидированной package identity.
   Используется тот же openImpl/ACL/reparse/hardlink/exact16 ID путь, без create/
   scan/repair/regenerate. Own intent context получается из открытых native IDs,
   не JSON. Store ID intent совпадает с retained bootstrap store.
   Discover остаётся readonly-exclusive: writable=false при сохранённых handles;
   sticky failed/blockWrites semantics не ослабляются.
4. **Один validator и непрерывная lease.** Новый overload не вызывает старый
   публичный root-read с повторным открытием. Общая внутренняя граница принимает
   уже discovered lease и повторно использует единственный BOTH алгоритм.
   Обе payload closures, strict v1/v2 decode с их index generations, progression/
   immutable sources/full anchor/sticky receipts/barrier/auth и direct Birth
   обоих слотов остаются как в accepted Round273. ≤64KiB/single DATA, no ZERO/
   singleton/invalid peer skip. Discovery lease закрывается только после cleanup
   либо последнего результата, не между discovery и semantic decode.
5. **Fixed queue linkage.** Для queue единственный ledger source destination ID
   каждого intent slot равен independently held fixed queue id.bin. Для package
   anchor.objectId каждого slot равен этому ID. Не подменять это сравнением
   intent.objectId с queue ID: это разные physical roles. Не утверждать проверку
   actual queue anchor generation/hash, destination length/hash/roots или copy
   success. Если equality выводится через existing immutable correlation, SOURCE
   должен проверить, что она действительно покрывает оба slots.
6. **Prepared reservation.** Matching prepared queue + reserved fixed ID без
   queue indices допускается как связанная own-intent пара, НЕ empty ledger и
   НЕ regular admission. Package link аналогично не доказывает обязательную
   protected queue pair до package prepared: она нужна последующему owner.
   Нельзя использовать этот узкий успех для обхода этапной таблицы §8.
7. **Владение/отмена/ошибки.** Existing NativeJob≤4 и дополнительный Pin≤32,
   shared charged allocator/owned limit64MiB, object/controlblock и Debug proxies
   входят в бюджет без исключений. Все potentially throwing moves/constructors
   завершаются безопасно до transfer parent/lease/pin. Parent удерживается при
   отказе/controlblock throw до cleanup; результат хранит strong parent.
   Cancel до IO, после discovery/native/decode/Birth и после materialization
   shared_ptr перед return. Нет обещания прерывания синхронного native вызова.
   Fixed plaintext structs и scratch очищаются на всех выходах до release;
   destructor не выполняет IO. Exact typed native/allocation/cancel/conflict
   причины сохраняются, без empty/default/fallback/repair.
8. **Старый API и неполномочность результата.** Explicit own/root API сохраняет
   прежнюю direct-only семантику и compatibility. Новый overload не даёт
   writable Files/HANDLE, account/root-inventory/queue readiness или admission.
   Схемы/bootstrap mode/writer bytes не меняются; никаких load/persist/sweep/
   recover/network/purge/AppMain activation в этом срезе.

## Требуемая последующая SOURCE/validation матрица

Это будущие проверки, НЕ текущие PASS. Reviewer VM/тесты не выполнял.

- Generated native v1/v2 × queue/package; оба g1, разные valid generations,
  same/forward stages по существующему Pair, reordered sources; direct Birth
  обоих слотов и regression старого explicit own API.
- Selected migrating + matching migrating peer; старый protected peer + новый
  migrating; selected protected с migrating peer DENY; differing migrating
  tuple, null/explicit-only bootstrap и wrong fixed queue linkage DENY.
- Queue prepared reserved ID без indices succeeds link-only; provisional/bad
  queue indices не читаются и не выдаются за queue authority. Package anchor ID
  match/mismatch отдельно от generation/hash, без fake current-queue proof.
- Wrong store/object/txn/subject/directory, invalid fixed IDs/ACL/confinement,
  singleton/invalid unselected intent index/DATA, semantic native-authenticated
  tampering, чужой direct Birth/version/size/cipherSHA, missing direct.
- RootA и rootB с одинаковыми store/object bytes, но различными payloads:
  новый overload использует только retained A; rootB path не входит в public
  call и не может заменить источник. Root path остаётся native confined, не JSON.
- Native read faults, pin/job/quota refusal, все actual allocation cuts включая
  Debug proxy/result/controlblock; pre/mid/decode/Birth/final controlblock cancel,
  baseline cleanup/fresh retry, readonly methods reject writes.
- Parent release до последнего intent owner не снимает bootstrap/queue/store/
  intent identity locks. Последний owner освобождает их и charges. Нет write,
  rename, create, repair или effect; отдельная competing worker проверка без
  same-thread mutex UB, если применяется такой seam.
- Genuine runtime RED перед code, затем exact final native Release/Debug normal
  existing target, portable applicability и shared Files/metadata consumers.
  Compiler failure не runtime RED; first/mid/last cuts не exact scanner coverage.
  SOURCE подтверждает реальные source maps/receipts/raw/EXE readback отдельно.

## Обязательное продолжение, НЕ принято этим gate

Startup consumer должен закрыть admission ДО legacy load/sweep/recover, учитывать
absent bootstrap с prepared intent, invalid peer, independently fixed IDs,
matching intent и actual queue candidate/whole snapshot. Для stage authority
нужны destinations/roots/full hashes, source/owner/currentness и account/epoch.
Protected bootstrap reconciliation cuts также обязательны: отказ этого overload
в selected protected — НЕ разрешение legacy/effects и НЕ их реализация.

Standalone verified tombstone и все конфликтующие copies, root inventory/
absence, durable switch/old-reader fence и cleanup authority остаются отдельными
owner/recovery требованиями. Отсутствующий direct Birth здесь — отказ, не GC
permission. Linked pair — следующий необходимый prerequisite, не приложение.

T116/T117/T118/T119/T120, H250, legacy AAC RED, physical x64/audio, UI parity,
installed/auth/upload/signing/release и конечная цель остаются открыты.
Новые задачи/checkbox/issue closure и разрешение commit/merge не выданы.

## SHA-256 проверенного снимка

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.h | `9bbb8305400a31dd6a5765da31f37f26bff1bc3548f5df156081e638146dde5f` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `57b3db0d930e0f134d7d8d24badcb089f03c2eaef0c993e1ae74cbeb64e2ad5b` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h | `fa5538d7e8a6e633607bd0e093e0c426afd50f6459df3e1c0ce42b6bd93e9865` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | `d971dda38d13370d55acab3b1ab474fcbbd349888b53d2c6708a6a3e87580650` |
| specs/200-windows-desktop-app/tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| .specify/feature.json | `d4be889d623986959cc6b11beeb6227a4a33d0a1d9b2052e782db105439ba882` |
| .specify/extensions.yml | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| specs/200-windows-desktop-app/spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| specs/200-windows-desktop-app/plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| specs/200-windows-desktop-app/data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| specs/200-windows-desktop-app/quickstart.md | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | `26687aebdfd2752fe915fcbbb1466dbecb9b49b681f6515bf919197d2ac1ce01` |

Единственная reviewer-owned запись — этот новый отчёт. Его создание не меняет
предыдущие 155 файлов/markers и перечисленные normative/production/test inputs.

