# Round448 — независимый requirements/checklist/analyze gate native startup B

Дата: 2026-10-16. Lane: high-risk-product, существующая Feature200 / T116 / #7444.
Repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

## Вердикт

**Нормативный GO до реализации узкой native sealing-интеграции B.
Scoped analyze: CRITICAL 0 / HIGH 0; constitution violations 0;
blocking clarification choices 0.** Это не source/runtime acceptance.

Текущие plan/research/data-model/quickstart позволяют подключить существующий
cold capturing/finalizing → sealedDegraded к startup recovery. Private
acquisition выполняется только storage owner, полная проверка/encoding —
существующим recovery executor. Native B не создаёт normal proof, queue mutation
ticket, promotion, HTTP или новый доступ quarantine playback. Прежний
sealedNormal recovery остаётся отдельным strict proof/commit/adoption путём.

Новая схема, persistent поля, dispatcher/pool, account inference, публичная
capability и synthetic V5WriterResult не нужны и не разрешены. T116 остаётся
открытым; T117/T118, installed/hardware/release этим gate не принимаются.

## Fresh baseline и действия reviewer

- Active feature и owner проверены `.specify/feature.json`, branch/HEAD и
  prerequisite-командами checklist/analyze. Owner — `codex`.
- Все **198 checklist-файлов** инвентаризированы. До изменения reviewer:
  **442 checked / 0 unchecked**, aggregate198
  `27d7a70d82118519d3889f5b08707d6592d367dbf349fcb0f667aef0c9b3cb27` —
  точное совпадение с Round447.
- Сохранённый baseline197 без `cold-prefix-recovery.md`:
  `59bc24759fca8106f71173c1b12f19dade015ca887b0471249eaf58c5391d692`.
  Его неизменённые нормативные markers сохранены; исторические runtime/source
  narratives не перечитывались как новая приёмка реализации.
- Перечитаны standalone B CHK001–012, Start-owner CHK001–010, packed-writer
  требования и текущие четыре append448. В существующий
  `checklists/cold-prefix-recovery.md` добавлены только вопросы качества native
  этапа CHK013–022: сначала unchecked, затем независимо сопоставлены с
  указанными в каждом пункте нормами и отмечены supported. Старые 12 пунктов
  не переписаны; прежнее исключение Native integration обозначает границу
  standalone этапа, не запрет последующего этапа.
- После перечитывания: **198 файлов / 452 checked / 0 unchecked**;
  `cold-prefix-recovery.md` — **22 / 0**. Aggregate198:
  `854d7bb9071c38cf7d08f16f2e9651e58a84cd97dcba66cea729de44a19c2e48`.
  SHA самого checklist:
  `fee33dd557d29e4daae29f899051fa0b0de1c12141663cae2825fff0468de21f`.
  Aggregate algorithm: sorted basename + space + SHA-256(file bytes) + LF,
  затем SHA-256 всей последовательности.
- Tasks: **120 / 93 checked / 27 open**, SHA прежний. T116/T117/T118 открыты.
  Local mapping T116 → #7444 — `tasks.md:552`; исполнительная задача — :568.
  Fresh GitHub OPEN не проверялся: user scope запрещает GitHub/VM действия.
- Из 10 нормативов изменились только четыре заявленных append. Удаление
  нового раздела вместе с одной разделительной LF из каждого файла даёт
  точный прежний Round447 SHA; прежние части четырёх файлов сохранены.
  Spec/tasks/три contracts/constitution совпали с baseline побайтно по SHA.
- Использованы текущие AGENTS, guidance index, spec-kit-flow/product-gates,
  tracker/release guidance, relevant PRD/status, constitution и custody fences.
  Hooks before/after checklist/analyze не имеют enabled действий; commit hooks
  отключены. Code/tests/нормы/tasks/GitHub/VM/Git index не изменялись reviewer.

## Scoped analyze / coverage

