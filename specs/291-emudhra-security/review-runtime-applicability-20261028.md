# Независимая проверка применимости runtime-проверок F291

Дата: 2026-10-28. Область: качество reviewer-owned требований и документальная
приёмка применимости для T007/T008, issue #7734. Проверяющий не выполнял новых
запросов в production/GitHub, тестов продукта, перезапусков или изменений сети.
Прочитаны локальные первичные результаты и исходники. Это не общая приёмка
выпуска и не разрешение закрыть issue.

Основа чтения: ветка `codex/291-runtime-closeout`, HEAD
`1cd847d934a1d8070ff218b925fa5a688127ed78`. Выпущенный source:
`c4a742eb9fb3f9c9d62d8c4f6e5b9bd12c0a62c4`, tag `v2026.10.27.2`.
Полоса проверки: независимое документальное ревью существующей F291;
код, spec, plan, tasks, принципы проекта и результаты проверок не меняются.

## Вывод по применимости

Ограниченная неприменимость внешней HTTPS-пробы к текущему прикладному пути
`rec-media-worker` обоснована исходными требованиями. Основание — отсутствие
в этом пути прикладного внешнего HTTPS и его действующая изолированная сеть,
а не неуспех сетевой пробы. FR-004, SC-001 и quickstart §5 определяют проверку
применимых клиентов. Широкое описание Independent Test User Story 1 следует
читать вместе с этими измеримыми условиями, а не как требование добавить
worker новый внешний сетевой путь.

`github-issue-canon.md`, Closing Rules, допускает явно обозначенную
неприменимость с причиной. Это не отменяет известную проблему безопасности и
не подменяет отсутствующее доказательство: обновлённые CA/пакеты установлены,
образ отдельно проверен, а фактический прикладной путь не использует внешнее
HTTPS. При переходе MinIO на HTTPS, включении внешних клиентов/отправителей,
изменении сети или пути обработки решение необходимо пересмотреть. Открывать
сеть, ослаблять TLS или вводить новую инфраструктуру ради этой проверки не нужно.

## Прослеженный прикладной путь

Исходники следующих путей на проверяемом HEAD побайтно совпадают с выпущенным
source: `infra/docker-compose.yml`, `normalization/`,
`storage/minio_client.py`, `workflows/temporal_client.py`,
`observability/logging.py` в `apps/server/src/twobrain_rec_server/`.

- Compose запускает `normalization.worker`, выключает web runtime и подключает
  media-worker только к `twobrain-rec-media-private` с `internal: true`.
- `MinioStorage` получает внутренний endpoint `rec-minio:9000` и
  `TWOBRAIN_MINIO_SECURE=false`: текущая передача объектов использует внутренний
  HTTP. `normalization.service` загружает объект в локальный файл с проверкой
  размера/хеша; ffmpeg/ffprobe используют `-protocol_whitelist file`.
- `run_worker` регистрирует normalization/readiness activities и подключается
  к внутреннему `rec-temporal:7233`. Он не включает ветку
  `outcome_tracing=True`, в которой создаётся Langfuse.
- Настройка журналирования использует `logging.StreamHandler`; внешнего
  HTTP-отправителя в этом пути нет. В прочитанных worker/service/pickup/logging
  нет вызова HTTPX/Requests/aiohttp для внешнего HTTPS.

Это ограниченный вывод о текущем пути media-worker. Он не утверждает отсутствие
всех потенциальных сетевых клиентов во всём серверном приложении.

## Результаты нельзя объединять в ложный PASS

Локальные первичные файлы обозначены логическим корнем `DEV`.

| Доказательство | Установлено чтением | Предел |
| --- | --- | --- |
| `growth/runtime-release2-acceptance.json` | API, processing-worker и maintenance: HTTPX/Requests/system SSL × два advisory-адреса и контроль, всего 27 PASS | Это выполненные проверки выпуска; проверяющий их заново не запускал |
| Тот же файл, media-worker | Все 9 исходов неопределённы, включая обычный контроль; `tls_pass=false`, общий `all_pass=false` | Не является доказательством TLS rejection; исходный файл сохраняется без правки |
| `growth/media-image-tls-acceptance.json` | 9 PASS в отдельном временном bridge-контейнере точного media image `sha256:45cdac7e6a058143eda1bab03a21cd82fb73aa94f749096d3af2fca5d918df23` | Доказательство свойств образа; не TLS PASS работающего изолированного worker |
| Переданный inventory от `2026-10-27T22:07:28.119119+00:00` | Четыре службы running/restarts 0, source labels и runtime SHA совпадают с выпущенным source, `certifi=2026.10.23`, HTTPX `0.28.1`, Requests `2.34.2`, CA package `20250419~deb12u2`, overrides отсутствуют | Новые TLS-запросы не выполнялись; maintenance имеет `health=not_configured`, что нельзя называть healthy |
| Media в том же inventory | Единственная internal-сеть, внутренний MinIO без TLS, тот же image ID | Подкрепляет применимость; само по себе не подтверждает готовность выпуска |

