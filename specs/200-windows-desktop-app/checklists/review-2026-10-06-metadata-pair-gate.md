# Независимая проверка требований Round252: обе версии защищённых метаданных

**Дата**: 2026-10-06. **Владелец**: независимый reviewer.
**Область**: существующая T116, dependency step5 плана; только worker-only
чтение и удержание обеих проверенных v1 index slots и package payloads.
**Полоса**: high-risk-product storage, проверка требований и отдельный отчёт.

## Решение

**REQUIREMENTS APPROVED / scoped GO — C0/H0/M0/L0, 14/14 критериев качества
требований удовлетворены.** Можно начать RED и ограниченную реализацию ниже.
Это не source approval нового кода и не приёмка приложения. Дополнительного
решения о schema или нового жизненного цикла для этого prerequisite не нужно.

Последние уточнения main принимаются как конкретизация реализации уже
написанных правил, а не изменение protocol. Разрешён reuse:

- Сохранить публичную сигнатуру и поведение `readValidatedSnapshot()`;
  вынести тот же validator в private `readValidatedSnapshotImpl` с optional
  peer/selected outputs. Новый metadata-only `readValidatedMetadataPair()`
  возвращает fixed array двух validated `CustodyIndex` и selected slot. Нет
  второго сканера, алгоритма выбора или fallback. Допустимы только роли
  manifest..migrationIntent; прежний audio/trusted-prefix путь не меняется.
- В существующем Metadata слое — immutable `ProtectedCustodyPackagePair::read`
  либо столь же узкий `readCustodyMetadataPair` package wrapper. Только
  `packageState`, независимо ожидаемые context/directory, cancellation;
  общий job4/pin32 до native операций, существующий Files и allocator.
- Открыть **существующий** объект через `writeExisting`, без CREATE_NEW,
  публикации, восстановления IDs, ACL-изменения или записи payload. Эта
  аренда исключает второго protocol writer через его `id.bin` до освобождения.
  После проверки result удерживает private lease и pin; `blockWrites()`
  запрещает изменения через этот экземпляр. Наружу — только const values,
  slots/current, не Files/HANDLE/writer capability. Object/control block
  учитываются существующим `CustodyAllocator`, как у Tree.
- Оба package payloads читаются из собственных проверенных indices и DATA
  под той же непрерывной арендой, каждый строго парсится существующим
  `readCustodyPackage` с generation **своего** index. До общего результата
  оба должны пройти; нет успеха с одним удобным slot. Length1..64KiB,
  ровно один DATA block, без ZERO/empty default. Plain buffers очищаются.

Результат доказывает происхождение **этих двух собственных payload values**
из actual protected object при удержанной аренде, не авторизацию пакета.
Member IDs/roots/closures/logical hashes, manifest/trusted prefix/positive
short predicate, cross-record state/phase transitions, account/admission,
upload/playback/delete/GC, все bootstrap/intent/barrier retainers и миграция
проверяются далее. T116/T117/T118/T120 остаются открыты; H250-1/H250-2 не сняты.

## Почему нельзя считать readExisting замороженным снимком

Лично прочитан существующий Files.cpp:167–176: reader открывает identity
`GENERIC_READ` с `FILE_SHARE_READ | FILE_SHARE_WRITE`; writer использует
`GENERIC_READ | GENERIC_WRITE`, только `FILE_SHARE_READ`. ReadExisting допускает
protocol writer и сам по себе не стабилизирует последовательное чтение двух
slots. Main правильно отказался от такого предположения.

WriteExisting удерживает actual writer identity handle; второй protocol writer
не может получить совместимое открытие. Native sharing refusal классифицируется
существующим typed error/nativeError; не создавать новую mutex/retry queue и не
ждать на UI. При уже работающем writer factory отказывает без snapshot/effects.
После возврата proof блокировка живёт до последнего owning reference, не до
возврата worker. Будущая собственная mutation требует отпустить эту readonly
аренду и получить/перепроверить актуальную authority; этот prerequisite не
обещает одновременно writable package metadata и замороженный proof того же
объекта. Проверка consumer ordering остаётся следующей отдельной работой.

Generic physical pair method не приобретает lifetime/immutability authority
самим возвращением array: его caller обязан сохранять соответствующее владение.
Нельзя документировать readExisting pair как frozen proof. Package wrapper
получает исключающую writer аренду **до** валидации и не отдаёт её публично.
Это защита протокола GRAF, не от владельца профиля/администратора, который
обходит id.bin и меняет файлы напрямую; threat boundary базового §1 не расширен.

Семантика share flags проверена по [официальному CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew): несовместимое открытие
отказывает, режим совместного доступа сохраняется до закрытия handle; доступ
только к attributes не заменяет data-access exclusion. Это native API fact,
не execution нашего wrapper и не proof power-loss/аппаратной матрицы.

## Проверка качества требований

