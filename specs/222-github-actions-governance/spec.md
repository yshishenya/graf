# Feature Specification: Автоматические SHA-bound PR-проверки

**Feature Branch**: `codex/222-github-actions-governance`

**Created**: 2026-08-31

**Status**: Draft

**Input**: Аудит процесса GRAF: GitHub Actions выключены, required checks отсутствуют, долгие CI-запуски могут завершаться на устаревшем SHA. Нужен безопасный PR fast-gate без запуска production действий.

## Actors and Goals

- **Автор PR** — получает быстрый результат по текущему commit SHA и не тратит время на устаревший запуск.
- **Reviewer** — видит независимый статус exact-SHA проверки и metadata-only evidence.
- **Владелец репозитория** — может включить required checks, не открывая production secrets и deploy-путь.
- **CI operator** — повторно запускает bounded fast workflow, понимая, какой SHA проверялся и почему запуск отменён.

## User Scenarios & Testing

### User Story 1 — Fast-gate для PR (Priority: P1)

Автор открывает или обновляет PR. GitHub запускает bounded fast workflow ровно для head SHA PR, проверяет governance и затронутые компоненты, публикует безопасный metadata-only artifact и сообщает результат.

**Independent Test**: synthetic PR run с успешным и неуспешным fast lane показывает exact SHA, artifact и блокировку required check при failure.

**Acceptance Scenarios**:

1. **Given** PR head SHA известен, **When** workflow стартует, **Then** checkout SHA, requested SHA и recorded source SHA совпадают.
2. **Given** workflow завершает fast lane с ошибкой, **When** GitHub оценивает required check, **Then** merge остаётся заблокирован.
3. **Given** evidence содержит неразрешённое поле или секретный/приватный путь, **When** artifact validator запускается, **Then** workflow завершается ошибкой и artifact не считается valid.

### User Story 2 — Отмена устаревшего запуска (Priority: P1)

Автор быстро отправляет новый commit в тот же PR. Предыдущий незавершённый запуск отменяется, а его результат не может удовлетворить проверку нового SHA.

**Independent Test**: два запуска с одной PR concurrency group и разными SHA дают `cancelled`/`stale` для первого и отдельный результат для второго.

**Acceptance Scenarios**:

1. **Given** run-A выполняется, **When** появляется run-B того же PR, **Then** GitHub отменяет run-A через `cancel-in-progress: true`.
2. **Given** отменённый run-A сохранил evidence, **When** проверяется head SHA-B, **Then** evidence-A отклоняется как stale или cancelled.
3. **Given** workflow перезапущен для того же SHA, **When** он завершён, **Then** повтор не меняет смысл exact-SHA проверки и не запускает production actions.

### User Story 3 — Required checks и операторский контракт (Priority: P1)

Владелец репозитория включает Actions и required status checks после проверки названий jobs. Branch protection требует успешный fast-gate, но не требует Full CI для каждого коммита.

**Independent Test**: API snapshot branch protection показывает требуемый check; PR с missing, cancelled или stale check остаётся blocked.

**Acceptance Scenarios**:

1. **Given** workflow и check name опубликованы, **When** branch protection обновляется, **Then** требуемый check привязан к `master` и не включает production deploy.
2. **Given** Actions временно недоступны, **When** PR оценивается, **Then** отсутствие required check блокирует merge и содержит следующий шаг.
3. **Given** release candidate создан, **When** выполняется release process, **Then** authoritative Full CI остаётся отдельным единственным gate и не заменяется fast workflow.

## Edge Cases and Failure States

- requested SHA отсутствует, не является полным 40-hex SHA или не совпадает с PR head — workflow fail-closed до тестов.
- checkout SHA отличается от requested SHA — результат `stale`, merge/release запрещены.
- рабочее дерево содержит неожиданные untracked secrets или приватные пути — artifact publication блокируется.
- workflow отменён runner'ом, потерял связь или завершён неоднозначно — evidence `cancelled`/`ambiguous`, не `passed`.
- PR target не `master` или событие не pull request/ручной audit — workflow не изменяет branch protection и не выполняет CD.
- GitHub API/Actions недоступны — локальный fast lane остаётся диагностическим fallback; required check не обходится вручную.

## Requirements

### Functional Requirements

