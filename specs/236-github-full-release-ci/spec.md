# Feature Specification: Authoritative GitHub Full CI для релизного кандидата

**Feature Branch**: `236-github-full-release-ci`

**Created**: 2026-09-02

**Status**: Clarified

**Input**: User description: "Настроить полный предрелизный процесс проверки приложения в GitHub; локальный Full CI оставить только fallback."

## User Scenarios & Testing

### User Story 1 - Один проверяемый frozen candidate (Priority: P1)

Как release operator, я хочу вручную запускать полный CI в GitHub для одного
замороженного кандидата, чтобы решение о релизе опиралось на exact SHA, а не на
рабочий Mac или изменившийся checkout.

**Why this priority**: без единого authoritative прогона нельзя безопасно
решить, что именно можно выпускать.

**Independent Test**: запустить workflow с валидными `candidate_id` и 40-символьным
SHA и получить единственную metadata-only запись `authoritative_full=true` с
нулём пропущенных gate и тем же SHA во всех компонентах.

**Acceptance Scenarios**:

1. **Given** чистый frozen candidate на `origin/master`, **When** operator
   запускает GitHub Full CI, **Then** workflow проверяет candidate identity,
   запускает серверные и macOS-проверки параллельно и агрегирует их в один
   passed evidence.
2. **Given** checkout SHA отличается от requested SHA, **When** начинается
   workflow, **Then** он завершается failed и не создаёт release evidence.
3. **Given** у candidate уже есть reservation или authoritative evidence,
   **When** запускается повторный workflow, **Then** GitHub сериализует его
   после первого run и он сразу завершается failed с причиной
   `candidate_already_reserved`; первый run не отменяется и не перезаписывается.

### User Story 2 - Честное разделение быстрых и полных проверок (Priority: P1)

Как разработчик, я хочу получать быстрый GitHub PR-gate, а полный прогон только
на релизном кандидате, чтобы CI не перезапускался бесконечно после каждой
небольшой правки и при этом release gate оставался полным.

**Why this priority**: это устраняет текущую гонку между изменениями в worktree
и долгим локальным CI.

**Independent Test**: PR получает только `governance-fast`; workflow Full CI не
запускается на `pull_request` и доступен только через `workflow_dispatch`.

**Acceptance Scenarios**:

1. **Given** новый commit в PR, **When** GitHub Actions запускает проверки,
   **Then** выполняется только fast lane на exact PR SHA.
2. **Given** release candidate подготовлен, **When** operator запускает Full CI,
   **Then** workflow не использует локальное evidence и не принимает stale,
   cancelled или skipped-gate результат.
3. **Given** ошибка воспроизводится только на закреплённом macOS runner, **When**
   разработчик вручную запускает macOS diagnosis на exact SHA, **Then** workflow
   выполняет только macOS-проверки, не запускает server-full и не создаёт
   authoritative release evidence.

### User Story 3 - Безопасный fallback и воспроизводимый closeout (Priority: P2)

Как владелец репозитория, я хочу сохранить локальный `ci-local.sh` как
диагностический fallback и получить инструкции, как связать GitHub evidence с
`release-candidate.sh`, чтобы offline-проверка не выглядела как релизное
доказательство.

**Why this priority**: аварийный инструмент нужен, но его границы должны быть
однозначными.

**Independent Test**: документация и contract tests показывают, что локальный
`--full` не является authoritative, а decision/attestation принимают только
GitHub evidence с candidate ID и exact SHA.

**Acceptance Scenarios**:

1. **Given** локальный Full CI завершён успешно, **When** operator пытается
   использовать его как release evidence, **Then** process documentation и
   validator требуют GitHub authoritative record.
2. **Given** GitHub Full CI passed, **When** operator скачивает metadata-only
   evidence и выполняет `train-attest`/`decide`, **Then** candidate остаётся
   неизменным и цепочка сохраняет exact SHA.
3. **Given** после последнего опубликованного GitHub Release уже были
   подготовлены, но не опубликованы секции changelog, **When** operator готовит
   следующий release candidate, **Then** все такие секции и новые fragments
   объединяются в один новый релиз без потери или повторения записей.

## Edge Cases

- Невалидный candidate ID, SHA или отсутствующий input должен завершать workflow
  до тестов.
- Одновременные ручные запуски одного candidate должны сериализоваться без
  `cancel-in-progress`; второй после первого reservation завершается failed с
  причиной `candidate_already_reserved` и не заменяет первый результат.
- Отмена, timeout, failure одного component job или пропущенный gate должны
  давать `no-go`, а не частичный success.
- GitHub runner может быть Linux или macOS; component job обязан явно сообщать
  свою платформу и exact SHA.
- Артефакты workflow не должны содержать secrets, raw audio, transcript text,
  private paths или полные test logs.
- Наличие более нового локального тега или подготовленной секции changelog не
  должно сдвигать границу release train, пока соответствующий GitHub Release не
  опубликован как non-draft и non-prerelease.

## Requirements

### Functional Requirements

- **FR-001**: Репозиторий MUST иметь отдельный GitHub Actions workflow,
  запускаемый вручную только для `candidate_id` и exact 40-символьного SHA.
- **FR-002**: Workflow MUST checkout и проверить тот же SHA, который передан в
  inputs; изменение SHA во время run MUST завершать run failed.
- **FR-003**: Workflow MUST выполнить полный серверный, governance,
  infrastructure и macOS validation scope на подходящих GitHub runners.
