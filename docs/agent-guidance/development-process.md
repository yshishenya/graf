# GRAF Development Process

This is the short operator runbook. Detailed product gates remain in the
constitution and linked guidance; this file only routes a feature through them.

## Roles and ownership

| Role | Owns | Must not do |
|---|---|---|
| Product owner | goal, priority, acceptance and release approval | silently change a running candidate |
| Feature agent | one worktree, branch, Feature ID, owned source/spec/fragment | edit another feature's context or root changelog |
| Reviewer | requirements, checklist state, risk acceptance and evidence | let implementation mark reviewer checkboxes |
| Dev operator | single Dev manifest, promote/rollback/status/smoke | activate two SHAs or touch production |
| Release operator | candidate freeze, one Full CI, CalVer/tag/Release/notes | release a floating branch or stale evidence |

## Start a feature

1. Start from `/Users/yshishenya/Documents/crisp` or a disposable Codex
   worktree based on `origin/master`.
2. Check `git status --short --branch`, exact `HEAD`, remote and
   `.specify/feature.json`.
3. Reserve a collision-free Feature ID and umbrella GitHub issue before branch
   or spec creation. The online allocator checks the candidate with bounded
   exact GitHub searches, ignores the requested branch ref, and fails closed on
   lookup errors. Never use only the local maximum.
4. Run the full significant/high-risk sequence:
   `specify → clarify → plan → checklist → tasks → analyze → taskstoissues →
   implement → converge → quickstart → fast validation`.
5. Keep root `AGENTS.md` stable. Active feature/task context is per-worktree in
   ignored `.specify/feature.json`; no mtime fallback is allowed.

## Agent context budget

- Load root rules, then only the active feature's `spec.md`, `plan.md`,
  `tasks.md`, `quickstart.md`, relevant contracts and risk guidance.
- Do not load all historical specs, all worktrees or complete CI logs into the
  prompt. Use bounded summaries and links.
- The optional Spec Kit context updater writes only the ignored
  `.dev/active-feature-context.md`; it must never replace the stable root
  `AGENTS.md` with a current feature plan. `.specify/feature.json` remains the
  authoritative per-worktree pointer.
- Every state-changing command prints Feature ID, task and exact SHA in
  metadata-only output.
- If the active pointer is missing, malformed or points outside the current
  worktree, stop rather than guessing.

