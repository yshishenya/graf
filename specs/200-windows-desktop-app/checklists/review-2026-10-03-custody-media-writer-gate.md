# Независимый requirements gate T116 — worker-only logical media writer

Дата: 2026-10-03, Europe/Istanbul.
Canonical root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Branch: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Risk/validation lane: **high-risk-product**; проверка качества неизменных
принятых требований, не source/runtime acceptance нового writer.

## Решение

**PASS: 112 checked / 0 unchecked. Unresolved CRITICAL=0 / HIGH=0
в области требований следующего последовательного media writer core.**
Для заявленного шага нормы достаточны: нового protocol, JSON schema,
продуктового решения или ослабления accepted design не требуется.
Main может начать scoped synthetic regressions и реализацию этого core
в существующей T116 при соблюдении приведённых ниже норм. Сам gate не
утверждает, что новый код уже им соответствует.

Следующий шаг декомпозиции выделен main implementation agent, не пользователем
или владельцем продукта. Пользователь сохранил полную Windows цель; нового
разрешения сократить итоговый scope не было. E1–E5 из Phase18 tasks — открытая
работа/история convergence, не пять новых дефектов качества требований.
Общий Windows PASS и закрытие T116 этим отчётом не объявляются.

Область: worker-only seekable logical writer для roles canonical/media/playback
поверх Files/Codec/Memory; write/readAt, явное ZERO extension, immutable
shrink/rewrite, bounded dirty staging, orphan sealing до checkpoint,
sequential canonical full-block checkpoints и explicit flush tail,
alternate index/exact full validated reopen/ACK, sticky failure,
retained ownership и cancellation. Full-value metadata semantics неизменны.
COM IStream adapter, V5/encoder, producers/ledger/state/GC сюда не подключаются.

## Обязательные чтение и привязка

Прочитаны инструкции canonical `speckit-implement` и `speckit-analyze`,
инструкции `code-reviewer`; роль — независимый reviewer требований, не
исполнитель всей implement-команды. Правила задач/коммитов/issue mutations
из общего workflow не расширяют пользовательское разрешение на этот отчёт.
Before/after implement/analyze hooks не требуют выполнения активного hook;
taskstoissues/commit hooks не вызывались.

Prerequisites с поддерживаемыми `--json --require-tasks --include-tasks`
и `--json --paths-only` подтвердили активную Feature200. Наличие spec проверено
отдельно: предписанный analyze флаг `--require-spec` локальный скрипт не
поддерживает. Это обход несовместимости интерфейса проверки, не пропуск spec.
Фактическая Git branch подтверждена отдельно от feature-name в JSON скрипта.

База: AGENTS, feature pointer, constitution, guidance index/worktrees/spec-kit
flow/product gates/tracker policy/issue canon/release-and-validation;
PRD и current product status; active spec/plan/tasks, research/data-model/
quickstart/parity-matrix/issue-map и contracts. Для bounded решения повторно
сопоставлены FR-012/013/014/022, SC-003/005/006/008, Phase18, актуальный порядок
плана, data-model §12, quickstart §12 и custody contract §§3–7, с сохранением
§§1–2/8–9 как границ context/confinement/migration/полной приёмки.
Неизменные ранее прочитанные материалы не переобъявлены новой Windows приёмкой.

Все **41** существовавшие checklist artifacts прочитаны/учтены в инвентаризации;
пять файлов с пунктами перечитаны и пересчитаны. Для исторических отчётов
сопоставлены решения, исправления и ограничения применимости; поздние
дополнения не потеряны за первоначальными Request Changes. Отчёты без checkbox
не добавляют требований и не считаются unchecked. Ни один marker не изменён.

Особенно проверены storage-independent/status-only freshness, protected-custody
design с закрытием F1–F6, codec/files/resources/reader/snapshot gates и source
reviews, прежний metadata writer gate и весь актуальный metadata source report.
Исторические NOT READY до принятия T114/T115 не заменяют нынешний порядок
плана: его актуальный раздел явно разрешает самостоятельный storage-срез.

`review-2026-10-03-custody-metadata-source.md` SHA-256
`87a89433a92b3d13d1ae8195e13769c7e952aacfc222c3654eae80046f336967`:
повторный обзор со sticky writer fix — **Approved**, P1 снят на его source
snapshot. Initial Request Changes сохранён как история. Main-observed runtime
receipts в дополнении не являются исполнением этого reviewer. Этот PASS
требований не переносит source approval на последующие изменения Files/Memory
или на ещё не проверенный media core; новые bytes требуют нового source review.

## Checklist counts

| Checklist | Total | Checked | Unchecked | Gate |
| --- | ---: | ---: | ---: | --- |
| advanced-routing.md | 14 | 14 | 0 | PASS |
| audio-capture.md | 24 | 24 | 0 | PASS |
| requirements.md | 22 | 22 | 0 | PASS |
| security.md | 27 | 27 | 0 | PASS |
| ux.md | 25 | 25 | 0 | PASS |
| Остальные 36 analyze/review artifacts | 0 | 0 | 0 | История/evidence, не implementation checkbox |
| **Всего** | **112** | **112** | **0** | **PASS требований** |