| Обязательство | Текущая опора и оценка |
| --- | --- |
| Original ownership и fresh row | Spec FR-012/013 и Session 2026-10-16; plan448 п.1; CHK014. Сравниваются original IDs/path/owner/status/reason/updatedAt и server/deletion fences; unrelated generation допустима, изменение самой строки отменяет B. |
| Genuine mutable acquisition | Plan448 п.2–3 + standalone B §1–3; CHK015/016. Временный readonly pair освобождается; writable capability заново создаёт genuine owner под тем же удерживаемым root, без upgrade/caller proof. |
| BOTH/prefix/history/content | Standalone B §2–6; CHK003–009/020. Новая интеграция не меняет unused classification, canonical bytes, privacy/history/optional times, final full inspection/AAC. |
| Threading и ресурсы | Plan448 п.2–3; custody §5; CHK015/017. StoreOwner не уходит executor, full prefix/hash/encode не выполняется на единственном storage worker; прежние memory/job/pin limits сохраняются. |
| Lifetime/Stop/reconciliation | Plan448 п.3/5; custody §5/7 и Start-owner; CHK017–019. Отмена не равна drain; native writer/package/proof освобождены до recoveryDone, owner reopen и physical purge. Record/Stop/EOS не ждут старое encoding. |
| Нет нового публичного допуска | Plan448 п.4/acceptance; data-model handoff; CHK013/021. Degraded не normal proof, не queue effect, не HTTP и не обход playbackRowCurrent. |
| Failure evidence и границы | Quickstart448; CHK009/012/022; constitution VI. Actual cold generated positives, refusal/drain/concurrency, прежние regressions; partial/ambiguous сохраняются без factory retry. |

Покрытие семи scoped групп — 7/7; unmapped scoped work 0. Противоречий между
четырьмя append, spec, T116, custody contracts и constitution не найдено.
Новых продуктовых решений для clarify не требуется. Эти показатели не
являются общей оценкой покрытия Feature200 или выполненности T116.

## Архитектурные риски, обязательные для source/runtime review

Это конкретные риски переноса текущего read-only handshake на mutable B,
а не уже принятый код или требования к новому сервису.

1. **Цикл ambiguous/inFlight/drain.** В текущем `NativeCapture.h:1984–1988`
   reconciliation исключает recovery network; recovery resultReady при этом
   ждёт отсутствия recording/inFlight. `submitProtectedDeletion:1252–1285`
   пока не учитывает recovery token. Если deletion либо concurrent recording
   finalizer получает ambiguous outcome, буквальное сохранение этих ожиданий
   может дать цикл: reconciliation ждёт retirement, retirement ждёт adoption,
   adoption ждёт снятия inFlight. Требования cancellation/actual retirement
   должны быть выполнены без такого цикла: закрыть конфликтующий admission
   либо безопасно обслужить отмену/terminal retirement независимо от чужого
   inFlight. Нельзя ослаблять прежний normal promotion/stale-dispatch fence или
   переоткрывать owner при живом writable package. Это реализационное условие,
   не разрешение признавать timeout завершением.
2. **Split до тяжёлой проверки.** Текущий `V5LocalRecordingWriter.cpp:142–188`
   после `openUnfinished` сразу делает inspectUnfinished/history/Tree::verify.
   Prepare должен закончиться на genuine acquisition/распределении terminal
   writer, а не переносить эти full walks на storage thread. Полная проверка
   и эффекты finish — вне work mutex. `openUnfinished` сохраняет существующие
   native/bounded metadata guards; это не повод убрать их.
3. **Ни одной лишней живой ссылки.** Пробный pair не должен пережить переход к
   writable acquisition: он может удерживать конфликтующий package-state
   handle. Writer передаётся однократно; proceed=false, cancellation и exception
   также обязаны освободить writer/package/readers на executor и довести
   handshake до фактического done. B-результат не помещается в recoveryProof.
4. **Fresh row не current account.** Сравнение с исходной reservation, а не с
   вошедшим после restart B; пустые/unknown/legacy поля не backfill. Снимок
   initial scan сам по себе не разрешает effects. Проверка непосредственно
   перед acquisition и cancellation при последующем изменении/deletion
   выполняются worker-side. Unrelated Start может менять общий generation,
   не разрешая менять old row и не отменяя её только из-за общего счётчика.
