# Implementation Plan: Единое поле выбора
**Branch**: `6793-unified-settings-combobox` | **Date**: 2026-09-11 | **Spec**: [spec.md](spec.md)

## Summary
Общий локальный combobox поверх штатного select и поле-фильтр приложений. В macOS — нативный редактируемый список с тем же контрактом. Существующие формы/мост остаются владельцами сохранения.

## Technical Context
- Language/Version: JavaScript ES2022, Python 3.12, Swift/AppKit/SwiftUI существующих пакетов.
- Dependencies: без новых зависимостей; DOM и NSComboBox.
- Storage: прежние настройки; новый компонент не хранит и не отправляет данные.
- Risk / Validation Lane: high-risk-feature, общий UX и доступность на web/embedded/offline поверхностях.
- Release Gate: no deploy; коммит только после разрешения; затем GRAF Dev, exact-SHA governance-fast для PR; release-full на замороженном кандидате перед релизом.
- Performance: локальный каталог 600 вариантов, фильтрация ≤100 мс.
- Scope: все одиночные выпадающие списки настроек и фильтр приложений; карточки/флажки вне scope.

## Constitution Check
До/после проектирования PASS: ввод не меняет сохранение, target allowlist, auth, privacy, capture, consent, manual controls или API. Локальная фильтрация, доступная клавиатура/озвучивание, русский текст, темы. Независимая реализация на существующих платформах, без сторонних активов. Пользователь прямо запросил отклонение от прежнего UX поиска. Только GRAF Dev через harness после авторизованного коммита.

## Validation Plan
Браузерные сценарии timezone-settings и новый settings-combobox, contract settings, Swift WKWebView bridge и focused macOS checks; пользовательское принятие в GRAF Dev после коммита. Отдельная проверка требований до реализации и Ponytail/code review перед PR. См. quickstart.md.

## Project Structure
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`: общий helper, регистрация, приложение-фильтр, timezone; сохранение штатного select, disabled/change/reset/catalog sync.
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`: внешний вид меню/поля/фокуса в существующих темах.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_*_content.html`: удаление отдельного timezone поиска, маркеры единого выбора.
- `apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift`: общий платформенный компонент.
- `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`: общий нативный выбор для приложения и правил; notification surface при наличии меню.
- `apps/server/tests/browser/`, `apps/server/tests/contract/test_settings_ui_contract.py`, `apps/macos/Shared/Tests/`: соответствующие проверки.
- `changes/unreleased/F6793.yaml` и `validation/receipt.md`.

## Complexity Tracking
Новые библиотеки и отдельный UI framework не нужны. Штатный datalist не гарантирует единообразное открытие всех вариантов и запрет свободного значения; DOM helper нужен для этого контракта. На macOS использовать платформенный NSComboBox.

## Дополнение пользователя: размер и отступы
Начальный размер резервного окна 1040×800, ограниченный visibleFrame текущего экрана с полями 16 px. Минимум 820×680 также ограничен экраном; вкладки используют одно окно без автоматического уменьшения. Каталог приложений остаётся прокручиваемым. Локальные строки сгруппированы без межстрочного spacing (40 px + разделитель), web строки имеют вертикальный отступ 4 px и минимум 44 px. Хранение и правила не меняются; проверка в рамках текущего high-risk-feature lane.
