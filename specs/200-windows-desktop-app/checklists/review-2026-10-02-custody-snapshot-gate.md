# Независимый допуск verified snapshot/reopen — T116

Дата среза: **2026-10-02 UTC**; локальная дата Europe/Istanbul — 2026-10-03.
Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Ветка: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.

## Решение и точный объём

**PASS требований для ограниченного `readValidatedSnapshot` helper в existing
ProtectedCustodyFiles.** Можно начинать регрессии и реализацию чтения обоих
index slots, проверки всех referenced DATA и выбора проверенного snapshot.
Обязательное условие: **сохранить различие typed codec/IO failures и блокировать
native/hash/allocation/unclassified IO failure; не выдавать его за повреждённый
слот и не возвращать degraded успех посредством fallback**.

Это не source approval нового helper, не повторный аудит физического Files,
не full logical IO/commit/global quota/adapters/producers и не завершение T116.
Новый writer, первая pair publication, logical ACK, миграция и GC не реализуются
этим разрешением. Caller reservation/budget, pin и lifecycle/ownership остаются
явной границей helper; snapshot сам по себе не даёт account/delete/upload права.
Risk lane: **high-risk-product**, без ослабления обязательного Spec Kit пути.

## Свежесть и основание

Git branch/HEAD и активная feature подтверждены заново через Git,
`.specify/feature.json` и read-only prerequisites `--json --paths-only`.
Применена разрешённая владельцем повторная привязка полного поэлементного
`review-2026-10-02-storage-independent.md`, включая status-only дополнение.
Все 6 текущих feature normative hashes и 10 root/constitution/guidance/product/
pointer hashes совпали с прежним полным review. Checklist markers перечитаны
заново во всех 33 Markdown-файлах checklists: 5 checkbox-файлов, 28 отчётов без
checkbox. Пять checklist-файлов побайтово неизменны; прежнее основание 112
критериев сохраняется. Отчёт без checkbox не считается FAIL.

| Checklist | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | --- |
| requirements.md | 22 | 0 | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| audio-capture.md | 24 | 0 | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| advanced-routing.md | 14 | 0 | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| security.md | 27 | 0 | `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9` |
| ux.md | 25 | 0 | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| **Всего** | **112** | **0** | Custom **90/90**, built-in **22/22** |

Новых/снятых markers: **0/0**. Они означают качество требований, не выполненную
аппаратную или установленную приёмку. Встроенный requirements не редактировался.

Заново рассмотрены accepted contract §§3–6, действующий завершающий порядок
plan, storage task mapping и относящиеся к этому допуску правила Spec Kit.
Current spec/plan/tasks/constitution/guidance остаются теми же нормативными
байтами; повторный полный аудит истории и посторонних срезов не заявляется.
В accepted plan сохранены storage analyze CRITICAL=0/HIGH=0, отсутствие новых
storage clarification blockers и owner mapping #7443–#7446. T116 связан с #7444;
T114/T115 приняты в своём объёме, T116–T118 открыты. Новый analyze, live GitHub
query или issue sync не выполнялись: свежесть здесь привязана к неизменным
локальным документам и ранее записанному внешнему evidence, не новому live чтению.

Заключение отдельного `review-2026-10-02-custody-files-source.md` прочитано:
Approved source only, 0 blocking findings для прежнего физического Files слоя.
Round206/runtime **36/36** — отдельное сообщение владельца, не лично выполненный
опыт reviewer и не доказательство нового resolver. Actual source/proof/recovery
consumers не читались: их трассировку выполняет main. Installed untouched.

## Правила поколения, слотов и authority

1. **Проверка кандидатов до выбора.** Оба slots учитываются отдельно с exact
   slot identity/entropy и одинаковым ожидаемым store/object/role context.
   Index проходит accepted codec §3: schema, checksum, identity, generation,
   bounds/count/entry combinations. Затем проверяются **все** его DATA refs.
   Нельзя выбрать max generation после одного удачного index decode, проверить
   только выбранный index или объявить lower metadata допустимым до проверки
   второго slot и referenced blocks. Temporary/orphan — не index authority.
2. **Parity из §4.** После birth placement равен `(generation-1)%2`: odd в
   slot0, even в slot1. Специальное исключение — metadata birth g1, опубликованный
   в slot0 и независимо защищённый в slot1. G1 в slot1 не переносит это исключение
   на canonical/media. Проверяется decoded generation и настоящий slot context,
   не filename/mtime или предполагаемый последний commit.
3. **Equal generations.** Допустимо только metadata g1 birth pair с одинаковыми
   decoded index bytes после полной проверки обеих copies/refs. Ciphertext может
   отличаться из-за независимой защиты/slot entropy. Equal non-g1 и conflicting
   g1 — blocked, без выбора произвольной копии. Нельзя распространить g1 pair
   исключение на другие роли только потому, что обе копии читаются.
4. **Metadata.** Любой singleton metadata после restart, включая valid g1/slot0,
   any existing invalid/unreadable slot или referenced DATA блокирует authority
   соответствующего контекста. Нет rollback к старому ledger, автодостройки pair,
   пустой очереди или признания missing slot непринципиальным. Оба missing при
   известном inventory — blocked/no validated snapshot, не доказанный virgin root.
5. **G1 singleton canonical.** Требование двухслотового birth относится к metadata,
   не ко всем media objects. Полностью validated canonical g1 в правильном slot0
   при действительно missing slot1 не отбрасывается только как singleton metadata.
   Это доказательство bytes конкретного snapshot, не доказательство отсутствия
   потерянного более нового поколения, normal package или upload authority.
   G1 только в slot1 canonical нарушает placement; нельзя оправдать его metadata
   birth exception. Отсутствие slot1 нельзя автоматически назвать повреждением
   или выдать за подтверждённую историю восстановления.
