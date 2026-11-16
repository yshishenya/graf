# Независимая проверка требований: cold retained-root reader, T116

**Дата**: 2026-10-06. **Владелец отчёта**: независимый reviewer.
**Область**: существующая T116, dependency step5 плана, обязательство packed
contract §6.1. Последние уточнения main ограничили первоначальный запрос
проверкой холодного чтения исторического корня; это не общий semantic package
authority gate и не повторная проверка parser/serializer Round250.
**Полоса**: high-risk-product storage; read-only investigation + reviewer report.

## Решение

**REQUIREMENTS APPROVED — C0/H0/M0/L0 в указанной ограниченной области.**
Нормативных уточнений для начала RED и реализации этого prerequisite не требуется.
Действующие §§2–5/6.1 packed contract, §6 базового contract и plan step5 уже
задают необходимую границу. Перечисленные ниже правила — их следствия, не
новые поля формата, продуктовые допуски или редакция протокола.

Разрешённая форма: worker-only `Tree::verifyRetained(owner, expectedContext,
untrustedDescriptor)` либо столь же узкий метод существующего Tree. После
проверки actual owner/prefix/context, корректной текущей пары и полного обхода
обоих текущих деревьев он полностью проверяет отдельный historical descriptor
под тем же Guard и создаёт **только readonly media-root proof**. Result сохраняет
actual owner, pin и собственный immutable descriptor. Это не второй owner,
backend, dispatcher, реестр пакетов или общий resolver полномочий.

**Не принято**: происхождение stamp из защищённых package/migration metadata,
полнота восстановления всех внешних retainers, normal package admission,
сверка всего logical SHA finalized artifact, права аккаунта, upload, GC,
discard/delete, consumer adoption, bootstrap/migration, T116 целиком,
T117/T118/T120, установленное приложение и release. H250-1/H250-2 не сняты.
Будущий source review проводится отдельно по замороженному точному diff.

## Метод и источники

Каноническая копия лично сверена:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Рабочие изменения сохранены;
HEAD не является идентификатором новых незакоммиченных байтов.

Лично прочитаны полностью инструкции `speckit-analyze`, `speckit-checklist`
и `code-reviewer`. Прочитаны root AGENTS, guidance index, codex-worktrees,
spec-kit-flow, product-gates и constitution; относящиеся к проверке
release/validation, PRD local-buffer/privacy и current-product-status sections.
Extensions прочитан: before/after analyze/checklist commit hooks отключены.
Никакие изменяющие состояние hooks не выполнялись.

Active feature установлен из feature.json и поддерживаемого prerequisite
`--json --require-tasks --include-tasks`; checklist template прочитан через
`--json --template checklist-template`. Предписанный skill аргумент
`--require-spec` не поддерживается этим скриптом: получен явный отказ, затем
прочитан `--help`, spec проверен отдельно, скрипт не менялся.

Текущие spec FR-012/013/022, SC-006, storage clarifications, plan:1501–1598,
tasks T115–118, model §§12–13, quickstart §14, packed contract §§1–7 и
base authority/GC/read-only §§5/6/8.1 прочитаны в относящихся к области местах.
Идентичность норм сверена с Round250, но прежний PASS parser не использован
как approval нового API. Исторические reviewer reports прочитаны по
релевантности, согласно последнему уточнению main, не повторно вся история.

Проверены актуальные критерии package gate CHK009–012 и его конечная граница
SOURCE/DOCS APPROVED; tree-gate явно исключал historical retained roots,
поэтому не выдаёт разрешение автоматически. Прочитаны конечные разделы
writer/cadence source reports и working-profile gate. Существующие
Tree.h, verify/readHeads/walk/readBlock/checkWrite/commitBlock и Format.h/.cpp,
Owner.h, релевантные Reader/Writer места прочитаны для границ reuse. Это не
новый полный source audit; `verifyRetained` сейчас отсутствует.

## Качество требований: 12 удовлетворённых критериев, 0 неподтверждённых

Ниже результаты reviewer, не новые checkbox markers и не реализация тестов.
Все 12 критериев имеют нормативную ссылку; traceability 12/12.

