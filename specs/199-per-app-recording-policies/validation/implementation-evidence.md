# Evidence: Feature 199

Дата проверки: 2026-08-24

## Проверки

- `swift test --package-path apps/macos --disable-swift-testing --filter 'MeetingDetectionPolicyTests|MeetingDetectionCountdownTests|CaptureControlTests'` — 90 тестов, 0 ошибок.
- `swift test --package-path apps/macos --disable-swift-testing --filter AppControlAccessibilityTests` — 22 теста, 0 ошибок.
- Объединённый focused/accessibility filter — 112 тестов, 0 ошибок.
- `swift run --package-path apps/macos ContractValidation` — `ContractValidation: PASS`.
- `GRAF_DEV_ORIGIN=http://127.0.0.1:8081 apps/macos/Scripts/build-dev-app.sh` — отдельный подписанный `GRAF Dev.app` собран.
- `codesign --verify --deep --strict apps/macos/.build/dev/GRAF Dev.app` — подпись проверена; `CFBundleIdentifier=pro.2brain.graf.dev`.

## Проверенный контракт

- Новые target IDs получают `ask`; legacy target selection мигрирует в `ask`.
- `always`, `ask`, `never` проходят policy resolution с сохранением capture gates.
- Таймер остаётся 8 секунд и по истечении вызывает только текущий `promptTimeout` start; checkbox не сохраняется.
- Явные Start/Skip с checkbox сохраняют `always`/`never`; без checkbox правило не меняется.
- Настройки используют radio-карточки, mixed state `Разные`, короткие технические labels и hints; bundle ID в UI отсутствует.
- Индикатор записи и однокнопочная остановка покрыты существующими capture tests.

## Граница evidence

Использованы synthetic/metadata-only проверки. Реальная встреча, аудио,
транскрипты и production app не запускались и не изменялись. Full CI, commit,
push, release и production deploy не выполнялись.
