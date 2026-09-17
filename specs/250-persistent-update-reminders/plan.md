# Implementation Plan: Постоянное напоминание об обновлении

**Branch**: `250-persistent-update-reminders` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

## Summary

Сохранить Sparkle единственным механизмом обнаружения/установки; дополнить существующее представление небольшим кэшем известного предложения. Показать нативное сообщение над главным окном и в существующем меню календаря; сохранить узкий веб-мост.

## Technical Context

- Language/Version: Swift 6, SwiftUI, AppKit, Foundation.
- Primary Dependencies: существующий Sparkle 2.9.4; новых зависимостей нет.
- Storage: один Codable объект в UserDefaults, только метаданные.
- Testing: существующий XCTest, сборка SwiftPM, shell syntax, governance.
- Risk / Validation Lane: high-risk-feature (интерфейс и безопасность обновления).
- Release Gate: no deploy в текущем запросе; перед публикацией точный SHA, GitHub governance-fast/release-full, Developer ID, notarization/stapling/Gatekeeper, continuity и публичная проверка appcast.
- Target Platform: существующие поддерживаемые macOS; пакеты и идентичность не меняются.
- Performance Goals: штатный интервал 14400 секунд; никакого собственного постоянного опроса, максимум один кэшированный объект.
- Constraints: запись не прерывается, кэш не авторизует установку, пропуск подавляет окна, но сохраняет пассивный индикатор.
- Scope: только macOS, сборочные настройки и соответствующие тесты.

## Constitution Check

До исследования и после проектирования: PASS. I/II: существующие защищенные состояния и Stop сохраняются. III/IV: содержимого встреч и новых внешних получателей нет. V: проверка подписанного списка/архива и Developer ID не ослабляется. VI: clarify выполнен, требования/план/задачи анализируются до реализации, чеклисты принадлежат отдельному рецензенту. VII: штатные компоненты GRAF, доступные текстовые действия, без чужих ресурсов.

## Implementation

1. AppUpdateController.swift: состояние/кэш, восстановление только при совпадении доверия, текущей сборки и ОС; CalVer плюс SUStandardVersionComparator; сбои/skip сохраняют известную версию. Только didFindValidUpdate создает новое предложение. didFinishLoading сверяет наличие уже известной сборки в доверенной ленте; no-update без однозначной несовместимости не очищает кэш.
2. AppUpdateNotice.swift: переиспользуемая нативная строка с версией, пояснением и одной кнопкой; показ в главном окне и CalendarTray. Пункт меню локализован, значок/подсказка строки меню отражают известную версию.
3. Builder, configuration и validator согласуют период 14400; validator принимает также прежние 86400 для проверки предыдущих опубликованных приложений. Запуск добавляет один рекомендованный Sparkle background check, только при разрешенных автоматических проверках. Однократно мигрирует прежний продуктовый интервал 86400 в 14400; другие явно настроенные интервалы и отключение поиска сохраняются.
4. Существующие relaunch gate и main-frame allowlist сохраняются. canCheckForUpdates наблюдается для доступности новых кнопок. На ошибке скачивания не теряются версия и повторное действие.

## Validation Plan

Focused XCTest: AppUpdateControllerTests, EmbeddedCabinetUpdateBridgeTests, DesktopCalendarReminderTests, InstallerLifecycleEvidenceTests. Нужны проверки кэша/пропуска/отзыва/ошибки и всех защищенных состояний. Собрать executable. По quickstart — синтетическое окно/строка меню без записи или обращения к реальному аккаунту. Локальные проверки не заменяют GitHub governance-fast на будущем SHA; полный CI и публичная установка выполняются в отдельном разрешенном выпуске.

## Project Structure

- apps/macos/RecApp/Sources/Updates/AppUpdateController.swift
- apps/macos/RecApp/Sources/Updates/AppUpdateNotice.swift
- apps/macos/RecApp/Sources/Calendar/CalendarTray.swift
- apps/macos/RecApp/App/TwoBrainRecApp.swift
- apps/macos/Installer/Scripts/build-local-installer.sh
- apps/macos/Scripts/validate-app-updates.sh
- apps/macos/Shared/Tests/AppUpdateControllerTests.swift
- apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift
- changes/unreleased/F250.yaml

## Complexity Tracking

Используются существующие Sparkle, UserDefaults и системные элементы. Отдельный сервис обновлений, собственный установщик, push и таймер не нужны.

Уточнение расписания: 4 часа — настроенный период, когда нет активной сессии Sparkle или уже загруженного отложенного обновления. В этих состояниях штатный планировщик может отложить следующую проверку. Старое продуктовое значение 86400 мигрирует в 14400 один раз; другие явно настроенные интервалы сохраняются. Флага включения автоматического поиска миграция не меняет. Интерфейса настройки периода в GRAF сейчас нет.
