# Round447 — независимый pre-implement gate отказов и process-crash cuts B

Дата: 2026-10-16. Lane: high-risk-product, существующие Feature200 / T116 / #7444.
Repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

## Вердикт и область

**Нормативный GO до test edits. Scoped analyze CRITICAL 0 / HIGH 0;
constitution violations 0; blocking ambiguities 0.** Существующие требования
достаточны для реальных IO/cancel и process-crash cuts `V5::recover` по
media/playback/recovery/manifest/package publication и ACK. Новые требования,
checklist, task, persistent schema или Native integration для этого не нужны.

Основания: plan construction B §1–7 и заключительная acceptance часть
(`plan.md:2316` onward); quickstart construction B (`quickstart.md:1037` onward),
особенно отдельный учёт каждого publish/rollover/final ACK cut;
`cold-prefix-recovery.md` CHK002–012, в особенности CHK009/010/012;
local custody §4–5 и packed custody cold/BOTH closure. Spec FR-012/013/014/022,
SC-003/005/006 и T116 задают сохранность, no-normal и ограниченные ресурсы.

Этот gate не принимает будущий test source, hooks/linkage или runtime. Он не
добавляет право продолжать started/partial outputs, ремонтировать metadata birth
или выпускать normal/upload authority. T116/T117/T118 остаются открытыми.

## Fresh baseline

- Active feature подтверждён `.specify/feature.json` и одним выполнением
  `check-prerequisites.sh --json --require-tasks --include-tasks`.
- Все **198 checklist-файлов** инвентаризированы: **442 checked / 0 unchecked**.
  Старые markers не изменялись, новый checklist не создавался.
- Полный aggregate198 SHA-256:
  `27d7a70d82118519d3889f5b08707d6592d367dbf349fcb0f667aef0c9b3cb27`.
- Прежний aggregate197 (без `cold-prefix-recovery.md`) совпал с Round446:
  `59bc24759fca8106f71173c1b12f19dade015ca887b0471249eaf58c5391d692`.
  Алгоритм: сортированные basename + пробел + SHA-256 файла + LF, затем SHA-256.
- 12 пунктов B перечитаны и сопоставлены с текущим scope; дополнительно
  перечитаны относящиеся к scope packed-writer/start-owner/privacy требования
  и действующие custody/constitution/guidance положения. Неизменённый baseline
  прочих checklist сохранён; исторические runtime/source review narratives
  не переинтерпретированы как новая приёмка cuts.
- Все **10 нормативных SHA** совпадают с отчётом Round446 (таблица ниже).
- Tasks: **120 / 93 checked / 27 open**, SHA неизменён. Local tasks связывают
  T116 с #7444; fresh live OPEN GitHub этим review не проверялся.
- До этого gate current source совпал с принятым manifest446 **216/216**,
  manifest SHA `0ce68a9c89559f1937a0be3250500bac3aa1ea3d2350a8f12d7ad9880da1b6da`.
  Новые Round447 production/test edits этим review не принимались.

## Scoped analyze / coverage

| Существующее обязательство | Покрытие / результат |
| --- | --- |
| Existing-only capability, непрерывные root/role leases | Plan B §1–3; CHK002–004; T116. Инъекция в test TU не даёт caller proof или новых writable полномочий. |
| BOTH authority, unused против partial/started | Plan B §2–3; custody §4; CHK003–006. Fresh classification по actual inventory/BOTH, не default/fallback. |
| Canonical/queue/original owner неизменны | Plan B §5/7; FR-012/013; CHK005/011. Полные maps/hashes и actual IDs/session/history, не один scalar success. |
| Публикация, rollover и ACK | Plan B §6; quickstart B; CHK008/009/012. Каждый physical cut имеет отдельный достигнутый event и исход. |
| Ошибка после эффекта не является успехом | Custody §4, CHK009. Исход failed/ambiguous call и отдельный результат fresh inspection не смешиваются. |
| Ограниченные ресурсы/retained ownership | Custody §5; CHK010. Cancel/IO/quota и последний release не ослабляют текущие limits и first fault. |
| Проверяемые доказательства и границы | Quickstart B; CHK012; Constitution VI. Exact source/PE, actual child termination, cold reopen, непроведённые cuts явно open. |

Семь проверенных групп обязательств связаны с существующей T116: 7/7;
unmapped scoped work 0; противоречий/дублирующих требований, требующих ремонта,
не обнаружено. Это не общая coverage оценка Feature200 или статус реализации
всех FR/tasks. Старые неполные implementation gates не закрываются.

## Допустимый уточнённый test design

Test TU + scoped CMake linkage exclusion может компилировать настоящий Files.cpp
с wrappers `WriteFile`, `FlushFileBuffers`, `GetProcAddress(NtSetInformationFile)`
по существующему native-test pattern. Production switches, новая public proof
authority и формат не нужны. Корректность отсутствия duplicate Files symbols,
реального делегирования native calls и selector попадания проверяется позже
по конкретному diff/build, а не считается доказанной этим gate.

