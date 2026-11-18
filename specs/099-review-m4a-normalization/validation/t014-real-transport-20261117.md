# T014/#3361 — настоящая автоматическая серверная приёмка, этап A

Дата: 2026-11-18 UTC. Lane: `high-risk-product`. Ветка:
`codex/099-real-transport-acceptance`. Проверенная база:
`2805b0f91d5c6d13aad13edb573274b8460e1d19`.

Этот документ фиксирует только фактически исполненный этап A контракта
[real-transport-acceptance.md](../contracts/real-transport-acceptance.md).
Этапы B и C, startup/container/UI/release/deploy и production-приёмка остаются
открытыми. Успех A не закрывает T014 и #3361.

## Допуск и привязка к коду

Implementation admission выдан после независимого reviewer PASS 120/0,
analyze без CRITICAL/HIGH и sync существующего #3361. Reviewer-owned checklist
не редактировался основным агентом.

Финальный прогон: run token **`098af0b4671aa3ecd59c7368584da649`**,
`started_at=2026-11-18T00:13:43Z`, `finished_at=2026-11-18T00:14:02Z`.

Receipt привязан к исполненным файлам:

| Артефакт | SHA-256 |
|---|---|
| supervisor | `b214f4efc6729c3bd1a0b7db3111a46289fe60fdfff03d9713bb9afb6831c9ce` |
| acceptance | `4636408b15ffcc71bceb132bff9644892e64aff4b0a121efdd5cce0b2c06356b` |
| PostgreSQL runner | `3f55b37506594453e80fd5f5801114f2faf71020aa2f41e1401b18f0d0f366a2` |

## Что исполнено

Единый запускатель:

```sh
GRAF_F099_DOCKER_HOST=unix:///path/to/docker.sock \
GRAF_F099_TEMPORAL_CLI=/path/to/temporal \
apps/server/.venv/bin/python apps/server/scripts/run_playback_normalization_real_transport.py
```

Запускатель до collection проверил отсутствие `.env`, локальный Docker unix
socket, свободное место не меньше 10 GiB, локальные image ID, checksum Temporal
CLI, наличие FFmpeg/ffprobe и frozen-зависимости. Затем он передал
существующему `run_local_postgres_tests.sh --focused` собственный PostgreSQL
resource context, очистил окружение, ограничил дочерний процесс 600 секундами,
контролировал 60-секундную фазу `starting` PostgreSQL по внешнему state и
выполнил проверяемую очистку по сохранённым identity.

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

Temporal запускался `start_local` с `dev_server_existing_path`, `ip=127.0.0.1`,
случайным портом, `ui=False`, in-memory SQLite и настоящими часами. MinIO
запускался из принятого image ID с `--pull=never`, случайным loopback-портом,
синтетическими credentials и без именованных томов. Media-role проверена как
`NOSUPERUSER`, `NOBYPASSRLS`, `row_security=on`. После появления meeting та же
роль видела ровно 1 строку своего tenant и 0 строк чужого.

## Источники

| Сценарий | Файл | Размер | SHA-256 |
|---|---|---:|---|
| A-success | синтетический WAV PCM mono/16 kHz | 32 078 | `25546b9b5994c92d1a8e0cdcde8935a3507462b64ff2d012b3c22274fc4a3b6a` |
| A-corrupt | один нулевой байт, `invalid.wav`, `audio/wav` | 1 | `6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d` |

Оба источника отправлены только через настоящий `POST /api/v1/media-uploads`.
Приёмочный код не вызывал dispatcher, `start_workflow`, reconciliation или
`run_normalization_job`. Workflow handle использовался только для наблюдения.
Durable job и отсутствие canonical проверены до старта worker, поэтому результат
не зависит от гонки с обработкой.

## Результаты этапа A

| Проверка | Результат |
|---|---|
| A-success HTTP | `202`, один record/revision/job |
| A-success barrier | ровно один job, canonical ещё отсутствует, worker не запущен |
| A-success job | `ready`, `canonical_track_artifact_id` заполнен |
| A-success attempt | ровно одна `published`, `full_decode_passed=true`, `moov_before_mdat=true` |
| A-success canonical | ровно один validated/stored playback, 9 268 байт, `sha256:8d8d66826212e6895cec89ea2c8e0c23df70f051179571d15eb99be747f04895` |
| A-success profile/BMFF | AAC-LC 48 kHz mono, `moov` до `mdat`, не fragmented, полный decode PASS |
| A-success source | 32 078 байт и исходный SHA-256 сохранены |
| A-success verified source download | подтверждён вызов helper с исходным SHA-256 |
| A-success Range | `206`, `Content-Range: bytes 0-99/9268`, байты совпали |
| A-corrupt HTTP | `202`, источник принят |
| A-corrupt job | `terminal`, причина ровно `corrupt_source` |
| A-corrupt retry | `next_attempt_at=null` |
| A-corrupt canonical | 0 playback artifacts |
| A-corrupt attempt | 0 `uploaded`/`published`; объекты попытки отсутствуют |
| A-corrupt source | 1 байт и исходный SHA-256 сохранены, байты скачаны и сверены |
| A-corrupt work directory | нормализационная рабочая папка пуста |