- **FR-001**: Workflow MUST запускаться на `pull_request` для PR в `master` и поддерживать явный `workflow_dispatch` с полным requested SHA.
- **FR-002**: Workflow MUST использовать concurrency group, уникальную для PR, с `cancel-in-progress: true`.
- **FR-003**: Workflow MUST проверять, что requested SHA, checkout SHA, PR head SHA и observed source SHA совпадают; при расхождении MUST завершаться fail-closed.
- **FR-004**: Workflow MUST вызывать только bounded `infra/scripts/ci-local.sh --fast` или эквивалентный lane и MUST NOT выполнять production deploy, migration mutation, reset volume или публикацию релиза.
- **FR-005**: Workflow MUST сохранять metadata-only evidence с run identity, event, PR number, requested/observed SHA, lane, result, cancellation/stale reason и digest artifact.
- **FR-006**: Evidence validator MUST отклонять неизвестные поля, секреты, raw logs, private meeting data, абсолютные machine-specific paths и evidence со stale/cancelled/ambiguous статусом как merge-ready.
- **FR-007**: Artifact upload MUST происходить только после успешной schema/secret/path проверки и не должен раскрывать полный CI log.
- **FR-008**: Repository documentation MUST фиксировать canonical job/check name, rerun behavior, stale-SHA semantics, local fallback и boundary с authoritative Full CI.
- **FR-009**: Branch protection для `master` MUST требовать успешный canonical fast check после проверки workflow; required status check не должен отсутствовать или быть привязан к плавающей ветке.
- **FR-010**: Workflow MUST быть безопасен при повторном запуске одного SHA и не менять продуктовые данные или production configuration.
- **FR-011**: Feature and PR metadata MUST include Feature ID `222`, umbrella issue `#6155`, Spec task IDs, selected validation lane и Legacy Impact.

### Non-Functional Requirements

- **NFR-001**: обычный PR fast-gate должен завершаться в пределах 15 минут или явно завершаться timeout/failure с actionable next step.
- **NFR-002**: проверка не должна читать или публиковать секреты, raw audio, transcript text или private meeting content.
- **NFR-003**: configuration and job names must be deterministic and reviewable from repository files.

## Scope

### In Scope

- `.github/workflows/governance-fast.yml`, exact-SHA wrapper/validator и metadata-only artifact.
- Contract/self-tests for workflow text, concurrency, SHA guard and artifact safety.
- Документация включения Actions и branch protection; evidence in PR.
- Feature 222 issue/PR metadata and changelog fragment.

### Out of Scope

- Production deploy, migration, backup/restore, release tag or notarization.
- Full CI на каждый commit; Full CI remains release-candidate-only.
- Реальный Dev.app/TCC rollout and legacy deletion.
- Изменение продукта, API или пользовательских разрешений.

## Success Criteria

- **SC-001**: 100% synthetic runs with changed/mismatched SHA are rejected before merge-ready status.
- **SC-002**: In a two-run concurrency test, the older run is cancelled or stale and never accepted for the newer SHA.
- **SC-003**: Required check is present on `master`; a PR with missing, failed or cancelled check remains blocked.
- **SC-004**: 100% published artifacts pass metadata-only schema and secret/path scans; forbidden payloads are rejected.
- **SC-005**: Fast workflow does not invoke production scripts and remains separate from the one authoritative Full CI release gate.
- **SC-006**: A clean contributor can find the exact command, check name, rerun rule and next step in under five minutes from the repository guidance.

## Legacy Impact

**Classification**: `untouched`

This feature adds no aliases, fallback paths, flags, dependencies or compatibility branches. Existing legacy contours remain out of scope and must be handled by Feature 220 retirement slices.

## Assumptions and Dependencies

- Feature 216 governance contracts are available on the base branch and remain reviewer-gated until merged.
- GitHub Actions permissions and branch protection are changed only after workflow contract tests pass.
- The repository remains public; artifacts are metadata-only and do not require product secrets.
- `master` is the only protected integration branch for this slice.

## Clarifications

- GitHub Actions are enabled by this feature only after the workflow is present and a dry-run/contract validation passes; production deploy remains excluded.
- One canonical fast check is required per PR; Full CI remains a release-train gate.
- Feature ID 222 is already reserved by umbrella issue #6155 and is not to be reused.
