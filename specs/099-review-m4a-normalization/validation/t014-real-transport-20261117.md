# T014/#3361 — настоящая автоматическая серверная приёмка, этап A

Дата: 2026-11-17. Lane: `high-risk-product`. Ветка:
`codex/099-real-transport-acceptance`. Проверенная база:
`2805b0f91d5c6d13aad13edb573274b8460e1d19`.

Этот документ фиксирует только фактически исполненный этап A контракта
[real-transport-acceptance.md](../contracts/real-transport-acceptance.md).
Этапы B и C, startup/container/UI/release/deploy и production-приёмка остаются
открытыми. Успех A не закрывает T014 и #3361.

## Что исполнено

Единый запускатель:

```sh
GRAF_F099_DOCKER_HOST=unix:///path/to/docker.sock \
GRAF_F099_TEMPORAL_CLI=/path/to/temporal \
apps/server/.venv/bin/python apps/server/scripts/run_playback_normalization_real_transport.py
```

Запускатель до collection проверил отсутствие `.env`, локальный Docker unix
socket, свободное место, локальные image ID, checksum Temporal CLI, наличие
FFmpeg/ffprobe и frozen-зависимости. Затем он передал существующему
`run_local_postgres_tests.sh --focused` собственный PostgreSQL resource context,
очистил окружение, ограничил дочерний процесс 600 секундами, контролировал 60-секундную фазу
`starting` PostgreSQL по внешнему state и выполнил проверяемую очистку по
сохранённым identity.

Приёмочный файл выбран явно:

```text
acceptance/playback_normalization_real_transport.py
```

Обычный discovery `testpaths=[tests]` его не импортирует. Без контекста
запускателя явный выбор падает до импорта приложения и до создания ресурсов
(проверено contract tests).

## Версии и checksums

| Компонент | Значение |
|---|---|
| PostgreSQL image | `postgres:17-alpine`, `sha256:97106b46c3da2dcd9bcdb89cfb4b9dec61ff62a6f17e77bee6c5487145696e46` |
| MinIO image | `minio/minio:RELEASE.2025-05-24T17-08-30Z`, `sha256:460b46057cbcf8d01c2f7ceae9209290334b75dc1912235b10ad9bd35de056db` |
| Temporal CLI | `1.8.2`, Server `1.31.2`, SHA-256 `268711d469c0b8a981251d49c4f2150c7ae41665018800749b95ca44aa83593a` |
| Temporal Python SDK | `1.30.0` |
| FFmpeg | `8.1.2`, SHA-256 `2ce81b92499c1b6b96eb060c69723114bd0da13f1bfbd9da26dee24d099e644a` |
| ffprobe | `8.1.2`, SHA-256 `c806a3513d745902058911abf087d7dd26bcc7c1e62e5133e36a37eb42ae72b0` |
| PostgreSQL run token | `90ccc58c9292e730a9270f231fb8f7bd` |

Temporal запускался `start_local` с `dev_server_existing_path`, `ip=127.0.0.1`,
случайным портом, `ui=False`, in-memory SQLite и настоящими часами. MinIO
запускался из принятого image ID с `--pull=never`, случайным loopback-портом,
синтетическими credentials и без именованных томов. Media-role проверена как
`NOSUPERUSER`, `NOBYPASSRLS`, `row_security=on`; чужой tenant дал 0 строк.

## Источники

| Сценарий | Файл | Размер | SHA-256 |
|---|---|---:|---|
| A-success | синтетический WAV PCM mono/16 kHz | 32 078 | `25546b9b5994c92d1a8e0cdcde8935a3507462b64ff2d012b3c22274fc4a3b6a` |
| A-corrupt | один нулевой байт, `invalid.wav`, `audio/wav` | 1 | `6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d` |

Оба источника отправлены только через настоящий `POST /api/v1/media-uploads`.
Приёмочный код не вызывал dispatcher, `start_workflow`, reconciliation или
`run_normalization_job`. Workflow handle использовался только для наблюдения.