5. **Не регрессировать ownership/квоты.** Concurrent old recovery + live writer
   + playback остаются в прежних limits. Quota/IO/cancel могут законно отказать
   с сохранением partial artifacts; нельзя повышать limits, повторять factory
   поверх started outputs или объявлять normal/playable по одному phase.

## Минимальные реальные доказательства следующего шага

- Cold capturing и finalizing с genuine owned A reservation, birth owners
  освобождены, current account B. До startup ACK нет recovery effect; после
  actual executor completion cold full inspection/AAC доказывает degraded,
  exact prefix, history/optional times/session/IDs; canonical и полная очередь
  неизменны. Нет B queue mutation ticket, normal proof, protected HTTP или
  новой recording factory. Startup ticket и посторонний Record ticket считать
  отдельно, не требовать ложного отсутствия всех tickets вообще.
- Held canonical read на executor + genuine новый Start/ACK/frames/Stop/EOS:
  новая запись обслуживается до release old read. Проверить старую row и
  legitimate global generation change отдельно; включить прежний real playback
  regression, не подменять его UI-флагом.
- Actual changed-row/deletion/server/alias fence перед acquisition: отказ без
  content effects. Started/orphan/already-degraded также не перезаписываются.
  Unknown/no-login не назначаются B. Проверки лишь одного happy owner мало.
- Stop/update/shutdown/lost poll при held recovery: отмена наблюдается без
  ожидания завершения всего decode, но actual owner lease удерживается до
  release/drain. Physical purge и owner reopen запрещены до него. Реальный
  ambiguous deletion/finalizer вариант должен показать отсутствие цикла п.1,
  без fake network/proof и без silent redispatch прежней команды.
- При отказах учитываются достигнутая стадия и partial artifacts; unchanged
  disk обязателен для pre-effect refusal, но не утверждается после публикации.
  Старые crash cuts standalone B не заменяют native handshake tests. Прежние
  sealedNormal recovery, degraded restart, concurrent recording/playback,
  revalidation/consumer и V5 regressions должны иметь fresh результаты.
- Exact source manifest/current, actual PE, executed names/cases/markers,
  receipt exit/elapsed/timeout и postflight/process evidence квалифицируются
  позже. Runtime Round448 сейчас не выполнялся reviewer и не принимался.

## Текущие 10 нормативных SHA-256

Пути относительно feature directory, кроме constitution.

| Файл | SHA-256 |
| --- | --- |
| spec.md | `0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11` |
| plan.md | `cb5d5c9edeea9863ed8bc8354b59cd929ba554c9dcafb9dc20d882d80294ab08` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `c352f1b9a4970a3468bb66e52638c377aefcf075c60876a9d06bb87364b25e38` |
| data-model.md | `4d03cbc8517403e1bd754dff0dc7aa877a21a03309aec5de1c1b8f5bacb1815f` |
| research.md | `6c1b4432fc37af7eb97f7d9202072344b0c8e5ccf7724d26ad3081ec8b79f716` |
| contracts/windows-desktop-contract.md | `8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4` |
| contracts/windows-protected-local-custody.md | `38c86bcb8a600dcff0a76098099b1876c4d783238f39c44a8d3712dcce2c7f93` |
| contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Разрешён следующий tests-first/implementation шаг только в указанном scope.
Ни checklist, ни этот report не разрешают commit/push/GitHub mutation,
закрытие задачи/issue, изменение admission/schema или quarantine playback.

## Append-only refresh — GREEN6 qualification / оставшиеся сценарии

