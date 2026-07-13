# Feature 098 PR Closeout Draft

**Recorded**: 2026-07-13 (Europe/Moscow)
**Tasks**: T103–T104 complete
**Branch**: `codex/098-calendar-auto-context-match`
**Base**: `3b62270c2b6c8e236444d521759b682323aa80bf`

## Current State

- The validated `117`-file implementation scope was committed as
  `13af76a7adacc4ee18f8dc4ff8f89d59b2df79cb`
  (`feat(098): добавить безопасный автоконтекст календаря`).
- The implementation worktree was clean immediately after that commit, and the
  branch was `ahead 1` of `origin/master`; this closeout reconciliation is a
  separate documentation-only follow-up.
- No PR has been created.
- The committed scope is `117` files: `77` tracked modifications and `40` new
  files, based on `3b62270c2b6c8e236444d521759b682323aa80bf`.
- Both recovery stashes remain preserved:
  `codex-098-pre-release-refresh-2026-07-13` and
  `codex-098-pre-origin-master-refresh-2026-07-13`.
- The user explicitly approved Chrome visual QA and the validated
  implementation commit. Staging contained exactly the `117` feature-owned
  files, with `0` unstaged and `0` untracked files; `git diff --cached --check`
  passed before the commit.
- Chrome visual QA passed for web and embedded routes. It found and closed an
  invalid nested-link/grid-wrap defect before the final rerun; eight synthetic
  screenshots and interaction receipts are in `validation/visual-qa.md`.
- Feature 097 and its standalone Codex Security scan remain separately
  deferred and untouched.

## Russian PR Description

The following body follows `.github/pull_request_template.md` and is ready to
use after commit approval and final branch/CI evidence are inserted.

```markdown
## Кратко

- Добавляет безопасное автоматическое сопоставление обычной записи GRAF с
  календарным событием, если подходящий вариант один и данные свежие.
- Не блокирует запись, загрузку и обработку при недоступном календаре.
- Оставляет неоднозначность, приватные события, ручные загрузки и recovery без
  сомнительной автоматической привязки.

## Что изменилось

- macOS после фактического старта локальной записи неблокирующе запрашивает у
  сервера match attempt и сохраняет в upload queue только его opaque ID.
- Сервер детерминированно выбирает один свежий meeting-like event, атомарно
  потребляет attempt при создании meeting и хранит один immutable context
  snapshot с безопасным title, временем, bounded roster и recurring evidence.
- Добавлены явный выбор при ambiguity, продолжение без календаря, поздняя
  correction/clear логика и безопасный previous-occurrence pointer.
- Calendar roster не меняет speaker labels, permissions, share grants,
  recipients или delivery.
- Добавлена миграция `0021_calendar_auto_context_match` с SQLite/PostgreSQL и
  RLS evidence.
- Unsafe URL/email/token-like text отсекается общей metadata-policy на ingest,
  matching, title application и cabinet egress; использованный attempt сразу
  очищает дублирующий snapshot.

## Как проверено

- Focused server: `145` unit + `99` contract + `162` integration tests.
- Performance: resolve p95 `0.602250 ms` при 4 sources / 50 events / 100
  samples; consume p95 `2.007667 ms` при 100 samples.
- Focused macOS: `195` tests, `0` failures.
- Auth/privacy/forbidden-content: `72` tests, `0` failures.
- Migration: `12` focused tests; disposable PostgreSQL/RLS и cleanup — pass.
- Ruff и `git diff --check` — pass.
- Canonical local CI: `ci_local_result=pass`; macOS `631/631`, server
  `1414 passed, 4 skipped`, Ruff/compile/Compose/deployment-evidence — pass.
  Локальный RLS boundary ожидаемо требует PostgreSQL URL; отдельный disposable
  PostgreSQL/RLS прогон для 098 — pass с cleanup.
- Chrome visual QA — pass: list/matched/recurring/ambiguity/correction/clear,
  keyboard focus and real embedded choose/clear actions; `8` synthetic
  screenshots. Найденный invalid nested-link/grid-wrap дефект исправлен,
  recovery slices `3 passed` и `85 passed`; финальный canonical local CI после
  исправления снова завершился `ci_local_result=pass`.
- Полные receipts: `specs/098-calendar-auto-context-match/validation/`.

## Risk / validation lane

- Lane: high-risk active Spec Kit slice — запись metadata, privacy-sensitive
  calendar content, owner/workspace boundaries, миграция/RLS и web/macOS UX.
- Что запускалось: полный focused quickstart, migration/RLS, macOS, privacy,
  Ponytail review и canonical local CI.
- Более широкие gate не запускались, потому что: standalone Codex Security scan
  feature 097 отдельно отложен пользователем; production gate возможен только
  после merge/release.
- Release/deploy gate: не запускался; PR сам по себе не является release.

## Issues

- Task-backed implementation/PR-readiness issues: #3082–#3185; точное
  соответствие T001–T104 и evidence записано в
  `validation/implementation-evidence.md`.
- Release/deploy/cleanup issues #3186–#3190 этим PR не закрываются.
- Issues закрывать только после merge evidence и подробного русского closure
  comment; локальная валидация сама по себе их не закрывает.

## Что не входит

- Feature 097 и отдельно возобновляемый Codex Security scan.
- Auto-record, provider writes, auto-share/delivery, speaker naming, native
  duplicate review UI и retrospective matching recovery-очередей.
- Production deploy/runtime smoke и публичный signed/notarized macOS installer.

## Release / versioning

- [ ] Этот PR не публикует релиз; после merge нужен отдельный CalVer release
      `vYYYY.MM.DD.N`.
- [x] Читаемый postfix будет только в GitHub Release title, не в stable tag.
- [x] `CHANGELOG.md` обновлен понятной русской записью под `[Unreleased]`.
- [ ] Release notes с validation, migration/compatibility и known limitations
      готовятся только в release phase.

## Перед merge

- [x] Описание PR написано на русском и понятно не только инженеру.
- [ ] Closing keywords добавляются только после финальной сверки issue scope.
- [x] Связанные issues и точный task map записаны в evidence.
- [x] Risk / validation lane выбран и обоснован.
- [x] Validation evidence записан.
- [ ] Для каждого закрываемого issue после merge будет добавлен подробный
      русский closure comment.
```

