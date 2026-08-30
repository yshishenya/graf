# Contract: Spec Kit governance check

## Invocation

```sh
python3 scripts/check_spec_kit_governance.py
python3 scripts/check_spec_kit_governance.py --self-test
```

## Success contract

- Exit code `0`.
- Стандартный вывод содержит короткое подтверждение bootstrap integrity и GRAF governance invariants.
- Проверка не изменяет repository state и не требует сети.

## Failure contract

- Exit code не равен `0`.
- `stderr` называет каждый нарушенный инвариант и соответствующий файл.
- При провале frozen doctor диагностика объединяет его непустые `stdout` и `stderr` и атрибутирует ошибку файлу `.specify/speckit-bootstrap.lock.json`.
- Проверка fail closed как минимум для unsupported lock schema, missing project-local skills, неполного workflow, отсутствующей reviewer ownership, отсутствующего managed ignore и провалившегося frozen doctor.

## Self-test contract

`--self-test` создаёт только temporary fixtures, доказывает положительный сценарий и пять обязательных отрицательных классов, включая неправильный порядок стадий, затем удаляет fixtures. Реальный GRAF repository не изменяется.
