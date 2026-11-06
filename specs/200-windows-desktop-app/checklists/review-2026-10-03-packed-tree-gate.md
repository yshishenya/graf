# Независимый requirements-quality gate: packed tree / cold closure

Дата: 2026-10-03. Reviewer: текущий независимый sidecar, навык `code-reviewer` прочитан лично. Проверка требований, не проверка ещё не написанной реализации.

## Решение и точная граница

**Scoped APPROVED: unresolved CRITICAL=0, HIGH=0.** Блокирующее уточнение spec для указанного ниже этапа не требуется. Допустимо начать его RED-тесты и реализацию внутри открытой T116; полный T116 не принят и не сокращён.

Основание: spec FR-012 и уточнение 2026-10-03; plan «Поправка масштабирования хранения — 2026-10-03», dependency order Steps 2–3; tasks T115–T118; packed contract §§2–6; quickstart §14. Отдельная реализация семантики и полной проверки — предпосылка persistent-tree update, не альтернативный lifecycle и не замена всех обязанностей Step 3.

Последнее уточнение main в текущем чате сужает первоначальное поручение:

- Принимается качество требований для descriptor/node semantics, полного streaming cold verify **обеих текущих HEAD snapshots**, ограниченного readonly чтения blocks и закрытого readonly RAM proof с pin, привязанного к тому же непрерывному Owner. Это не normal app admission.
- Допустим private stack scope в существующем Owner, доступный Tree friend: единственный заранее admitted NativeJob, retained strong owner и unique_lock State mutex удерживаются через весь cold verify/DPAPI, typed sticky reject и выдачу результата. Tree заимствует этот job без второго admission; public physical calls не interleave с операцией. Закрытая factory выдаёт readonly proof только после обеих current HEAD и полного DFS.
- **Исторические protected retained roots в этом этапе не принимаются.** Их strict metadata restoration, аутентифицированное происхождение stamps, интеграция и полный обход остаются обязательным последующим этапом по §6.1. Raw descriptor/root-ref либо публичная структура stamp не дают historical authority.
- Не принимаются writer/structural delta transition, logical commit/ACK, adoption, package.v2/migration.v2 integration, GC, миграция пользовательских записей, приложение, sustained capture, физическая x64/audio/installed/release acceptance.

Сужение допустимо именно как неполная предпосылка: proof текущей пары не означает восстановление всех persistent retainers. До последующего восстановления/проверки roots из обоих metadata slots/barriers запрещено считать всю цепочку восстановленной или разрешать на этом основании GC и обычные эффекты приложения. Нормативное обязательство §6.1 не снято.

## Прочитанные источники и качество требований

Лично прочитаны AGENTS и индекс guidance; применимые `codex-worktrees`, `spec-kit-flow`, `product-gates`, раздел Validation Lanes в `release-and-validation`; действующие принципы/управление constitution; относящиеся к локальному хранению положения PRD и границы evidence в current-product-status. Пять нормативных checklists прочитаны, включая их актуальные примечания. Packed contract прочитан целиком. В больших spec/plan/tasks прочитаны текущие требования/уточнения и порядок storage-среза, FR-012/013/014/022, применимые SC и T115–T118; data-model §§12–13, quickstart §14 и strict metadata codec базового контракта §8.1. Исторические отчёты/все прошлые раунды plan не использованы как заместитель текущей нормы.

Существующие Owner/format/codec API просмотрены для проверки границы будущей реализации, не для повторного полного source audit. Нынешний `readCiphertext()` держит mutex только на одну операцию; `appendPosition()` возвращает выровненное значение. Эти API сами по себе не устанавливают cold closure, protected stamp provenance или logical authority.

| Нормативный checklist | Checked | Unchecked |
| --- | ---: | ---: |
| requirements | 22 | 0 |
| audio-capture | 24 | 0 |
| advanced-routing | 14 | 0 |
| security | 27 | 0 |
| ux | 25 | 0 |
| **Итого** | **112** | **0** |

Markers не изменены: оснований ухудшать оценку качества сформулированных требований не найдено. **112/0 — требования, не implementation PASS.** tasks: **93 checked / 26 unchecked**; T116/T117/T118 остаются unchecked. Прежняя проверка physical Owner и сообщённые main результаты 40 native/38 portable/VS не принимают будущее дерево.

## Обязательные границы реализации и её будущей проверки

### 1. Замкнутая операция Owner, а не набор отдельных чтений

§2 требует непрерывный actual owner и proof, привязанный к epoch/native identity/container/exact root. §5 требует полную проверку перед normal admission; §1/§4 запрещают скрывать наблюдённую ошибку. Поэтому общая critical section должна охватывать чтение пары, exact actual EOF, обход, финальную проверку confinement/identity/fault и установление proof/результата.