A-success занял 0,6 с, A-corrupt — 0,7 с; общий дочерний запуск — около 20 с.
Пределы контракта (60/120/60/30/600 секунд) не нарушены; 60-секундная фаза
`starting` дополнительно ограничена внешним monitor-потоком запускателя.

## Проверки запускателя и обычного CI

- `pytest tests/contract/test_local_postgres_test_runner.py tests/contract/test_playback_normalization_real_transport_runner.py` — **124 passed**.
- H1 doubles: malformed/symlink manifest, image mismatch до SQL, потеря ответа
  create после появления контейнера, отсутствие cidfile, foreign/unknown
  ownership, cleanup failure, повтор только после подтверждённого удаления,
  TERM/KILL, whole-run timeout и 60-секундный bootstrap monitor.
- H2: обычный `testpaths=[tests]` не импортирует acceptance; явный выбор без
  контекста падает до application imports; реальный pytest discovery проверен
  на синтетическом проекте.
- Ruff по изменённым Python-файлам — PASS; `bash -n` — PASS.
- Обычный runner без `GRAF_TEST_POSTGRES_RESOURCE_DIR` сохраняет прежние
  selection/режимы; `--no-sync` включается только в resource context.

## Очистка

- PostgreSQL resource context: фаза `removed`, контейнер удалён по проверенному ID.
- MinIO: `removed`, контейнер удалён по проверенному ID и label.
- После запуска не осталось контейнеров `f099`, `graf-postgres-test-*` или
  `graf-minio-test-*`.
- `docker prune` не выполнялся; чужие ресурсы не затрагивались.
- Supervisor receipt: `work_directory_cleanup=removed`, `scenario_count=2`,
  `bootstrap_timed_out=false`.

## Analyze и ревью

`$speckit-analyze` по spec/plan/tasks/contract: CRITICAL — 0, HIGH — 0;
T014 имеет task-покрытие, новые пути перечислены в Plan и Tasks, противоречий с
конституцией и F275 нет.

Независимые ревью выявили и заставили исправить:

- cleanup timeout больше не прерывает очистку остальных ресурсов;
- tenant isolation проверяется после появления meeting, а не на пустой таблице;
- barrier вынесен до старта worker, чтобы не было ложного FAIL/Pass из-за гонки;
- добавлены отсутствовавшие H1-doubles и проверка байтов повреждённого source;
- receipt привязан к SHA supervisor/acceptance/runner и содержит acceptance summary.

## SHA изменённых файлов

| Файл | SHA-256 |
|---|---|
| `apps/server/acceptance/playback_normalization_real_transport.py` | `4636408b15ffcc71bceb132bff9644892e64aff4b0a121efdd5cce0b2c06356b` |
| `apps/server/scripts/run_playback_normalization_real_transport.py` | `b214f4efc6729c3bd1a0b7db3111a46289fe60fdfff03d9713bb9afb6831c9ce` |
| `apps/server/scripts/run_local_postgres_tests.sh` | `3f55b37506594453e80fd5f5801114f2faf71020aa2f41e1401b18f0d0f366a2` |
| `apps/server/tests/contract/test_local_postgres_test_runner.py` | `49d66d3d085ae0c588e10a75efb04891d4dc48c81b0a5500ebe41e1562ebf0c5` |
| `apps/server/tests/contract/test_playback_normalization_real_transport_runner.py` | `267e7c59ec6e3ad781ab074a971f6cdbfda1cbb033d664d40bc7a52cda28eeb0` |
| `specs/099-review-m4a-normalization/contracts/real-transport-acceptance.md` | `3cace5eb63fc16ebfb20f6c7c657deffea420124e25b8e67dd5b96411d8f8a50` |

## Что остаётся открытым

- B: полная матрица форматов, copy/remux/transcode, wrong extension,
  выбор дорожки.
- C: limits/failure/retry/recovery/backfill/concurrency/deletion/retention/Range
  для всех состояний.
- Startup/reconcile `run_worker()`, non-root production container,
  near-limit benchmark, UI/`GRAF Dev`, release/deploy и production grants.
- T014 и #3361 остаются открытыми до собственных доказательств этих строк.