`aiohttp` в исходной runtime-матрице не установлен; отсутствие клиента не
превращается в успешную TLS-пробу. Запись о неприменимости относится к текущему
прикладному пути media-worker и должна сохраняться рядом с исходными
неопределёнными результатами и отдельным доказательством образа.

## Поэлементная проверка качества требований

Все восемь пунктов — проверка качества требований, а не выполнения T007/T008.

| Checklist / пункт | Основание | Решение |
| --- | --- | --- |
| security CHK001 | FR-001/002/003 задают advisory minimums, lock/constraints, CI и runtime; документы образов содержат версии | Требование проверяемо, `[x]` сохранён |
| security CHK002 | FR-004/SC-001 и quickstart §5 задают применимых клиентов, оба адреса, обычный контроль, 15 секунд, отсутствие redirects; DNS/timeout явно неопределённы | `[x]` сохранён; ограниченная неприменимость обоснована выше, 9 неопределённых исходов не изменены |
| security CHK003 | FR-003/004/006 запрещают ослабление TLS/trust, раскрытие секретов и содержимого встреч | `[x]` сохранён; изменение сети/CA для обхода проверки недопустимо |
| security CHK004 | FR-005/008/SC-003 связывают выпуск с точным source и честным readback | `[x]` сохранён; общая приёмка пока не дана |
| infra CHK001 | FR-006/008 и quickstart задают владельца, сохранность чужой работы и различие draft/public | `[x]` сохранён; ранний отказ и поздний успех разграничены первичными журналами ниже |
| infra CHK002 | FR-005/007 сохраняют backup authority, restore readiness и остановку execute при их отсутствии | `[x]` сохранён; текущий набор чтения не подтверждает всю исходную authority/restore цепочку |
| infra CHK003 | FR-005/Edge Cases требуют rollback, health/smoke, повторную readiness и отсутствие потери данных | `[x]` сохранён; inventory не заменяет эти доказательства |
| infra CHK004 | FR-008 ограничивает выпуск сервером и сохраняет опубликованные macOS assets/trust | `[x]` сохранён; новый macOS выпуск не входит в эту проверку |

## Остаток перед приёмкой T007/T008

Прочитаны candidate `rc-20261027T201336Z-b6489893dcef`, decision GO,
publication attestation и authoritative Full `40576128669`. Source и
цепочка digest согласованы; authoritative JSON сообщает passed без skipped
gates. Переданный родителем readback GitHub от `2026-10-27T22:06:50.261435+00:00`
сообщает совпадение digest ZIP, один побайтно идентичный authoritative JSON
внутри и разрешение tag в правильный source. Проверяющий не запрашивал GitHub
сам и не считает этот локальный readback независимой живой проверкой.

При дополнительном чтении подготовленного
[итога сверки](validation-runtime-20261028.md) и добавления quickstart
подтверждено следующее:

- `DEV/growth/release-2026.10.27.2-retry-execution.log:2015–2030`
  сохраняет ранний `branch_mismatch` и запись abandoned. Прочитанные ветки
  `scripts/release.sh:72–155` и `infra/scripts/cd-remote.sh:100–145`
  объясняют EXIT-handler и остановку до удалённого CD. Это не утверждение
  об отсутствии прежних GitHub/tag-действий: ранний журнал отдельно содержит
  создание и последующую очистку неопубликованного tag.
- `DEV/growth/release2-temporary-checkout.json` связывает чистую временную
  рабочую копию с `master` и точным выпущенным source; её последующая очистка
  записана отдельно. `release2-temp-clone-dry-run.log` содержит тот же
  decision/evidence, `candidate_gates=passed`, `deploy_result=dry_run`.
