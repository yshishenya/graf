# Research: Процесс от разработки до релиза

## Decision: Локальные validation lanes остаются источником CI evidence

**Rationale**: `docs/agent-guidance/release-and-validation.md` уже фиксирует,
что GitHub Actions выключены, а `infra/scripts/ci-local.sh` поддерживает
`--fast` и `--full`. Новая инструкция должна уточнить порядок, а не добавлять
ещё один runner.

## Decision: Production execute — обязательная full-validation boundary

**Rationale**: `infra/scripts/cd-remote.sh --execute` проверяет clean worktree,
ветку и совпадение с `origin`, затем запускает `ci-local.sh --full` до remote
backup/deploy. Это уже существующий безопасный gate.

## Decision: Evidence идентифицируется точным SHA

**Rationale**: deploy script передаёт ожидаемый commit на remote и повторно
проверяет его. Плавающая ссылка на branch не доказывает, что проверялся именно
выложенный код.

## Alternatives rejected

- Full CI после каждого локального edit: медленный feedback loop без добавочной
  release-ценности.
- Только fast CI перед production: не покрывает macOS, RLS, compose и deployment
  readiness checks, которые входят в full lane.
- `--skip-local-ci` как обычная оптимизация: скрывает обязательный release gate.
