# Приёмка серверного выпуска v2026.10.27.2

Опубликован 27.10.2026 в 20:41:39 UTC. Источник и работающая версия:
`c4a742eb9fb3f9c9d62d8c4f6e5b9bd12c0a62c4`.
База: опубликованный v2026.10.27.1, `7e32f0da25db5d78d742f9cde1ed59a49ffcaf1a`.
Полоса выпуска — release/deploy; этот отчёт — docs-only/mechanical.

## Проверенная цепочка

- [x] Все 21 PR после базы приняты штатной сверкой: #7735, #7747, #7749,
  #7752–#7767, #7769 и #7770. Train `train-20261027T201109Z-c4a742eb9fb3`.
- [x] Candidate `rc-20261027T201336Z-b6489893dcef`; digest CHANGELOG:
  `sha256:af4865ad7598fa16f18660c39e3edb9b0ab196d9163f6c1dd40a9af287e2e78e`.
- [x] Единственная авторитетная [полная проверка 40576128669](https://github.com/yshishenya/graf/actions/runs/40576128669)
  — SUCCESS на точном source; все компоненты совпали, `skipped_gates=[]`.
  SHA-256 evidence: `9f444d8d9de797b646e44e9a8a5033365e7f5583ad5158d5e8d90a96318b53ef`.
- [x] Train-attest/decision — go; неизменные candidate, evidence и decision
  повторно приняты `validate --current` и CD dry-run.
- [x] Штатные backup, миграции/RLS, образы, health и smoke пройдены;
  `deploy_result=pass`, source/runtime совпадают. Backup оставлена в закрытом
  хранилище рабочего сервера; на Mac не копировалась.
- [x] После smoke повторно подтверждена готовность Temporal/processing-worker.
- [x] [GitHub Release](https://github.com/yshishenya/graf/releases/tag/v2026.10.27.2)
  не draft и не prerelease; annotated tag разрешается в source выше.
  Publication attestation `pa-rc-20261027T201336Z-b6489893dcef` создана
  в 20:41:42 UTC и подтверждает тот же SHA.

Первый Full 40573065595 на прежнем source завершился ошибкой правила текста
и не использовался как разрешающий. Исправление #7770 прошло обязательные
проверки, после чего заморожен новый кандидат.

Driver остановил первую попытку execute до удалённых действий с
`branch_mismatch`: текущая рабочая копия detached. Занятая основная ветка
master не менялась. Для штатного CD создан отдельный временный shared clone
с чистой веткой master на принятом SHA; исходные абсолютные decision/evidence
не менялись. Validate, dry-run и execute прошли, повторный Full не запускался.
После публикации чистота копии проверена, временная копия удалена; журналы
и метаданные сохранены. Неизменяемая запись первоначального отказа сохранена.

## Публичные материалы

- [x] Все 17 canonical URL: HTTP 200, по одному H1/title/description/canonical,
  уникальные title/description, без noindex; неизвестный URL — 404.
- [x] В [руководстве протокола](https://rec.2brain.pro/guides/protokol-vstrechi-iz-zapisi#graf-result)
  прочитаны пять сопоставлений настоящего учебного результата, ошибка и
  ограничения. CTA в действующей сессии открывает «Мои встречи».
- [x] Два версионных PNG доступны без входа: image/png, 1200×630,
  32026/31149 байтов; SHA-256 совпадают с подготовленными файлами.
- [ ] Реальная карточка предпросмотра площадкой (G042) не подтверждена.
  Сообщения для такой проверки не отправлялись; наш черновик ссылки очищен.

PR материалов [#7766](https://github.com/yshishenya/graf/pull/7766): source
`1435d14dc7cb942fa5abf65ee3ab018c1bc565c3`, checked base
`873b264730c022bed28526e198067e546cc9b069`, merge
`a1e11dfd2157564dcc835b2018eab25736d49b93`. Общий validator обязательных
проверок PASS: governance 40570217656, native 40570217541, metadata 40570225990.

## Работающие службы и TLS

API, processing-worker, media-worker и maintenance используют source выше;
restart_count=0. Первые три healthy, у maintenance нет healthcheck.
Установлены certifi 2026.10.23, HTTPX 0.28.1, Requests 2.34.2;
aiohttp отсутствует, системные CA 20250419~deb12u2.

В работающих API, processing-worker и maintenance оба проверочных адреса
eMudhra отклонены именно проверкой сертификата; pypi.org — HTTPS/200.
Проверены HTTPX, Requests и default system SSL.

Media-worker по конструкции работает во внутренней сети без выхода наружу.
Его внешняя live-проба неопределённа, включая контрольный адрес. Поэтому
первоначальный общий runtime-отчёт имеет `all_pass=false`, а не общий PASS.
Тот же установленный media image
`sha256:45cdac7e6a058143eda1bab03a21cd82fb73aa94f749096d3af2fca5d918df23`
отдельно прошёл 9 TLS-проверок во временном ограниченном контейнере без
mounts/секретов. Контейнер удалён; изоляция работающей службы сохранена.
Это отдельное доказательство образа, а не успешная внешняя проба live media.
F291/T008 автоматически не принимается и не закрывается.

## Ограничения и измерение

Расширенная аналитика и запись IP выключены. Nginx не применялся;
T098, G010–G019, полное восстановление/наблюдение F273 и коммерческие
AC01–AC06 остаются открытыми. [Карта разрывов воронки](../../growth/measurement-chain-2026-10-27.md).
Вердикт CD: `infra_smoke_ready`, `playback_normalization_scope=worker_capability_only`.
Automatic retry, backfill inventory, Range playback и normalization cleanup
сохраняют `required_post_deploy`. Новый клиент macOS/appcast не публиковался.

Все посещения этой приёмки — операторские/автоматические; ими не подтверждены
новые клиенты, поисковые клики, пригодность частных встреч или продажи.
Окно освобождено сообщением задаче «Проверь порядок в репозитории» после
публикации и приёмки.

Метаданные под игнорируемым `.dev/growth/`: `release2-publish.log`,
`release2-temp-clone-dry-run.log`, `release2-temp-clone-deploy.log`,
`public-release2-acceptance.json`, `runtime-release2-acceptance.json`,
`media-image-tls-acceptance.json`; publication record — `.dev/release/attestations/`.