| ID | Вопрос к требованиям | Оценка и основание |
| --- | --- | --- |
| R01 | Определена ли необходимость исторических корней вне текущей пары? | PASS — packed §6.1:336–340 и model §13 явно сохраняют stamps обоих metadata slots/barriers, даже вне двух текущих media heads. |
| R02 | Разделены ли структурный descriptor, проверенное чтение и полномочия пакета? | PASS — packed §§1/2/6/6.1, base §8.1 и прежний CHK009. Untrusted fields не доказывают provenance; full closure даёт bounded read proof, не package authority. |
| R03 | Достаточно ли точно задан ожидаемый context и непрерывное владение? | PASS — packed §2: тот же actual HANDLE/epoch/native identity/store/object/container/role, confined location; prefix не authority. Контекст не берётся из самоподтверждающего входа. |
| R04 | Полны ли требования cold проверки текущих голов и исторического дерева? | PASS — packed §§3/5/6.1: обе valid adjacent heads и обе closures, затем каждый historical root после gap, под тем же owner до результата. Highest-only/lazy/cached прошлый proof недопустим. |
| R05 | Измеримы ли shape/extent/EOF/root/tail/версии? | PASS — packed §3 descriptor128/ref64, §4/5: exact block count, actual EOF, root NODE_L2/base0 либо EMPTY при length0, g1 exact birth, child-before-parent и exact tail. |
| R06 | Согласованы ли historical stamp и известные committed generations? | PASS — packed §5 единственный selected base+1, неизменные records и неуменьшающийся extent; точные следствия приведены ниже. Старый stamp не обязан быть одной из current heads. |
| R07 | Определены ли обязательные проверки ciphertext до decode? | PASS — packed §3: expected envelope length/SHA до DPAPI для root/всех NODE/DATA, затем expected context/checksum/payload. Самосогласованный child не заменяет expected Ref. |
| R08 | Явно ли readonly snapshot не имеет write capability? | PASS — base §6 Read-only snapshot SetSize/Write отвергает; packed §2 различает pin/read и writer capability, §6.0 open требует current selected Tree. Даже совпавший с current head retained result остаётся readonly. |
| R09 | Заданы ли bounded память, jobs/pins/cache и lifetime? | PASS — packed §§2/3/5/6: один admitted Guard/job через обход/результат, stack depth3+DATA, owned64MiB/pins32/jobs4/cache2MiB/root4KiB; нет N-sized bitmap или второго HANDLE. |
| R10 | Разделены ли отказ полномочия и наблюдаемая порча? | PASS — base §6 readonly отказ; packed §§1/4/5 sticky observed failure. Предложенный `conflict` без нового enum для healthy readonly mutation не меняет норму; физический/context/hash/structure fault не скрывается им. |
| R11 | Определено ли сохранение исторических bytes после здоровых переходов и отказов? | PASS — packed §§2/4/6/6.1: старый pinned root видит прежние bytes/длину; fault invalidates normal effects, artifacts сохранены, cancel не освобождает actual operation. |
| R12 | Явны ли задача, минимальная приёмка и оставшиеся зависимости? | PASS — existing T116/plan step5, quickstart §14/packed §7 покрывают root proof; metadata provenance/retainer enumeration и consumers следуют отдельно, T117→T118 не сокращаются. |

## Exact consistency: что следует из существующего протокола

### Не подменять root текущей head

`generation()/logicalBytes()/readBlock()` исторического proof используют его
собственный immutable retained descriptor. Текущая пара хранится отдельно как
проверенное основание, не переписывается fake historical head. Старый snapshot
может иметь другую длину, больше bytes и другой root, чем current snapshot:
replace/shrink/grow по §4 специально сохраняют старое представление.
Нельзя требовать, чтобы historical bytes совпадали с current bytes.

### Generation и extent

1. Descriptor имеет generation>0, length≤64GiB, exact count=ceil(length/block),
   valid root Ref/extent и все структурные проверки §3. committed extent≤actual
   EOF, не rounded appendPosition. g1 — только EMPTY/length0/extent32896.
2. stamp.generation выше highest current validated head — несовместимость.
   Она не чинится rollback/new empty/default/generation reset. Если persistent
   metadata указывают более поздний root, это будущий recovery conflict,
   а не право автоматически выбрать более старую head как normal package.
3. Если stamp.generation равна generation **любой** текущей head, весь
   descriptor обязан быть exact equal этой head: generation/length/count/
   committedExtent/root со всеми Ref fields. Same generation с другим root,
   SHA/ref/длиной или extent — conflict, не альтернативный исторический root.
