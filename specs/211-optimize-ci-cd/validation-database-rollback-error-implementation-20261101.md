# T116 — локальная проверка передачи ошибки, 01.11.2026

Lane: active Spec Kit, high-risk deployment. Основа
`8d189785be2b5dca00beb1677cd346cee592231f`.

- До кода: независимые checklist3/0 и scoped analyze C/H/M0; существующая
  #6989 OPEN дополнена явным владельцем T116 и критериями, точное чтение
  body PASS; canon ensure/validate PASS (244issues).
- Наблюдение настоящего helper с отказом17: прежнее тело дало ложный0 и
  выполнило три role-query. Никакого подключения к БД/серверу не было.
- RED нового параметризованного теста:4FAIL/1PASS/80deselected,0skips.
  Миграция и role-query потеряли код; role-drop продолжил следующие роли.
- Реализация: только три `|| return` в настоящем helper. Caller, схема0108,
  контроль согласия, данные, образы и политика отката не менялись.
- GREEN всего readiness модуля:85PASS/1существующее предупреждение/1.86s.
- Связанные release-images/smoke/backup-restore/RLS контракты:
  95PASS/0skips/30.88s.
- Bash syntax, Ruff, diff, fragments и development-process PASS.
- Независимые code review/converge PASS: P1/P2/C/H0, остаток обязательной
  реализации0; checklist перечитан3/0. Exact PR gates и protected merge ещё
  ожидаются. Новый кандидат/Full/CD/runtime/измерение/T0 отдельно.

Журналы вне Git: graf-t116-observed-failure-20261101.txt,
graf-t116-red-20261101.txt, graf-t116-green-20261101.txt,
graf-t116-related-20261101.txt в /private/tmp. Секретов и содержимого встреч нет.

## SHA-256 реализации

- `infra/scripts/cd-remote-runtime.sh`: `d5754035869c0e499921ce0fc4c3e96b2e64d554f43f6d2192876cdadd08bc34`.
- `apps/server/tests/integration/test_deployment_readiness_gates.py`: `ef4b89c2680adc71a243e629e03552c9dc60504c744a16b9dedf269efcfe91ea`.
- `changes/unreleased/F211.yaml`: `5021bb35e3e1f4ff3ccad08c0f34c070d2bd1a7f1303212fce6c602d64f1f827`.

## Exact PR-приёмка T116

PR #7881 принят: source `745f28853babffb5b2349e3ccad9da9f9ff06580`,
checked base `8d189785be2b5dca00beb1677cd346cee592231f`.

- governance-fast PASS: https://github.com/yshishenya/graf/actions/runs/41309544878
- macos-pr PASS: https://github.com/yshishenya/graf/actions/runs/41309544888
- pr-metadata PASS: https://github.com/yshishenya/graf/actions/runs/41309544869
- Common validator до/после protected squash PASS; обсуждений review0.
- Merge `3d3cb6aea119795492ddaa4ef8455374e61ddd5d`,01.11.2026 13:25:21UTC.

T116 принята в пределах заявленной реализации и PR-проверок. Общая #6989
остаётся OPEN: общие T071/T097 и рабочие критерии выпуска не закрываются
этим узким исправлением. Full/CD/рабочее измерение/T0 принимаются отдельно.
