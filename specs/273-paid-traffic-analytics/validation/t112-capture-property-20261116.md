# T112 — первый шаг реализации: свойство локальной записи

Изолированная ветка `codex/f273-result-visibility-20261116`, полоса
`high-risk-product`. Требования приняты независимым reviewer124/0;
[scoped analyze и issue mapping](t112-analyze-20261116.md) пройдены до кода.
Полный T112 не выполнен и не заменяется этим первым шагом.

## Изменение

`cabinet/web.py:build_first_value_product_analytics_payload()` больше не
ставит `first_recording_completed=true` без входного доказательства.
Обязательное явное значение `bool | None` сохраняет false/true, а при None
не сериализует поле. Неверный тип отклоняется без приведения по truthiness.
Реальные ready/useful guards, безопасный каталог и unknown campaign сохранены.
Параметр сообщает доказанное вызывающим кодом происхождение, но не проверяет
его сам; будущий доверенный T112 trigger обязан получить его из полной
цепочки. Client JSON таким доверенным вызовом не становится.

Поиск всех упоминаний builder до изменения нашёл только определение и
исторические документы: производственных callers ещё нет. Новый unit-файл
является первым вызывающим кодом в этой ветке. Существующий каталог разрешает
поле, не требует его присутствия. В проверенных серверных модулях аналитики
и infra/posthog не найден обязательный first-value фильтр по capture=true.
Поля старых payload и отдельная локальная capture-веха не переписываются.

## Причинная проверка

- RED на старом builder:12 failed/1 warning. Старый вызов без решения о capture
  не отказал и выдавал true; случаи явного false/unknown не поддерживались.
- GREEN:50 passed/1 warning,1.02s. Профиль включает12 новых случаев и
  существующие unit activation, funnel, campaign labels и contract catalog.
- `ruff check` двух затронутых Python-файлов и `git diff --check`: PASS.
- Warning — уже импортированный pytest fixture module; пропусков тестов нет.
- Перед выполнением проверено место:172172356KiB доступно, выше запаса80GB.
  Сборка, PostgreSQL и копирование архивов для этой правки не нужны.

Команда из корня:

```sh
PYTHONPATH=apps/server/src /Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python -m pytest -q \
  apps/server/tests/unit/test_result_visibility.py \
  apps/server/tests/unit/test_product_activation_analytics.py \
  apps/server/tests/unit/test_product_analytics_activation_funnel.py \
  apps/server/tests/unit/test_product_analytics_conversion_campaign_labels.py \
  apps/server/tests/contract/test_product_activation_analytics_contract.py --tb=short
```

| Изменённый код/тест | SHA-256 |
| --- | --- |
| apps/server/src/twobrain_rec_server/cabinet/web.py | 7c2cf44e58aa49984be9d002ec09913cdfe3158fbadbb952e51074913cc5bad3 |
| apps/server/tests/unit/test_result_visibility.py | 748d8deb9fc2d88ddc07571b8b9897f04358ff078d93225bdf477482d52ffedb |

## Остаток полного результата

Независимое implementation review этого кода ещё не выполнено. Полный trigger
source/audit/projection/proof, browser/native visibility, защищённый POST,
общая T113 admission и их DB/browser/Swift/concurrency/failure матрица ещё
не реализованы. Проверка builder не считается end-to-end или готовностью
измерения. Нового PR/CI/merge/Full/CD/выпуска/рабочего включения нет.
Истёкшее исключение T098 не продлено; защитные отказы не сняты.
T112/T113/#7698, измерение, T0 и внешние AC открыты. Посетителей,
регистраций, просмотров клиентов и оплат этот профиль не доказывает.