4. Более старый stamp допустим без current-head membership после strict shape
   и полной historical closure. Из монотонного extent §4/5 следует:
   его extent не больше extent каждой более поздней проверенной head.
   Если stamp старше lower peer, недостаточно сравнить только с highest:
   extent также ≤lower-peer extent. Меньшая generation не обязана означать
   меньшую logical length: SetSize shrink разрешён.
5. Каждый reachable ref ограничен именно historical descriptor extent и
   generation, своим parent offset, level/base/selector, actual file size и
   exact tail; orphan tail не разрешает расширить stamp. ZERO лишь по §4,
   отсутствующее/битое DATA не становится нулями.

Эти проверки необходимы, но **не доказывают**, что произвольный supplied
descriptor действительно когда-либо был опубликован или указан защищённым
metadata. Происхождение и actual finalized logical SHA остаются внешней
authority validation. Нельзя превращать «данное дерево удалось полностью
прочитать» в «этот пакет разрешён для upload/GC/normal admission».
Новая гарантия forensic anti-rollback этим шагом не вводится.

### Readonly и ошибки

Readonly принадлежит результату proof, не только mode физического Owner.
Через retained result отвергаются appendBlock, replaceBlock, setSize, включая
same-size no-op, и открытие Writer. `conflict/notCommitted`, без snapshot и
без append/HEAD/flush/публикации, соответствует предложению main.
Нельзя превращать readonly отказ в committed no-op.

Здоровый отказ записи не вызывает guard.reject, revokeWrites/blockWrites
общего owner и не лишает genuine current writer права работать. Уже
наблюдаемая sticky причина owner не маскируется новым conflict. Реальные
identity/context/crypto/hash/structure/IO faults сохраняют exact first fault
и существующее blocking поведение. Возврат result и exception classification
происходят до отпускания actual Guard/job/owner/buffers.

После здорового продвижения current heads historical reads остаются возможны
под тем же непрерывным owner: иначе требование pinned snapshot бессмысленно.
Не требовать вечного равенства текущей пары сохранённой при verifyRetained
паре на каждом чтении. Наблюдаемый fault/gap не обходится этим исключением.

## Минимум для следующего отдельного source review

Это ожидаемые доказательства соответствия, **NOT RUN reviewer**:

- RED отсутствующего API; generated history g1→g2→g3→g4 с retained g2,
  отсутствующим в current heads, точными прежними bytes/length/EOF; reopen
  после release всех refs и новая cold проверка, не только RAM pin до gap.
- Одновременно исправная current pair и повреждённое historical-only DATA
  либо NODE на каждом уровне должны отвергаться. Исправный historical root
  не обходится повреждённой lower/current head. Envelope SHA до DPAPI.
- stamp выше highest, совпавшая generation с отличающимся descriptor;
  старый extent выше lower peer при допустимом actual EOF/highest extent;
  count/root/version/tail/EOF/forward bounds; EMPTY g1 и shrink-to-empty g>1.
- Expected store/object/container/role substitution и Owner mismatch;
  отказ без выдачи partial proof или права на другой объект.
- Append/replace/setSize/same-size/Writer-open через readonly proof отказывают
  при writable Owner. После них retained read и genuine current writer
  остаются здоровыми; известный sticky native fault не замещается conflict.
- Healthy current commit не изменяет historical cursor/generation/length;
  Reader/Clone переиспользуют descriptor и actual owner. Release writer с
  active retained read, retained result lifetime и cancellation не закрывают
  живой job/HANDLE раньше actual completion.
- Admission/allocator/pin/job pressure, exact first error, cleanup/wipe и
  bounded stack/reads на ZERO/64GiB logical edge без гигантского fixture;
  existing v1/current-pair/Tree/Writer regressions не ослабляются.

Предъявить frozen changed-file hashes и точный baseline. Source approval
сначала отдельно; native/portable execution receipts только с исполнителем,
source identity и terminal результатом. Старые 49/49 или parser 5/5 не
засчитываются исполнением новых кейсов. Reviewer сам runtime не запускает.

## Scoped analyze и coverage

| Требование | Существующий владелец | Что проверяется сейчас |
| --- | --- | --- |
| FR-012 | T116, packed §§2–5/6.1 | Cold verified historical logical read, не полный защищённый pipeline. |
| FR-013 | T116; переход T117 | Нет authority из field/default/старой удобной head; реестр не открывается. |
| FR-022 | T116, последующая T117/T118 | Нельзя получить GC/delete right из root proof; retained lifecycle сохранён. |
| SC-006 | T116 | Context/bounds/failure и metadata-only evidence, не bridge matrix целиком. |

