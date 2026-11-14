# Независимый requirements gate read-only reader — T116

Дата среза: 2026-10-02 UTC; локальный контекст Europe/Istanbul — 2026-10-03.
Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Branch: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.

## Решение и точный объём

**PASS требований — 112/112, новых блокирующих нормативных пробелов: 0.**
Разрешён минимальный реальный read-only protected logical IStream: actual
validated snapshot ownership/process pins, exact Read/EOF/signed Seek, Clone,
shared bounded cache, CopyTo, sticky failures и worker/context lifetime.
Сначала регрессии, затем реализация. Risk lane остаётся **high-risk-product**.

Не подключать пока producers/MF/hash/upload/playback consumers до ledger/state.
Это bounded последовательный шаг accepted T116, не full logical writer/commit,
не process/pipeline acceptance и не закрытие T116–T118. `speckit-implement`
применён как независимый requirements gate, не код/hooks/task marking.

## Свежесть и analyze/ownership

Git root/branch/HEAD, active feature pointer и prerequisites `--paths-only`
проверены заново. Шесть feature normative и десять root/constitution/guidance/
product/pointer hashes совпали с полным storage-independent review и resources
review. Его полный instruction/checklist контекст переиспользован по неизменным
байтам; перечитаны contract §§4–7, data-model §12, quickstart §12, T116 и
завершающий accepted порядок plan. Старые исторические подпункты не отменяют
актуальный отдельный storage development допуск.

Все 37 Markdown-файлов checklists до записи просканированы: пять с checkbox,
32 reports без checkbox. Маркеры пяти перечитаны, полные checklist SHA
неизменны относительно полного112item review. После отчёта ожидается38 файлов.

| Checklist | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | --- |
| advanced-routing.md | 14 | 0 | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| audio-capture.md | 24 | 0 | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| requirements.md | 22 | 0 | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| security.md | 27 | 0 | `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9` |
| ux.md | 25 | 0 | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| **Всего** | **112** | **0** | Custom **90/90**, built-in **22/22** |

Markers изменены: **0**. Reports без checkbox не FAIL; PASS требований не
означает hardware/runtime выполнение. Accepted plan сохраняет storage analyze
CRITICAL=0/HIGH=0, отсутствие storage clarification blockers, issue-sync
#7443–#7446/canon PASS и mapping T116→#7444. Эти recorded gates остаются
применимыми к тем же normative hashes; новый analyze/live GitHub не выполнен.
T116–T118 открыты. Clock T094–T096 и T119 не dependencies этого reader шага.

Прочитан allocation source report: Approved source only/0 blockers на его pins;
он отдельно не утверждает native/host runtime. Исходники allocator/Files/
snapshot не переаудированы; их новая реализация и wiring остаются main.

## Синхронный worker stream допустим

Contract §5 запрещает UI/readiness disk scans/decrypt/hash/encode/GC, WASAPI
callback IO/crypto и ожидание persistence IO внутри UI bool. Он требует existing
background workers, но **не требует отдельного async task/ticket на каждый
read-only Read/Seek/CopyTo**. Поэтому синхронный native stream, исполняемый и
сериализуемый на worker, соответствует нормам. Это не разрешение синхронно
сканировать очередь в startup/UI и не замена typed pending/committed/
not_committed/ambiguous для ledger mutations/ACK (§5).

Можно сохранить явный worker-only caller contract и последовательный доступ
к mutable cursor/shared state без нового dispatcher/scanner. Однако реальные
одновременные process admissions и lifetime accounting не могут быть unsafe:
сериализация чтения не освобождает pin/cache/reservation другого живого owner.
UI/WASAPI/синхронная readiness integration в этом этапе отсутствует.

## Обязательства минимального реального reader

1. **Authority и неизменный snapshot.** Открывать только успешно validated
   snapshot с exact store/object/role/generation/length/index entries, caller
   context и реальным удержанием ownership. Чтение не переоткрывает «последнее»
   поколение по имени/mtime и не заменяет selection из snapshot-gate. Оба slots
   и все referenced DATA validation остаются prerequisite. Degraded/trusted-
   prefix status сохраняется, не нормализуется в package/upload authority.
