# Round273 — REQUIREMENTS gate: own MigrationPair с direct Birth

Дата: 2026-10-07. Reviewer-owned, 0 checkbox, high-risk-product, existing T116 / #7444.

## Решение и предел результата

**SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** для конкретного предложения
`ProtectedCustodyMigrationPair::read(root, own, transaction, subject, directory, cancellation)`
в существующих `ProtectedCustodyMetadata.h/.cpp`, с проверками в существующем
`ProtectedCustodyFilesTests`. Допуск позволяет RED/реализацию только указанной
границы. Это не SOURCE GO, не пройденные тесты и не завершение T116.

Результат — genuine удерживаемая readonly пара собственных intent-слотов,
их согласованность и содержательная связь обоих с direct immutable Birth.
Он НЕ является startup recovery proof, matching bootstrap/queue authority,
допуском эффектов, восстановлением retained media roots или разрешением GC.
Он не доказывает отсутствие/conflict-free состояние tombstone. Если direct
block отсутствует, результат — отказ даже при наличии standalone tombstone.
Будущий resolver обязан проверить standalone источник и все конфликтующие
копии ДО recovery authority/GC/effects. Такое ограничение не меняет §8.1.

## Identity, сохранение и качество требований

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`; HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.

До создания этого отчёта: 143 Markdown в checklists, все 143 byte-identical
инвентарю после SOURCE272. Sorted basename<TAB>SHA256<LF> inventory:
`cb36b748746d8df7e1aa1ba9e726d40bb85115f720fa55ef0a1da52fe0e45fbe`.
10 текущих нормативных документов и 133 прочих/исторических документа —
разные категории; прошлые unchecked текстовые итоги не становятся новой нормой.

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

Markers не изменены; они принимают качество требований, не реализацию.
Ранее полностью прочитанные constitution/guidance/feature context переиспользованы;
identity и hashes обновлены, релевантные нормы и источники перечитаны.
Применены `speckit-checklist` и `speckit-analyze`, полные инструкции доступны
и прочитаны. Взамен генерации новых checklist markers создан только этот
разрешённый 0-checkbox report. Большая validation-история не перечитывалась
и не подменяла текущие нормы.

Prerequisites с поддерживаемыми `--json --require-tasks --include-tasks`
и `--json --template checklist-template` подтвердили активную Feature200.
Spec/plan/tasks существуют. Установленный скрипт не поддерживает
`--require-spec` из навыка; инструмент не изменялся.
Tasks: 120 всего / 93 checked / 27 open, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
T116 — существующий CRITICAL owner; новая задача не нужна.
#7444 OPEN/canonical ownership — сообщённая свежая проверка main,
не самостоятельно выполненный reviewer GitHub audit.
Hooks before/after analyze/checklist/implement: каждый зарегистрирован1,
enabled0, dispatched0. YAML разобран; hooks/commit не выполнялись.

## Нормативная трассируемость и scoped analyze

| Норма / исходник | Принятые требования |
| --- | --- |
| Constitution III/IV/VI; spec FR-012/013/014/022, SC-003/005/006 | Защищённые данные, честные ограничения, отсутствие fallback/эффектов; independent high-risk gate |
| Base custody:155–172 | BOTH metadata slots до выбора; singleton/invalid peer блокирует; g1 tie только при одинаковом decoded index; post-g1 placement и largest validated generation |
| Base custody:415–434,481–518 | Независимые own/tuple; ≤64KiB; strict schema/fields/types; полные anchor/sources, destination receipt и barrier |
| Base custody:520–545 | Прямой Birth position0/ref-generation1/version exact; связь с current; standalone tombstone/conflicts обязательны для последующего recovery, не доказаны Pair |
| Base custody:364–370,547–559 | Stage порядок без вывода IO по JSON; sticky authorization; actual absence/fresh permissions не выведены из complete |
| Packed custody §6.1:297–347 | v1/v2 exact schemas; representation/container immutable; sealed stamps структурные, full closure/retained roots до GC отдельны |
| Data-model:533–578; plan:1565–1597; quickstart:509–532 | Whole logical receipts, versioned metadata, budgets/roots и отдельные integration/installed gates |
| Tasks:568–570 | T116 prerequisite; T117 recovery/transition и T118 acceptance остаются открыты |
| Files.cpp:538–636; Metadata.cpp:46–103,397–437,580–643,733–801 | Реальный BOTH validator, strict codecs/Birth, существующий retained readonly pair pattern; новый сканер не нужен |

Не выявлены противоречие constitution, новая неподдержанная schema,
непокрытое требование этой границы или блокирующая C/H ambiguity.
Это scoped analyze, не общий анализ полноты приложения.
Предварительные вопросы stage/tombstone разрешены конкретными границами ниже,
без нового product decision и без изменения норм.

## Принятая точная граница

1. **Вход/местонахождение.** Worker-only synchronous read. Own.role строго
   migrationIntent; context/transaction/subject/directory задаются независимо,
   не читаются как ожидания из JSON. Queue directory пустой, package — точная
   допустимая identity. Существующий Files.open выбирает fixed root/package
   migration-intent location и проверяет native IDs/ACL/confinement; ничего
   не создаётся, не сканируется произвольно и не ремонтируется.
2. **BOTH.** Reuse readValidatedMetadataPair, каждый payload положительный
   ≤65536, один DATA entry, exact native read/open и собственная index generation.
   Строгий readCustodyMigration v1/v2; никакого ZERO/default/rollback/peer skip.
   Равный g1 допускается существующим validator. Не добавляется требование
   соседних generation: flat metadata validator его не задаёт.
3. **Immutable correlation.** Schema/context/transaction/subject/directory,
   весь anchor и sourceCount/set неизменны. Sources сопоставляются по kind:
   origin length/SHA, destination ID, representation/reserved container.
   Порядок массива не значим; union/subset совпадение недостаточно.
4. **Stages/receipts.** При разных generation newer.stage≥older.stage;
   same-stage разрешён. Stage jumps не удостоверяют выполнение промежуточных
   durable действий; Pair не принимает switch/cleanup. Если copied destination
   receipt уже присутствует, generation/length/SHA и packed extent/root
   остаются exact идентичными. Prepared→copied добавляет поля по прежнему codec.
   Historical queue receipt не сравнивается с current mutable queue snapshot.
5. **Sticky facts.** Если у older barrier/auth non-null, у newer они не могут
   исчезнуть либо изменить любое поле. Null→valid non-null разрешён там, где
   существующий per-slot codec допускает; copied_verified не получает нового
   обязательного barrier, ранний valid auth не запрещается произвольной политикой.
   g1 prepared остаётся со своими null полями.
6. **Birth обоих слотов.** Для каждого non-null barrier — direct exact
   readMigrationBirthEnvelope(blockVersion,envelopeBytes), затем существующий
   readCustodyMigrationBirth с authenticated own slot. Ref-generation1 не
   приравнивается к blockVersion; g1 index может отсутствовать при current g3/g4.
   Size/cipherSHA/native context/header/g1 schema/tuple/anchor/source invariants
   проверяются полностью. Общий tiny immutable-comparison helper допустим:
   одна и та же логика для Birth и Pair, без generic framework/нового parser.
7. **Владение и отказ.** Private constructor, readonly exclusive Files и Pin
   удерживаются до последнего владельца; NativeJob через фактическую составную
   операцию. Object/controlblock/owned storage используют существующий charged
   CustodyAllocator, quotas64MiB/pins32/jobs4 не расширяются. Potentially throwing
   Debug proxy construction/move выполняется безопасно до переноса lease/pin.
   Native errors и allocation/cancellation не превращаются в invalid JSON/default.
8. **Отмена/очистка.** Non-null cancellation; проверки до IO, вокруг per-slot
   native/decode/Birth шагов, до публикации и после shared_ptr materialization.
   Отмена не означает досрочное освобождение активной native операции.
   Все fixed decoded structs/временные parsed Birth values очищаются на каждом
   выходе и при уничтожении результата ДО закрытия lease/pin. No destructor IO.
9. **Публичный результат.** Только const slots/indices/current, tied to owner
   lifetime; нет Files/HANDLE/writes. Полномочия root/account/queue/bootstrap,
   normal/upload/playback/delete/GC/migration admission из него не выводятся.

## Обязательная последующая SOURCE/validation матрица

Это ещё не выполненные тесты. Main/worker выполняют их, reviewer VM не запускает.

- Настоящие native DPAPI v1/v2 × queue/package, equal g1 и разные слоты;
  queue g2 prepared+Birth вместе с g1 prepared, затем g3/g4 без g1 indices.
  Source permutations принимаются, actual immutable mismatch отвергается.
- Singleton/оба missing/invalid neighbor index или DATA; ZERO/empty/oversize/
  multiple-entry, own/context/transaction/subject/directory/generation mismatch.
- Stage regression rejected; same и forward-jump по указанной узкой семантике.
  Изменение schema/anchor/source count/kind/length/SHA/destination ID/container/
  representation; изменение/исчезновение copied receipt/extent/root.
- Barrier/auth null→present, non-null→null и каждое поле sticky fact;
  независимая ошибка direct Birth в невыбранном слоте блокирует весь результат.
  Неправильные exact version/size/SHA/native/semantic Birth.
- Missing direct отвергается и при fixture tombstone: не заявлять проверку
  standalone path или conflicting copies этим тестом.
- Null/pre/mid/Birth/late cancel; pin/job/owned quota; actual allocation cuts,
  включая MSVC Debug proxies, object/controlblock, partial cleanup и retry.
  Если final-publication cancel не отдельно injected, SOURCE честно отделяет
  ordering proof от runtime coverage; не выдумывает PASS.
- Identity lease исключает конкурирующего writer до последнего shared owner;
  все charges/jobs/pins после failure/final release возвращаются к baseline,
  writes/rename/repair/effects отсутствуют. Успех не сохраняет mutable views.
- Genuine runtime RED до code; final exact-source native Release/Debug, portable
  applicability, старые codec/Birth regressions после shared-helper extraction.
  Compile failure не называется runtime RED; quota tests не отключаются и
  assertions и Debug quota/proxy checks не ослабляются. Последующий SOURCE review отдельно.

## Что остаётся открытым

Direct-only Pair не является полноценным startup consumer. Standalone verified
tombstone и обе конфликтующие копии; matching durable bootstrap/queue/package
chain; actual destination full closures и retained roots обоих slots/barriers
до GC; fresh account/epoch/source/stamp; переходы/old-reader fence/authorized
cleanup/actual absence — последующие owner/recovery требования, НЕ выполнены
и НЕ разрешены этим результатом.

T116/T117/T118/T119/T120, H250, legacy AAC counterexample, физическая Windows x64,
UI parity, installed/auth/upload/audio/release и общая цель остаются открыты.
Проверка не запускает приложение, VM или тесты, не читает private audio/profile,
не меняет schema/spec/plan/tasks/старые отчёты/GitHub/коммиты.

## SHA-256 нормативного и исходного снимка

| Файл | SHA-256 |
| --- | --- |
| .specify/feature.json | `d4be889d623986959cc6b11beeb6227a4a33d0a1d9b2052e782db105439ba882` |
| .specify/extensions.yml | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| specs/200-windows-desktop-app/spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| specs/200-windows-desktop-app/plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| specs/200-windows-desktop-app/tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| specs/200-windows-desktop-app/data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| specs/200-windows-desktop-app/quickstart.md | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h | `28780ac32a1236d4551378621bf627dccbfe313de7ab7f05634a8f6e452c78ba` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | `40375b28dcd0d1ffccdebe6cdb514d83a20d5cc62272a96ec85b45c8938aeabb` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `c62a6bcd879a678178ff3b5da311b5434b2d618dc61648d1bb3b7ba769a6384c` |

Единственная reviewer-owned запись — этот новый отчёт. После создания выполнена
повторная проверка: предыдущие 143 files и их markers byte-identical.
