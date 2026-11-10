# Audio Capture Checklist: Сквозное укрепление интерфейса GRAF

**Purpose**: Проверить полноту и безопасность требований к записи, разрешениям, остановке, локальной сохранности и деградации.
**Created**: 2026-11-10
**Feature**: [spec.md](../spec.md)

**Note**: Reviewer-owned requirements-quality artifact.
**Marker Semantics**: `[x]` means the requirements-quality criterion is satisfied; it does not mean implementation is complete.

## Capture Safety

- [x] CHK001 Определено ли, что активная запись всегда имеет видимый локальный индикатор? [Completeness, Constitution §II]
- [x] CHK002 Определено ли, что Stop доступен одним действием при закрытом окне? [Completeness, Spec §FR-005]
- [x] CHK003 Определено ли, что интерфейсные изменения не ослабляют трёхсостояние автозаписи и восьмисекундный отсчёт? [Consistency, Constitution §II]
- [x] CHK004 Определено ли, что изменения не затрагивают системный звук, микрофон и эхо-обработку? [Scope, Spec §Assumptions]
- [x] CHK005 Определено ли, что ручной старт остаётся доступным при разрешённой политике? [Completeness, Spec §US1]

## Permissions

- [x] CHK006 Определены ли состояния unknown, granted, denied, restricted и stale для обоих разрешений? [Completeness, Spec §FR-004]
- [x] CHK007 Определено ли, когда показывается системный запрос, а когда — настройки macOS? [Clarity, Spec §FR-004]
- [x] CHK008 Определено ли, что restricted не приводит к бесконечному повторному запросу? [Consistency, Spec §US4]
- [x] CHK009 Определено ли, что onboarding не начинает запись сам? [Completeness, Spec §US4]
- [x] CHK010 Согласованы ли тексты разрешений между onboarding, панелью и гейтом старта? [Consistency, Spec §FR-004]

## Recording States

- [x] CHK011 Определены ли действия для starting, active, paused, degraded, stopping и failed? [Completeness, Spec §US1]
- [x] CHK012 Определено ли, что paused показывает Resume и Stop, а system audio продолжается? [Clarity, Spec §US1]
- [x] CHK013 Определено ли, что stopping не показывает повторный доступный Stop? [Consistency, Spec §Data Model]
- [x] CHK014 Определено ли, что failed не выглядит как «Готово к записи»? [Consistency, Spec §US1]
- [x] CHK015 Определено ли, что degraded не маскируется под полный успех? [Clarity, Spec §US1]

## Local Custody

- [x] CHK016 Определены ли состояния active, saved, degraded, blocked, failed и terminal для локальной копии? [Completeness, Spec §US1]
- [x] CHK017 Определено ли, когда локальная копия требует внимания? [Clarity, Spec §Data Model]
- [x] CHK018 Определено ли, что открытие, отправка и удаление — разные действия? [Consistency, Spec §Interface Contract]
- [x] CHK019 Определено ли, что deletion copy не обещает удаление вне контроля GRAF? [Consistency, Constitution §IV]
- [x] CHK020 Определено ли поведение при повреждённой, частичной и старой записи? [Edge Cases, Spec §Edge Cases]

## Failure & Recovery

- [x] CHK021 Определено ли, что пользовательские сообщения не содержат внутренних кодов ошибок? [Clarity, Spec §FR-002]
- [x] CHK022 Определено ли, какие ошибки retryable, а какие требуют действия пользователя? [Completeness, Spec §Data Model]
- [x] CHK023 Определено ли, что сбой сохранения не приводит к ложному «сохранено»? [Consistency, Spec §US1]
- [x] CHK024 Определены ли recovery action для permission, storage, capture, policy, indicator, source? [Completeness, Spec §Data Model]
- [x] CHK025 Определено ли, что смена аккаунта не меняет состояние локальной записи и не удаляет её? [Consistency, Spec §FR-006, §FR-020]

## Performance & Long Run

- [x] CHK026 Определён ли сценарий 60-минутной записи с очередью 100 записей? [Completeness, Spec §SC-004]
- [x] CHK027 Определено ли, что путь отрисовки не выполняет файловых проверок и DiscoverySession? [Clarity, Spec §FR-009]
- [x] CHK028 Определено ли, что обновление уровней 5 Гц не создаёт форматтеры и не блокирует UI? [Clarity, Spec §FR-010]
- [x] CHK029 Определено ли, что очередь не блокирует главный поток при активации/пробуждении? [Completeness, Spec §FR-011]
- [x] CHK030 Определено ли, что логи ограничены и не раскрывают приватные данные? [Completeness, Spec §FR-012]

## Edge Cases

- [x] CHK031 Покрыт ли сценарий одновременной остановки из нескольких поверхностей? [Coverage, Spec §Edge Cases]
- [x] CHK032 Покрыт ли сценарий отключения микрофона во время записи? [Coverage, Spec §Edge Cases]
- [x] CHK033 Покрыт ли сценарий закрытия приложения во время сохранения? [Coverage, Spec §Edge Cases]
- [x] CHK034 Покрыт ли сценарий обновления во время записи? [Coverage, Spec §Edge Cases]
- [x] CHK035 Покрыт ли сценарий смены аккаунта во время записи? [Coverage, Spec §Edge Cases]

## Notes

- Отмечать `[x]` только после проверки требований, а не реализации.
- Пункты без подтверждения оставлять `[ ]` с причиной в отчёте ревью.
