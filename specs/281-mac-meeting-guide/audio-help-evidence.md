# Помощь: слышна одна сторона записи

## Scope и уникальность

База master: `df9c8f4ee4b538cba6c42e1fad6007595e22774a`, повторно проверена через git ls-remote перед коммитом. Чистый отдельный worktree; основная рабочая копия не изменялась. Список всех семи открытых PR прочитан через GitHub connector и gh API: нового материала об одной стороне нет. PR7433 — закрытие меню; 7400 — другие поисковые страницы; опубликованные три guides/учебный протокол — отдельные задачи. На master Help — только enum и отрицательные HTTP404 tests. Минимальный scope объявлен до реализации: список одной статьи и fixed route, без CMS/поиска/deploy.

Lane: tiny-low-risk editorial content within F281. Тексты о диагностике не меняют диагностический сбор или capture/permissions/auth/storage код. Трекер #7544, T014/T015; отдельно разрешенная публикация — T016. Старые T011/T013 этим PR не закрываются.

## Источники утверждений

- `apps/macos/Shared/Sources/Models/SystemAudioCaptureCoreModels.swift`, SystemAudioStatusLabels: «Источник»/«Системный звук», «Уровни записи», «Микрофон»/«Встреча», Mute/«Включить микрофон», summary сигналов, отсутствие гарантии meeting-app mute.
- `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift`: выбор микрофона и «По умолчанию macOS», статусы входа.
- `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`: выбранный inputDeviceId, default input и исключения недоступного входа. Это не выбор выхода приложения звонка.
- `apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift`: два шага прав, имя текущего канала GRAF/GRAF Dev, «Открыть настройки», «Проверить еще раз», restart; restricted→администратор.
- `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`: CGPreflightScreenCaptureAccess/CGRequestScreenCaptureAccess и consent-gated ScreenCaptureKit probe; stream capturesAudio=true, screen+audio outputs, audio-only callback handling, excludesCurrentProcessAudio=true. Поэтому отдельное macOS audio-only permission не объявляется достаточным. Системный screen output не означает сохранение видео.
- `apps/macos/Installer/Scripts/build-local-installer.sh`: minimum macOS14.5. На новых ОС не заявлена прошедшая installed-app приемка.
- Apple, прочитано 2026-10-05: [Sonoma14](https://support.apple.com/ru-ru/guide/mac-help/mchld6aa7d23/14.0/mac/14.0), [Sequoia15](https://support.apple.com/ru-ru/guide/mac-help/mchld6aa7d23/15.0/mac/15.0), [Tahoe26](https://support.apple.com/ru-ru/guide/mac-help/mchld6aa7d23/26/mac/26), [микрофон](https://support.apple.com/ru-ru/guide/mac-help/mchla1b1e1fe/mac). Версионные страницы называют «Запись экрана и системного звука», разрешают screen+audio или audio-only; GRAF-specific требование сверено отдельно с кодом.

Результат проверки звука не выдуман: инструкция предлагает читателю согласованный тест, но исполнитель задачи не записывал экран/микрофон и не менял разрешений. Уровни/права/успешное сохранение/наличие речи/расшифровка различены. Отсутствующая в файле речь не объявляется восстановимой.

## Локальные проверки

- Штатный `apps/server/scripts/run_local_postgres_tests.sh --focused` по девяти public-help/guides/navigation/copy/landing files: **117 passed**, 20.65s pytest; `postgres_test_result=pass`, `postgres_test_cleanup=isolated_container_removed`. Единственное предупреждение pytest об уже импортированном fixture module.
- Реальные Chromium HTML+local CSS/font: Help hub/article и общая навигация guide/hub на3203907681440; Help body text200%, остальные страницы header200%, overflow0, одинH1, skip link/Enter, noJS PASS. Test обнаруживается pytest (browser marker), отсутствие Node/Playwright — FAIL, не skip. Вся внешняя сеть blocked, картинки — только локальные assets.
- Снимки новых страниц безопасны, просмотрены 390px; находятся в ignored `output/playwright`, не закоммичены. Никаких личных экранов/звонков/данных.
- Дополнительное расширение проверки всего старого `/guides` до200% текста на320px выявило переполнение. Оно воспроизводится без Help-ссылки (~472px scrollWidth), body/CSS hub побайтово прежние. Исправление старых карточек не входит в узкий article scope; этот результат не объявляется PASS.
- Ruff по измененным Python files, `validate-agent-context.py`, `check-development-process.py`, `validate-changelog-fragments.py`, `git diff --check`: PASS.
- Protected diff: landing/download/privacy/cookies/terms/offer/analytics-consent templates, все public static assets и analytics.py без изменений. Billing/Windows/analytics source не меняются. PUBLIC_CONTENT_SURFACES и PUBLIC_ANALYTICS_SURFACES Help не включают; новые routes не вызывают DB/record helper и не ставят attribution cookie. Старые measured guides проходят прежние PostgreSQL tests.

## Онлайн gate

T014 implementation/local verification и исходная T015 завершены. PR7545, исходный head `6fe34ead257b8c10fecde4605c5ca7f4af17a4b6`: governance-fast37364831663 attempt2, macos-pr37364831594 attempt2, pr-metadata37364833578 attempt1 SUCCESS; общий validator exit0. Первые metadata-попытки двух workflows не получили hosted runner во время официального инцидента Actions; после подтвержденного восстановления выполнен один полный retry каждого существующего workflow, без повторения успешной metadata. CI доказал исходный код и метаданные, не функциональную запись на Mac.

## Свежая база и граница владельцев выпуска

2026-10-06 владелец явно разрешил публикацию и обязательную штатную свежую копию GRAF для Help, без нового хранилища/резервного PostHog. Master обновлен до `de255e0d7f72ed5123f9f0ffffe34f586723cba6`; чистая собственная ветка Help перенесена на эту базу без изменений чужих файлов. Старый source SHA/CI нельзя выдавать за текущий proof обновленной ветки.

Первоначальная read-only проверка: production checkout и SHA-метка работающего rec-api совпали с de255e0d; контейнер был недавно перезапущен и healthy. v2026.10.06.1 был draft, release-full37396717004 SUCCESS относится только к F286/de255e0d. Последний опубликованный тогда stable — v2026.10.04.6/source02c79e14. Диапазон до master:94файла,+10479/−1205, включая sharing/AUTO, nginx/compose и миграции0102–0104. Это не означает, что весь F286 не был развернут: последующая точная сверка нашла terminal CD result deployed, все четыре прикладных сервиса de255 и migration0104. Блокером оказался post-CD activation smoke cleanup FK; исправление и его выпуск оставлены другому оператору.

Focused на базе de255e0d: **120 passed**,23.28s pytest; isolated PostgreSQL cleanup PASS. Реальный Chromium снова проверил Help320/390/768/1440,text200%,keyboard/noJS и общую навигацию. Ruff,node syntax,agent-context,development-process,changelog-fragments,git diff --check PASS. Protected diff относительно новой базы пуст; Help runtime/browser implementation побайтово совпал с исходным6fe34ead. Diff именно F286 от прежней базыdf9c8f4e:90файлов,+10406/−1201.

Новый exact-SHA proof проверяется после push; прежний PASS не объявляется доказательством нового head. T016/production200/canonical/sitemap/navigation/mobile еще не закрыты. Native recording compatibility не проверялась; прежнее переполнение guides остается отдельным замечанием.

## Подтвержденный опубликованный baseline

После read-only наблюдения чужого Full/CD: v2026.10.06.1 опубликован 2026-10-06T20:48:54Z. Annotated tag04c7be34bfa631491ac90012e23cefd2341b402f разрешается в29264c66520ee36b1a2f287fa7edd6e92139dd9f. Full37527256994 SUCCESS, candidate rc-20261006T203243Z-ab47b37ce582; terminal CD attempt f9d6600102e14cd1b08561828f9d6d48 result deployed. Media worker healthy на29264c66, общие ссылки включены у API/processing/maintenance, точная проверка inode deploy lock показывает отсутствие держателей. Публичные live/ready200 с ok/ready. Чужие функции/миграции теперь входят в опубликованную базу; собственной выкладки и записи людей во время наблюдения не было.

Собственная Help ветка перенесена на29264c66. Старый локальный тег отмененного de255-кандидата удален только в изолированной копии; получен новый опубликованный tag, remote теги не менялись. Новый PR proof и отдельный Full/CD еще обязательны. Копия приложения macOS, billing, Windows, analytics и protected public files не входят в Help diff.

Focused на опубликованной базе29264c66:120 passed,22.45s pytest; runner focused27s, isolated_container_removed. Chromium Help320/390/768/1440,text200%,keyboard/noJS PASS. Agent-context/development-process/changelog-fragments/node syntax/git diff --check PASS. Protected diff пуст; Help runtime/browser/test files побайтово равны проверенному72d2ef9f. Эти результаты не заменяют новый exact-SHA PR proof или будущий Full/CD.

## Завершенная публикация Help — 2026-10-06

По прямому разрешению владельца выполнены исправление блокера проверки F211,
merge, один frozen Full, штатный CD и публикация. Risk lane исправления:
active Spec Kit slice F211 / high-risk CI-governance; выпуска: release-deploy.
Настоящий source важнее прежних промежуточных evidence выше.

- [PR7545](https://github.com/yshishenya/graf/pull/7545): head
  `4227b699ca8d2dd5d3333b7725fee554976cdac9`; source governance37529781951,
  macos37529782085, metadata37531270850 SUCCESS. Common exact-SHA validator PASS.
- Train `train-20261006T215826Z-ad597c114e3b` содержит каждый PR:
  #7545/#7576/#7577/#7579/#7580, с отдельными live proofs. Предыдущая стабильная
  база — опубликованный v2026.10.06.1 /29264c66; F286 уже завершен.
- Candidate `rc-20261006T220142Z-95a12ddbc931`, source
  `ad597c114e3bf9e627525c578ec68e353d54a44e`.
  [Full37537979359](https://github.com/yshishenya/graf/actions/runs/37537979359)
  SUCCESS; receipt authoritative/passed, requested/observed start/end и все
  component SHA совпадают, skipped gates пусты. Train и decision go.
- CD dry-run/execute PASS; attempt `599561ecaa474082b65ce28cfe345373`,
  `infra_smoke_ready`, backup `/opt/projects/2brain-rec/backups/20261006T221459Z`.
  Откат не потребовался. Штатная проверка восстановления предыдущего backup
  в отдельные временные DB/bucket PASS, удаление обеих целей подтверждено.
- [v2026.10.07.1](https://github.com/yshishenya/graf/releases/tag/v2026.10.07.1)
  опубликован 22:25:10Z, не draft/prerelease. Annotated tag
  `9bb87922f27cf607328a2d2d66a014ae056572eb` разрешается в source выше;
  immutable publication attestation `pa-rc-20261006T220142Z-95a12ddbc931`
  создана 22:25:18Z. Frozen checkout не менялся при последующем docs closeout.

Живые `/help`, статья одной стороны и все guides HTTP200, один H1, правильные
canonical; sitemap содержит каждый URL один раз, навигация доступна. Полученный
production HTML и совпадающие с source CSS/шрифты/изображение проверены Chromium:
320/390/768/1440, Help текст100%/200%, общие заголовки guides200%, клавиатура и
без JavaScript PASS. Скриншоты — только безопасные публичные страницы.
Прежнее замечание о полном тексте старого guide при320/200% этим не закрывается.

Protected: семь исходных шаблонов главной/download/политик, их helpers,
обработчики, аналитика и статика побайтово совпадают с29264c66. SHA15 файлов
в работающем API совпадают с проверенным source. Два одинаковых HTTP запроса
дают одинаковое стабильное содержимое после выделения только документированных
per-render `graf_attribution_id` с его копиями в handoff и `bridge_expires_at`.
Изначальная попытка сравнить весь HTML с прежним SHA закономерно не прошла:
эти поля случайны/зависят от времени. Raw HTML before/after равенство не заявляется;
никакие тексты, цены, настройки consent или иные поля из сравнения не исключены.

Набор175 обычных нескрытых файлов zip/pkg/appcast сохранил точную SHA map:
`0e909ffade44b7ee0c0d40a3fa912b37f4c5087005f63103a3e7e59c1617af6b`.
Действующие graf.pkg/appcast/GRAF-2026.10.04.6.zip не изменены. Все482 исходных
root filenames/sizes совпадают; mtime совпадает в числовой точности исходного
JSON, точное равенство nanoseconds не заявляется. Сравнение рекурсивного after
с root-only before не используется как проверка изменений. Это инвентаризация,
а не утверждение о публичности или подписи каждого исторического файла.

API/processing/maintenance/media работают на sourcead597c11, необходимые
healthchecks healthy; maintenance running без отдельного healthcheck. F286
share_public_links_enabled, share_public_links_abuse_gate_approved,
share_external_invitations_enabled и email_login_delivery_enabled true.
Публичные live/ready200 ok/ready, deploy lock освобожден. Реальные письма,
личный экран/аудио и новые разрешения не использовались. Совместимость записи
в установленном GRAF с каждой macOS/meeting-app не проверялась.

Локальные metadata records сохранены в task `ci-evidence`: authoritative Full,
train-go/decision/publication, release/CD/restore logs, live-readback,
browser/screenshots, runtime/source hashes и before/after SHA maps. Секреты,
частные аудио и содержимое резервных копий в документы не добавлены.
