# A6 PR check requirements review

Owner: independent reviewer. Scope FR-038–041 / SC-019, T058–T063. Implementation may not check items.

- [X] CHK001 Are trust boundaries, fork handling and trusted policy/source separation explicit?
- [X] CHK002 Are body-only, retarget, unknown-event, cancelled and skipped-check outcomes complete?
- [X] CHK003 Are conservative native scope, exact inputs and mandatory result requirements clear?
- [X] CHK004 Is activation additive before removal, with current protection read-back and no gap?
- [X] CHK005 Are closeout/freeze, historical policy and post-merge freshness limits covered?
- [X] CHK006 Are verification, task paths and absence of unsupported merge-queue claims traceable?

## Independent review — 2026-09-13

Result: BLOCKED (5/6 supported). Requirements review within the active high-risk CI/governance slice; marks assess requirements, not implementation or live protection.

Supported: CHK001 → FR-039, A6 owner-trust clarification, plan §A6.3, SC-019; CHK002 → FR-038/040, plan §A6.2/4; CHK003 → FR-038, plan §A6.1/2, T058; CHK004 → FR-041, plan §A6.4, T060 → T061, quickstart A6; CHK006 → SC-019, T058–T063 and quickstart A6. Existing owner/admin trust is retained; no new service or trust architecture is required. Merge-queue availability is treated as the declared scope assumption, not independently verified online.

Blocking gaps for CHK005:

- **HIGH — exact base freshness at consumers.** FR-038/039 bind individual checks to head/base, but plan §A6.5 requires only workflow/event/head/conclusion across the three results; quickstart A6 likewise names final body/source SHA without explicitly requiring a common checked base. Require all three results to bind to the same final PR head/base and reject missing or different bases, including same-head retarget/base advancement and a fresh metadata result beside stale code/native results. For merged PRs, identify the saved final checked base and its relationship to the actual merge history; merely being an ancestor is insufficient to distinguish an older base. Existing `scripts/validate-issue-closeout.py:_github_run/_github_pr/verify_feature_runs` has no base binding, and `scripts/validate-release-train.py:validate` does not require a base in each PR receipt, so current consumers do not fill this requirement gap. Add these negative acceptance cases to SC-019/quickstart and T062–T063.
- **HIGH — historical policy selection.** Plan §A6.5 pins the foundation commit but also preserves historical pre-cutover evidence; T060 and quickstart place activation after that merge. Specify the deterministic rule using the real boundary: which policy applies to the foundation PR itself, PRs merged between foundation and activation, and PRs already open at activation or updated afterward. State how missing/ambiguous boundary evidence fails closed rather than selecting the historical exemption. The future SHA need not exist yet; the selection rule must be defined before T062 can preserve history without exempting a current PR.

Reviewed current A6 spec/plan/tasks/quickstart and relevant local metadata/workflow/closeout/train source only. No tests, Docker, network, commits, issue actions or other agents; only this reviewer-owned checklist was edited.

## Независимая повторная проверка CHK005 — 2026-09-13

Результат: PASS. Оба HIGH-пробела CHK005 устранены на уровне требований; чек-лист 6/6 с сохранением прежних оценок CHK001–004/006 без их повторной проверки. Режим: проверка требований в существующем высокорисковом этапе CI/governance; изменён только этот документ. Предыдущий BLOCKED и его основания выше сохранены как история.

- **HIGH — exact base freshness at consumers: устранён.** [spec.md:276](../spec.md#L276), [plan.md:225](../plan.md#L225) требуют общего final head/checked base для code receipt, native scope и metadata snapshot с привязкой к проверенному run/attempt. Для открытого PR база равна текущей API base: retarget или продвижение базы при прежнем head не допускают старые результаты. Для squash проверенная база равна первому родителю merge commit, для linear rebase — предшественнику диапазона по сохранённому числу коммитов с линейной исходной историей; итоговые деревья равны final head. Одного отношения предка недостаточно, неизвестная форма слияния блокируется. [quickstart.md:308](../quickstart.md#L308) явно покрывает свежие metadata со старой code base, отсутствующую native base, несовпадение head/base, просроченные/смешанные попытки, старого предка, различие деревьев и неверный rebase. [spec.md:280](../spec.md#L280) определяет обновление metadata после merge по неизменяемой истории с двумя совпадающими снимками, отказ для closed/unmerged и срок хранения доказательств 90 дней; свежие metadata не обновляют доказательства кода/native.
- **HIGH — historical policy selection: устранён.** Финальное [уточнение spec.md:278](../spec.md#L278) и [plan.md:225](../plan.md#L225) конкретизируют прежнюю формулировку foundation boundary: SHA/PR подготовительного слияния сохраняются, но граница выбора политики — UTC успешного protection read-back. Только уже слитые PR с `merged_at < activation`, включая foundation PR и промежуточные слияния, используют combined policy. Открытые при активации PR, старые ветки после обновления и любое слияние ровно в момент активации или позднее требуют все три проверки независимо от возраста head. Отсутствующее, некорректное или неоднозначное подтверждение активации не даёт исторического исключения; прежний gate сохраняется до cutover. Эти граничные случаи перечислены в [quickstart.md:308](../quickstart.md#L308).

Доказательства этой повторной проверки: только финальные абзацы A6 в spec.md, plan.md и quickstart.md и два ранее записанных HIGH-пробела. PASS не подтверждает реализацию, выполнение сценариев или живую активацию protection. Код, тесты, сеть, Docker, коммиты, issues и другие агенты не использовались; остальные изменения сохранены.