2026-10-16. Повторная независимая сверка без новых markers и без повторного
исторического runtime-аудита: **198 файлов / 452 checked / 0 unchecked**.
Aggregate по прежнему алгоритму
`854d7bb9071c38cf7d08f16f2e9651e58a84cd97dcba66cea729de44a19c2e48`
совпал с baseline этого отчёта. Все **10/10 нормативных SHA** из таблицы выше
совпали с текущими файлами. Tasks SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`,
120 tasks = 93 checked / 27 open; T116 открыт, local owner mapping #7444.
Active feature owner codex / high-risk-product / HEAD b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1
сохранены. GitHub state не запрашивался. Enabled before/after checklist/analyze
hooks отсутствуют; никаких commit/sync действий не выполнено.

Scoped analyze оставшегося test-only continuation: **CRITICAL 0 / HIGH 0**,
constitution violations 0, unresolved normative choices 0. Две группы имеют
существующее покрытие T116, новые task/checklist/plan append не требуются:

1. Уточнение штатного no-change auth prepare ACK не изменяет authority или
   durable truth: plan448 п.4, Start-owner CHK003/005/009, B CHK013/021. B не
   создаёт mutation ticket; это не запрещает отдельный legitimate auth intent.
   Ticket kind/state квалифицируются по фактической production ветви, а не
   объявлением no-change commit. В частности, здесь no-change uploadPrepare
   штатно notCommitted/no-error; это source clarification, не нормативная правка.
2. Actual Stop/EOS новой записи **до release** held old B canonical read прямо
   задан plan.md:2401–2405 и quickstart.md:1066–1068; B CHK018/022 и Start-owner
   CHK010 сохраняют Record/Stop, limits и actual drain. Нужны real Start
   reservation ACK/factory/frames, Stop/EOS observation при всё ещё held cut,
   затем release/retirement и cold exact rows/owner/canonical/queue/generation
   в соответствии с реально опубликованными эффектами. Не объявлять encoding,
   callback или cancellation признаком drain; не повышать limits.

Прежний plan.md:2113–2150 относится к более раннему sealedNormal upload
inspection regression, который освобождал read перед полным finalization/drain.
Новый B-вариант не заменяет и не ослабляет тот тест: explicit Round448 сценарий
проверяет дополнительную границу. Его fresh runtime ещё не принят этим gate.
Ambiguous/deletion/changed-row и остальные ранее названные cuts сохраняются
открытыми до собственных доказательств. T116 целиком, T117/T118 и публичная
готовность не принимаются. Checklist markers и нормы не менялись; appended
только reviewer reports.

## Append-only pre-implement refresh — purge и ambiguous concurrent finalizer

2026-10-16, после bounded GREEN12 acceptance. **Нормативный GO** для двух
следующих сценариев существующего T116: (1) actual committed deletion intent
→ physical purge при held cold B read; (2) ambiguous finalizer новой записи
до release held old B read. Scoped analyze: **CRITICAL0/HIGH0**, constitution
violations0, unresolved normative choices0; покрытие двух групп2/2. Это не
source/runtime GO новых сценариев и не перенос GREEN12 PASS на них.

Свежая проверка: authoritative branch codex/200-windows-followup, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, feature200/owner codex/high-risk-product.
**Все10/10 нормативных SHA** таблицы этого отчёта совпали с текущими файлами.
Все198 checklist files инвентаризированы: **452 checked/0 unchecked**,
aggregate `854d7bb9071c38cf7d08f16f2e9651e58a84cd97dcba66cea729de44a19c2e48`
неизменён. Перечитаны B CHK013–022 и Start-owner CHK001–010; новых markers или
checklist не требуется. Tasks120 =93 checked/27 open, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`;
T116 открыт, local mapping tasks.md:552/#7444, task:568. GitHub OPEN сейчас
не запрашивался и не выдаётся за fresh remote fact.

Основания и обязательные границы:

1. **Committed delete → purge.** Plan:2401–2405 прямо требует cancellation B
   и ожидания actual retirement до purge; quickstart:1065–1069 и B CHK017/019/022
   сохраняют этот сценарий. Local-custody:232–239, :302–308 требуют intent ACK
   → закрыть admission/cancel/quiesce → actual OS absence → removed ACK.
   Реальный cut должен доказать held nonempty canonical read, committed intent
   и отдельную adoption, затем отсутствие преждевременного purge/removed ACK
   пока executor/package/pins ещё живы. После release нужен actual retirement,
   действующий confined recycle/purge helper и fresh absence/обычный durable
   removed ACK. Cancellation flag, timeout, пустая UI projection или уже missing
   path не заменяют эти доказательства. Не расширять authority: local user
   delete остаётся existing Recycle Bin-only, server purge/short — своими
   существующими путями. При отказе сохранять pending intent/lease/artifacts.