Это оценка написанных требований, не новые checkbox markers и не результаты
тестов. Traceability14/14; каждый вопрос имеет явное нормативное основание.

| ID | Вопрос к требованиям | Оценка и основание |
| --- | --- | --- |
| R01 | Определена ли необходимость сохранять обе версии, а не только highest? | PASS — base §§4/5/8.1 и packed §6.1: persistent roots обоих metadata slots; model §§12/13. |
| R02 | Разделены ли protected payload provenance, structural value и полномочия? | PASS — base §§6/7/8.1, packed §6.1; package gate CHK009–012. Parser/value/decrypt не дают normal/upload/delete/GC authority. |
| R03 | Задан ли неизменный ожидаемый context/directory независимо от JSON? | PASS — base §§2/3/8.1: actual confined identities, fixed role/location, own generation совпадает с pinned own index. |
| R04 | Явны ли обе-slot/full DATA проверки и no rollback? | PASS — base §4: любая missing/invalid metadata slot/ref блокирует контекст; singleton g1 не достраивается, g2/delete intent не теряется выбором g1. |
| R05 | Однозначны ли birth equality и current selection? | PASS — base §4: только equal decoded g1 pair, прочие equal generations конфликт; далее highest validated generation, slot `(generation-1)%2`. |
| R06 | Определены ли bounds и отказ empty/ZERO package payload? | PASS — base §§3/8.1:64KiB package-state, exact DATA/tail/checksum/context; strict обязательный JSON object нельзя получить из пустоты/нулей. |
| R07 | Согласован ли reuse strict package v1/v2 codec без расширения schema? | PASS — base §8.1 и packed §6.1: exact девять top-level/schema, refs6/10 fields, duplicate/unknown/null/number/depth bounds и собственная generation. |
| R08 | Полно ли определено реальное владение на время получения и использования? | PASS — base §§4–7/model pinned snapshots, уточнение main о private writeExisting lease; readExisting не принимается как frozen. |
| R09 | Отделена ли readonly capability от физического режима открытия? | PASS — base §6: readonly result не даёт Write/SetSize; private blocked lease/const values не создают разрешение публикации. |
| R10 | Измеримы ли общие resource/admission/lifetime пределы? | PASS — base §5/packed §6 и quickstart §14: owned64MiB, pins32/jobs4, bounded64KiB payload; actual operation/lease до выхода, без новых квот/IO в UI. |
| R11 | Полны ли failure/cancel/exception и запрет partial success? | PASS — base §§3–7 и FR-012/013: typed error, artifacts retained, не default/legacy/normal; buffers/pin/lease не освобождаются раньше actual completion. |
| R12 | Явно ли прежнее audio fallback не становится metadata fallback? | PASS — base §4 и plan: v1 metadata no-rollback неизменен; canonical/media trusted-prefix исключение не переносится на package-state/playback authority. |
| R13 | Задана ли граница diagnostics и side effects? | PASS — FR-012/022, SC-006, constitution III/IV: payload/IDs/private content не логируются/не выдаются WebView; read proof не запускает сеть/cleanup/GC. |
| R14 | Прослеживаются ли prerequisite, тестовые критерии и оставшиеся зависимости? | PASS — T116/plan dependency5, quickstart §§12/14; T117/T118 и consumer authority имеют отдельных владельцев, не новая задача или общий PASS. |

## Scoped analyze

| Requirement | Владелец | Область текущей проверки |
| --- | --- | --- |
| FR-012 | T116 | Защищённая обе-slot provenance собственных package metadata и bounded readonly владение; не full pipeline. |
| FR-013 | T116; последующий переход T117 | Общий metadata validator сохраняет no-rollback/no-empty правила; очередь ещё не подключается. |
| FR-022 | T116; T117/T118 | Пара удерживает данные, не выдаёт cleanup/GC/delete права. |
| SC-006 | T116 | Context/schema/bounds/failure и metadata-only evidence; не вся bridge/security matrix. |

Scoped requirement coverage4/4=100%, executable task1 (T116), unmapped0,
ambiguity0, duplication0, unresolved C0/H0/M0/L0. Конституция II/III/IV/VI
соблюдена: Stop/индикатор не меняются; локальная защита не меняет серверную
plaintext observability; deletion truth и independent review сохранены.
Новая schema/жизненный цикл/численные допуски/продуктовые квоты не добавляются.
Это не full-feature analyze22FR/10SC/120tasks. Незавершённая реализация
полного T116 не является неоднозначностью требований данного prerequisite.

## Состояние действующих checklist файлов

Все десять нормативных active checklist файлов прочитаны. Исходные97 Markdown
файлов перечислены и SHA-256 зафиксированы; исторические отчёты прочитаны по
относящимся к области verdict/исключениям, не как новый полный аудит истории.

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
| **Итого** | **154** | **0** |

