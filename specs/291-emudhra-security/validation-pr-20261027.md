# F291: принятие исходного исправления, 27.10.2026

Полоса текущей записи — scoped docs-only: код и условия приёмки не меняются.
Полоса принятого исправления — high-risk-product, затем отдельный release-deploy.

## Проверенная цепочка

- PR: https://github.com/yshishenya/graf/pull/7735 .
- Точный PR SHA: `56cf5729b7bff5c8cef0d63a6d7bc836c8a6c5ff`.
- Проверенная основа: `0a1bce3505cd1582ccda552ba4ac10b4c4258d26`.
- Обычный rebase merge: `48e5d90d197f450367770e5c093cd897eece31fd`,
  27.10.2026 12:40:25 UTC. Защиты не обходились.
- governance-fast: PASS https://github.com/yshishenya/graf/actions/runs/40502921105 .
- macos-pr: PASS https://github.com/yshishenya/graf/actions/runs/40502921166 .
- pr-metadata: PASS https://github.com/yshishenya/graf/actions/runs/40503034557 .

Последние текстовые итоги governance-fast 40503034121 и macos-pr 40503033903
повторно проверили исходные доказательства без нового исполнения продуктовых
тестов. Штатный `validate-pr-checks.py --repository yshishenya/graf --pr 7735
--expected-sha 56cf5729b7bff5c8cef0d63a6d7bc836c8a6c5ff` прошёл до и после
слияния; в повторном результате merge SHA совпадает с указанным выше.
Перед слиянием незавершённых обсуждений и запрошенных изменений не было.

Профильные 142 PASS, воспроизводимый lock/export и 18 TLS-проверок двух
локальных Linux/arm64 targets описаны в [validation-images-20261027.md](validation-images-20261027.md).
Они не считаются проверкой работающих Linux/amd64 production-сервисов.

## Граница завершения

T006 принята; эта запись приводит `tasks.md` к факту слияния.
T007/T008 и общая #7734 остаются открытыми: нужны замороженный кандидат,
один authoritative release-full, train/decision, dry-run, применимое разрешение
резервирования и проверка восстановления, затем штатный выпуск и фактические
пакеты/TLS/health/smoke с повторной готовностью workers. Выпуск, production
и macOS-публикация в этом срезе не выполнялись.

Статус опубликован в существующей issue:
https://github.com/yshishenya/graf/issues/7734#issuecomment-6442136260 .
