# Analysis: Сквозное укрепление интерфейса GRAF

**Feature**: `293-interface-hardening` | **Date**: 2026-11-10
**Scope**: spec.md, plan.md, tasks.md, research.md, data-model.md, contracts/, quickstart.md

## Verdict

- Critical: 0
- High: 0
- Medium: 3, явно ограничены и не блокируют выпуск
- Low: 2

Чеклисты требований (`ux`, `audio-capture`, `security`) независимо проверены: 100/100 PASS.
Все обязательные FR покрыты задачами или явно ограничены; противоречий между spec,
plan, data-model и contracts не найдено.

## Requirement coverage

| Область | Требования | Задачи | Доказательство |
|---|---|---|---|
| Статусы записи | FR-001, FR-003, SC-002 | T009–T011, T014 | `CaptureStatusPresentationTests`, `CaptureControlV5Tests` |
| Ошибки без внутренних кодов | FR-002 | T013 | `SystemAudioStatusLabels.captureFailureDetail`, тесты кодов |
| Разрешения | FR-004 | T012 (частично) | типизированный `SystemAudioPermissionGate`; тексты онбординга остаются отдельными |
| Глобальная остановка | FR-005, SC-005 | T017 | `AppMenuBuilderTests`, `AppLifecycleDelegate.stopRecordingFromMenu` |
| Смена аккаунта | FR-006, FR-025 | T015–T016 | `AccountSwitchResetTests`, `applyAccountSwitchReset` |
| Настройки и кабинет | FR-007, FR-022 | T018 | `LocalSettingsSection`, состояния `DesktopCabinetState` |
| Предпочтения окна/панели/микрофона | FR-008 | T019 | `AppShellBehaviorTests`, `InterfacePreferencesStore` |
| Путь отрисовки | FR-009–FR-011, SC-004 | T021–T022 | `InterfacePerformanceContractTests`, `ci-local` stress-тесты |
| Логи и приватность | FR-012 | T022 | `AppLog`, `BoundedLogFileWriter`, существующие redaction-тесты |
| Меню и масштаб | FR-013–FR-014 | T017, T024 | `AppMenuBuilderTests`, `WorkspaceZoomTests` |
| Доступность | FR-015 | T025 (частично) | sort priority, reduce motion, ScaledMetric; отдельная contrast/long-string матрица не добавлена |
| Мёртвый код | FR-016 | T027 | удалены типы/enum’ы/константы; сборка и тесты PASS |
| Дизайн-токены | FR-017 | T006 | `DesktopDesignTokenContractTests` |
| Поведенческие тесты | FR-018 | T009–T020, T024–T027 | Swift suite 1313 тестов |
| Релиз | FR-019, SC-007 | T031–T034 | PR checks, release-full, notarization/Sparkle gates |
| Продуктовые гейты | FR-020 | все | гейты записи, приватности, удаления и диагностики не ослаблены |
| Support-сводка | FR-021 | T026 | «Скопировано», metadata-only политика |
| Завершение при сохранении | FR-023 | T019 | `preserveRecordingForInterruption`, существующий тест writer |
| Карточка уведомления | FR-024 | T019, T026 | `DesktopNotificationProtectedConsumerTests` |
| Частичная отправка/срок | FR-026 | T009–T010 | typed `uploading`/`expired` presentation |

## Findings

### Medium 1 — 60-минутный аппаратный performance gate

- Spec SC-004 требует 60-минутную запись и очередь 100 записей с измерением ≤100 мс.
- В поставке выполнены: кэш устройств, вынос строк очереди из view builder, detached I/O,
  кэш форматтеров, пакетные логи, контрактные тесты и существующий стресс-тест 100 пакетов.
- Полный 60-минутный аппаратный прогон в `/Applications/GRAF Dev.app` не выполнялся.
- Решение: не считать это доказанным; ограничение записано в `validation.md`. Автоматический
  `release-full` не заменяет аппаратное измерение, но и не требует его по контракту релиза.

### Medium 2 — Permission copy unification

- Типизированный `SystemAudioPermissionGate` остаётся источником для стартового гейта.
- Онбординг использует собственные тексты шагов; противоречий по смыслу нет, но единый
  `PermissionPresentation` не добавлен, чтобы не создать второй источник правды.
- Решение: T012 оставлен открытым с пояснением; унификация текстов — отдельная задача.

### Medium 3 — Accessibility matrix

- Добавлены sort priority, reduce motion, адаптивные ширины и проверки существующих
  accessibility-деревьев.
- Отдельная матрица increased-contrast и длинных русских строк не создана.
- Решение: T025 оставлен открытым с пояснением; критические действия проверены существующими
  тестами.

### Low 1 — Мёртвый CSS кабинета

- Очистка подтверждённо мёртвых классов `cabinet.css` не входит в кодовый кандидат.
- Это отдельная низкорисковая web-задача; текущие контракты кабинета не менялись.

### Low 2 — Структурный перенос дизайн-системы и titlebar host

- T007/T029 не выполнены полностью: перенос файлов и общий `TitlebarAccessoryHost` —
  структурная гигиена без изменения поведения.
- Функциональные требования покрыты; перенос отложен.

## Consistency checks

- Все FR-001–FR-026 присутствуют в spec и не противоречат data-model/contracts.
- Все задачи T001–T034 сопоставлены с фазами и user stories; release-задачи T031–T034
  остаются открытыми до фактической публикации.
- `changes/unreleased/F293.yaml` соответствует feature ID, issue #7967 и задачам.
- Legacy Impact: `untouched`; удалённое audio routing не возвращается, буфер и analytics
  scaffold сохранены.
- Публичный релиз остаётся Developer ID-only с нотаризацией, stapling, Gatekeeper и Sparkle.
- Нет новых секретов, приватных данных, путей или внутренних кодов в UI/логах.

## Release readiness

Кодовый кандидат готов к PR-проверкам и release-full. Перед публикацией обязательны:
успешные `governance-fast`, `macos-pr`, `pr-metadata` на точном SHA; `release-full`;
Developer ID; Accepted notarization; staple; Gatekeeper; Sparkle; live appcast.