Физические markers всех97 файлов:410 checked/10 unchecked. Это исторические
повторы, **не420 уникальных требований** и не новый implementation PASS.
Unchecked находятся в старых tree-source3/writer-source4/cadence-source3.
Конечные writer/cadence append verdicts9/0 сохранены; tree имеет отдельный
непроведённый engaged-snapshot error-return cut. Они не переотмечаются и не
выдаются за14 blockers нового requirements gate. Package parser gate имеет
12/0, но не заменяет этот самостоятельный review. Tasks120=93checked/27open.

SHA-256 sorted manifest исходных97 (`filename + space + sha256 + LF`, UTF-8):
`709fd3833931c616847a6ec9eccf52cf894eba8fe3add0bc4e96470eeca485c0`.
Новый отчёт не содержит checkbox markers; прежние файлы/отметки сохраняются.

## Минимум для отдельной source проверки после RED

Ожидается frozen incremental diff и baseline hashes, не source approval сейчас:
оба actual slots и разные собственные generations/values; equal g1 и conflict;
g2→missing/corrupt lower или higher slot, invalid referenced DATA; исправная
highest physical slot с malformed lower payload не даёт result. Wrong own
IDs/role/directory/generation/schema/types/size/empty/ZERO отвергаются.

Actual writer exclusion до/после factory и до последнего shared ref; отсутствие
public write access, file/create/rename/flush/GC side effects; после release
обычный writer может снова открыться и factory берёт новую пару. Existing
audio fallback/metadata birth/update regressions не сокращаются. Cancellation
до IO/между slots/перед return, native/hash/DPAPI/allocation failures, process
pin32/job4/owned pressure и plaintext wipe должны сохранять artifact/lifetime
и не возвращать partial pair. Generic physical validator не обещает frozen
readExisting proof. Debug allocating vector/result moves проверяются отдельно.

Не выполнять реальный profile/app/migration/audio для этой проверки. Runtime
receipts main не являются independent reviewer execution; будущий source
review и фактические тесты остаются отдельными доказательствами.

## Лично сверенная идентичность

Canonical root: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
HEAD не идентифицирует dirty bytes. Ниже SHA-256 прочитанного **baseline до
Round252 реализации**, не будущая freeze/source приёмка.

| Артефакт | SHA-256 |
| --- | --- |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| quickstart.md | `4ba06328532a417002d126ce1e5b47963f72859155311c477b53aeb344b5034a` |
| local custody contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed custody contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| Files.h | `108f2e989b081812a38a2464a3eda9930fe35c1173a86df0f288851e6aefeced` |
| Files.cpp | `c7ddc8367c205a9f6e2177ff54b9a46ccc7e8b7a039079dba863378e67b11882` |
| Metadata.h | `bc5b665d0e28a10ade9b66e4c7966a8255055627746a1d0b5705343e4ed14f05` |
| Metadata.cpp | `f8ad4a5ed733f803088e025e8de15a4f427e6f747241929a658dbadb9d646965` |
| Memory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |
| Codec.h | `a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde` |

Лично прочитаны `speckit-analyze`/`speckit-checklist` целиком; root AGENTS,
guidance index, worktrees/spec-kit-flow/product-gates/релевантные release
правила, constitution; относящиеся spec/plan/tasks/model/contracts/quickstart,
PRD local-buffer и current custody status sections. Sources Files identity/open/
snapshot/commit, Metadata parser/commit, Memory/Codec headers прочитаны для
обоснования reuse/границ, **не** для принятия ещё не написанного wrapper.

Supported prerequisite `--json --require-tasks --include-tasks` и checklist
template успешно прочитаны. Skill `--require-spec` получил явный unsupported
option; spec существование/содержание проверены отдельно без изменения script.
Extensions YAML прочитан: все before/after analyze/checklist hooks отключены;
никаких изменяющих состояние hooks не было. Analyse вывод сохранён в этом
отдельном reviewer отчёте по явному запросу, не правкой spec/plan/tasks.

## Терминальная граница

**Scoped requirements GO только для обе-slot readonly payload primitive.**
Source NOT REVIEWED; consumers/полная metadata authority/manifest/hash/GC/
bootstrap/migration/реальный inventory/installed parity/release — NO-GO до
собственных доказательств. Reviewer прекращает проверку после отчёта до
отдельного запроса main о frozen source review. Единственная запись — этот
новый файл; code/spec/plan/tasks/старые checklists/runtime/GitHub/commit/push/
PR/merge/install/audio/server не изменялись и не запускались reviewer.

После записи отчёт лично перечитан. SHA всех исходных97 checklist файлов
повторно вычислены и совпали97/97; прежние отметки и содержимое не изменились.
Новый файл добавляет0 checkbox markers. Это terminal requirements verdict;
текущие тесты/сборка/будущий source review здесь не ожидаются и не принимаются.
