# Независимый gate: packed media custody, 2026-10-03

**Решение: REQUEST CHANGES — C0 / H2 / M1.** Это проверка качества проекта
wire/continuous owner/tree/proof перед соответствующей реализацией T116,
не повторная приёмка F200, миграции, установленного приложения или скорости.
Минимальные исправления H1/H2 обязательны до разрешения реализации этого среза.
M1 также требует уточнения нормативного правила удаления и повторной отметки
security CHK015; нового алгоритма GC или новой задачи для этого не требуется.

## Область и актуальность

- Канонический worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
- HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`; документы поправки не закоммичены.
- Прочитаны пять фактических reviewer-owned checklists, текущие затронутые
  spec/plan/data-model/quickstart/contracts, research §11, T115/T116 и constitution.
  Применены code-reviewer и локальные speckit-analyze/speckit-checklist;
  обязательная репозиторная guidance прочитана самим рецензентом.
- Последнее разрешение владельца на изменение времени обнаружения скрытой
  порчи принято как требование; оно не разрешает игнорировать наблюдаемую
  ошибку, собственный AES/key/nonce lifecycle или выпуск приложения.
- Дополнение §6.1 включено в этот снимок и проверено на согласованность;
  consumer adoption/migration требуют своей следующей проверки.
- GitHub #7443/#7444 OPEN, исходные bodies без comments — сведения из
  текущего read владельца, не самостоятельная connector-проверка рецензента.

## Конкретные замечания

### H1 — Live ACK не определяет ровно следующую generation

`contracts/windows-protected-packed-custody.md:160–170, 174, 183–185`.
Cold resolver требует соседнюю пару и правильные slots, но commit не требует
до записи `candidate.generation = selected_base.generation + 1`.
«Base peer descriptor» не определяет однозначно, какой из двух прежних roots
должен остаться после публикации.

Контрпример к буквальной последовательности: selected base g3 в slot0,
peer g2 в slot1; candidate g5 снова пишет slot0. Candidate readback совпадает,
другая cell совпадает с сохранённым peer g2, новые records проверены — описанные
условия live ACK выполнены. После gap cold resolver отвергает пару g5/g2.
Это несовместимость двух путей установления authority, не утверждение о баге
ещё не написанного кода.

Минимальное исправление: зафиксировать selected highest proven base;
вычислить checked `base.g + 1` и отказ при исчерпании u64 до append/head I/O;
target slot вычислять из этого значения. После readback другая cell обязана
равняться **selected base descriptor**, а не прежнему lower peer. Проверять
валидную соседнюю пару/slot rule перед ACK, с отдельным birth g1 исключением.
В требования к тестам добавить jump/stale-base/wrong-peer/overflow отказ.

### H2 — Exact Ref SHA явно проверяется только для DATA

`contracts/windows-protected-packed-custody.md:104–112, 133–139`;
`quickstart.md §14`, строка Exact wire/context; `data-model.md §13 PackedRef`.
Ref64 содержит SHA-256 exact child envelope и для NODE, но §3 перечисляет
проверку envelope SHA лишь для DATA. Проверка собственного whole-plaintext
checksum NODE не задаёт сверку с SHA ожидаемого защищённого parent/root Ref.
Quickstart требует exact envelope SHA шире, чем описанный нормативный decoder.

Минимальное исправление: до DPAPI decode/использования child refs сравнивать
exact envelope length и SHA с ожидаемым Ref для **каждого non-inline DATA и
NODE_L0/L1/L2, включая root**. Затем проверить typed context и внутренний
payload/whole-plaintext checksum. EMPTY/ZERO не имеют envelope. Проверка
должна действовать для новых readback records, base-path disk reads и cold
closure, включая retained roots из §6.1. Уже проверенный cache допустим только
по принятому exact owner/root/ref правилу, без нового обещания fresh disk.
Нужен отрицательный критерий на NODE/root envelope-ref mismatch при
самосогласованном внутреннем checksum. Это уточнение существующего поля,
не новая криптографическая схема.

### M1 — Удержание records и удаление всего container смешаны

`contracts/windows-protected-packed-custody.md:200–205, 250–253`.
Буквальное «весь container сохраняется, пока ссылается любой head/delete
snapshot» удерживает объект его собственными heads и самим delete receipt.
Следующая цепочка удаления не определяет исключение из этого правила.
Риск — вечное удержание/невозможность подтвердить локальную очистку, а не
доказанный unsafe delete или повод менять согласованный delete lifecycle.

Уточнить: отсутствие per-record reclamation/compaction защищает closure
обоих heads, retained metadata roots и pins **пока объект жив**. Whole-object
delete отдельно разрешён после durable intent, снятия внешних live retainers,
закрытия admission и actual completion/guard release. Собственные heads и
receipt, содержащий идентичность уже удаляемого объекта, не являются вечными
keep-edges. Unknown/ambiguous external references по-прежнему блокируют purge;
actual absence предшествует removed ACK. Исторические migration/delete barriers
не списываются по догадке и проверяются по своей authority.

## Что согласовано в проверенной области

- Математика wire: prefix128; cell offsets128/16512; append32896;
  framing16; typed header128; Ref64; descriptor128. NODE plaintext4224,
  HEAD plaintext256. `64^3 × 262144 = 68719476736` bytes (64GiB).
  DATA cap266240 +3 NODE caps8192 =290816 bytes (284KiB), без head cells.
  Caps — пределы приложения, не гарантия внутренних allocations/latency DPAPI.
- Закрытые роли canonical1/media2/playback3, kinds DATA/NODE/HEAD и inline
  EMPTY/ZERO; LE, reserved/padding, type/context/offset/length bounds;
  child-before-parent и committed extent не делают orphan tail authority.
- Same-HANDLE непрерывный GuardOwner, отдельные Clone cursors/pins; writer
  release не закрывает owner, живой job/retained result удерживает lifetime;
  cancel/таймер не разрешают освобождение работающей native операции.
- Наследование только exact proven base paths с bounded structural diff;
  новые DATA/NODE проверяются с диска. Cache подтверждает выдаваемую память,
  не свежесть диска; gap инвалидирует proof/cache, observed fault sticky.
- Empty birth — две independently protected identical-descriptor g1 cells;
  torn/singleton birth не достраивается в normal authority. Fixed overwrite
  не atomic; начало head I/O делает отказ ambiguous до reconciliation.
- Metadata v1 full/no-rollback сохраняется. Partial tail переписывается;
  shrink не меняет pinned root, grow выдаёт ZERO, не старые bytes. Radix depth3,
  dirty4/cache2MiB/pins32/jobs4/owned64MiB ограничивают traversal/ownership;
  числовой random read bound не обещает wall-time или sustained capture.
- §6.1: package refs = прежние6+4=10 fields; migration sources =7+4=11.
  Explicit flat_v1/packed_v2, root_ref128hex, reserved container IDs, live/
  prepared null и sealed/copied verified stamp правила согласованы с physical
  v1 metadata codec. Unknown/duplicate/schema mismatch не означает downgrade.
  Оба metadata slots/barriers удерживают даже roots вне current media heads;
  после gap их full closure обязательна до GC. Plan/data-model/quickstart
  ссылаются на точный §6.1; схема сама по себе не принимает её реализацию.
- T115 теперь `[ ]` для поправки; прежняя v1 acceptance явно историческая.
  Всего119 task IDs,92 checked/27 unchecked; T116/T117/T118 открыты.
  Создания новых задач нет. FR-012/013/014/022 и SC-003/005/006/008 имеют
  существующие design/implementation/validation owners; это не proof выполнения.

## Reviewer-owned checklist checkpoint

До этого review:112 checked/0 unchecked. После scoped review:

| Checklist | Checked | Unchecked | Изменение рецензента |
| --- | ---: | ---: | --- |
| requirements.md |22|0|Без изменений; traceability с reopened T115 сохранена |
| audio-capture.md |24|0|Без изменений, не новая audio acceptance |
| advanced-routing.md |14|0|Без изменений, вне поправки |
| security.md |25|2|CHK012 открыт H1/H2; CHK015 открыт M1 |
| ux.md |25|0|Без изменений, не новая UI/runtime acceptance |
| **Итого** |**110**|**2**|112 существующих критериев |

CHK012 уточнён: atomic rename относится к v1; packed v2 имеет non-atomic
heads и собственные requirements к generation/ref checks. CHK015 уточнён
для whole-container removal. Исторические записи и прочие отметки сохранены.
Следующий checkpoint — только исправленные H1/H2/M1 и текущие затронутые
bytes/counts; после него отдельное разрешение wire/owner/tree реализации.

## SHA-256 снимка

Пути ниже относительно `specs/200-windows-desktop-app/`, кроме constitution.

| Файл | SHA-256 |
| --- | --- |
| spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| contracts/windows-protected-local-custody.md | `5c2aad2bbcdee3b47c19df1a80574f9ab03a023f1d7ab59aef6948c1518f2509` |
| contracts/windows-protected-packed-custody.md | `477eaeb2f4f79d266752fc6f5ac349c93072363f137f95daa44d3121510fdb44` |
| data-model.md | `ed7da763ddaa281f7cca2d05b9f4349eca9c9af5293d807008371e6e9a42c16d` |
| quickstart.md | `edd8aef6e3125f56d9ba0f7853e09f6d73162dc9fb724509594a031c2e0cd504` |
| tasks.md | `7ca46d9cf375d47e89d80498b8fcf9622125508aeac82fa082703ac29e3db598` |
| checklists/research-2026-10-03-scalable-custody-proof.md | `d53306ff8554166603c98c97ecb209166a9986d6b56d9c8ff5e14c2d0d626b6d` |
| .specify/memory/constitution.md (repo root) | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| checklists/requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| checklists/audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| checklists/advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| checklists/security.md (после review) | `c8cc921f6626a6165f8089c27e590c87569b740d02cdc490062e9897c8ceaf84` |
| checklists/ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |

Security до review: `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9`.
SHA привязан к этому снимку, не переносится на последующие изменения main.

## Граница результата

Выбор минимального DPAPI packed/radix64 proof подхода соответствует
согласованной области; gate удерживают точные H1/H2/M1, не требование другой
криптографии или повторного полного аудита. Требуемые отрицательные проверки
выше — критерии будущих tests, в этом review они не запускались.
Нет build/runtime/VM/микрофона/реальных данных/performance/installed/release
claim; результаты прежнего CNG slice не принимают новый protocol.
Рецензент изменил только security checklist и этот новый отчёт; не менял
product source/spec/plan/data-model/quickstart/tasks/constitution, Git или GitHub.
Чужие текущие изменения сохранены.

## Продолжение независимой проверки — 2026-10-03: H1/H2/M1 закрыты

**Актуальный scoped вердикт: APPROVED по качеству требований,
C0 / H0 / M0.** Он заменяет REQUEST CHANGES выше только для проверенных
исправлений wire/owner/tree/proof; исходные замечания и SHA сохранены как
история. Приёмки кода, выполнения T116 или общего принятия F200 нет.

Повторная проверка ограничена исправлениями H1/H2/M1, тремя новыми критериями
quickstart §14 и свежими hash/counts. Старые source changes, остальные
исторические аудиты и реализация downstream migration повторно не проверялись.

| Замечание | Прочитанное исправление | Решение |
| --- | --- | --- |
| H1 | Packed contract:166–180: highest proven paired base; equal-g1 birth выбирает slot0; checked candidate=base+1, exhaustion/stale/non-selected/incorrect target отказ до append/head I/O; другая cell exact selected base, соседство/slots обязательны перед ACK | Закрыто: переход g3→g5 больше не удовлетворяет требованиям; g1→g2 сохраняет selected g1 в slot0 |
| H2 | Packed contract:112–118: каждый non-inline DATA/NODE_L0/L1/L2/root сверяет exact envelope length/SHA с expected protected Ref до decode/child use; далее typed context/checksum; новые readbacks/base-path disk/cold retained roots охвачены; cache только после checks по прежнему exact key | Закрыто: внутренний NODE checksum не подменяет проверку связи с Ref; fresh disk на cache hit не заявлен |
| M1 | Packed contract:210–219: records/extents удерживаются пока объект жив; whole-object delete имеет отдельную authority после durable intent/retirement внешних retainers; own heads/identity receipts не вечные keep-edges; unknown/ambiguous external refs и historical barriers продолжают проверяться; actual quiescence→absence→removed ACK | Закрыто: самоблокирующееся удержание устранено без разрешения unsafe reclaim/delete |

Quickstart:487–488,495 содержит отдельные Generation/peer, NODE/root Ref и
Whole-object delete критерии: jump/stale-base/wrong-peer/overflow refusal,
самосогласованный plaintext checksum при неверном expected envelope SHA/length,
и порядок retirement/completion/absence/ACK с отказом unknown external refs.
Это проверяемые требования к будущим отрицательным tests, не результаты их запуска.

Новых противоречий constitution или C/H в этой дельте не обнаружено.
Узкое соответствие требованиям/задачам не нарушено: H1→FR-012/T115/T116/T118;
H2→FR-012/SC-006/T115/T116/T118; M1→FR-022/T115/T116/T117/T118.
Остальные нормы, metadata §6.1 и ограничения прежнего review сохраняются;
schema/consumer/migration adoption и runtime gates этой записью не принимаются.

### Отметки и граница следующего шага

Рецензент восстановил `[X]` только у security CHK012/CHK015 после чтения
исправленного contract и quickstart. Текст критериев не изменён.
Текущие пять checklists: requirements22/0, audio-capture24/0,
advanced-routing14/0, security27/0, ux25/0 — **112 checked / 0 unchecked**.
Другие checklist bytes неизменны. T115/T116/T117/T118 всё ещё `[ ]`;
119 task IDs,92 checked/27 unchecked. T115 marker рецензент не менял.
Данный checkpoint снимает три requirements-quality замечания, но не
подменяет последующее решение основного владельца по T115 и порядку работ.

### Синтетическое свидетельство mapping — предоставлено main

По сообщению main: Windows VM, исходный .NET RW FileStream с
ReadWrite|Delete sharing; writable MemoryMappedFile view сохранён после
dispose исходного FileStream; новый RW+FileShare.Read guard отклонён.
Результат `{guard_denied:true, guard_error:0x80070020,
mapping_still_writable:true, synthetic_only:true}`, shell exit0/session28712.
Первый запуск с null mapping name не дал evidence; повторный использовал
unique Local mapping name. По сообщению main fixture удалён в finally.
**Рецензент этот тест не выполнял и его session/log отдельно не читал.**
Это узкая поддержка acquisition-guard предположения в этой конфигурации VM,
не source implementation, все native mapping варианты, ACL parity,
физическая x64 или runtime acceptance приложения. Оно не заменяло
нормативные исправления H1/H2/M1.

### Свежие SHA-256 после исправлений и reviewer marks

Канонический root и HEAD `99b00a579c24b50e320465b69d9a296038bc544d` прежние.
Пути — относительно `specs/200-windows-desktop-app/`, кроме constitution.

| Файл | Текущий SHA-256 |
| --- | --- |
| spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| contracts/windows-protected-local-custody.md | `5c2aad2bbcdee3b47c19df1a80574f9ab03a023f1d7ab59aef6948c1518f2509` |
| contracts/windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| data-model.md | `ed7da763ddaa281f7cca2d05b9f4349eca9c9af5293d807008371e6e9a42c16d` |
| quickstart.md | `2a1c494eafe087b46470de527b4af024970054adcd75bb5df2e1032312bac2f3` |
| tasks.md | `7ca46d9cf375d47e89d80498b8fcf9622125508aeac82fa082703ac29e3db598` |
| checklists/research-2026-10-03-scalable-custody-proof.md | `d53306ff8554166603c98c97ecb209166a9986d6b56d9c8ff5e14c2d0d626b6d` |
| .specify/memory/constitution.md (repo root) | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| checklists/requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| checklists/audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| checklists/advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| checklists/security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| checklists/ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |

До append SHA этого отчёта был
`73f63c8990d9ffff2dd138939f034a27f87c468e177e3b9a8ffc891a66196e20`.
Первые176 строк сохранены без изменения; свежий SHA всего отчёта выдаётся
при handoff, чтобы не создавать self-hash. В этом продолжении изменены
только две security marks и append отчёта. Нет product/norm/tasks/Git/GitHub
mutation, сборок, тестов, runtime/performance/installed/release claims.