2. **Ambiguous new recording finalizer while old B held.** Plan:2401–2405,
   local-custody:210–239/Start-owner:630–638, B CHK018 и Start-owner CHK005/009/010
   уже требуют удержания scalar finalizer result+lease до ACK/reconciliation,
   exact-row update и запрета normal/Saved/new-effect при ambiguous outcome.
   Нужны genuine новый Start/reservation ACK/frames/EOS и реально достигнутый
   queue-qualified ambiguous publication до release old read, не один enum
   или инъекция до публикации. Наблюдать отмену/retirement старого B без цикла
   inFlight→reconciliation→recoveryDone и без owner reopen при живом writable
   package. После release — actual fresh reconciliation, отдельная adoption,
   exact row/IDs/original owner/server/deletion/generation и cold content proof.
   Не требовать успешного reconciliation до release, если для него законно
   необходим фактический retirement удерживаемого package. Не заменять
   ambiguous результат автоматическим повтором finalizer/encode/factory.

Source follow-up должен использовать existing helpers, private authority и
прежние job/pin/memory limits; новые wire/schema/fields/pools/publisher, account
inference, quarantine playback или normal promotion этим gate не разрешены.
Generated-data metadata-only evidence, actual reached cut, order observations,
exact source216/PE/receipt/cold assertions и fresh adjacent regressions нужны
позже; самостоятельных VM/test запусков reviewer не было.

Skill refresh: speckit-checklist применён как проверка существующих требований,
без генерации нового checklist; scoped speckit-analyze выполнен по активным
spec/plan/tasks/constitution и relevant custody guidance. У локального
prerequisite script нет опции --require-spec из skill: она безопасно отказала,
после чего supported --json --require-tasks --include-tasks успешно вернул
active Feature200; наличие spec проверено чтением/hash. Enabled before/after
checklist/analyze hooks0. Изменён только этот reviewer-owned report; code,
norms/tasks/checklists/GitHub/VM/commits не менялись. Новые требования, plan
append, clarify и task/issue не нужны. Umbrella T116/T117/T118 и внешние
installed/hardware/release gates остаются открытыми.

## Append-only pre-implement refresh — changed-row при held cold B read

2026-10-16, после bounded Round449 GREEN6. **Нормативный GO** для проверки
changed-row существующего T116, без нового плана, task, checklist или authority.
Scoped analyze: **CRITICAL0/HIGH0**, unresolved normative choices0. Это не
source/runtime GO будущего diff и не закрытие T116.

Свежая проверка authoritative branch/HEAD: codex/200-windows-followup /
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Все10/10 нормативных SHA
таблицы этого отчёта совпали. Checklist inventory198 files, **452 checked /
0 unchecked**, aggregate
`854d7bb9071c38cf7d08f16f2e9651e58a84cd97dcba66cea729de44a19c2e48`.
Tasks120=93 checked/27 open, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
T116 открыт, local mapping #7444 сохраняется; remote GitHub сейчас не
запрашивался. Plan:2381–2386/2401–2405, quickstart:1065–1069 и existing B
CHK014/017–020/022 уже требуют exact original reservation, cancellation при
её изменении и actual retirement до purge. Новая нормативная развилка не нужна.

Свежий production trace ограничивает достижимую матрицу:

- NativeCapture.h:816–851 `requestProtectedDeletionSelection` с ownOrigin
  проверяет текущую projection и original owner. QueueService.cpp:245–315
  переводит own no-server row в quarantined/local_delete_pending, меняя время,
  но сохраняя IDs/path/owner. NativeCapture.h:731–764 public local-removal
  front door достигает того же intent через canLocalRemoval/planLocalRemoval
  (QueueService.cpp:937–963), с проверкой exact snapshot/epoch.
- NativeCapture.h:1259–1271 сам заранее cancels recovery для intent/purge;
  purge ждёт actual token retirement. Поэтому такой runtime доказывает
  безопасное изменение/отмену/retirement, но НЕ изолированный вызов каждого
  сравнения recoveryRowCurrent (NativeCapture.h:1471–1482).