Успешный generated recover может собрать trace first-write/first-flush packed
media/playback и before/after всех metadata renames, включая finalizing,
manifest rollover, recovery и sealedDegraded. Затем fresh fixture на каждый
event: child исполняет настоящий recover и аварийно завершает себя через
`TerminateProcess(88)` в целевом физическом событии. Parent ждёт actual handle;
birth owners/унаследованные handles не должны подменять cold reopen.

Это допустимое доказательство process-crash boundary, **не power-loss durability**.
IO error return/cancellation и process termination — разные виды инъекций;
прошедший вариант одного не означает выполнение другого. Late inspection
cancel/quota не считается проверенным только по pre-effect budget refusal.

## Требования к evidence по существующим нормам

1. **Достигнутый cut.** Для каждого planned event — role/context, operation,
   before/after, ordinal при необходимости, hit count и native result там,
   где вызов уже вернулся. Привязка к actual handles/target operation;
   evidence writes не должны становиться целевым storage event. Ни broad
   Nth-call count, ни один только exit88 не доказывают нужную boundary.
2. **Настоящий процесс.** Fresh generated fixture; child actual recover,
   подтверждённые targeted hit и завершение с88, parent wait на реальном handle.
   Destructor cleanup не выдаётся за crash. Другие процессы/тесты не убиваются.
3. **Инварианты.** Exact canonical SHA/size, полный service queue/bootstrap
   map/SHA и owner/session/role IDs неизменны. История/optional times не
   выдумываются. Полное равенство package root после возможных эффектов не
   требуется: новые protected outputs/package generations могут законно остаться.
4. **Fresh classification.** После release/termination используются genuine
   fresh owner/readers, BOTH и полная closure. Bad/singleton/unbound metadata
   не откатываются к удобному старому slot; нет empty queue, identity rebirth,
   plaintext fallback, normal claim или unsafe deletion/GC.
5. **Различать исходы.** До эффектов — unchanged disk. После одного finalizing
   ACK outputs ещё могут быть доказанно unused: fresh explicit recover может
   правомерно завершиться, если все прежние guards снова выполнены. После
   content birth/partial/orphan outputs текущий B отказывает без изменения,
   не чинит/перезаписывает и не делает blind retry. Эти исходы определяются
   диском, а не общим attempted-effect boolean.
6. **Post-seal.** Неуспешный/оборванный вызов не получает playable success.
   Если fresh read находит действительно завершённый sealedDegraded, отдельная
   full semantic inspection и actual AAC decode могут доказать этот факт;
   это не ретроактивный ACK старого вызова и не normal. Mere phase/header/AAC
   encoder return недостаточны. Неполный пакет остаётся сохранённым отказом.
7. **Привязка и учёт.** Source216 до/после, manifest/actual PE hashes, actual
   exit/elapsed/timeout, terminal receipt, logs и сохранённый process0;
   skipped/unhit cuts не PASS. Trace count и число квалифицированных cuts
   сверяются явно. Primary и необходимые adjacent native regressions имеют
   собственные результаты; historical446 PASS не является выполнением447.
8. **Ограничения.** Generated data и metadata-only evidence. Нет реального
   account/audio/network/install. Current resource caps не увеличиваются;
   teardown/last release и error propagation проверяются в фактически
   исполняемых случаях. Неисполненные late inspection/IO/power-loss cuts
   перечисляются отдельно, без заявления всей crash matrix.

## Нормативные SHA-256 — совпали с Round446

Пути относительно `specs/200-windows-desktop-app/`, кроме constitution.

| Файл | SHA-256 |
| --- | --- |
| spec.md | `0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11` |
| plan.md | `e035ba133f121620eb0df8c6fa4f8fba823127fe075bc392e474ae79bda0d6c2` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `8a6eebb7f5b1b5d21932e1822b2ff0f9404db4a1a60d06d57aa5636f0b38170a` |
| data-model.md | `d8e264aa7b2756390c1482033942ff944c9482045968daf16f93fdb438076a87` |
| research.md | `fb4877fa1e9b489fa8a794204c583e86a23e4a7d01b1327571e0b659e717fe06` |
| contracts/windows-desktop-contract.md | `8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4` |
| contracts/windows-protected-local-custody.md | `38c86bcb8a600dcff0a76098099b1876c4d783238f39c44a8d3712dcce2c7f93` |
| contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| .specify/memory/constitution.md (repo root) | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Review actions: создан только этот отдельный отчёт. Checklist markers, code,
tests, spec/plan/tasks/constitution/guidance, GitHub, commits и VM не менялись.
Analyze prerequisites выполнены; enabled before/after analyze hooks отсутствуют.
Разрешён следующий tests-first шаг в указанном scope; никакая runtime
приёмка Round447 и никакое закрытие T116 этим отчётом не заявляются.
