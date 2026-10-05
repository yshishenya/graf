# Помощь: слышна одна сторона записи

## Scope и уникальность

База master: `df9c8f4ee4b538cba6c42e1fad6007595e22774a`, повторно проверена через git ls-remote перед коммитом. Чистый отдельный worktree; основная рабочая копия не изменялась. Список всех семи открытых PR прочитан через GitHub connector и gh API: нового материала об одной стороне нет. PR7433 — закрытие меню; 7400 — другие поисковые страницы; опубликованные три guides/учебный протокол — отдельные задачи. На master Help — только enum и отрицательные HTTP404 tests. Минимальный scope объявлен до реализации: список одной статьи и fixed route, без CMS/поиска/deploy.

Lane: tiny-low-risk editorial content within F281. Тексты о диагностике не меняют диагностический сбор или capture/permissions/auth/storage код. Трекер #7544, T014/T015; deployment и старые T011/T013 этим PR не закрываются.

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

T014 implementation/local verification завершена. T015: draft PR и exact-SHA required CI проверяются после push; здесь не заявлен успех еще не запущенного CI. Источником текущего статуса будет PR и общий `scripts/validate-pr-checks.py`. Merge/release/deploy/публикация исключены; native recording compatibility не проверялась.
