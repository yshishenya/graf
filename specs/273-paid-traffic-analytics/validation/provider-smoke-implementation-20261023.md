# F273/T118 — исправление provider-smoke, 23.10.2026

Полоса: существующий высокорисковый срез F273; связанная issue #7697,
PR #7727. Исходный HEAD `1c5148dbe5c1c3d19ae69d713b99cc8227458cb6`.

## Причина и результат

Исходное Python-тело smoke воспроизведено без сетевых подключений: отказ
`provider smoke failed`. Учебный restore-state v2 не является доказательством
согласованного восстановления; настоящий collector возвращает
`restore_consistent=False`. Скрипт ошибочно ожидал успешную доставку.

Исправлен только проверочный путь. До подстановки проверяется настоящий
restore blocker и отказ обоих клиентов, счётчики транспортов равны 0.
Стандартный `unittest.mock.patch` временно заменяет одно типизированное поле
через `dataclasses.replace`, сохраняя настоящий сбор всех остальных состояний.
Внутри контекста по одному синтетическому запросу достигает предоставленных
транспортов. После выхода повторяются настоящая проверка готовности и оба
отказа; счётчики остаются 1/1. Runtime, флаги и формат рабочего отчёта не менялись.

Вывод отдельно сообщает `provider_transport_evidence=synthetic_test_process_only`
и `restore_gate=blocked_before_and_after_transport_test`. Новый тест исполняет
настоящее Python-тело с audit hook, запрещающим socket.connect/getaddrinfo;
Docker и SSH в этом отдельном тесте не запускаются. Обычные shell-контракты
также исполнены, включая detached HEAD.

## Проверки

Команда итогового профиля: `PATH="$PWD/apps/server/.venv/bin:$PATH"
PYTHONPATH=apps/server:apps/server/src apps/server/.venv/bin/python -m pytest -q`
с шестью файлами:

- `tests/contract/test_product_analytics_provider_smoke_output.py`
- `tests/contract/test_product_analytics_provider_smoke_contract.py`
- `tests/unit/test_product_analytics_provider_delivery_gate.py`
- `tests/unit/test_product_analytics_yandex_offline_provider.py`
- `tests/unit/test_product_analytics_posthog_provider.py`
- `tests/contract/test_product_analytics_posthog_provider_contract.py`

Все пути относительно `apps/server`. Итог: **34 passed**, 2 существующих
предупреждения, 2.92 секунды. Отдельно новый тест без унаследованного PYTHONPATH:
**1 passed**, 1 deselected, 2 предупреждения. Отказы/пропуски не приняты за PASS.
Shell syntax, Ruff, diff, project-process и Spec Kit governance пройдены.
Полный локальный CI не запускался; GitHub checks нужны на новом SHA/основе.

| Локальный журнал | SHA-256 |
|---|---|
| baseline-negative.log | `43c9e780f46d32dbbfff0e6412b7695bc4819bdf9d17389c4330f7dff87821d5` |
| final-profile.log | `a20673e99bf5d729eaeb9c5ea541e3f6d8027ebde447ba1f87c4e70bd93fe950` |
| isolated.log | `9b5bfe054c42ce2e3dafc8feefc0fede0756282a2ee18e757d9430268c3ab02d` |
| process.log | `55507484622f1851e251a6e2685b434464ac9c1228358368eae395bfeb8f625d` |

Журналы сохранены в локальном `.dev/provider-smoke-recheck`, содержат только
синтетические данные и технические метаданные.

| Проверенный файл | SHA-256 |
|---|---|
| run-product-analytics-provider-smoke.sh | `440e8a37942828a2f705215d2555f4884f2a790bb0de0d3ce983093870bcd245` |
| test_product_analytics_provider_smoke_output.py | `cc7e3b4c2fc90c3409aa138d72d8535916933b6ab633294bcb09d4862388f43b` |
| provider_readiness.py, без изменения | `265cbd6a53ea08d83990bbacdd9416c74b266d2716837d3ebc193d2d64672a44` |

## Анализ, синхронизация и сходимость

Узкий повтор анализа: CRITICAL 0/HIGH 0; FR-035/053 связаны с T118,
operations §T118, plan §выбранный путь восстановления и quickstart7.
Покрытие двух затронутых требований задачей — 2/2; это не общая приёмка F273.
Нет нового требования, непокрытой задачи, ослабления конституции или дубликата.
Независимое ревью требований: 111/0, отдельный отчёт сохранён.
Текущее состояние #7697 OPEN; она владеет T116–T119, T118 `[ ]`.
Изменение проверочного пути не создаёт отдельной задачи и не закрывает #7697.

Критерии узкого исправления реализованы существующими средствами. Полный
writer, изолированное восстановление/нативное чтение, очистка, рабочая установка,
выпуск и платный запуск остаются открытыми. Новых рабочих секретов, отправок,
изменений данных или зависимостей нет. Legacy Impact — untouched:
legacy_new=0, unowned_legacy=0, expired_exceptions=0.
