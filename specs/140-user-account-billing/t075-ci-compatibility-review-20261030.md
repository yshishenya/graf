# Независимая проверка совместимости CI и восстановления F140/T075 — 2026-10-30

## Итоговое решение

**PASS для шести замороженных файлов исправления совместимости перед
обновлением PR #7831. Открытых замечаний в этой области не осталось.**
Основа: `c48cfb8edd344cc4b790d5ce344eb7a313ed53d5`, ветка
`codex/140-registry-implementation`.
Полоса: исправление совместимости внутри действующей `Active Spec Kit slice`,
с сохранением проверок высокого риска PostgreSQL и восстановления.
Это отдельное дополнение к прежнему B1–B3 PASS; старые отчёты не переписаны.

## Предметная проверка

Непосредственно прочитан полный diff шести файлов, окружающий код verifier,
SQL inventory, настоящий сценарий резервирования/восстановления и изменённые
ожидания migration head. Старый verifier и SQL inventory полностью прочитаны
на предыдущем предметном проходе этого же замечания. Проверена неизменность
кода импорта, store, CLI, модели, миграции 0107 и tasks относительно HEAD и
контрольных сумм прежней независимой приёмки.

1. Разрешён только дополнительный вид relation `S`. Для каждого такого
   отношения обязательна ровно одна строка `sequence_state` с теми же
   `(schema, name)`. Точное множество сравнивается в обе стороны; существующий
   контроль уникальности ключей и точного состава полей сохранён.
2. `last_value` проверяется через `type(...) is int`, `is_called` — через
   `type(...) is bool`. Поэтому JSON `true` не заменяет число, а число 1
   не заменяет логическое значение. Не введён неверный общий запрет
   отрицательных значений произвольной допустимой sequence.
3. SQL читает `last_value/is_called` для всех несистемных последовательностей
   через безопасные `format %L/%I` и `gexec` в существующей read-only
   транзакции. В verifier нет вызова `nextval` и изменения проверяемой БД.
4. Источник и восстановленная БД по-прежнему сравниваются полностью через
   `without_expressions`; новый state этой функцией не удаляется.
   Исключение `sequence_state` действует только при сравнении с пустой
   восстановленной схемой. Там множество и типы state также проверяются.
5. Строгое `schema(canonical) == schema(target)` осталось. Параметры sequence,
   ownership и default/dependency не исключаются из SQL-сравнения. Прежние
   checksums, регулярные файлы/права/ссылки, замкнутые JSON поля/ключи,
   точные role/RLS/policy/constraint/trigger/ledger проверки, migration graph,
   совпадение revision и server version не ослаблены.
6. В тесте реально создаются receipt и gap под фактической maintenance role
   до capture, оба получают id 1. После настоящего pg_restore, проверок и
   последнего reset штатная вставка без заданного id получает 2 в обеих
   таблицах. Восстановленную БД не чинят bootstrap/grants перед сравнением.
7. Отдельные настоящие изменения target проверяют счётчик 100, состояние
   `(last_value=1, is_called=false)` при исходном `(1,true)` и конфигурацию
   `INCREMENT BY 2`. Перед каждой мутацией target заново восстанавливается.
   Каждый случай обязан дать `postgres_verification=failed`.
8. В существующий цикл проверки до Docker добавлены missing state,
   `last_value=true` и `is_called=1`; manifest пересчитывается, поэтому отказ
   вызван содержанием inventory, а sentinel доказывает отсутствие обращения
   к Docker. Старые отрицательные случаи сохранены.
9. Четыре действующих ожидания/связи head обновлены на
   `0107_billing_registry`. Исторические 0106 в отрицательных проверках
   duplicate/branch/broken graph и нижняя поддерживаемая граница verifier
   оставлены намеренно. Upgrade с прежнего 0037 теперь дополнительно требует
   обе новые таблицы; продуктовый код ради зелёного теста не менялся.

Один совместимый вид метаданных и существующий механизм строгого сравнения
достаточны; новых служб, зависимостей или общего движка последовательностей
не добавлено. Универсальная проверка `nextval > max(id)` не нужна для
доказательства точного восстановления источника и не подменяет его аудит.

## Ограничение последовательностей

Состояние последовательности PostgreSQL **не входит в MVCC-снимок**.
Если оно различается между чтением счётчика `pg_dump` и чтением inventory,
точное сравнение source/restore отказывает и требуется новое резервирование.
Это намеренный безопасный отказ, а не обещание единого снимка счётчиков.
Изменение до первого или после второго чтения само по себе не означает
расхождение; обычные строки таблиц по-прежнему используют exported snapshot.
Указанное ограничение прямо записано в SQL и новом F140 changelog fragment.

## Проверенные фактические результаты