2. **Actual process pins/Clones≤32.** Admission до создания нового живого
   holder, отказ/rollback при неудаче создания. Shared generation root не
   оправдывает неограниченное число Clone holders. Snapshot identities/refs,
   store/context lifetime и resource ownership удерживаются до actual release
   последнего соответствующего owner/in-flight operation. Token/count без
   защищённого владения snapshot не считается реализованным pin.
3. **Actual shared plain cache≤2MiB на процесс, общий для Clone.** Не по2MiB
   на object/stream/Clone. Реально retained capacity/allocations, включая
   одновременное replacement/eviction, укладываются в cache budget и общий
   owned64MiB. Reserve до allocation, charge до actual deallocation. Clone
   не копирует cache в отдельный неучтённый буфер. Cache hit относится только
   к exact pinned identity/version/context; совпадение block position само
   по себе не допускает reuse bytes другого объекта/поколения. Конкретный
   eviction algorithm/global cache-manager architecture нормами не задан.
4. **Exact Read/EOF.** Только verified logical bytes pinned generation, exact
   DATA position/version/payload/envelope length; explicit authenticated ZERO
   читается как ZERO, missing/invalid DATA — ошибка, не zero-fill. Full/tail и
   границы blocks соблюдаются. Короткое EOF=S_FALSE, got exact; Read за EOF не
   добавляет bytes. Никакой whole-object materialization ради одного Read.
5. **Signed Seek/Clone.** Проверять signed offset/overflow и невозможный
   результат до использования; Seek/Read за EOF не создают bytes/extension.
   Clone имеет independent cursor и тот же pinned generation/shared cache,
   не live refresh текущего index и не разделённый изменяемый cursor.
6. **Bounded CopyTo.** Чтение/передача частями≤256KiB, временные buffers внутри
   owned64MiB. Ошибки source и destination не маскируются; exact transferred
   bytes не выдаются за полный success при short/error. Уже переданный prefix
   destination нельзя объявить откаченным: контракт не даёт transaction/rollback
   всей CopyTo. Это не разрешение вернуть S_OK после ошибки.
7. **Fail-closed sticky error/got0.** Native/hash/semantic/budget/allocation/
   unknown IO failures не missing/corrupt candidate/recovery-success; cache
   или alternate slot не очищает уже полученный отказ. Ошибка Read sticky/got0,
   caller не использует частичный buffer после ошибки. Не требуется выделять
   whole Read buffer для имитации атомарности. Коррупция после pin не может
   вернуть непроверенные bytes как нормальное чтение.
8. **Honest read-only surface.** Write/SetSize отказ; writer dirty groups,
   publish/commit/ACK не реализуются. Unsupported Commit/flags/locking/revert
   не получают ложный S_OK; если операция поддержана, её semantics/flags явны
   (§6). Wire codec/role classification и ошибки не меняются ради IStream.
9. **Context/lifetime.** Reader/job владеет value snapshot, cancellation,
   store/account epoch, package/state identity и pin, не raw UI/controller/
   queue reference (§7). Проверка cancellation до IO; producer-side owner/
   epoch/admission остаётся явной границей. Stop/timeout/UI close не actual
   worker exit и не причина premature pin/cache release. Jobs/results/Clone
   удерживают ресурсы до actual completion/ownership release; будущий async
   ledger result — также до adoption/revalidation. Native bytes не дают
   account/delete/upload права. No plaintext file/URL/temp fallback.

## Уточнение предложенной минимальной архитектуры

**PASS также для последнего proposed объёма main.** Native read-only factory
может сама выполнить confined `readExisting` + `readValidatedSnapshot` на worker
и вернуть stream вместе с verified/trustedPrefix status и original fault.
Неуспешная validation не становится stream success; разрешённый degraded
snapshot не теряет fault/status и не выдаётся за normal package authority.

- Immutable shared State владеет Files/context/index; process32 stream pins,
  включая Clones, держатся по actual RAII lifetime. Failed factory/clone
  откатывает admission; возврат factory или release исходного stream не
  уничтожает State/ресурсы ещё живого Clone/operation.
- Один process-wide decrypted block cache **≤256KiB разрешён**: это более
  узкий implementation ceiling внутри normative≤2MiB, не ослабление и не новая
  обязательная норма. Actual retained capacity, replacement/staging buffers и
  CopyTo scratch учитываются в соответствующих cache/owned64MiB budgets.