6. **Gap между validated slots.** Contract требует выбрать наибольшую fully
   validated generation и задаёт parity; отдельного предела разницы поколений
   или обязательного `difference == 1` в нём нет. Новый gap threshold reviewer
   не вводит. Gap сам по себе не разрешает downgrade/repair, не доказывает lost
   commit или power-loss свойства; pairing/identity/content/error checks всё
   равно обязательны. Устанавливать новую adjacency/history policy надо отдельно,
   не скрывать её в данном helper.
7. **Ограниченный fallback.** Только canonical/media имеют разрешение §4 на
   полностью validated прежний snapshot с явным degraded/trusted-prefix result,
   никогда normal upload. Это не общее правило для playback, manifest, recovery
   или authority records. Нет подходящего полностью проверенного кандидата —
   нет recovery-success. Из unreadable candidate нельзя угадать его generation
   и по одному имени объявить альтернативу «последней» или «точно предыдущей».
   Byte snapshot не заменяет downstream sealed package-state/semantic authority
   validation, account fences и actual caller admission.

## DATA, ZERO, bounded reads и sticky failure

Для каждого index entry ordinal задаёт position. DATA читается по точным
position/version, pinned IDs/role, `physical_envelope_bytes`, full-block либо
exact-tail payload length; native context/header и SHA payload проверяются.
Обход — по одному bounded block, без сборки whole logical object в RAM.
Отсутствующий/усечённый/невалидный DATA не заполняется нулями. ZERO допускается
только как явная authenticated entry §3 (`flags=1, version=0, size=0`), а не
как компенсация ошибки. Происхождение SetSize/extension и semantic payload
authority не выдумываются из успешного чтения структуры.

Caller заранее резервирует index/candidate/buffer budget, удерживает snapshot
pins и lifecycle protection. Helper не объявляет доказанным весь process quota,
не выполняет UI/capture IO и не снимает чужие leases. После завершения проверки
не допускается TOCTOU-подмена: returned snapshot должен оставаться под caller
pin/ownership contract, а не разрешать позже открыть любое поколение по имени.

Ошибка DATA/index не игнорируется и не возвращает частичный verified buffer.
§§3/6 сохраняют sticky error/got0 semantics; known fault не нормализуется в
обычный snapshot success. Разрешённое media recovery отражает fault и degraded
статус явно, не очищает ошибку исходного объекта и не даёт записи/GC/effects.
**Physical published != logical ACK**: validated reopen primitive не реализует
весь ordered commit, metadata birth acknowledgment или persistence ticket.

## Typed failure gate — дополнение владельца

По сообщению main, нынешние physical `Files::readIndex/readBlock` объединяют
codec failures в `invalidContent`, включая `hashFailed/nativeFailed`. До
fallback это было общим fail-closed отказом; новый resolver **не может**
использовать такое объединение как доказательство повреждения для успешного
degraded возврата. Reviewer этот факт исходников независимо не аудировал.

Обязательные правила будущего implementation/source review:

- Сохранить и проверять typed codec failure до классификации candidate. Ошибка
  вычисления SHA — не computed digest mismatch. DPAPI/native failure — не
  доказательство известного semantic corruption. Allocation/budget failure —
  невозможность проверить, не corrupt generation. При любом таком отказе весь
  resolver blocked/unavailable; нельзя подавить его из-за другого valid slot.
- Missing — только подтверждённое отсутствие ожидаемого slot/DATA в проверенном
  контексте. Unknown IO, access/read error, недоступный root/storage и нарушение
  confinement не missing и не подтверждённый invalid-content candidate.
- В media fallback может участвовать лишь отдельно установленная artifact
  invalidity при работающей проверке и полностью validated альтернативе;
  инфраструктурная/неопределённая ошибка не становится этим разрешением.
  Неизвестный reason классифицируется консервативно blocked, не recovery-success.
- Contract не задаёт полный Win32/DPAPI error-code triage или разрешение
  автоматически исправлять инфраструктуру. Это **не предоставленное** полномочие,
  а не повод придумать recovery. Сохранение typed reason и консервативный отказ
  достаточны для данного ограниченного helper; точные enum/API имена не
  вводятся reviewer как новый wire/authority contract.

При сохранении старого flattening без явного infrastructure guard принятие
resolver/fallback по исходникам должно получить **STOP**. Это конкретное
условие проверки реализации, не blocker начать согласованные регрессии и
исправление распространения ошибок в existing Files. PASS требований не
утверждает, что этот guard уже реализован.

## Точные SHA-256 нормативных байтов

Пути относительно `specs/200-windows-desktop-app`, кроме обозначенных root.

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f` |
| plan.md | `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc` |
| tasks.md | `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287` |
| contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |
| Contract от `## 1.` до EOF | `fc831b083699fb7e96f17cb642ad9a50b79d68bb2130fff69d4e2500b3151c6b` |
| data-model.md | `b494c57fa6cff34c0128d674677f5fca09e647aabbf60aea15c2a53603c43848` |
| quickstart.md | `9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59` |
| Root .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| Root AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |

Единственная запись reviewer — этот новый отчёт. Код/spec/plan/tasks,
checklist markers, прежние отчёты и чужие изменения сохранены. Нет test/build/
VM, GitHub/external writes, commit, migration или install. Physical/audio/
clock/calendar и installed/full-storage/release gates остаются отдельными
открытыми условиями, не новой зависимостью разработки принятого storage-среза.