Предложенный main private scope соответствует этой границе при следующих проверяемых условиях:

- Tree обращается к внутренним операциям под уже удержанным State mutex; не вызывает заново lock-taking public methods и не получает второй NativeJob на каждый child read. Заимствование не создаёт копию учётного токена и не освобождает его до actual completion.
- Strong owner/учёт job/буферы удерживаются до классификации исключения и latch; исключение не разматывает guard перед попыткой установить failure. Exact первый error/nativeError сохраняется, дальнейший cache/proof не скрывает fault. Revoke не сбрасывает fault и не даёт новой write authority.
- Проверка использует retained native handles и context существующего confined Owner. Не появляются второй backend, reopen, публичный HANDLE, arbitrary writeAt или обход исходных identity/ACL/ancestor/stream checks.
- Все public raw physical writers/publishers исключены из окна проверки тем же State mutex. Future writer должен соблюдать тот же протокол; отдельный caller mutex/обещание «один writer» не заменяет его.

Конкретный отрицательный сценарий для теста: после последнего child read, но до выдачи proof конкурентный `publishHead()` либо операция, получившая sticky fault, меняет состояние owner. Только per-read mutex и совпавший epoch не доказывают актуальную проверенную пару и не разрешают normal proof. Новый scope должен исключать это окно, а при фактическом fault — не выдавать proof.

Это следствие уже принятых норм, не новый C/H и не утверждение о готовом scope API. Возврат к схеме отдельных public reads потребует повторного review её доказательства согласованности.

### 2. Exact semantics и actual EOF

Descriptor128: generation>0, length≤64GiB, block262144, count=ceil(length/block), radix64/depth3, flags/reserved zero; HEAD version равен generation. Root — NODE_L2/base0; EMPTY разрешён только для length0, ZERO не заменяет root. Exact typed context/slot/role/IDs проверяется, неизвестное не нормализуется.

Нужен **actual EOF из `State::size()`**, под тем же guard. `appendPosition()` округляет вверх и не годится как верхняя граница доказанной сохранности: конец ref/extent может оказаться в ещё отсутствующем выравнивающем хвосте. Проверять committed extent относительно actual EOF и каждый non-inline ref относительно descriptor extent, точного envelope size, разрешённого offset/alignment/version/ожидаемого kind/selector. Child-before-parent применяется к append records; root ограничен extent, не физическим offset фиксированной HEAD cell.

NODE_L2/L1/L0 содержат ровно 64 Ref64. Уровень и base selector выводятся из проверенного пути; нельзя доверять self-described child context. Forward refs/cycles, неправильный level/base, overflow и неканонические EMPTY/ZERO отвергаются. EMPTY — ровно 64 нулевых bytes, ZERO — kind6 и остальные поля zero; отсутствие/ошибка DATA не превращается в ZERO. Вне EOF — предусмотренные §4 EMPTY/ZERO правила; exact tail DATA не принимается как полный block после роста. Shrink/grow не раскрывает отрезанные bytes старого root. Полный writer shrink/grow переход этим gate не принят.

### 3. SHA до DPAPI и обе closures до выбора

HEAD читается из известной fixed slot и аутентифицируется её ожидаемым typed context; descriptor fields до этого не authority. Для root и каждого non-inline child сначала сверяются **exact ciphertext envelope length/SHA из защищённого Ref**, затем DPAPI и typed context/inner checksum. DATA дополнительно проходит exact payload length/SHA. Успешный DPAPI и самосогласованный inner digest не заменяют expected parent Ref.

Обходятся обе HEAD closures, включая lower peer, до допуска результата. Equal generations разрешены только для exact identical empty g1 birth; ciphertext разных slots не обязан совпадать. Tie выбирает slot0. В остальных случаях generations соседние и соответствуют slot formula; invalid/missing/torn/nonadjacent/conflicting cell не превращается в normal highest-head fallback. Degraded prefix — отдельная базовая authority, не результат этого этапа.

Fault/hash/DPAPI/native/allocation/metadata failure не разрешают выдачу partial proof или переход к более удобной HEAD. Owner/artifacts сохраняются по исходному протоколу; retry/new acquisition не создаёт cache-only proof. Physical publication сохраняет свою существующую ambiguity boundary; cold verifier не «исправляет» частично записанные HEAD.

### 4. Bounded traversal, reads и proof provenance

