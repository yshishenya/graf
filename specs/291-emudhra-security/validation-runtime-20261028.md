# F291: сверка выпущенного сервера и применимости TLS

28.10.2026. Текущая полоса — `docs-only`: сверка существующих доказательств,
без изменения кода, требований, доверенных сертификатов или конфигурации.
Исходный срез относится к `high-risk-product`, выпуск — к `release-deploy`.
Владелец T001–T008 — [#7734](https://github.com/yshishenya/graf/issues/7734).

## Исходники и опубликованный выпуск

[PR #7735](https://github.com/yshishenya/graf/pull/7735) принят на исходном
SHA `56cf5729b7bff5c8cef0d63a6d7bc836c8a6c5ff`, основе
`0a1bce3505cd1582ccda552ba4ac10b4c4258d26`, merge
`48e5d90d197f450367770e5c093cd897eece31fd`.
Общий `validate-pr-checks.py` повторно прошёл при этой сверке:

- [governance-fast 40502921105](https://github.com/yshishenya/graf/actions/runs/40502921105), attempt 1;
- [macos-pr 40502921166](https://github.com/yshishenya/graf/actions/runs/40502921166), attempt 1;
- [pr-metadata 40503034557](https://github.com/yshishenya/graf/actions/runs/40503034557), attempt 1.

Этот merge входит в источник опубликованного
[v2026.10.27.2](https://github.com/yshishenya/graf/releases/tag/v2026.10.27.2):
`c4a742eb9fb3f9c9d62d8c4f6e5b9bd12c0a62c4`. GitHub подтверждает
`draft=false`, `prerelease=false`, публикацию 27.10.2026 в 20:41:39 UTC;
annotated tag отдельно разрешён в тот же коммит.

[release-full 40576128669](https://github.com/yshishenya/graf/actions/runs/40576128669)
— успешный `workflow_dispatch`, attempt 1, точный источник выше.
Неистёкший артефакт `graf-full-ci-rc-20261027T201336Z-b6489893dcef`
получен заново: SHA-256 ZIP совпал с digest GitHub
`fe7870f7213914ebe0c7bfea805714b20382b3111b55a8e922341dc7fc208666`.
Один файл внутри побайтно совпал с сохранённым authoritative evidence,
SHA-256 `9f444d8d9de797b646e44e9a8a5033365e7f5583ad5158d5e8d90a96318b53ef`.
В нём `authoritative_full=true`, `status=passed`, `skipped_gates=[]`;
requested/start/end и все component SHA совпадают с источником выпуска.
Новая полная проверка не запускалась.

Candidate `rc-20261027T201336Z-b6489893dcef`, train
`train-20261027T201109Z-c4a742eb9fb3`, decision `go` и publication
`pa-rc-20261027T201336Z-b6489893dcef` связаны теми же source и digest.
SHA-256 decision —
`30a2cef3c8b16d810a43a2d57f5b312bc1089dbce124730ec6290552de9f9c3f`;
publication ссылается именно на него и опубликованный tag/source.

## Неудачная попытка и последующая публикация

Ранняя попытка CD 27.10.2026 в 20:25:00 UTC остановилась с
`deploy_result=blocked`, `reason=branch_mismatch` до действий CD на рабочем сервере.
Штатный EXIT-handler `scripts/release.sh` сохранил отдельный
`.abandoned.json` рядом с неизменным candidate. Его текст «кандидат оставлен
без выпуска» относится к этой попытке; сам файл сохранён. Создание GitHub tag
и его штатное удаление при этом отказе уже состоялись; их не следует путать
с развёртыванием на сервере.

Позднее оператор использовал чистую временную рабочую копию на точном
источнике с веткой `master`. Сохранённые dry-run и deploy журналы подтверждают
повторную проверку того же decision/evidence, `backup_result=pass`,
`deploy_result=pass`, совпадение deployed/runtime SHA, публичную проверку
сохранённых macOS download/update и повторные
`final_temporal_readiness_result=pass` /
`final_processing_worker_readiness_result=pass` после smoke.
Публикация и attestation в 20:41 UTC подтверждены отдельно.
Ранний отказ и последующий успех не объединяются в один успешный запуск.

Это соответствует принятому
[отчёту выпуска](../../docs/deployments/2brain-rec/release-v2026.10.27.2.md).
Сам `backup_result=pass` не является доказательством восстановления.

## Фактические службы

Новая читающая проверка выполнена 27.10.2026 в 22:07:28 UTC
(28.10.2026 по местному времени). Для каждой службы image source label
`org.2brain.graf.dev.source-sha` и runtime `GRAF_DEV_SOURCE_SHA` совпадают
с источником выпуска. Все четыре службы работают, число перезапусков — 0.

| Служба | Состояние | Образ |
|---|---|---|
| API | healthy | `sha256:d1c0b42846ccbca724e377eebdecbdb2c54ca39ad16597981ec56ec070e96223` |
| processing-worker | healthy | тот же server image |
| media-worker | healthy | `sha256:45cdac7e6a058143eda1bab03a21cd82fb73aa94f749096d3af2fca5d918df23` |
| maintenance | running, healthcheck не настроен | тот же server image |

Во всех четырёх контейнерах прочитаны certifi 2026.10.23, HTTPX 0.28.1,
Requests 2.34.2, системный пакет CA 20250419~deb12u2; стандартный SSL-контекст
загружает 148 CA. Переменные переопределения trust store не установлены.
Этот шаг не выполнял внешние запросы, перезапуски, миграции или чтение встреч.

## Применимость внешнего HTTPS для media-worker

FR-004, SC-001 и quickstart §5 требуют проверки применимых HTTP-клиентов.
User Story 1 относится к защищённым исходящим соединениям. Для данной
конфигурации внешний HTTPS media-worker — **неприменим**, со следующим
проверенным основанием:

- Production Compose и фактический Docker inventory дают ровно одну сеть
  media-worker: `twobrain-rec-media-private`, `internal=true`.
- Точка запуска `normalization.worker` использует внутренние PostgreSQL,
  Temporal и MinIO. `MinioStorage` получает внутренний `rec-minio:9000`,
  `secure=false`; это HTTP внутри принятой сети, без TLS-рукопожатия.
- Temporal подключён без outcome tracing; FFmpeg ограничен файловым
  протоколом. Пути worker/storage/Temporal/FFmpeg сверены с исходником выпуска.

При выпуске в работающих API, processing-worker и maintenance три клиента
(HTTPX, Requests, системный SSL) отвергли оба advisory-сертификата именно
ошибкой проверки сертификата и приняли контрольный `pypi.org`: **27 PASS**.
У media-worker все внешние пробы, включая контроль, остались неопределёнными.
Исходный общий runtime JSON сохраняет `all_pass=false` и эти результаты.
Они не переименованы в TLS PASS. Отдельные **9 PASS** того же media image
во временном контейнере подтверждают образ, не внешнее соединение работающей
службы. Обновление CA, проверка image/source/packages/health для media-worker
остаются обязательными и подтверждены выше.

Если появятся HTTPS-получатель, другая сеть или конфигурация клиента,
применимость проверяется заново до приёмки. Текущая запись не даёт постоянного
исключения и не разрешает менять сеть или отключать TLS ради проверки.
Независимое основание и проверка всех восьми пунктов требований:
[отчёт проверяющего](review-runtime-applicability-20261028.md).

## Остаток T007/T008

T007/T008 пока остаются `[ ]`. В проверенном наборе release evidence не найдено
отдельного принятого подтверждения применимости разрешения резервирования
и успешной проверки восстановления. Последний плановый запуск
[40296980179](https://github.com/yshishenya/graf/actions/runs/40296980179)
завершился ошибкой; это не успешное восстановление. Отсутствие такого журнала
в проверенных каталогах не доказывает отсутствия всех иных свидетельств.
Для завершения нужно найти и проверить подлинные записи либо выполнить
предусмотренную изолированную приёмку в согласованной области.

Выпуск и TLS-пакетные проверки не заменяют этот пункт. #7734 остаётся открытой;
перед её закрытием обязательны принятый итог T007/T008, подробный русский
комментарий и штатный `validate-issue-closeout.py --verify-live
--require-release-full`. Остальные открытые критерии воспроизведения медиа,
аналитики и приёмки macOS из отчёта выпуска не присваиваются F291.

При этой сверке новый выпуск, production execute, backup/restore, изменение
сети и запуск GRAF Dev не выполнялись. Пользовательские данные не копировались.
