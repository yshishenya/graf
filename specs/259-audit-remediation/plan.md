# План F259 — первый этап B019

## Summary

Исправить выбор номера и подготовку feature-метки. Только US3/FR-012–FR-018; остальные B-пункты не входят в эту итерацию. База e81b412dff920cc29ed37de60be13dd8fc4d1c43.

## Technical Context

Python stdlib, существующий GitHub CLI, Bash/Python/PowerShell оболочки. Новых зависимостей нет. Состояние — существующий JSON под общим git lock; формат не меняется.

## Constitution Check

Риск: significant governance / полный Spec Kit для этапа. Clarify записан в spec. Capture/auth/production/данные пользователя не изменяются; credentials не логируются. Clean tree, collision, mutex и GitHub проверки обязательны. Root AGENTS и общая рабочая копия аудита не меняются.

## Structure / Design

- scripts/claim-feature.py: только heads/remotes, распознавание конечного feature segment, единый поиск от specs; strict online lookup; подготовка метки.
- .specify/extensions/git/scripts/{bash,python,powershell}/create*feature*: одинаковый вызов предложения через repository-local allocator; generic путь без allocator сохраняется.
- tests/governance/test_feature_allocator.py: реальные git refs и изолированные GitHub responses, поведение оболочек; действующий test_validator_safety.py остаётся регрессией.
- /Users/yshishenya/Documents/speckit-bootstrap/bin/speckit-bootstrap: сохранить те же изменения оболочек в source overlay, не перезаписывать чужой dirty diff.

## Validation

Focused allocator/validator tests, self-test, Bash syntax, Python compile, read-only online suggestion на текущих refs; live label/issue не создаётся тестами. Полный CI только перед выпуском. governance-fast/merge/release не объявляются пройденными без точного commit/remote evidence. См. quickstart.md.

## Legacy Impact

Classification: untouched. Generic ветка — действующий standalone контракт, не legacy fallback; существующие IDs/claims не переписываются.

## Дополнение: завершение workflow

Scope US3/FR-019–FR-022: .specify/workflows/speckit/workflow.yml, project-local implement/taskstoissues skills и source bootstrap overlay; scripts/validate-issue-closeout.py получает только --verify-live режим чтения для одного issue. Существующая verify_feature_runs переиспользуется без нового сервиса. GitHub Actions permissions и production не изменяются. Проверки: CLI acceptance/rejection, YAML order/gates, загрузка workflow реальным specify, source overlay и governance tests.