- В `release2-temp-clone-deploy.log` строки 1–30 подтверждают принятие того же
  authoritative evidence и `backup_result=pass`; строки 485–508 — публичный
  download/update smoke, повторные Temporal/processing-worker readiness,
  `deploy_result=pass` и совпавшие deployed/runtime SHA. Поиск по журналу также
  подтверждает ранние readiness и `smoke_result=pass` до финальных readiness.
  Неопределённые runtime TLS-исходы этим deploy PASS не заменяются.

Ранний abandoned marker и поздняя публикация теперь имеют подтверждённое
объяснение: разные попытки на том же source/candidate с ранним отказом и
последующим штатным CD. Marker сохранён как история первой попытки, сам
candidate не переписан. Это снимает вопрос хронологии; не подтверждает
отсутствующие исходные authority/restore evidence.

Подготовленный итог и добавление quickstart не ослабляют требований: media
неприменимость ограничена текущим путём, raw `all_pass=false` сохранён,
maintenance не объявлен healthy, T007/T008 и #7734 остаются открытыми.
По проверенной области документального итога замечаний нет. Сведения о живых
GitHub/PR проверках остаются результатом основного исполнителя; проверяющий
сам их не повторял.

Остаются обязательными:

1. Сверить сохранённые исходные разрешения/применимость backup и успешную
   проверку восстановления. `backup_result=pass` этого не доказывает.
   Выпуск не получает общую приёмку до принятого доказательства; если есть
   дополнительные обязательные rollback/no-data-loss критерии, они также
   должны иметь собственное подтверждение. Не создавать новый выпуск только
   ради оформления; отсутствующие доказательства обозначать явно.
2. Сохранить при дальнейших правках исходный `all_pass=false`, отдельные
   27 runtime PASS / 9 inconclusive / 9 image PASS, причину узкой неприменимости
   и отсутствие healthcheck у maintenance.
3. Проверить окончательные доказательства и live-валидатор закрытия issue
   силами основного исполнителя. Новые документальные коммиты/PR требуют своих
   обязательных проверок точного SHA и основы.

На момент этого отчёта **нет заключения PASS для всей T007/T008 или #7734**.
Положительный вывод относится к качеству исходных требований и обоснованию
узкой неприменимости; задача выпуска остаётся до проверки перечисленного.

## Контрольные суммы прочитанных документов

SHA-256 фиксирует байты материалов этого ревью. Относительные пути — от
корня проверяемой рабочей копии. Внешние материалы обозначены логическими
корнями `DEV` (сохранённые release/runtime evidence) и `AUDIT` (результаты
читающей сверки). Журналы повторного CD прочитаны в указанных выше фрагментах,
контрольная сумма идентифицирует весь соответствующий файл.

