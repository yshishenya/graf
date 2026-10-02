# Quickstart — F285

## Локальные проверки

1. Native regression: `cd apps/macos && swift test --filter AppControlAccessibilityTests` и `swift test --filter NativeSettingsComboBoxTests`; `swift test --filter DesktopNotificationAccessibilityTests`.
2. Browser: существующая установка Playwright в `apps/server/tests/browser`, `node apps/server/tests/browser/focus-indicators.test.cjs`, `GRAF_BROWSER=webkit node apps/server/tests/browser/focus-indicators.test.cjs`, `node apps/server/tests/browser/meeting-delete-focus.test.cjs`, `node apps/server/tests/browser/local-recording-focus.test.cjs`. При другом NODE_PATH использовать уже установленную библиотеку; новый test обязан пройти Chromium и WebKit.
3. `python3 scripts/check_spec_kit_governance.py`; `git diff --check`. Отсутствующий/пустой/skipped обязательный результат не считается PASS.

## Единственный GRAF Dev

После одобренного коммита: `infra/scripts/dev-harness.sh status --json`, штатный build → promote → status → smoke по infra/dev/README.md. Не обходить dirty/SHA/signing guards. Проверить manifest/SHA.

- Мышь: начать короткую явно разрешённую тестовую запись без частного содержимого, остановить; нет синей рамки. Кнопка нового старта доступна, остановка не запускает новую запись.
- Tab/Shift+Tab: нет остановок на capture/custody informational containers; доступные кнопки выделяются при системной навигации macOS. Не менять системную настройку автоматически; если текущая настройка ограничивает Tab, зафиксировать лимит и использовать существующий автоматический AppKit check.
- Поиск/имя/часовой пояс/code/textarea/редактор названия: один контур, прежние размеры; light/dark, high contrast/forced-colors на синтетических browser fixtures.
- NativeSettingsComboBox: мышь и Tab, один 2px контур внутри bounds; обе темы и Increase Contrast; стрелки/Return/Escape и редактирование сохраняются, popup не открывается от focus.
- Notification → recording: панель раскрывается и прокручивается к цели; VoiceOver target сохраняется. Не создавать реальное уведомление/запись чужой встречи.
- Dialog: Tab trap и Escape restoration; disabled actions остаются disabled.

## PR и прод

Три обязательных checks на точном PR SHA через scripts/validate-pr-checks.py. Затем frozen release candidate, один authoritative release-full, CD dry-run/execute и metadata-only smoke. Public macOS: Developer ID, notarization/stapling/Gatekeeper, Sparkle previous/new validation, публичные ZIP/PKG/appcast bytes. Установленная версия отделяется от публикации. Данные тестов и screenshots с частным содержимым не сохраняются.

На macOS WebKit полная навигация по действиям проверяется Option+Tab, обычный Tab следует системной настройке; это не пропуск keyboard proof. Перед чтением computed styles тест ждёт окончания существующих transition.