## Результаты этапа A

| Проверка | Результат |
|---|---|
| A-success HTTP | `202`, один record/revision/job |
| A-success job | `ready`, `canonical_track_artifact_id` заполнен |
| A-success attempt | ровно одна `published`, `full_decode_passed=true`, `moov_before_mdat=true` |
| A-success canonical | 9 268 байт, `sha256:8d8d66826212e6895cec89ea2c8e0c23df70f051179571d15eb99be747f04895` |
| A-success profile/BMFF | AAC-LC 48 kHz mono, `moov` до `mdat`, не fragmented, полный decode PASS |
| A-success source | 32 078 байт и исходный SHA-256 сохранены |
| A-success verified source download | подтверждён вызов helper с исходным SHA-256 |
| A-success Range | `206`, `Content-Range: bytes 0-99/9268`, байты совпали |
| A-corrupt HTTP | `202`, источник принят |
| A-corrupt job | `terminal`, причина ровно `corrupt_source` |
| A-corrupt retry | `next_attempt_at=null` |
| A-corrupt canonical | 0 playback artifacts |
| A-corrupt attempt | 0 `uploaded`/`published`; объекты попытки отсутствуют |
| A-corrupt source | 1 байт и исходный SHA-256 сохранены |

A-success занял 0,62 с, A-corrupt — 0,68 с; общий дочерний запуск — около 20 с.
Пределы контракта (60/120/60/30/600 секунд) не нарушены; 60-секундная фаза
`starting` дополнительно ограничена внешним monitor-потоком запускателя, а не
только внутренним циклом runner.

## Очистка

- PostgreSQL resource context: фаза `removed`, контейнер удалён по проверенному ID.
- MinIO: `removed`, контейнер удалён по проверенному ID и label.
- После запуска не осталось контейнеров `f099`, `graf-postgres-test-*` или
  `graf-minio-test-*`.
- `docker prune` не выполнялся; чужие ресурсы не затрагивались.


## SHA изменённых файлов

| Файл | SHA-256 |
|---|---|
| `apps/server/acceptance/playback_normalization_real_transport.py` | `2b18eb53ff269acdd31d01900f0993492e1f2cd8d7812822dfbc21c172d37b95` |
| `apps/server/scripts/run_playback_normalization_real_transport.py` | `2e86027bdeaa4af9d290c50a2cb935a287c5d597db523f4ffb8c87095ba13993` |
| `apps/server/scripts/run_local_postgres_tests.sh` | `5586db56dcb615828936ef160c338e779561bdbf1157182f3dafd13664cf8348` |
| `apps/server/tests/contract/test_local_postgres_test_runner.py` | `7ad1d51dd3dcc740f5fab0ed407c150ee9a5867cf088c6af86c294305727c600` |
| `apps/server/tests/contract/test_playback_normalization_real_transport_runner.py` | `5629ede639c792ba3aa19d775c707ee67c2201c77a679abf168f350f4ddf8268` |
| `specs/099-review-m4a-normalization/contracts/real-transport-acceptance.md` | `dedc092e7071c60e54c71c37bb3fbae47130a472d9ba025d301caaea055626f0` |

## Analyze

`$speckit-analyze` выполнен по spec/plan/tasks/contract после согласования T014:
CRITICAL — 0, HIGH — 0. T014 имеет task-покрытие; новые пути реализации
перечислены в Plan и Tasks; противоречий с конституцией и F275 не найдено.
Замечания ограничены уже описанной открытой областью B/C и отдельными
startup/container/UI/release/deploy воротами.

## Что остаётся открытым

- B: полная матрица форматов, copy/remux/transcode, wrong extension,
  выбор дорожки.
- C: limits/failure/retry/recovery/backfill/concurrency/deletion/retention/Range
  для всех состояний.
- Startup/reconcile `run_worker()`, non-root production container,
  near-limit benchmark, UI/`GRAF Dev`, release/deploy и production grants.
- T014 и #3361 остаются открытыми до собственных доказательств этих строк.