Codex instruction discovery follows the official OpenAI contract: global
guidance is loaded first, then project and nested-directory guidance; the
closest non-empty file wins, and `AGENTS.override.md` replaces `AGENTS.md` at
the same directory level. Keep this file and the root `AGENTS.md` concise: the
default combined instruction budget is 32 KiB. Put task-specific procedures in
one scoped guidance file and verify the active chain from a fresh Codex run;
never copy the whole repository history into always-on instructions. See the
[official AGENTS.md guidance](https://developers.openai.com/codex/guides/agents-md).

## Делегирование вспомогательным агентам

Если делегирование разрешено действующими инструкциями или пользователем,
основной агент до начала работы задаёт вопрос и ожидаемый результат, роль,
владельца и рабочую копию, разрешённые файлы и действия, проверки и запрещённые
побочные действия. Внутри активной фичи обязательны Feature ID и task IDs.
Для разрешённого прямого задания только для чтения или docs/mechanical без фичи
указать репозиторий, точный SHA, lane и «feature/task: не применимо — активная
фича не требуется»; создавать фиктивную фичу или issue ради делегирования нельзя.
Эта процедура сама по себе не даёт разрешения создавать агентов.

- **Исследователь только для чтения** возвращает вывод, проверенные факты,
  точные источники (SHA, строки или ссылки), результаты проверок и ограничения.
  Он не меняет файлы, Git, GitHub, приложение или данные и не выполняет выпуск
  или развёртывание. Проверку, которая создаёт файлы или меняет состояние,
  передаёт основному агенту для отдельного назначения исполнителю.
- **Исполнитель** получает одного явного владельца и одну рабочую копию задания,
  перечень разрешённых файлов и проверок. Ему сообщают, что другие участники
  также работают в репозитории: их изменения нужно сохранить. Несколько
  исполнителей могут писать только непересекающиеся файлы. При пересечении или
  неясном владении запись затронутых файлов останавливается до явной передачи
  владения; отменять чужие изменения или присваивать соседний файл нельзя.
  Остальная разрешённая работа может продолжаться.
- **Новая задача вне назначения** передаётся основному агенту с фактами и
  предлагаемым следующим шагом. Найденная проблема не расширяет полномочия:
  для её изменения нужно новое явное назначение.
- **Независимый проверяющий** получает отдельное явное право менять только
  назначенный reviewer-owned checklist и свой отчёт по правилам Spec Kit.
  Это исключение не разрешает исследователю запись в проект или проверяющему
  изменение кода, spec/plan/tasks, Git, GitHub, приложения или данных.

Ответ агента краток: вывод; источники и точная версия; изменённые файлы, если
запись разрешена; команды, результаты и пропуски проверок; ограничения и
неопределённость; следующий шаг. Не передавать секреты, личные данные,
содержимое встреч или весь диалог.

Основной агент сверяет фактические файлы, источники и результаты проверок с
назначением, а не принимает сообщение PASS за доказательство. Ответ другого
агента не заменяет обязательное независимое ревью. Делегирование не расширяет
разрешения на commit, merge, release или deploy: действуют отдельные разрешения
пользователя и существующие ворота проверки.

## Parallel development and Dev testing

Development is parallel; manual end-to-end verification is serialized:

```text
feature worktrees (parallel) → focused checks / fast CI
        → one selected exact SHA
        → build → promote (lock) → status → smoke
        → one /Applications/GRAF Dev.app + one active manifest
        → rollback or next promotion
```

Builds may run concurrently, but only one manifest is active. Promotion is
lock-protected, atomic and reversible. The Dev app keeps bundle ID
`pro.2brain.graf.dev`, its designated requirement/signing identity and local
permission trust. Production app, data and origins are always rejected.

## CI and release rhythm

- Focused tests are the inner loop. The workstation does not start the
  repository-wide local CI automatically.
- GitHub Actions `governance-fast` is the PR-ready gate and must pass on the
  exact PR SHA. It runs the bounded `infra/scripts/ci-local.sh --fast` lane on
  the GitHub runner.
- Local `infra/scripts/ci-local.sh --fast` / `--full` remain optional commands
  for explicit diagnosis and offline fallback; their evidence cannot replace
  the required GitHub check.
- Fast/full evidence requires a clean worktree so the recorded SHA identifies
  the tested bytes. `GRAF_CI_ALLOW_DIRTY=1` is diagnostic-only: its evidence is
  `ambiguous` and cannot authorize merge or release.
- A release operator freezes one candidate SHA and metadata digest. Exactly one
  authoritative `--full` run belongs to that candidate; changed SHA makes
  evidence stale.
- GitHub Actions are enabled. The required `governance-fast` check is
  authoritative for PR merge and validates exact SHA, concurrency cancellation
  and metadata-only evidence. Local CI remains available only as fallback.
- Use release windows (for example twice weekly) to batch completed features.
  Hotfixes are explicit exceptions with a reason and the same evidence rules.
- A product release requires CalVer tag, GitHub Release and Russian notes with
  changes, validation, compatibility/migration impact, known limitations and
  links. Production execute still requires explicit approval.

After Feature 227 is reviewed and merged, PR checks will remain bound to the
PR target SHA, `merge_group` checks will bind the synthetic merge SHA, and a
release train will record both that SHA and the actual post-merge `master` SHA.
Only the frozen post-merge candidate may receive one authoritative Full CI;
cancelled, superseded or drifted receipts are not release evidence.

## Files agents may change

- Own feature directory under `specs/<id>-<slug>/`.
- Own `changes/unreleased/F<id>.yaml` fragment.
- Source files explicitly listed by the task and their tests.
- Project-local adapter files when the task grants ownership.

Do not edit root `CHANGELOG.md` during feature work. Do not add current feature
or task pointers to root `AGENTS.md`. Do not auto-commit implementation code;
commit only after validation and convergence.

## Legacy Definition of Done

Every spec and PR has one `Legacy Impact` classification: `remove`,
`retain-with-exception` or `untouched`. New aliases, fallback names, flags,
dependencies, fixtures, tests or docs that preserve an old path are forbidden.
An exception requires owner, expiry, removal trigger, risk, validation and a
retirement task. The closeout target is:

```text
legacy_new=0
unowned_legacy=0
expired_exceptions=0
```

Existing migrations, Temporal history and client update compatibility are
retired in separate small features with cutover and rollback evidence.

## Blocked-state next actions

| State | Next action |
|---|---|
| No Feature ID/umbrella | reserve through GitHub; do not guess a number |
| Dirty or detached worktree | preserve changes, create a disposable clean worktree |
| Pointer/context mismatch | repair `.specify/feature.json`; do not use mtime |
| Dev promotion lock held | inspect active manifest; wait or rollback, never overwrite |
| SHA mismatch/stale CI | invalidate evidence and rerun the selected lane on the new SHA |
| Failed smoke | keep previous manifest active, capture reason, fix or rollback |
| Checklist/analyze blocker | reviewer updates requirements/design; implementation does not bypass |
| Legacy exception expired | block merge/release and create/execute retirement task |

Before closing a task-backed issue, export its metadata and run
`python3 scripts/validate-issue-closeout.py --issue-json /tmp/issue.json
--tasks specs/<feature>/tasks.md --expected-sha <PR-SHA>`. It must pass for every issue named by the
feature. A closed issue without a detailed Russian closure comment is a process
failure even when GitHub closed it automatically; add the comment and reconcile
the task state before declaring the feature complete.
The individual JSON command is only a structural pre-close check; it does not
authenticate GitHub URLs.
For final feature closeout, use the same script's live feature mode so checked
tasks cannot coexist with open, missing, duplicate or orphan task-backed
issues. Task issues close first; the umbrella closes last.