90 custom requirements-quality пунктов + 22 built-in spec-quality пункта.
Каждый из 112 относится к полноте/ясности/проверяемости требований; это не
112 пройденных runtime сценариев. Новый отчёт намеренно без checkbox.

## Достаточность норм и обязательные границы следующего кода

В таблице C — `contracts/windows-protected-local-custody.md`.

| Часть core | Действующая норма | Что нельзя потерять в реализации |
| --- | --- | --- |
| Roles/identity/bounds | C §3:76–119; §§1–2 | Только canonical/media/playback, fixed context/opaque IDs, exact position/version/role/length/digest. Unknown role/flags, overflow и 64GiB+ отвергаются до allocation/native IO; 64GiB не продуктовая quota. Metadata roles не проходят через media checkpoint API. |
| New/update authority | C §4:123–153 | Existing single-writer process/Files lease. Base0 — exclusive createNew, не missing/corrupt recovery. Update от fully verified current base; trustedPrefix/error не writable authority. Нельзя восстановить object/store ID или выбрать удобный orphan/index по mtime. |
| write/readAt | C §4:131; §6:250–256 | Accepted working bytes не durable. ReadAt рабочей версии не ACK и не публикация snapshot внешнему reader. Сохранённые DATA читаются с codec/integrity validation; native/semantic error sticky, без использования частичного buffer/zero-fill. EOF короткий, чтение за EOF не расширяет объект; offset/size arithmetic проверяется. |
| Explicit ZERO | C §3:101–115; §6:250–256 | ZERO entry только от явного SetSize/seek extension: flags1/version0/size0. Missing/corrupt DATA никогда не ZERO. Hole/extension bytes определены, не uninitialized memory; старый short tail при расширении становится новой exact DATA version, а не full block под старым именем. |
| Shrink/rewrite | C §3:111–115; §4:123–125; §6:253 | Не затронутые versions переиспользуются; изменённый partial/full/tail block создаётся новой immutable version. Shrink не удаляет committed bytes/versions из старых pinned snapshots. Повторное extension не возвращает ранее усечённые байты как будто они были ZERO. |
| Seal orphan before checkpoint | C §4:123–135 | Чтобы перейти к другой dirty позиции, текущие exact bytes можно encrypt/write/flush в новую CREATE_NEW version и сохранить bounded candidate ref; это ещё не commit. Orphan не выбирается authority и не переиспользуется/перезаписывается. Enum streamed; version/generation no wrap/reset, exhaustion blocked. Plaintext spill запрещён. |
| Dirty admission | C §5:170–176 | Один pending dirty block≤256KiB/writer — допустимое более узкое исполнение принятого group ceiling. Совокупно≤4 dirty slots/≤1MiB на процесс, не четыре на object/worker. Metadata staging тоже входит в общий лимит либо исключается общей сериализацией; отдельные 1MiB+metadata бюджеты недопустимы. Admission до принятия новых dirty bytes; wipe/deallocate прежде освобождения slot. |
| Shared ownership/memory | C §5:170–176,196–206; §7:277–299 | Reader/Clone/writer/retained result используют общий process pin≤32 и charged owned≤64MiB; не второй счётчик. Capacity, old+candidate indices, cipher/plain scratch/cache и retained completion учитываются до allocation. Slot, pin и byte charge — разные ограничения. Pin/admission не освобождаются раньше actual handles/consumer; DPAPI/MF internal memory — отдельное измерение. |
| Canonical cadence | C §5:179–183 | Sequential canonical публикует каждый full256KiB block, включая несколько границ внутри крупного Write. Это byte cadence, не таймер/1.365s SLA. Explicit Flush сохраняет tail; будущие Pause/Stop обязаны вызвать этот путь. Переписанный header/tail не получает ложного automatic normal seal. |
| Index/ACK | C §4:128–153; §6:250–256 | Все нужные DATA sealed/flushed → full protected temporary index/flush → alternate slot `(generation-1)%2` → flush → full validated reopen обоих slots и всех DATA refs → exact target comparison → ACK. Physical published и успешный flush сами по себе не ACK. Reopened lower generation/trustedPrefix или иной валидный target не success. Metadata g1pair exception не переносится на media roles. |
| Cancel/failure | C §4:131–135; §5:202–206; §7 | До начала publication — not_committed для этого checkpoint, без ACK, artifacts/old checkpoint retained. После начала publication закончить exact reopen несмотря на cancel: committed либо ambiguous; post-start failure ambiguous. Сам retained Files/writer blocked, не только error enum. Никаких next mutation/GC/auto-heal/retry через тот же instance до reconciliation. Отмена следующего checkpoint не отменяет ранее ACK full-block checkpoints. |
| Physical reserve | C §5:225–236; PRD local buffer policy | Native reserve guard прежде content writes учитывает physical peak группы/indices/candidate/orphans/pins/temp и cluster rounding. Reserve=min(10GB,10% actual disk capacity), не caller quota. Query не гарантирует последующий OS write: write/flush refusal terminal. Device cap5GB/retention7days/80%/95% и caller admission не заменяются codec length bound. |
| Package/effects/fences | C §4:156–164; §§6–7 | Checkpoint — verified bytes, не sealed_normal/WAV/AAC/manifest/queue saved. Canonical recovery frame cutoff floor(length/1920)×1920 остаётся обязанностью recovery/finalizer, не padding writer. canonical/media fallback лишь degraded trusted prefix; не расширять его на playback/metadata. No deletion/network/normal-package permission из decrypt/ACK. |

