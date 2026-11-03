# Requirements gate: packed cadence measurements / F200 T116

**Purpose**: Независимая проверка достаточности существующих требований для
test-only generated measurements plan step4, не source/runtime acceptance.
**Created**: 2026-10-04.
**Feature**: [spec.md](../spec.md), [plan](../plan.md),
[packed contract](../contracts/windows-protected-packed-custody.md).

**Review Ownership**: Только независимый reviewer. `[x]` означает подтверждённое
качество требований, не успешный тест или завершение T116. При генерации все
пункты оставлены unchecked; оценка ниже выполняется отдельно. Основной агент
markers не меняет.

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Anchor feature.json: F200/codex/200-windows-followup/source_sha
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Git не проверялся.
Lane: high-risk-product storage; ограниченный requirements review внутри
существующей T116. Разрешён только этот новый report/checklist.

## Полнота и ясность требований

- [x] CHK001 Разделены ли test-only измерения существующего worker Writer и запрещённое пока consumer adoption/продуктовая приёмка? [Scope, packed §6.0/§6.1/§7; Plan step4–5]
- [x] CHK002 Однозначны ли формат generated canonical, размер исходного batch и различие sample time, byte cadence и фактического wall time? [Clarity, Quickstart §14; base §5]
- [x] CHK003 Заданы ли full-block checkpoint и короткий tail при Flush/Pause/Stop без нового размера/предела/автоматического таймера? [Completeness, packed §6.0; base §5:197–202]
- [x] CHK004 Разделены ли accepted bytes, independently acknowledged Tree и complete-frame recovery prefix, включая отсутствие premature ZERO/normal saving после ошибки? [Consistency, packed §6.0; base §4:174–184; FR-012]
- [x] CHK005 Измеримы ли constant live transition cost и физический рост на нескольких длинах при отдельном, не constant-cost, cold verify? [Measurability, packed §7; Plan step4; Quickstart §14]
- [x] CHK006 Согласованы ли owned/cache/dirty/pin/job bounds с отдельным наблюдением native allocations/RSS, без приписывания им общего доказанного quota? [Consistency, packed §6; base §5; SC-003]

## Жизненный цикл, отказ и границы доказательства

- [x] CHK007 Определены ли old pinned Reader/Clone и actual release→cold full verification, без нового backend, root refresh или GC живых records? [Coverage, packed §5/§6/§6.0/§7]
- [x] CHK008 Однозначно ли отделено storage tail/Stop measurement от продуктового drain/EOS/timeline/finalizer и 5s от обещания завершить зависший native IO? [Clarity, base §5:197–202; Plan:1437–1438; packed §7]
- [x] CHK009 Определены ли delay/expiry/failure как отсутствие normal completion при сохранении actual ACK/ambiguous result/lease до реального завершения? [Exception coverage, packed §6.0; base §4/§5; FR-012]
- [x] CHK010 Определены ли учёт physical append/pinned/orphan peaks и неизменные disk admission, без новой придуманной latency/physical-ratio нормы? [Bounds, packed §6; base §5; Plan step4]
- [x] CHK011 Ограничены ли generated input и metadata-only evidence без private audio, реального inventory/установки и claim sustained capture по одному лучшему замеру? [Security, packed §7; Quickstart §14; SC-006; Product gates]
- [x] CHK012 Есть ли непротиворечивое соответствие существующим FR/SC/T116 и constitution, без нового task/policy и автоматического закрытия полной Windows цели? [Traceability, Spec FR-012/013/022, SC-003/006; Tasks T116; Constitution I/II/VI]

## Лично прочитанный контекст и способ проверки

Прочитаны полностью code-reviewer, speckit-checklist, speckit-analyze SKILL.md,
текущие root AGENTS и guidance index, extensions.yml и checklist template.
Переиспользовано прежнее полное личное чтение неизменённых constitution и
guidance после свежей проверки их SHA; дополнительно перечитаны constitution
I/II/VI и релевантные guidance sections. Прочитаны все12 пунктов packed-writer,
packed §6/§6.0/§6.1/§7, plan:1418–1472 (включая step4), T116:568 и соседние
границы T117/T120, актуальные FR/SC, quickstart §14, base custody §4/§5 и
desktop Stop contract. Старые hundreds validation history не перечитывались.

Генерация и оценка требований разделены. Скрипты prerequisite, сборки/тесты,
Git/VM/GitHub не запускались: пользователь разрешил только чтение и этот
report. Вместо script setup лично прочитаны feature.json/template и явные
активные пути. before/after checklist/analyze hooks в extensions.yml — disabled
git.commit; их исполнение не требуется. Никаких норм, product API, quotas,
tasks или исторических reviewer marks не меняется.

Прежний source acceptance
`62a2f6b76f7bac7e043bce46ca83a2824e26c3ac94519f3bc91b3d4148ff251e`
принимает только Writer step3. Свежие Writer.cpp dc1e9cc… и OwnerTests2a30db6…
совпали; это prerequisite reuse, **не cadence PASS**. VS0 сообщён main, не
используется для требований и не заявлен как personally observed installed app.