- Key State-lifetime+position достаточен для immutable exact snapshot, где
  State фиксирует identity/generation/entry versions/context. Простой адрес
  освобождённого State не lifetime key; last-State release/eviction должны
  исключать reuse старых bytes после нового State по тому же адресу. Предложенные
  wipe/clear — выбор реализации; выполняются без race с живым читателем.
- Process serial worker IO, сериализация Read/Seek/Clone и shared sticky error
  допустимы как документированный ceiling. Partial-error got0/no cursor advance
  совместимы с нормами. Signed Seek ceiling INT64_MAX не разрешает extension;
  accepted logical length≤64GiB остаётся отдельным пределом объекта.
- CopyTo≤256KiB с tracked/wiped scratch и target.Write вне global lock допустим.
  При снятии lock сохраняются реальные pin/context/buffer owners; ошибки target
  не маскируются. Удержание IO lock не заменяет lifetime этих владельцев.
- Existing ProtectedCustodyFilesTests/native fixtures/FileFault wrappers и
  регистрация нового reader TU в CMake/VS — допустимый путь регрессий/сборки
  main, не новые subsystem/gates. Reviewer их не запускал/не аудировал.

Новых нормативных решений для такой ограниченной реализации не требуется.
GC/ledger/state/app consumers по-прежнему не подключаются и не принимаются.

## Риски и допустимые исключения этого этапа

Основные риски: счётчик без реального snapshot ownership, dangling Files/store
reference, преждевременный release при Clone/timeout, отдельные process budgets,
неучтённый cache capacity/replacement peak, cache reuse другого контекста,
latest-generation refresh, частичный Read после native/hash отказа, скрытый
UI IO и ложный CopyTo/unsupported-method success.

Допустимо пока не подключать producers/MF/hash/upload, ledger/state payload
parsers, dirty writer/SetSize, commit worker/first metadata pair/ACK, mutation
commands/results, migration и GC execution. Это не разрешение отказаться от
них в T116. In-memory pin не persistent GC root: refs обоих indices/snapshots/
state и transitive roots после restart остаются требованиями §5; **GC нельзя
разрешить только по этому reader/count primitive**. Нет claim delete quiescence,
MF Shutdown-before-pin-release, protected whole pipeline или installed pass.

## Регрессии, предшествующие реализации/приёмке слоя

- Настоящие generated protected snapshots: full/tail/ZERO, межблочный Read,
  exact EOF/Read past EOF, negative/overflow Seek, independent Clone cursors,
  pinned generation при смене текущих slots, lifetime после выхода factory.
- Реальные holders на разных objects/Clones: process32 admission/refusal,
  failed-open/clone rollback, actual release/re-admission, retained owner во
  время worker read. Counter-only тест не подтверждает snapshot ownership.
- Shared cache reuse и process2MiB exhaustion/replacement across objects;
  реальная capacity/owned64MiB accounting, allocations/copies/temporary chunks,
  rollback при allocation failure, no reuse чужой identity/version.
- DATA/hash/native/allocation/IO failure, в том числе после успешного первого
  chunk: sticky/got0, no partial-buffer consumption/no fallback; CopyTo short
  target/source refusal, bounded allocation, unsupported mutators/flags.
- Worker-only serialization/context cancellation/lifetime в настоящем reader
  flow; не UI/MF интеграция. MF/ledger/stale callback/delete/GC и full generated
  pipeline regressions потребуются при следующих реальных integrations, не
  изображаются выполненными тестами reader.

## Нормативные SHA-256

| Файл | Текущий SHA-256 |
| --- | --- |
| spec.md | `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f` |
| plan.md | `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc` |
| tasks.md | `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287` |
| quickstart.md | `9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59` |
| data-model.md | `b494c57fa6cff34c0128d674677f5fca09e647aabbf60aea15c2a53603c43848` |
| contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |
| Contract tail от `## 1.` до EOF | `fc831b083699fb7e96f17cb642ad9a50b79d68bb2130fff69d4e2500b3151c6b` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |

Остальные восемь проверенных root/guidance/product/pointer pins совпали с
полным storage-independent/resources report; новая редакция норм отсутствует.
Перед ответом повторно проверяются эти hashes, все прежние checklist/report
bytes и counts. Только новый собственный reader report записан через
`apply_patch`; код/нормы/markers/чужие reports сохранены. Tests/build/VM/
GitHub/external writes/commit/migration/install не выполнялись.