Streaming DFS: stack трёх NODE levels и bounded DATA buffer. Разрешено повторно читать shared children; не вводить массив всех blocks, bitmap по размеру объекта, unlimited dedup/cache или HANDLE на record. DATA envelope≤266240B, NODE≤8192B, HEAD cell16384B; native physical chunks≤262144B. Применимы owned64MiB/cache2MiB/dirty4/pins32/jobs4 и ≤4KiB snapshot/proof stamp; учёт и admission до выделения, временные ciphertext/plaintext/native buffers не исключаются из оценки. Полная closure — O(reachable bytes), без обещания wall-time/Stop latency.

После proof establishment block read имеет bounded path≤3 nodes+1 DATA,≤284KiB envelope input и exact tail/EOF. Cache key включает exact owner/root/ref, ownership gap инвалидирует proof/cache. Cache hit не обещает fresh disk, но не скрывает уже наблюдённую ошибку. Даже огромный ZERO range не требует per-block массива; bytes за EOF не выдаются.

Proof — закрытый, не сериализуемый RAM authority, создаваемый только проверяющей операцией. Decode/структурно корректный mutable descriptor — лишь данные. Нет публичного `from-fields`, `verified=true`, копирования proof на иной owner/epoch/native identity/container/root или выпуска authority по caller stamp. Привязка должна происходить к реально удержанному owner, не к переданному caller набору ID.

Retained-root правила §6.1 проверены на согласованность: исторический root может не находиться в current HEAD pair, но это не разрешает произвольный historical descriptor. Для будущего этапа нужен strict аутентифицированный protected metadata/barrier witness обоих slots и полный обход под тем же guard. Проверка одной текущей пары, ref string, logical SHA или корректный schema field list такой witness не заменяют. Ни restoration, ни integration, ни право GC этим отчётом не приняты.

## Минимальная матрица доказательств следующего этапа

До source acceptance необходимы synthetic RED/положительные регрессии: exact descriptor/node bounds; неправильные kind/base/level/length/version/forward ref; ciphertext SHA mismatch до вызова DPAPI для root и всех трёх NODE levels/DATA; повреждённый lower peer при валидной highest HEAD; g1 tie/conflict/slot/nonadjacent pairs; exact actual EOF без округления; tail и EMPTY/ZERO; shared subtrees без растущей памяти; owner release/reacquire и forged/from-fields proof; native/hash/DPAPI/allocation fault и exact sticky error; конкурентный physical writer и сохранение job/owner при exception unwind; bounded block reads/EOF/cache faults. Все кейсы искусственные, без live audio/private inventory.

Закрытие этих тестов будет доказательством соответствующей реализации только после отдельного source review и exact-source receipts. Полный delta ACK/base→candidate, persistent retainers, pipeline budgets/account fences, migration и installed acceptance остаются следующими gates; plan/tasks не меняются.

## Идентичность проверенной нормы

Worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
SHA-256 сняты с текущих рабочих файлов, не приравнены к содержимому HEAD.

Пути ниже относительно `specs/200-windows-desktop-app/`, кроме constitution.

| Файл | SHA-256 |
| --- | --- |
| checklists/requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| checklists/audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| checklists/advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| checklists/security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| checklists/ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| tasks.md | `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98` |
| .specify/memory/constitution.md (repo-relative) | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| quickstart.md | `2a1c494eafe087b46470de527b4af024970054adcd75bb5df2e1032312bac2f3` |
| data-model.md | `ed7da763ddaa281f7cca2d05b9f4349eca9c9af5293d807008371e6e9a42c16d` |
| contracts/windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| contracts/windows-protected-local-custody.md | `5c2aad2bbcdee3b47c19df1a80574f9ab03a023f1d7ab59aef6948c1518f2509` |

API baseline, пути относительно `apps/windows/RecApp/Storage/`:

| Файл | SHA-256 |
| --- | --- |
| ProtectedPackedCustodyOwner.h | `d13e7aeb8263c7ba055c1394343d65abfec6ca9f93f875f360b53ccdc66c2d56` |
| ProtectedCustodyFiles.cpp | `fe81d4d3bc6cb7a2a076f9f9bddfdbd533ef418a8753e45739b3f52252a83476` |
| ProtectedPackedCustodyFormat.h | `a210c3331b36d8ae83ddcf3bd6af7e49c0e74fc2c2e4d1ef8bb573f6680fcc82` |
| ProtectedPackedCustodyCodec.h | `df71aee96738833815a9583590a53adff44b351dc7bbde8541d9b1e16cb664e1` |
| ProtectedCustodyMemory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |

Validation lane этого отчёта: read-only investigation + docs-only report. Reviewer не запускал build/CTest/VS/VM/device/inventory/server. Единственная запись — этот отчёт; source, normative documents/markers, tasks, constitution, чужие изменения и GitHub не изменялись.
