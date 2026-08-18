# Research: Надёжный RLS release gate

## Decision 1: запускать RLS boundary через project-managed runtime

- **Decision**: Вызывать существующий `verify_rls_hardening.py` из `apps/server`
  через `PYTHONPATH=src uv run python`.
- **Rationale**: Диагностика release candidate показала, что системный
  `/opt/homebrew/.../python3` не содержит `alembic`, тогда как `apps/server/.venv`
  содержит весь lockfile runtime. При отсутствии URL ошибка не проявлялась,
  потому что скрипт завершался до импорта probe-зависимостей.
- **Alternatives considered**:
  - Добавлять зависимости в системный Python — отвергнуто: это ломает
    воспроизводимость и обходит lockfile.
  - Дублировать RLS-проверку в shell — отвергнуто: существующий Python-script
    уже является единым источником поведения и guard-ов.

## Decision 2: не менять fail-closed и cleanup boundary

- **Decision**: Оставить `RLS_TEST_DATABASE_URL` как единственный вход для
  disposable probe, запретить `twobrain_rec`, а cleanup оставить во внешнем
  release-runner и внутреннем RLS script.
- **Rationale**: Эти границы уже покрыты контрактами и предотвращают случайный
  destructive probe production-базы. Исправление runtime не должно расширять
  полномочия проверки.
- **Alternatives considered**:
  - Подставлять локальную базу по умолчанию — отвергнуто: это скрывает
    отсутствие явного disposable target.
  - Ослабить scan/guard при отсутствии зависимости — отвергнуто: release gate
    должен блокировать неизвестный результат.

## Decision 3: минимальная validation surface

- **Decision**: Добавить контрактное утверждение на project-managed invocation,
  затем один exact-SHA full gate; не повторять full CI после focused-only
  правок, если они не меняют candidate commit.
- **Rationale**: Это соответствует release-and-validation policy и экономит
  время, сохраняя обязательный full gate для каждого нового release SHA.
- **Alternatives considered**:
  - Запускать full CI после каждого документационного шага — отвергнуто
    политикой проекта.