```text
7a44feda60014151f69ad4a95231bf9762fa9206efba812fa12ab8e3d0d743cc  specs/291-emudhra-security/spec.md
b7d99d4f292dd4af67201e43e2af00e7814c367749495ea65103f29e9f2f3773  specs/291-emudhra-security/plan.md
2a4ca6a84ef4c9fb0d84bce4324271f1c5bed4ab5e41ba84cdadfdc4f1241b44  specs/291-emudhra-security/tasks.md
07e776b3d9506068e04666ede170ac8d3dead408b83be536f4fe36d1c1453b6e  specs/291-emudhra-security/quickstart.md
7d029f484dbb6d92cdb78d89555fbfca7ccc8e93dbac4a0b0531fd3375d31b23  specs/291-emudhra-security/validation-runtime-20261028.md
7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8  .specify/memory/constitution.md
9793de5e158283c2d37bdd2b47f0daf4d312a44fd6ffa37cc22ac47f7a0c3472  docs/agent-guidance/tracker-policy.md
7cd5c1cde2bb51e3842cae9e3717b094fea9f6fbb33fb1a408e6d243f9d68bf3  docs/agent-guidance/github-issue-canon.md
ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f  docs/agent-guidance/release-and-validation.md
d4a2afaab3100e278eb54a74932a565825d3e11288879353454a225b81889354  specs/291-emudhra-security/validation-images-20261027.md
311376c28e7e4ada4428a6087b05976ed3382ecc99e44485b20269d1c26312ad  specs/291-emudhra-security/validation-pr-20261027.md
3e85f97d8c14d34f087315fc70717a36403cc087f116096f90c22722624a6cfa  docs/deployments/2brain-rec/release-v2026.10.27.2.md
610bc756230f2762f20c5a59c6887e2b9496d06a69256a8cbd5b5e6fb83445d6  infra/docker-compose.yml
ab50b798c107f888bf0aa8488a58b12d5029c2d4e720f3eccefef3890eca6b63  apps/server/src/twobrain_rec_server/normalization/worker.py
4af2cffeb4c76782f3a802bd0ba7e2619a885008d10f45ae233f8604bdfa259f  apps/server/src/twobrain_rec_server/normalization/service.py
6a64829a0bc310818d611b79687eda7c742fccc6a03862787ca6e4e23dc1ce90  apps/server/src/twobrain_rec_server/normalization/media.py
cf2d55f28f82412e8e6f4244785081312b513a4f9d6e74b15fa538a8dc852e56  apps/server/src/twobrain_rec_server/storage/minio_client.py
ba30932956e606636fa5fdd99e912b6a9731ee22c1dcf43d615f94cb52c66cfc  apps/server/src/twobrain_rec_server/workflows/temporal_client.py
c823ff63bb34d475b10b203e85b2eb2c64324863b523b64fca6edb13db34b04d  apps/server/src/twobrain_rec_server/observability/logging.py
19e109d65131cce163fb47903d5cd6ad7ed0c4dbe91b5a52e1eaa6bb2b1e0430  DEV/growth/runtime-release2-acceptance.json
e5612775ccc6613f49bc9fc610f20acf34bcccbc066a6438ff3185c16afa65cc  DEV/growth/media-image-tls-acceptance.json
358e20348da20d6b6eb28c85daecdcfc929bf554a58dbb3452f43ba34c0e88bf  DEV/release/candidates/rc-20261027T201336Z-b6489893dcef.json
e63b948c84b66721806bfa5ecf05d8d4ac02ce907a52b1e548964cd651d2bc8e  DEV/release/candidates/.rc-20261027T201336Z-b6489893dcef.json.abandoned.json
30a2cef3c8b16d810a43a2d57f5b312bc1089dbce124730ec6290552de9f9c3f  DEV/release/decisions/rc-20261027T201336Z-b6489893dcef.decision.json
5725a2368befef2d6d942971fdbea1baf47d7e70002496207cfa1cf71422c59b  DEV/release/attestations/rc-20261027T201336Z-b6489893dcef.publication.json
9f444d8d9de797b646e44e9a8a5033365e7f5583ad5158d5e8d90a96318b53ef  DEV/ci-evidence/authoritative-rc-20261027T201336Z-b6489893dcef.json
b57b0f4d0e8adce0cfbbb7161036afbb68df39f1e04e64ff3a56ca18502c1c3a  AUDIT/f291-live-media-inventory-20261028.json
3a51a64f58c5b47cb4113a4d9ebfb5e179caf389351d996900464bca45cbddb8  AUDIT/f291-live-services-inventory-20261028.json
9a5b3008869792600b84ce6c581bc938d9d7ad4190a64d8bf350a1d6b87e131d  AUDIT/f291-github-artifact-readback-20261028.json
5bec1dc9548b4ef6051a71d770457c10db3ddc16a0393e73729e08f1521e618f  scripts/release.sh
6acc5de16454ef17c66f5366e33a1bd318443b20be075a06626a73038b6c2bd8  infra/scripts/cd-remote.sh
9d9a21dbca2db99eb63e83cb67bf843d6e0125f2cffc4b52fed8c6596413a1c1  DEV/growth/release-2026.10.27.2-retry-execution.log
13e940fc800412398cbcbb4af4e4a8eeff5943729344942b5f1cd813ecf13f99  DEV/growth/release2-temp-clone-dry-run.log
ae3f703d101ebdd867f89dda0d982a1568766447691426d2aacab27ca90e539d  DEV/growth/release2-temp-clone-deploy.log
2a09ba98caa5c4501b66a01c753d9a726115bd3f18321eec54c8f2e21dd31f10  DEV/growth/release2-temporary-checkout.json
```

После записи reviewer notes оба чеклиста полностью перечитаны: security
**4 checked / 0 unchecked**, infra **4 checked / 0 unchecked**, всего **8/0**.
Старые отметки сохранены; новый пункт о выполнении выпуска не добавлялся.
