# Доказательства выпуска F286 — v2026.10.06.1

Полоса: high-risk-feature; выпуск/развертывание. Этот отчет и нормализация ссылок задач используют docs-only / mechanical: работа приложения не меняется.

## Текущий результат

Реализация развернута в production на `https://rec.2brain.pro`. Полное включение функции и публикация выпуска **не завершены**. Защита nginx установлена и проверена. Общие ссылки возвращены в выключенное состояние после отказа общей очистки; готовится исправление T021 и новый кандидат. T018 остается открытой; дочерние задачи и umbrella не закрывались.

Пользователь разрешил реализацию, коммиты после проверки и production выпуск. Первоначальное препятствие sudo устранено интерактивной авторизацией, предоставленной пользователем; секрет не сохранен. Обход прав не выполнялся. Настроенный KVN использован как промежуточный SSH-сервер; временный маршрут восстановлен с проверкой контрольной суммы исходной конфигурации после завершенного CD.

## Точная версия и проверки

- Production source и runtime SHA: `de255e0d7f72ed5123f9f0ffffe34f586723cba6`.
- Candidate: `rc-20261006T005745Z-ad663a04a781`.
- Train: `train-20261006T005646Z-de255e0d7f72`.
- Authoritative release-full: PASS, https://github.com/yshishenya/graf/actions/runs/37396717004 . requested/observed SHA должны совпадать с source; receipt status `passed`. Все восемь серверных частей, strict PostgreSQL/performance, static/governance, macOS и aggregate прошли. Полный прогон не повторялся на этом кандидате.
- PR #7565: source `30ca64ec7319ce66aca675b9a23b6c6736edcfe1`, merge `6502bcf6b5cc379cab745a5c4edc13d8a0374084`.
- PR #7569: source `47ea28967f9cca89f793b50cef8371ee36f3a381`, merge `889eb6bd3505957cf7f82e21091cb48df47464f9`.
- PR #7571: source `a0d27e5f5a939d845cb1606dc1d639de4a366ad3`, merge `21145f865911f66e27d4672b8ca8d52ff6ea52e7`.
- Latest preparation PR #7572: source `d6138f1ce07adcb2c5fc9785406af6c62a760e7c`, merge = production source. Canonical current-check validator PASS: governance-fast37396504186, macos-pr37396504147, pr-metadata37396504137; checked base `21145f865911f66e27d4672b8ca8d52ff6ea52e7`.
- Предыдущие кандидаты `rc-20261005T235931Z-f3b87b44222a` и `rc-20261006T003217Z-ec639d836515` FAILED и оставлены без выпуска. Их результаты не использованы для допуска нового кандидата.

## Развертывание

Штатный driver остановился после deploy с кодом 0. CD dry-run PASS и CD execute `deploy_result=pass`; deployed/runtime SHA совпадают с точной версией. Длительность remote deploy221с, driver deploy230с. Резервная копия создана `20261006T010805Z`, `backup_result=pass`.

Проверены migration head0104, RLS и реальные роли API/maintenance/media, конфигурация секретов, Temporal/processing/media readiness, синтетическая загрузка/обработка и cleanup. `smoke_result=pass`, `readiness_verdict=infra_smoke_ready`. После smoke снова проверены Temporal и processing. Публичные `/api/v1/health/live` и `/api/v1/health/ready` отвечают HTTP200 (`ok`/`ready`). Это не подтверждение отдельной служебной работы automatic_retry/backfill_inventory/range_playback/normalization_cleanup: CD сохранил их `required_post_deploy`.

После terminal CD `release-images.py current-override` успешно подтвердил завершенный закрепленный runtime. Публичный `summary-sharing.js` совпадает с байтами candidate, SHA256 `1b16ae27e8c617491c1a7b7221015e400589ea4ebfd2c5b00e31289ddb2bb7e4`.

Runtime: public links=false, abuse gate=false, external invitations=true; ключ хеширования установлен (длина проверена без вывода), почтовая конфигурация включена. Реальные письма участникам не отправлялись.

## Сохранение приложения macOS

Все98 публичных ZIP/установщик/appcast совпадают с сохраненной до развертывания картой SHA256. Контрольные суммы:

