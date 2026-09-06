# F255: промежуточная приёмка реализации

Статус: **не готово к выпуску**. Дата: 2026-09-06. Docs SHA `c6bbcf3765ff7a23221ced2aca64dd809dc420f8`; на момент первоначальной проверки исходники не были закоммичены. Последующий коммит, штатная Dev-сборка и исправления CI описаны в `dev-preparation.md`. Эти результаты не являются exact-SHA CI/Dev/release evidence. Точные хеши проверенных исходников записаны в `source-digests.json`.

## Автоматические проверки

- 170 Swift tests: `swift test --package-path apps/macos --filter 'DesktopCabinet|EmbeddedCabinet|DesktopMeetingShellWebViewBoundary|DesktopUploadQueueV5'`. Включает реальную SwiftUI/WebKit-компоновку, версии/размеры/типы сообщений, маршруты/origin/main frame, старое поколение/сессию, HTML fallback, тему с успешным POST/303 и ошибкой 503, стабильность документа при resize/collapse/theme и teardown окна.
- 146 pytest: navigation model, cabinet web shell, cabinet audit fixes, settings UI contract, shell response contract. Одна существующая `PytestAssertRewriteWarning`.
- `node --check cabinet.js`, `git diff --check`: успешно.
- `check_spec_kit_governance.py`: успешно после удаления только сгенерированного ignored `__pycache__` issue-canon. Исходники расширения/lock не менялись. Для повторных Python-проверок использовать `PYTHONDONTWRITEBYTECODE=1`.
- Первоначальные новые проверки были красными: отсутствующий bridge, старые обязательные заглушки. Runtime-тест дополнительно обнаружил и проверил исправление SwiftUI teardown.

## Реальный браузер с синтетическим сервером

Chromium через Playwright CLI, производственные Jinja/CSS/JS, локальный fixture server. Проверки не доказывают реальный auth/payment/provider flow.

| Проверка | Результат |
|---|---|
| Web и embedded HTML, light/dark, 320/390/768/1024/1440 | 20 комбинаций: document.scrollWidth не больше viewport, HTML fallback остаётся видимым |
| Профиль на пяти ширинах | Меню внутри viewport, 0 disabled; Escape возвращает фокус кнопке профиля |
| CSS zoom 200%, 1040×680: account/overview/billing/detail/shared | 5 страниц: горизонтального переполнения нет. Это не полная проверка каждого контрола и не native pageZoom |
| JavaScript выключен, 390px | Основные ссылки и содержимое доступны. Прежний вход к настройкам сохранён; native-команды без JS не заявляются |
| Native новый/новый | Runtime-тест согласовывает меню и скрывает HTML; старое поколение не очищает новое, invalidate возвращает HTML |
| Новый native / настоящий старый server | Ещё открыто; обработка отсутствующего JS API реализована, полноценная смешанная пара не запускалась |

Синтетические изображения сохранены в артефакте задачи `graf-interface-implementation/`. Диагностические снимки GRAF Local не использовать как приёмку GRAF Dev; точное различие описано в native-prototype.md.

## Пользовательские изменения

Основные разделы остаются доступны из настроек: переход к общим встречам сокращён с двух действий до одного. Из профиля убраны неработающие варианты. Выбор темы больше не переводит со встречи в аккаунт; при неподтверждённом сохранении есть откат и сообщение. Нового выбора материала нет.

## Обязательные открытые строки

- GRAF Dev: чистый выбранный SHA, build/promote/status/smoke, единый manifest и фактический app presentation.
- macOS 26 с разрешённой прозрачностью; macOS 14.5; обе темы/system, Reduce Transparency/Motion, Increase Contrast, активность окна, измеренный контраст, VoiceOver и порядок фокуса.
- Запись/Stop одним действием при двух панелях и 200%; реальная сессия записи, разрешения, local mode и повтор отправки. Исходники capture не изменены, но это не замена runtime проверки.
- Реальный вход/выход/смена сессии, WebContent termination и смешанные версии; старые сообщения покрыты изолированным runtime-тестом.
- Admin/public полная визуальная матрица и сохранение профиля сервером с реальной БД. Синтетический POST подтверждает клиентский путь, не сохранение в БД.
- F245–F253: повторно проверены PR #6611/#6615/#6613/#6626/#6707/#6660/#6692/#6710/#6706 — все OPEN, mergedAt=null. Совместная приёмка будущих объединённых SHA открыта.
- PR/governance-fast на точном SHA, release candidate, Full CI, CD dry-run и macOS distribution gates не запускались.
