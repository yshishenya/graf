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
- Проверка fail closed как минимум для unsupported lock schema, missing project-local skills, неполного workflow, отсутствующей reviewer ownership, отсутствующего managed ignore и провалившегося frozen doctor.

## Self-test contract

`--self-test` создаёт только temporary fixtures, доказывает положительный сценарий и четыре обязательных отрицательных класса, затем удаляет fixtures. Реальный GRAF repository не изменяется.
