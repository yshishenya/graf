# T014/#3361: сохранность пути при проверяемом скачивании

Полоса: **high-risk-product**, существующая F099/T014. Исходная база
`c22500f994a0dc5f951341e3c5f202d5d21ac8a2`; локальная ветка
`codex/099-preserve-existing-download`. Это ограниченная проверка серверного
метода, не доказательство выпуска или фактического рабочего провайдера.

## Требования и предварительные ворота

Уточнены FR-029/031/037/045, SC-018/025 в существующих spec/plan/quickstart;
T014 явно переоткрыта с сохранением истории. Независимое повторное ревью
качества требований: **100 checked / 0 unchecked**. Его внешний отчёт
`f099-t014-independent-requirements-rereview-20261117.md`, SHA-256
`2d5795822a2e350b2e63416181fc0e74366b534523495b8bc1b0d45e5a682c9e`.
Это отдельная проверка качества требований; ревью реализации описано ниже.
Текущие spec/plan/tasks проанализированы без блокирующих несогласованностей;
в существующих 128 tasks уникальные ID, единственная открытая — T014.
Дубли задач/issues не создавались. Штатные canon ensure и validate прошли:
281 Spec Kit issue. Синхронизация #3361:
https://github.com/yshishenya/graf/issues/3361#issuecomment-6944852084.
Внешняя квитанция предварительного допуска:
`f099-t014-implementation-admission-20261117.json`.

## Что изменено и почему

`MinioStorage.download_verified_to_path`: в обработчике OSError прежний
`descriptor = -1` теперь запрещает unlink до успешного exclusive create.
Это общий корень для async wrapper и двух потребителей: normalization
`_download_verified_artifact` и processing `_stage_artifact`. Сигнатуры,
O_EXCL/O_NOFOLLOW, 0600, fsync, bounded reads и действующие reason mappings
сохранены. StorageTransferError после создания по-прежнему чистит свой partial.
Нет схемы, новых зависимостей, UI, новых путей отправки или управления повторами.

## RED → GREEN

Изолированная собственная `.venv`: CPython 3.13.3, `uv sync --frozen --extra dev`,
исходный lock, 74 пакета. Чужое окружение не использовалось; uv проигнорировал
унаследованный VIRTUAL_ENV, последующие запуски удаляют только эту переменную
из окружения дочернего процесса. Настоящие модули импортированы полностью;
AST probe — отдельное предыдущее доказательство, здесь не применялся.

Команда из apps/server:

```sh
uv run --frozen --extra dev pytest -q tests/unit/test_playback_normalization_storage.py --tb=short
uv run --frozen --extra dev ruff check src/twobrain_rec_server/storage/minio_client.py tests/unit/test_playback_normalization_storage.py
```

- Первый вариант новых fixtures: 18 failed / 32 passed. Пять отказов были
  ошибкой позиционных аргументов S3Error в тесте; они исправлены именованными
  параметрами. Atime исключён из сравнения цели ссылки: чтение само меняет
  время доступа и не означает потерю содержимого.
- Исправленный fixture на неизменённом production source: **13 failed /
  37 passed**, ожидаемый RED. Пять collision случаев в async/обоих consumers
  и восемь отказов до create нарушили сохранность/запрет unlink.
- После единственного guard: **50 passed**, 2 предупреждения инфраструктуры
  тестов (pytest rewrite уже импортированного модуля и Starlette/httpx).
- Ruff: PASS. Проверяются также исходные immutable UUID object keys,
  disk-backed upload/download и digest; исходная T014 не сведена к collision.

## Покрытие и границы доказательств

| Требование | Наблюдаемый результат |
|---|---|
| FR-045, SC-025 до create | Настоящие regular/symlink, ENOSPC/EACCES с/без leaf; inode/байты/права/ссылка/цель сохранены, unlink не вызван |
| FR-031/045 после create | write/fsync/short/extra/max/digest: правильная причина, удалён только свой partial |
| FR-029/045 ресурсы | >4 MiB и маленькие порции; read bounds, 0600, O_EXCL/O_NOFOLLOW, настоящий fstat подтверждает закрытый descriptor; close/release проверены раздельно |
| FR-031/037 общий путь | async wrapper, оба consumers через async и sync: success/collision/missing/digest/unavailable, прежние reason mappings без диагностического содержимого |
| T014 исходный объём | Прежние key-builder/upload/digest тесты проходят в том же полном файле |

Ответ MinIO синтетический; ENOSPC/EACCES/write/fsync внедряются в обозначенной
точке. Файловая система и descriptor настоящие, только собственный tmp_path.
Сетевой I/O, DB/Temporal, настоящий accepted ingest→публикация, приложение,
MinIO integration, production и фактическая автоматическая пользовательская
приёмка этим набором не доказаны. Исходные критерии #3361 сохраняются.
Post-open pathname replacement и ошибки самой unlink/close/release не проверены.
Реальные данные, почта, платежи и службы не затронуты.

## Оставшиеся ворота

Собственная сходимость текущего исправления завершена: 6 относящихся ключей
FR/SC, две исходные части T014 и пять решений активного plan; новых
обязательных доработок кода нет. Внешний отчёт
`f099-t014-root-converge-20261117.md`, SHA-256
`a35fcad4e3040956a5ff4e267a1445846cf204be4c9831067ca64b9f03d4a1f9`.
Он относится к текущему исправлению; исходная приёмка T014 остаётся открытой.

Штатный `check_spec_kit_governance.py` прошёл после установки настоящей
закреплённой `specify-cli 1.0.7` из commit
`fe1d00e3ccaf495880aaf90fb0e17679e82f065b` в отдельное временное окружение
`uv tool`. Глобальная 1.2.6, lock проекта и verifier не менялись. Первые отказы
из-за версии/ref сохранены как история. Changelog/diff прошли. Проверка
`check-development-process.py` сначала обнаружила неполный owned_paths в
игнорируемом указателе: шесть reviewer-owned списков и validation receipt
не были перечислены. После перечисления уже разрешённых plan путей она
прошла; область кода и задач не расширена.

Отдельное независимое ревью реализации завершено: **Approved, P0–P3 = 0**.
Полный внешний отчёт `f099-t014-independent-code-review-20261117.md`, SHA-256
`1ff3481775de65cc1b31900f7424285c832c0871edde33059a414b96c300cf57`.
Root прочитал его целиком и сверил реальные code/test/caller hashes,
сохранность шести checklist и прежних reports; ошибок сверки нет. Reviewer
не менял код, требования, Git/GitHub и не повторял тесты. Это одобрение
локальной разницы, а не attestation будущего PR SHA.

Остаются окончательные clean exact-SHA проверки, commit/PR,
три штатных exact-head/current-base checks, замечания и проверенный merge.
#3361 и T014 остаются открытыми до индивидуальной проверки исходных критериев;
закрытие только с подробным русским комментарием и штатным
`validate-issue-closeout.py --verify-live`. Выпуск/развёртывание отдельно.
Историческая F099 и F140/T068 не объявляются принятыми этим отчётом.