Scoped requirements4, implementation task1 (T116); coverage4/4=100%,
unmapped0, ambiguity0, duplication0; unresolved C0/H0/M0/L0.
Constitution II/III/IV/VI не противоречат prerequisite: Stop/indicator,
серверная наблюдаемость, deletion truth и независимый review сохранены.
Нет новой задачи, спецификации, backend или нормативного поля.
Это не full-feature analyze 22FR/10SC/120tasks и не общий PASS T116.

## Состояние существующих checklist markers

Однократно перечислены все 95 Markdown файлов checklists. Физический
подсчёт **410 checked / 10 unchecked** включает исторические append-only
повторы; это НЕ 420 уникальных обязательств и НЕ текущий implementation PASS.
SHA-256 sorted manifest (`filename + space + sha256 + newline`, UTF-8):
`b19308dc796a1decbff67637f89c7925f08cda6bf49bf8279b87d3b40035a6a6`.
Он охватывает исходные95 файлов до появления этого отчёта.

| Нормативный checklist | Checked | Unchecked |
| --- | ---: | ---: |
| requirements | 22 | 0 |
| audio-capture | 24 | 0 |
| advanced-routing | 14 | 0 |
| security | 27 | 0 |
| ux | 25 | 0 |
| calendar-launcher | 5 | 0 |
| calendar-operation | 8 | 0 |
| calendar-wire | 5 | 0 |
| packed-writer | 12 | 0 |
| privacy-pause | 12 | 0 |
| **Итого десять нормативных файлов** | **154** | **0** |
| package parser requirements report, отдельно | 12 | 0 |

Все остальные markers reports вместе:256 checked/10 unchecked. Десять
неотмеченных строк находятся в tree-source3, writer-source4 и cadence-source3.
Их не удалять и не переотмечать: writer/cadence конечные append sections
содержат 9/0 в своих frozen scopes; tree конечная оценка сохраняет 17/1
с непроведённым exact engaged-snapshot worker error-return cut. Это история
локальных source/evidence cohorts, не 10 новых requirements blockers
проектирования данного reader и не доказательство отсутствия будущих дефектов.
В tasks: **93 checked / 27 unchecked**, всего120; T116/T117/T118 открыты.

Ни одна существующая отметка этим reviewer не изменена. Новый отчёт не
создаёт checkbox items и не переопределяет старое evidence. После записи
проверяется сохранность hashes всех исходных95 checklist файлов.

## Идентичность нормативного и исходного снимка

| Артефакт | Лично вычисленный SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| quickstart.md | `f88d2931c59420ef74332f51f15952dd4a39f09b59457f1e0a6a9c3c0e060d08` |
| base custody contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed custody contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| existing package gate | `0948256d5a234b3d7addcbb714d7940e780afc5ec6d2b0218c584d4f3f32cb62` |
| existing working-profile gate | `0c86c7a67a383c6387f3cf949d59e79ed78690e9b162f4a2b12462cc1fc41ed0` |
| Tree.h | `9c28432d20e49726033a1f855bc458b93040c6681d9155a81504dfad4a7a9b87` |
| Tree.cpp | `97f101c34413ac57bbe48ab64b98a6e3ecfdc11ff61ec24681c9a7f9e99a56b3` |
| Format.h | `0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88` |
| Format.cpp | `bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f` |
| Owner.h | `99dee259444c8a552d3e759e91e10a5a301d38991bfa655ebb90e5abb03922ed` |
| Reader.cpp | `0d38daf7ce709d112ca14edb3e87cb7a4a774c562ef48984c2ef91ad265977b9` |
| Writer.cpp | `dc1e9cc31ae90186f73d989602895026cff58c2bdb34414b25ffa3f91ad6a4fd` |

## Терминальная граница этого review

**Requirements APPROVED только cold retained-root readonly prerequisite.**
Права consumer/package/metadata provenance/retainer enumeration/GC и общая
приёмка NO-GO до собственных доказательств; source нового API NOT REVIEWED.
Единственная разрешённая запись — этот новый reviewer-owned отчёт.
Reviewer не выполнял code/spec/plan/tasks/старые checklist edits, GitHub writes,
commit, push, merge, VM/app/profile/device/audio/server/build/test/install.
Git использовался только для read-only identity/status/source inventory.