## Независимая оценка требований

| Пункт | Основание |
| --- | --- |
| CHK001 | Packed:250–256,294–295,343–347 и Plan:1459–1468 разделяют worker/test step4, schema-before-adoption и последующую продуктовую приёмку. |
| CHK002 | Quickstart:500–504 задаёт 48kHz mono Float32. 480 samples =1920B за10ms; rate192000B/s;262144/192000=1.365333s — nominal source interval, не обещанная latency crypto/IO. Размер test batch следует из запроса и base:177, не новая продуктовая норма. |
| CHK003 | Packed:258–265 и base:197–198 задают byte cadence full256KiB и explicit short tail. Measurement вызывает прежние writeAt/checkpoint; не вводит новый API или таймер. |
| CHK004 | Packed:269–287 различает pending/committed и actual generations. Base:174–184 отдельно определяет recovery floor(length/1920)×1920; raw storage checkpoint length не объявляется автоматически normal V5 recovery/package. |
| CHK005 | Plan:1459–1460, packed:353–365, quickstart:500–504 задают length sweep1/2/4/8/16/32/64MiB, last-checkpoint/actual record/read counts и отдельный cold cost. Constant относится к одной live transition, не суммарному IO всей записи; все повторы/неудачи сохраняются, лучший замер не является sustained claim. |
| CHK006 | Packed:223–227 и base:188–195 сохраняют owned64MiB/process, cache2MiB, dirty4, pins32/jobs4 и pre-allocation admission. Native DPAPI/MF allocations наблюдаются отдельно; SC-003 RSS128MiB/CPU25% относится к полной capture на reference x64, не подменяется owned счётчиком CLI. |
| CHK007 | Packed:211–219,231–240,269–289,356 требует retained old root и full bounded cold verification после ownership gap. Healthy Writer release не отзывает здоровое чтение; actual last release и cold reopen измеряются отдельно. |
| CHK008 | Base:197–202 и Plan:1437–1438 прямо исключают wall-time promise для hung native IO. 5s — dispatcher drain, не обязательный deadline одного checkpoint/cold scan/encoder; тест worker без dispatcher/EOS может измерить только storage-side tail/release, не подтвердить весь product Stop. |
| CHK009 | Base:199–202,214–227 и packed:281–289 требуют остановки normal capture при sink/queue/drain failure, удержания ownership до actual completion, truthful actual ACK/ambiguous и отсутствия нового success по истечению срока. |
| CHK010 | Packed:228–240 сохраняет physical peaks и продуктовый/free disk budget. Quickstart требует physical growth/cost measurement, но не задаёт универсальное ratio/latency PASS число: его нельзя изобретать или вывести из64GiB representation cap. |
| CHK011 | Packed:364–365, Quickstart:504–507 и Product gates запрещают raw/private diagnostics и перенос unit/big-O/VM результата на sustained capture, installed/hardware/release. |
| CHK012 | Existing T116:568 покрывает bounded IO/failure fences и остаётся open. FR-012 — protection/ACK, FR-013/022 — неизменные queue/delete authority, SC-006 — безопасные diagnostics. SC-003 и constitution I/II/VI сохраняют отдельные полноценные audio/control/quality/gates. |

### Уточнения границ, не новые требования

**C0/H0/M0 для начала test-only CLI measurements.** Реальной неоднозначности,
блокирующей именно измерения существующего Writer, не выявлено. Не требуется
новая норма, API, task или численный предел. Это не означает наличие достаточного
runtime evidence для закрытия полного cadence/Stop в T116.

В evidence необходимо сохранять разделение уже принятых понятий:

- Modelled source duration, реальное wall time обслуживания write/checkpoint,
  backlog/deadline наблюдения не один счётчик. Accelerated generated loop не
  доказательство real-time sustained capture. Если измерения выявят проблему,
  она записывается как проблема, не лечится увеличением256KiB/5s/64MiB.
- Worker CLI может обозначить storage-tail/Stop-like cost, но не product Stop
  latency/успешный dispatcher drain: dispatcher/EOS/timeline/finalizer здесь
  отсутствуют. Их отдельная integration/acceptance остаётся обязательной.
- Expiry не убивает native operation и не стирает поздний actual committed
  disk fact. Срок завершился/normal Stop не доказан — не «успешный Stop»;
  поздний storage ACK всё равно хранит верный root/generation/lease. Только
  после actual quiescence допустим last release/cold verification.
- Внешние DPAPI/OS allocations и RSS не входят автоматически в доказательство
  owned allocator cap. Нет новой нормы «каждый замер обязан быть≤1.365s» или
  «cold verify обязан≤5s». Физические/native расходы измеряются и публикуются
  честно, включая неудачи; SC-003/reference-x64 остаётся своим gate.