Исполнитель передал окончательный результат и frozen hashes после завершения
запуска. Reviewer непосредственно прочитал XML и полный журнал, пересчитал
их SHA256 и проверил совпадение всех шести исходных файлов с frozen JSON.

**142 testcase, 0 failure, 0 error, 0 skipped; 142 passed, 1 warning,
246.69 s.** Журнал runner: `postgres_test_mode=focused`, collection 142,
worker count 4, `postgres_test_phase=focused status=pass duration_seconds=251`,
`postgres_test_cleanup=isolated_container_removed`, итог `pass`.
Предупреждение — существующий повторный импорт pytest fixture.

| Файл набора | Пройдено |
| --- | ---: |
| unit/test_billing_registry.py | 38 |
| integration/test_billing_registry.py | 9 |
| unit/test_billing_reconciliation_activity.py | 12 |
| unit/test_playback_normalization_worker.py | 11 |
| integration/test_deployment_backup_snapshot.py | 7 |
| integration/test_deployment_restore_safety.py | 56 |
| integration/test_activation_restore_replay.py | 8 |
| integration/test_postgres_migrations.py | 1 |
| **Всего** | **142** |

XML включает именно `test_full_migrated_database_restore_comparison`,
`test_worker_schema_head_is_derived_from_packaged_migrations`,
`test_production_share_head_upgrades_to_regeneration_merge`, прежние
registry status-race и migration downgrade/history-refusal проверки.
Мутации внутри restore-сценария не объявляются отдельными testcase:
их исполнение проверяется по исходному коду прошедшего сценария.

Источники результатов:

- `/Users/yshishenya/Documents/Codex/2026-10-30/graf-repository-audit/f140-t075-ci-followup-final.xml`
  — SHA256 `78b69e743dd7905d7e61eaf9f5818e33e1b4648515d5db982eec8bc0372b00f9`.
- `/Users/yshishenya/Documents/Codex/2026-10-30/graf-repository-audit/f140-t075-ci-followup-final.log`
  — SHA256 `79ac94a5b27274cd835b1e9dcb69e0fd3bf5788ef45b6ea6818e3686d001c7a0`.
- `/Users/yshishenya/Documents/Codex/2026-10-30/graf-repository-audit/f140-t075-ci-followup-hashes.json`
  — SHA256 `cb4a18b615bcdc61aeb95f5cc0a1e6a8e54b827e5c8f1b5565514cba2c3098bb`.

Ruff/compile/governance/development-process PASS переданы исполнителем;
reviewer не выдаёт их за собственный запуск. Лично выполнены только чтение
исходников, diff/status/HEAD, read-only hashes/JSON/XML и `git diff --check`
(PASS). Reviewer не запускал тесты, БД, приложение, сборки, Docker,
резервирование, восстановление, Git/GitHub mutations, выпуск или production.
Единственная запись reviewer — этот назначенный отчёт.

## Контрольные суммы принятого дополнения

| Путь | SHA256 |
| --- | --- |
| `apps/server/tests/unit/test_playback_normalization_worker.py` | `8353b3ea449233200d2f3d491253f8ec91d52b6abffab1fc405fde77a5b563f5` |
| `apps/server/tests/integration/test_postgres_migrations.py` | `6b55d91c182549e194e9aa9f3eab4692f285e1c25c18ace880e3346790d81789` |
| `apps/server/tests/integration/test_deployment_backup_snapshot.py` | `a8f954e536e9deb00d523a7bdf8d3d24abeeb0bd8c62ade9bbb1f50e3b101b81` |
| `infra/scripts/rec-db-backup-inventory.sql` | `d9e761add12c8504b55624d72c286b2eb3dafd981afa99a01ffe2107d92e0295` |
| `infra/scripts/rec-db-verify.py` | `9867255f6bf350b1b5222c4f247613ccf184e64002f753c49de31dc59fc58548` |
| `changes/unreleased/F140.yaml` | `f017a082190f6e127d7a2b466dd59c62d1021a6a89fdb3b0c5337e64d4d90b75` |

## Сохранённые границы

Прежняя таблица hashes отчёта B1–B3 является исторической проверенной версией;
её не нужно молча заменять. В этом дополнении изменён checksum F140.yaml;
новая точная сумма приведена выше. Код и оба тестовых файла самого импорта,
CLI, модель, миграция 0107 и tasks остаются прежними.
Все восемь checklist и tasks побайтно совпадают с HEAD. Новых отметок нет;
сохраняются предметные IMP 10/0 и общий итог CHK 158/62.

T075/#4930 остаются открытыми: CSV ↔ authenticated provider API ↔ ledger
сверка и внешние условия запуска отдельно. `financial_status=not_checked`
не меняется. Окончательные GitHub-проверки нового точного SHA и основы
обязательны после обновления PR; локальные 142 PASS их не заменяют.