- **FR-004**: Workflow MUST агрегировать component results в одну
  metadata-only запись с `lane=full`, `authoritative_full=true`, candidate ID,
  component SHAs, artifact digests и `skipped_gates=[]`.
- **FR-005**: Для каждого candidate MUST существовать create-once reservation;
  повторный run того же candidate не должен перезаписывать evidence.
- **FR-006**: Failed, cancelled, stale, ambiguous и skipped-gate результаты MUST
  быть непригодны для `release-candidate.sh decide`.
- **FR-007**: Workflow MUST использовать read-only GitHub permissions для CI и
  не публиковать release, не деплоить production и не менять appcast.
- **FR-008**: Локальный `infra/scripts/ci-local.sh` MUST остаться доступным как
  manual/offline fallback, но документация MUST прямо запрещать использовать
  его evidence как authoritative release proof.
- **FR-009**: Contract validation MUST проверять workflow triggers, input
  validation, exact-SHA binding, no-secret boundary, reservation и evidence
  validation.
- **FR-010**: Release documentation MUST описывать последовательность
  freeze → GitHub Full CI → evidence download → train-attest/decide → signing,
  notarization, publication и guarded deploy.
- **FR-011**: Release preparation MUST определять базу по последнему реально
  опубликованному non-draft, non-prerelease GitHub Release и MUST включать все
  изменения от его тега до candidate SHA; подготовленные, но не опубликованные
  changelog-секции MUST объединяться со следующим релизом.
- **FR-012**: Feature closeout MUST fail closed проверять полное соответствие
  task↔issue, закрытое состояние всех task-backed issues, русский closure
  comment со ссылками на успешные `governance-fast` и `release-full`, отсутствие
  orphan/open child issues и закрытие umbrella issue последним.
- **FR-013**: macOS Full CI MUST сохранять строгие проверки на закреплённом
  macOS 14 runner: WebKit runtime-тесты MUST выполняться в одном последовательном
  XCTest-процессе, а JavaScript MUST выполняться через page-world callback
  bridge, который сохраняет допустимый `nil`-результат и ошибки JavaScript;
  plist MUST приниматься только при успешном
  exit code `plutil`, source scan MUST работать штатными средствами runner без
  необъявленной зависимости, а test resources MUST читаться из объявленного
  SwiftPM bundle без неограниченного source-tree поиска. Отладочный macOS-only
  workflow MAY проверять exact SHA без server-full, но MUST NOT создавать
  authoritative release evidence.

### Key Entities

- **Frozen candidate**: immutable ID, source SHA, feature set и changelog digest,
  созданные `release-candidate.sh`.
- **Component result**: metadata-only результат server или macOS job, привязанный
  к source SHA и GitHub run.
- **Authoritative full evidence**: единственная агрегированная запись, которую
  принимает release decision validator.
- **Candidate reservation**: create-once marker, не позволяющий повторно
  использовать тот же candidate для второго authoritative run.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% ручных Full CI runs проверяют exact requested SHA до запуска
  тестов; stale SHA получает failed result.
- **SC-002**: У passed candidate есть ровно одна authoritative full evidence
  запись и ноль skipped gates.
- **SC-003**: PR workflow не запускает полный lane; fast feedback остаётся
  отдельным check на каждый новый PR SHA.
- **SC-004**: Полный GitHub run покрывает server и macOS jobs; aggregation job
  завершается неуспешно при любом component failure/cancellation.
- **SC-005**: Evidence и workflow artifacts содержат только metadata и
  проверяемые digests; validator отклоняет private paths и credentials.
- **SC-006**: Оператор может связать downloaded evidence с frozen candidate без
  изменения candidate, changelog или source SHA.
- **SC-007**: Release preparation не оставляет отдельными ни одной
  неопубликованной changelog-секции после последнего опубликованного GitHub
  Release и не закрывает feature при открытых task-backed issues.
- **SC-008**: macOS component проходит на закреплённом GitHub runner без retry,
  quarantine, пропуска тестов или ослабления signing-custody проверок.

## Assumptions

- Candidate manifest и release decision остаются локальными ignored
  metadata-only файлами; GitHub получает их identity через workflow inputs.
- GitHub-hosted `ubuntu-latest` используется для backend/infrastructure, а
  `macos-14` — для Swift build/test/contract checks.
- Developer ID signing, Apple notarization, appcast publication и production
  deploy остаются отдельными operator gates и не выполняются из CI workflow.
- Один sole owner может принимать recorded owner/agent review evidence при
  нулевом required approval count.

## Out of Scope

- Удаление или переписывание локального CI.
- Автоматический production deploy или публикация GitHub Release из Full CI.
- Изменение backend, frontend, macOS capture semantics или пользовательских
  разрешений.
- Удаление legacy-путей; их retirement остаётся отдельной feature.

## Legacy Impact

Classification: `untouched`
owner: platform
expiry: none
removal trigger: not applicable; no legacy path is preserved or added
retirement task: not applicable
risk: release orchestration could accidentally make the retained local fallback authoritative
validation: development-process legacy-impact validator and GitHub Full CI contract tests
reason: Feature 236 changes release-validation orchestration only; runtime behavior, local commands and legacy paths remain unchanged.

## Clarifications

### Session 2026-09-02

- Q: Где должен выполняться authoritative Full CI? → A: GitHub Actions на
  отдельных Ubuntu и macOS runners, с одним агрегированным evidence.
- Q: Когда запускать полный lane? → A: Только вручную для frozen release candidate.
- Q: Что делать с локальным `--full`? → A: Оставить как offline/diagnostic
  fallback без release authority.