Scoped analyze: FR-012/013/022, SC-006 → existing T116; SC-003 поддерживается
measurements prerequisite, но не принимается; T117/T118/T120 не закрываются.
Неразмеченных требований или нового executable task для test-only шага нет.
Зависимость step3→step4→schema/adoption5 согласована; constitution conflicts0.

## SHA-256 норм и anchors при чтении

| Артефакт | SHA-256 |
| --- | --- |
| spec | `f59f95b967cf1b2bbf18b44e3a8ee99467418f46d4da2e956361527155132a7d` |
| plan | `5b5996e9c35a185c470f23b6e9228ebe7d46337513741505ba77ffcfe88928e8` |
| tasks | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart | `3045f730bc59bbc3abdeaf736a7e7e347825bdf6e8878bdaa10a34d293113acc` |
| packed contract | `6cb9bc197f44e689c83ddff4dc216ee818867abe06cca99fdd6c2fd8ba992644` |
| base custody contract | `090f4511fb9f3e1aa9fc27caf8ba922f39fc1a5d1d778e7b29a3ae946ec65402` |
| packed-writer checklist | `a1f18f2cdfe6ebcdb369ad0ed6a877f77af4658bc388a4cab1475c50b45b62a0` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| root AGENTS | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| worktrees guidance | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| Spec Kit flow | `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887` |
| product gates | `e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097` |
| release/validation guidance | `e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d` |

## Notes

Нет source acceptance, измеренных timings/memory/IO или claim implementation.
Этот gate разрешает только следующий test-only measurements этап по уже
существующим нормам; не product edits/consumer adoption/installation/audio/
inventory/commit/GitHub/release. Изменён только этот reviewer-owned файл.

## Уточнение test candidate: OwnerTests, не новая норма

Main до code edits уточнил предпочтительный reuse существующего OwnerTests
CLI/Fixture. Его лично прочитанные ранее real Files TU wrappers и codec spy
не заменяют CNG/DPAPI fakecodec; это подходящий test-only выбор без второго
backend/фабрики. Короткий selfcheck2MiB и explicit bench64MiB — параметры
генерированного опыта, **не product bounds** и не сокращение полной обязательной
матрицы quickstart1/2/4/8/16/32/64MiB для последующей приёмки.

Метрики per full checkpoint: реальные DATA/NODE seals, native write/read/flush
counts и requested IO bytes; owned highwater по существующему test allocator
observer; process PrivateUsage/handle counts, sampled после checkpoint.
Requested bytes не называют фактически transferred bytes при short/fault IO;
sampled PrivateUsage не actual OS peak и не доказательство bounded native
DPAPI allocations. Все эти различия — точное именование наблюдений, без новой
threshold нормы или библиотеки.

Правила candidate arithmetic следуют уже принятому §6.0, не изменяют его:

- Для empty birth1 последовательного canonical до explicit tail checkpoint
  generation =1+floor(actual accepted totalBytes/262144). Если remainder≠0,
  подтверждённый tail добавляет ещё одну generation; при remainder0 новая
  no-op generation не требуется. Нельзя применить pre-tail формулу к post-tail.
- Generated full480-float frames имеют1920B. И2MiB, и64MiB не кратны1920;
  bench label — nominal target, не основание объявить actual total точным.
  Количество полных frames/фактический total, remainder и expected generation
  выводятся из реально выбранного input. Никакого padding/скрытого truncation
  для достижения красивого размера. Это требование честных exact bytes, не
  предложение нового product frame format или нового лимита опыта.
- Storage tail checkpoint — **не app Stop/dispatcher/encoder/SC-003 PASS**.
  Cold verification идёт после actual release всех refs; retained pin сначала
  сохраняет старый root, а не даёт cold-open shortcut. Byte identity проверяется
  bounded read, без массива размера записи или plaintext temporary file.

Requirements остаются достаточными для такой test-only candidate;
source/execution acceptance будет отдельной. Product edits/API/libraries/
quotas/schema/consumer adoption этим выбором не разрешаются.

## Конечный статус независимого requirements review

**COMPLETED / PASS — 12 checked / 0 unchecked; C0/H0/M0.** Каждый пункт
оценён отдельно по приведённой таблице; итоговые markers перечитаны и
пересчитаны. Нормы достаточны для bounded generated diagnostic в существующем
OwnerTests CLI/Fixture. Ни один blocked criterion не остался; придуманных
latency/memory/IO thresholds, product API/лимитов или новых tasks нет.

По сообщению main v1 baseline20704 завершён EXIT0: generated16MiB,
15.432s, reads8511/hcreate4607. Это отдельный baseline существующего v1
probe, **не packed cadence acceptance** и не основание считать T116 выполненной;
reviewer его не запускал. Он не использовался для отметки требований.

Следующая допустимая область — test-only измерения по существующим нормам,
с отдельной source/execution review. Продуктовый cadence/Stop, SC-003,
consumer adoption, schema, T116 целиком и Windows/hardware/release не приняты.
Старые accepted отчёты не переотмечены; изменён только этот reviewer-owned файл.