## Browser / Embedded Visual QA Gate

**Status**: PASS in user-selected Chrome.

The synthetic-state pass used the same default Chrome viewport for browser and
embedded cabinet and compared both with the existing GRAF meeting list/detail
layout and its `state-row`, `chip`, `truth-copy` and `state-list` primitives:

1. compact list labels for matched, ambiguous, no-context and protected rows;
2. matched-auto detail with bounded safe title, event interval, roster copy and
   previous-occurrence pointer;
3. ambiguity chooser with initial focus, keyboard/radio operation and safe
   source/time labels;
4. corrected `matched_user` result with focus returned to the context heading;
5. clear confirmation and durable `cleared_by_user` result with stable title;
6. identical actions and copy through the embedded desktop route.

All six states passed through real DOM interaction, keyboard/radio operation
and web/embedded POST actions. The first pass exposed invalid nested anchors
that pushed the ambiguity-row date into a second grid row; the final code uses
one valid chooser link and the contract-required `64px` row minimum. The
targeted recovery tests passed `3/3`, the server was restarted, and the full
visual/interaction pass was repeated. Evidence and eight inspected synthetic
screenshots are in `validation/visual-qa.md`.

## T104 Approval Gate

Commit gate:

1. [x] Reconcile phase-9 issue comments and final status.
2. [x] Show the user the validation boundary and run the requested Chrome QA.
3. [x] Obtain explicit approval for the validated implementation commit.
4. [x] Stage only the 098-owned diff, create the approved commit and record the
   exact commit SHA/status here:
   `13af76a7adacc4ee18f8dc4ff8f89d59b2df79cb`, branch `ahead 1`, clean
   implementation worktree immediately after commit.

No push or PR had been performed when this commit receipt was recorded.
