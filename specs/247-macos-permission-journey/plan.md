# Implementation Plan: F247

Branch: `codex/247-macos-permission-journey` | Date: 2026-09-06 | Spec: [spec.md](spec.md)

## Summary
Одно нативное окно по запросу, два последовательных разрешения, помощь при возврате из Settings. Обновление состояния отделено от показа окна.

## Technical Context
Swift 6, SwiftUI/AppKit, AVFoundation, CoreGraphics, ScreenCaptureKit; macOS 14+. Существующие зависимости; новых нет. UserDefaults/AppStorage для истории попыток и незавершённой настройки, ОС — источник прав. XCTest в текущем Swift package.
Risk / Validation Lane: high-risk-product, permissions/capture/UX. Release Gate: no deploy; для публикации отдельный release/full/signing gate и согласование commit.
Performance: bounded permission probe ≤8 секунд; никакого опроса по таймеру в фоне.
Scope: DesktopPermissionOnboardingView.swift, TwoBrainRecApp.swift, CaptureControlViewCore.swift, SystemAudioCaptureService.swift и существующие профильные тесты.

## Constitution Check
До и после проектирования: system-audio-first сохраняется; нет новой маршрутизации/credentials/egress. Ручные Record/Stop и активный индикатор сохранены. Автозапись Всегда/Спрашивать/Никогда, 8 секунд и remembrance сохранены; открытая настройка временно делает маршрут недоступным. Никаких записей из действий настройки. Перезапуск через protected work. Нет чужих ассетов: SF Symbols, нативные стили, оригинальная схематическая подсказка. Доступность и privacy входят в критерии.

## Design
Удалить ложное правило restart по переходу состояния. Хранить stale функциональной проверки до успешной повторной проверки, но показывать recovery как возможность, а не гарантию. Проверка без запроса при preflight != granted; одно продолжение с таймаутом, поздний ответ игнорируется. Request и probe не пересекаются. После await снова preflight, чтобы не восстановить отозванный доступ.
Общий start до beginPreparing: passive preflight; manual missing открывает setup, detector missing возвращает blocked. Запросы только в setup. Пока окно/операция открыты, detector route unavailable; уже открытый prompt закрывается без skip и получает retryable. Queued decisions повторно проверяют доступность. После закрытия восстановлены прежние правила.
Окно: цель, прогресс 0/2, две строки; активная строка раскрывает действие. Готовность не закрывает окно. «Позже» всегда доступно. Settings help содержит путь, app identity, неинтерактивную иллюстрацию. Restricted/stale имеют помощь, retry и безопасный выход. Стартовая CTA вне окна доступна при missing permission и соблюдает busy guards.

## Validation Plan
Focused Swift tests: SystemAudioPermissionUXTests, AppControlAccessibilityTests, SystemAudioCaptureServiceTests, MeetingDetection tests; Swift build. Синтетический рендер настоящего SwiftUI окна initial/settings/ready/recovery, обе темы. Быстрый repository gate согласно release guidance. Реальная выдача TCC, MDM, clean install и VoiceOver на тестовом Mac — отдельное честно отмеченное acceptance; текущие разрешения пользователя не менять.

## Project Structure
`specs/247-macos-permission-journey/{spec,plan,research,data-model,quickstart,tasks}.md`, `contracts/permission-ui.md`, `checklists/{ux,audio-capture,security}.md`.
Исходники: `apps/macos/RecApp/{App/TwoBrainRecApp.swift,Sources/Capture/}`. Проверки: `apps/macos/Shared/Tests/`. Changelog: `changes/unreleased/F247.yaml`.

## Complexity Tracking
Новых архитектурных слоев, библиотек, серверных контрактов нет. Нужен только ограниченный completion для неотменяемого системного вызова; он повторяет существующий native timeout pattern.

## Уточнение реализации: системный Quit/Reopen

Обычная страница в существующем NSWindow вместо SwiftUI sheet. Существующий workspace остаётся смонтированным, но скрыт, недоступен для кликов/клавиатуры/VoiceOver. Один AppStorage Bool сохраняет открытое намерение настройки до Позже/Готово; штатный quit и собственный restart его не очищают. Перед возобновлением detector действуют те же guards. Подсказка заранее объясняет кнопку macOS и возвращение. Проверка: XCTest границ плюс запускаемый сценарий Quit Apple Event → штатная очистка → завершение процесса → повторный запуск отдельной локальной копии. Без TCC reset, захвата и изменения установленного GRAF.