Для generic seekable core не требуется сейчас COM cursor/Clone/CopyTo adapter:
их будущие semantics уже определены C §6. Отложенная обвязка не разрешает
неограниченный writer scratch, silent successful Commit, plaintext fallback
или синхронный crypto/scan на UI/capture callback. Full-value metadata по C §5
по-прежнему один complete commit, не последовательные media checkpoints JSON.

## Проверяемость ближайшего шага, не test PASS

Нормы имеют достаточные synthetic acceptance oracles для tests-first:
exact writes/ranges/readAt/EOF, explicit ZERO gaps и old-tail extension,
shrink→extend без resurrect, rewrite и сохранность старого snapshot,
multi-block writes/смена dirty position/orphan collisions/version exhaustion;
full-block canonical checkpoints/explicit tail flush; отказ пятого общего
dirty slot/33-го общего pin/owned allocation и удержанные failed results;
cuts block/index/flush/publish/reopen, pre/post-publication cancellation,
валидный, но не exact-target reopen, sticky запрет повторной mutation на
retained lease и actual release. Source review обязан проверить эти пути,
а не переносить положительные metadata tests на media роли.

Ничего из этого reviewer не реализовывал и не запускал. Долгая полная reopen
validation остаётся worker-only; старое измерение reopen не доказывает latency
нового core. Exact ACK не является универсальной power-loss гарантией носителя.

## Complete scope, ownership и issues

Все восемь FR/SC storage-среза имеют покрытие T116–T118 в Phase18; требований
без task owner в этом bounded шаге не найдено. Constitution II/III/IV/VI
сохранены: Stop/indicator не ослаблены, desktop protection не меняет server
plaintext observability, права/deletion truth или independent review gates.

T116 task остаётся `[ ]`. GitHub #7444 непосредственно прочитан: **OPEN**,
правильный task-backed title, feature200/P0/storage/pr-blocker/hardening labels;
body сохраняет весь T116 и прямо говорит, что primitive не закрывает задачу.
GitHub `assignees=null`: персональный assignee не выдуман. Локальный
implementation owner — main; этот reviewer владеет только новым report.
Task→issue связь существует; issue-state/assignee ничего здесь не менялись.
T117/#7445 и T118/#7446 отражены в tasks как следующие отдельные работы;
свежая внешняя проверка их states не заявляется. Closable issues: **0**.

Не принимаются COM/MF adapter, V5/encoder/producer hookup, async ticket/adoption,
JSON/account/ledger/package-state authority, GC/transitive roots, migration и
реальный inventory, normal package/inspection/hash/upload/playback/delete,
installed/hardware/100cycles/SC-003/release. Метаданные P1 исправлены, но это
не заменяет source review media failure/lifetime путей. Clock/T119 и прочие
complete Windows gates остаются отдельно открытыми; их готовность заново
не оценивается и их нормы не ослабляются.

## SHA-256 normative snapshot

Хеши относятся к текущим локальным bytes, включая чужие dirty/untracked
артефакты; один HEAD не обозначает их committed content.

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f` |
| plan.md | `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc` |
| tasks.md | `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287` |
| contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |
| data-model.md | `b494c57fa6cff34c0128d674677f5fca09e647aabbf60aea15c2a53603c43848` |
| quickstart.md | `9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| security.md | `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9` |
| ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |

Единственная запись reviewer — этот новый separate report через apply_patch.
Нормы, код, checklist markers, tasks/state/Git/issues и чужие изменения не
правились/не откатывались; runtime/build/mic/install/migration/network effects
не выполнялись. После записи выполнены readback и повторный контроль:
hashes всей прочитанной нормативной базы и всех 41 прежних checklist artifacts
не изменились, в 42 файлах с новым отчётом по-прежнему 112 checked/0 unchecked;
новый отчёт не содержит checkbox или trailing whitespace. Любая дальнейшая
normative delta требует нового scoped gate; PASS привязан к этому snapshot.
