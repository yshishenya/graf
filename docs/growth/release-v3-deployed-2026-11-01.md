# Серверный выпуск v2026.11.01.3 — рабочая проверка

Дата: 01.11.2026. Полоса этой записи — docs-only; выпуск — release-deploy.

- [x] Принять независимое ревью подготовки: P1/P2=0. Архив F179, прошлые ограничения F140, Unreleased и история CHANGELOG сохранены.
- [x] Принять PR #7889 на source `ccf10c47e6dea6a2c4829b01b60bef58d17fcd65`, base `3bf154995bae65093bbcdc050aa7e2fc5a2a3357`: governance41330510636/native41330510673/metadata41330510633 SUCCESS; common validator до/после PASS.
- [x] Защищённо слить подготовку17:20:13UTC в `e447407328f63ab7102e18718b0be9f3a487f526`; совпадение деревьев и единственный parent проверены. Чистая master совпадает с origin/master.
- [x] Проверить один draft ID430734941 с честными pending notes, точным target/body и без assets.
- [x] Закрепить состав4PR #7884/#7887/#7888/#7889,2фичи F140/F179: `train-20261101T172057Z-e447407328f6`, кандидат `rc-20261101T172141Z-0ae30a988bc8`.
- [x] Принять единственный [Full41331078229](https://github.com/yshishenya/graf/actions/runs/41331078229):13jobs SUCCESS, все компоненты и aggregate PASS. Driver97497EXIT0; CI664с, весь путь до dry-run729с. Повторного Full нет.
- [x] Принять решение go и предварительный прогон. Документированный прямой CD2536EXIT0: `deploy_result=pass`,230с; резервная копия, migration/RLS, smoke/cleanup и итоговая готовность служб PASS. Обходов проверок нет. `--stop-after` не применялся из-за известной ошибки разбора аргумента.
- [x] Сверить source/deployed/runtime/image label: `e447407328f63ab7102e18718b0be9f3a487f526`, API healthy.
- [x] Прочитать все17sitemapURL:200/одинH1/title/canonical; неизвестный404, live=ok/ready=ready. Вход/регистрация200, один consent loader, необязательная отправка выключена.
- [x] Проверить гостевой Word39652байта, SHA256 `db3382c12973eaa95a4c1737094386c77a6c5877faf0e630cad914a5c4906692`, обратная ссылка200.
- [x] Сверить рабочие CSS/JS с исходниками побайтово. CSS SHA256 `da6cddf1a7a4c938b87b4be17b7c0e9301d2c7bcfb52a5a4a99e6c4493b6c2d7`; JS `db64e4dcd20068c0d45e15b141d87e593f76f6eb55e395ce3ec5ed312922e7b4`.
- [x] В отдельном браузере проверить3рабочих режима320px:обычный/удвоенный текст/безJS. Document/body=320,3панелиDIV, no-JSnavBottom376<H1top557. Три публичных снимка просмотрены. Все контексты и собственный сеанс закрыты.
- [x] Подтвердить сохранность pkg SHA256 `b5df859986d0ad36a07302c87c598b7a7d6e027a65e4024dd70fe0cba3338662` и appcast `a41579d1b65a44ec2a6e33a4efb33aa1841f8ea4d1d5d44445f3ef8138d7711a`.
- [x] Принять независимое финальное чтение заметок (P1/P2=0), заменить pending body и опубликовать [Release](https://github.com/yshishenya/graf/releases/tag/v2026.11.01.3)17:41:56UTC. Publication57130EXIT0; точные body/ID430734941/assets/target/tag/attestation PASS. [Независимое ревью](release-v3-final-notes-independent-review-2026-11-01.md).
- [x] Явно освободить окно слияний соседней задаче после подтверждённой публикации; сообщение отправлено. PR7890 в этот выпуск не включался.

## Ограничения и следующий приоритет

Новых миграций/служб/зависимостей/macOS/nginx/рабочих флагов нет. F179/T041 и13прежних переполнений других страниц остаются открытыми. F140/T077/#4932 неполна; прежние FR-105/T048/T068/#7524 ограничения сохранены. Соседний PR7890 в выпуск не входит.

Catalog enabled=false, validation_mode/provider_mode disabled, rollout blocked. Рабочее измерение/T0, реальные внешние визиты, регистрации и оплаты не приняты. Служебные запросы и smoke из коммерческой когорты исключены. Outcome proof в deployment smoke skipped; эта выкладка не доказывает клиентскую обработку или пользу результата. Automatic retry/backfill inventory/range playback/normalization cleanup в итоговом CD отдельно обозначены required_post_deploy, не PASS.

После CD доступно281640443904байта из1880373706752 (14,98%, ниже20%). Это снимок df, не полная оценка ёмкости восстановления; ничего не удалялось. Привилегированная опись и весь F273/T113 остаются HOLD. Следующий приоритет — существующее измерение/фиксированный T0, затем ровно три разрешённых сообщения Product Radar. Недоступные свежие кабинеты не заменяются нулями.

Первичные metadata-only результаты сохранены в ignored `.dev/release/` оператора: `v3-driver-train.log`, `v3-full-final.json`, `v3-merged-checks.json`, `v3-dry-run.log`, `v3-deploy.log`, `v3-runtime-readback.txt`, `v3-live-public-20261101.json`, `v3-assets-readback.json`, `v3-live-browser.txt`. Секреты, содержимое встреч и рабочие данные сюда не копируются. История прежних выпусков/ошибок сохранена.