- graf.pkg: `b5df859986d0ad36a07302c87c598b7a7d6e027a65e4024dd70fe0cba3338662`.
- graf-appcast.xml: `a41579d1b65a44ec2a6e33a4efb33aa1841f8ea4d1d5d44445f3ef8138d7711a`.
- GRAF-2026.10.04.6.zip: `df9817ab93757e0bbed0fcb6ad3841a6c2cf18947445fce263b3d2cd375b2836`.

GRAF Dev47ea штатно build/promote/smoke PASS. Фактическое окно и reader повторно проверены на47ea. Runtime/native diff между этим Dev и release исходниками пуст; это не утверждение, что установленное приложение имеет SHAde255. Предыдущая actual проверка320/390, тем, клавиатуры и no-JS привязана к30ca; подробности и ограничение реальной доставки — в validation.md.

## Оставшееся включение ссылок

Установщик `infra/scripts/install-summary-share-edge.sh` требует root только для execute, сохраняет nginx, отклоняет посторонний drift, проверяет конфигурацию/reload/headers/health и откатывает при ошибке. Текущий site соответствует исходному конфигу за вычетом двух новых owned locations.

Операционная процедура независимо проверена: HIGH/MEDIUM0. Исправлен порядок SHA/lock: flock захватывается до проверки точного HEAD/чистоты. Локальные и размещенные на сервере файлы совпадают:

- activate: `fe66b25e4ed907ff30780039aedf819b855a41d2426732a8276acf2fd4442c97`.
- edge proof: `07f21e752b68392ab18acb1f082020219b643d9db3ad532be467a49078ce3e21`.
- sharing smoke: `6b3c8142b37ec30322f80a401d4a18a4c43800e8ce89cc298357cd679897db78`.

После административной установки должны быть доказаны HTTP/HTTPS защитные заголовки, global limiter429 и отсутствие синтетического URI в nginx logs. Только затем меняются три share-флага и пересоздаются те же закрепленные API/processing/maintenance образы. Подготовлены CAS возврат трех флагов, фиксация точного SHA под общим lock и синтетический summary-only HTTPS create/read/revoke404 с обязательной очисткой; реальная почта/доступ к записи не создаются. Source review PASS не заменяет фактический запуск.

## Публикация и задачи

Неопубликованные tag и draft `v2026.10.06.1` удалены штатной очисткой выпуска, кандидат помечен abandoned. Production исходники остаются de255 до нового проверенного CD. Человеческие русские заметки подготовлены. Штатный publish resume выполняется после activation PASS. До этого выпуск нельзя назвать готовым для пользователей ссылок.

Canonical mapping21 задач:20[X], T018[ ], все21 `(Issue #N)` распознаются; T021 связана с7573. В текущем body PR7565 есть отдельные Refs для7547–7564 и7566. Дочерние issues закрываются только после заполненного фактического evidence, live canonical validator и комментария; umbrella7546 — последней. Пока активация и публикация не завершены, T018/общая приемка открыты.

## Ограничения

Реальное получение писем во входящие, AUTO с живым Google Calendar и измеренный вирусный рост не подтверждены синтетической проверкой. По умолчанию ASK включен, AUTO выключен. Неизвестная доставка не повторяется автоматически. Частные данные, адреса, capability tokens и секреты в этот отчет не включены.

## Фактическая попытка включения 6 октября

После предоставленного пользователем административного доступа штатный установщик nginx PASS; конфигурация/reload, error headers, global429 и synthetic URI logs absent подтверждены. Первая попытка обнаружила отсутствие явного источника Compose interpolation в операционной процедуре; flags были возвращены. Добавлен только --env-file .env, независимо проверено HIGH/MEDIUM0; новая сумма activate7b2f1c62f25f579c2d247cd9c7dd184ed3ee101e539ea919bea5451e94a7708f.

Вторая попытка: три постоянные службы sharing config PASS; synthetic sharing setup/prove/cleanup PASS, mail none, residue none. Общая повторная загрузка/обработка обнаружила FK отказ удаления track_artifacts до storage_reservations. Runtime flags автоматически восстановлены; activation FAIL и Release остается draft. T021/#7573 добавлена для корневого исправления общего cleanup helper, PostgreSQL regression, нового полного кандидата и повторного production cleanup. Это не отказ функции чтения ссылок и не основание обходить cleanup.
