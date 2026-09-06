# Feature Specification: Надёжный GitHub CI для PR

**Feature Branch**: `233-github-actions-runner-bootstrap`
**Created**: 2026-09-02
**Status**: Clarified

## User Scenarios & Testing

### User Story 1 - Проверяемый PR

Как владелец репозитория, я хочу, чтобы каждый PR автоматически проверялся
GitHub Actions на exact SHA, чтобы merge не зависел от локального компьютера.

**Independent Test**: открыть PR и убедиться, что `governance-fast` завершился
успешно на том же SHA, который указан в PR.

### User Story 2 - Безопасный fallback

Как разработчик, я хочу сохранить локальный `ci-local.sh` для диагностики и
работы без сети, но он не должен быть обязательным merge-gate.

**Independent Test**: workflow проходит в чистом GitHub runner, а локальный
скрипт остаётся доступным и явно помечен как fallback.

## Requirements

- **FR-001**: GitHub Actions MUST быть включён для репозитория.
- **FR-002**: Workflow MUST установить зафиксированные версии `specify-cli`
  и `speckit-bootstrap` до запуска governance-проверки.
- **FR-003**: Workflow MUST проверять exact checkout SHA и metadata-only receipt.
- **FR-004**: Branch protection MUST требовать успешный check `governance-fast`,
  сохраняя `required_approving_review_count=0` для sole-owner репозитория.
- **FR-005**: Локальный `infra/scripts/ci-local.sh` MUST остаться в репозитории
  и быть описан как необязательный fallback.
- **FR-006**: Stale, cancelled и failed runs MUST NOT считаться merge evidence.

## Success Criteria

- **SC-001**: Каждый новый PR получает GitHub check `governance-fast`.
- **SC-002**: Два текущих PR получают настоящий запуск на точном HEAD SHA.
- **SC-003**: Runner не останавливается из-за отсутствующей команды
  `speckit-bootstrap`.
- **SC-004**: Branch protection показывает `governance-fast` среди required checks.

## Edge Cases

- Сеть или скачивание bootstrap недоступны — job завершается failed и merge
  блокируется.
- SHA ветки изменился во время проверки — exact-SHA проверка завершается failed.
- Старый manual run застрял в очереди — он не используется как evidence.

## Out of Scope

- Удаление или переписывание локального CI.
- Production deploy, release tag и прикладной код.

## Legacy Impact

Classification: `untouched`

CI fallback сохраняется намеренно; новые legacy runtime-пути и зависимости
продукта не добавляются.