- Ручной retry/confirmUnowned не допускается для quarantined/capture_prepared:
  retryableStatus (QueueService.cpp:91–95) исключает quarantine, а native
  manual-send проверяет его до dispatch. Ordinary auth recovery изменяет только
  needsAuth, automatic upload не выбирает quarantine. Server-task local purge
  требует uploaded/server-bound row и не является способом изменить eligible B.
  Новый genuine Start создаёт другую reservation, не перепривязывает старую.

Минимальное evidence будущего runtime:

1. Реально held nonempty canonical read на owned-A capturing/finalizing;
   current A, genuine ownOrigin deletion intent → actual commit/adoption
   g2→g3, exact preserved IDs/path/owner и local_delete_pending. Удержать
   continuation без запуска purge; после release/actual drain cold queue g3
   и original package/root content unchanged, без B seal/normal/HTTP. Полный
   root SHA до/после queue mutation не должен ошибочно требоваться неизменным:
   сравниваются package/canonical bytes и точное ожидаемое изменение metadata.
2. Второй public front door — local removal с actual adopted snapshot/epoch.
   Допустимо параметризовать прежний 449 purge fixture: intent ACK → held
   recovery/drain fence → actual purge → retained purge ACK/absence/cold queue.
   Это reuse существующего сценария, не новая система fixtures.
3. На held fixture короткие admission negatives: current B не может удалить A;
   current A не может manual-send/claim quarantine (включая confirmUnowned).
   Stale epoch/snapshot брать из настоящего предыдущего adopted value, а не
   из synthetic projection. Refusal не должен создавать ticket, менять owner,
   исходную строку или package; unrelated real Start/Stop generation control
   можно сохранять из уже принятого 449, не дублируя полный matrix.

Отдельные произвольные изменения UUID/path/owner/server/status через fake
projection, прямую подмену disk/worker value либо второго owner при живом
lease не являются legitimate native public-командами. Их не нужно изобретать
ради fieldwise runtime coverage. Полнота сравнений остаётся отдельной source
проверкой: sameUploadIdentity включает IDs/path/owner/status/attempts, native
добавляет reason/updatedAt/noServer/alias conflict. Changed-row через intent
и generic row predicate нельзя объявлять одним и тем же наблюдением.

Full-app diagnostic build без install — отдельная будущая проверка compile/
link с собственной exact-source/PE evidence; наличие guest dependencies и
ресурсов в этом read-only gate не проверялось. Она не заменяет named native
cut и не открывает installed/hardware/release gates. Reviewer не запускал
VM/build/tests/GitHub и не менял source/norms/tasks/checklist markers.

### Round450 supplement — full-app compile diagnostic

Existing normative gate также допускает full Release x64 compile/link как
diagnostic без install/launch/migration; новые требования, plan/task/checklist
не нужны. Quickstart:23–40 прямо содержит solution Release x64 build и
отличает его от CMake/CTest runtime. Release-and-validation:174–199 допускает
read-only review и optional local diagnostic, не заменяющий exact-SHA PR/
release gates. Этот GO разрешает scope проверки, а не предсказывает PASS.

При reuse AEC cache сохраняются существующие GrafWindowsApp.vcxproj:190–192
и build-graf-aec3.ps1:155–175: x64, pinned backend/стандартная library,
identity и artifact provenance; failure не обходится переключателем,
подменой library или новым provenance для непроверенных bytes. Для будущего
compile receipt нужны точные source216 pre/post, реальные restore/build exit
codes, Release/x64/toolchain и AEC verifier result, фактический output app PE
hash; timestamp/incremental stale output не является новым compile proof.
Диск/guest deps и AEC provenance reviewer не проверял в VM. User сообщает
проверенные VS2022/cached NuGets; это не выдано за независимое наблюдение.
Никакого install/launch/migration, SDK runtime/hardware/full T116 GO нет.
Evidence root указан main: /Users/yshishenya/Documents/graf-f200-build450.rXty3N.
