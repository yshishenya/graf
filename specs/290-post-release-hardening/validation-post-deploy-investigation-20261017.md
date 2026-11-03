# F290: исследование четырёх post-deploy проверок

Дата: 2026-10-17. Lane: high-risk-product, текущий объём — чтение,
проект процедур и изолированная проверка существующего кода. T009/T010/T011
остаются открытыми. Новый runtime код, production-запись, commit, merge,
выпуск и закрытие #6501/#7646 здесь не выполнялись.

## Изолированный PostgreSQL

Исходник: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5` плюс замороженный
первый CI-срез; его 23 файла повторно сверены и не менялись. Команда восьми
файлов — в `post-deploy-procedures.md`; штатный runner `--focused`, без
production `.env`, в уникальном контейнере PostgreSQL17 на loopback/tmpfs.

Использовано существующее окружение canonical checkout с `UV_NO_SYNC=1`.
`uv.lock` и `pyproject.toml` побайтно равны этой рабочей копии; `uv pip check`
подтвердил совместимость 80 установленных пакетов. Новое чистое окружение
не создавалось, зависимости не устанавливались.

**133 PASS, 0 FAIL, 0 SKIP**, pytest 51.83s, этап runner 56s, exit0.
Collection digest:
`f573f067c63ece570141d35d9d125340fd26be17a50ff6fe9054a8c3b13be6e4`.

| Набор | Пройдено |
|---|---:|
| retry | 3 |
| restart | 8 |
| backfill | 5 |
| priority | 2 |
| deletion | 7 |
| cabinet playback route | 17 |
| deployment readiness gates | 80 |
| normalization worker unit | 11 |

Один `PytestAssertRewriteWarning` о ранее импортированном
`tests.fixtures.postgres_test_database`; провалов и пропусков нет. Runner
сообщил штатное удаление своего контейнера; отдельный `docker ps -a`
подтвердил отсутствие контейнера с префиксом этого запуска. Диск до запуска:
91 GiB свободно. Тесты подменяют storage, Temporal и media pipeline, поэтому
этот PASS не доказывает четыре живых результата или работу FFmpeg.

## Настоящий FFmpeg на Mac

Существующий `verify_playback_normalization_runtime.py` запущен без изменения
кода в собственном приватном временном каталоге. Полный прогон **FAIL**:
`Unknown encoder 'libvorbis'` в локальной сборке FFmpeg. Адресная диагностика
повторила только создание источников: WAV/MP3/AAC/FLAC созданы, Ogg Vorbis
не создан. Остальные сценарии полной матрицы не объявляются пройденными.
Кодировщики host-среды не переустанавливались; оба собственных временных
каталога удалены. Это ограничение host-среды, не диагноз рабочего Linux image.

## Штатный Linux media-runtime

После host-диагностики выполнен существующий
`infra/scripts/test-playback-normalization-container.sh`, без изменения кода.
До сборки 91 GiB, после — 90 GiB свободно. Использована чистая закреплённая
основа `infra/server/Dockerfile`, сборка media-runtime, Linux arm64; зависимости
образа установлены штатным Dockerfile, host-среда не менялась.

**14 сценариев PASS**: 12 входных форматов, canonical byte-copy и faststart
remux. FFmpeg5.1.9-0+deb12u1, полный decode PASS, отказ non-file protocol PASS,
non-root, network none, read-only rootfs, private tmpfs512m, memory1g,
cpu1, cap-drop ALL и no-new-privileges. Проверялся настоящий pipeline.

Build image:
`sha256:8e85d8052f079c78bda207a483745b9758018978227d15d17037808a7feb192d`.
Exit0, synthetic residue0, container residue0, image tag residue0;
отсутствие собственного контейнера и тега образа подтверждено отдельно.
Штатный кэш сборки не очищался. Это локальная Linux capability-проверка,
не проверка установленного production image или четырёх US3 сценариев.

## Чтение текущего inventory

На рабочем сервере 2026-10-16T22:39:25–22:39:29Z подтверждён исходник
`834bdc87e3c83ebd86e1afd2c6e7760229b7297d`. В существующем `rec-postgres`
выполнен только `REPEATABLE READ READ ONLY`, timeout10s, `ON_ERROR_STOP=1`,
с положительной проверкой существующей роли `rolsuper OR rolbypassrls`
и SELECT на обе таблицы; права и RLS не менялись. Сохранены только boolean:

- Наличие run: true.
- Завершённый inventory имеет timestamp: true.
- Активный legacy job соблюдает inventory gate: true.
- Сумма четырёх action counters равна evaluated_count: true.

Exit0, ROLLBACK подтверждён. Это один текущий снимок четырёх условий. Полнота
перечня, обработка страниц, причины blocked, drain и новые synthetic jobs
этим не доказаны. Записывающая inventory функция не вызывалась.

## Независимое ревью и остаток

`review-post-deploy-20261017.md` проверяет исходники и проект процедур.
Найденное неверное использование `JsonHttpClient` исправлено на существующий
httpx с проверкой origin/token-file и запретом redirects. Уточнены и повторно
независимо приняты пределы
жизни/объёма, завершение собственного active control до cleanup, наблюдение
поздних записей и контекст SELECT. PD02–PD04 устранены документально;
PD01 остаётся P1. Все девять readiness gates сохраняются;
четыре US3 результата не заменяют остальные пять.

Реальный пробел: нет проверенного исполнителя однократного отказа только
собственного attempt, synthetic backfill, удержания browser session и cleanup
с положительной проверкой принадлежности. Требуется его уточнённый design,
owned paths, независимое ревью и исполнимые регрессии. Общий worker нельзя
останавливать ради такого сценария. До этого T009/T010 не завершены;
production-запуск T011 требует отдельного согласия на готовый объём.

Доказательства операторского реестра:
`F290-us3-baseline-environment-20261017.json`,
`F290-us3-baseline-result-20261017.json`,
`F290-us3-baseline-20261017.log`,
`F290-us3-baseline-reports-20261017/focused.jsonl`,
`F290-host-ffmpeg-capability-20261017.json`,
`F290-host-ffmpeg-diagnosis-20261017.json`,
`F290-linux-media-capability-20261017.log`,
`F290-linux-media-capability-result-20261017.json`,
`F290-backfill-readonly-snapshot-20261017.json`.
