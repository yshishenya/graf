# Feature Specification: Единая информационная архитектура меню GRAF

**Feature Branch**: `201-settings-navigation-consistency`

**Created**: 2026-08-25

**Status**: Implemented; release closeout in progress

**Input**: Сверить меню профиля GRAF с установленным Krisp по информационной архитектуре, сохранив clean-room реализацию и текущие auth/accessibility контракты.

## User Scenarios & Testing

### User Story 1 - Понятное меню приложения (Priority: P1)

Пользователь открывает профильное меню и видит account-контекст, внешний вид,
настройки, помощь и завершение работы в предсказуемом порядке.

**Independent Test**: отрендерить browser и embedded shell, извлечь пункты и
проверить порядок, границы секций и одинаковую IA.

### User Story 2 - Временные пункты помощи не выглядят активными (Priority: P1)

Пользователь видит будущие пункты поддержки, документации и диагностики, но
понимает по disabled-состоянию, что они пока недоступны.

**Independent Test**: проверить `disabled`, `aria-disabled="true"`, серый стиль
и отсутствие href/action у недоступных пунктов.

### User Story 3 - Рабочие действия остаются безопасными (Priority: P1)

Пользователь может выбрать тему, открыть «Настройки», выйти и в embedded GRAF
закрыть приложение. Browser не имитирует невозможное закрытие вкладки.

**Independent Test**: проверить theme POST/preview, settings routes, logout
CSRF/redirect и native quit bridge.

## Requirements

- **FR-001**: В browser и embedded profile menu MUST использовать порядок сверху вниз: аккаунт; разделитель; «Вид»; «Настройки»; разделитель; «Решение проблем»; «Документация»; «Техническая поддержка»; «Обратная связь»; «Присоединиться к ТГ каналу»; разделитель; «Выйти». Embedded дополнительно содержит «Закрыть GRAF» после «Выйти».
- **FR-002**: «Вид» MUST содержать «Светлая», «Тёмная», «Системная» и переиспользовать существующее сохранение account preferences.
- **FR-003**: «Решение проблем» MUST содержать disabled-пункты Report a problem, Record network log, Network diagnostics.
- **FR-004**: «Документация» MUST содержать disabled-пункты Getting started, What's new, Help center, Data privacy and sharing.
- **FR-005**: Техническая поддержка, Обратная связь и Присоединиться к ТГ каналу MUST быть disabled и не должны выполнять навигацию.
- **FR-006**: «Аккаунт» MUST вести в account settings, а «Настройки» — в корень settings; routes MUST быть surface-aware для browser и embedded.
- **FR-007**: «Выйти» MUST сохранить существующие POST, CSRF field и browser/desktop redirect targets.
- **FR-008**: «Закрыть GRAF» MUST вызывать validated native bridge только в embedded desktop. В browser пункт не должен рендериться.
- **FR-009**: Escape, click-outside, focus restoration, compact rail, long profile text и no-JS fallback MUST сохраниться.
- **FR-010**: Krisp используется только как clean-room reference IA/behavior; код, exact styling, assets и тексты реализации Krisp не копируются.

## Success Criteria

- **SC-001**: В browser список menu actions совпадает с browser-вариантом FR-001, в embedded — с embedded-вариантом FR-001; каждый submenu содержит ровно заявленное число пунктов.
- **SC-002**: Все 10 временно недоступных пунктов помощи/поддержки имеют `disabled` и `aria-disabled="true"`, а HTML не содержит для них активный href/action.
- **SC-003**: Визуальная и static-проверка wide/narrow/compact rail не показывает обрезки профиля, выхода за viewport или неактивных пунктов, выглядящих кликабельными.
- **SC-004**: Existing focused cabinet tests, settings-flow integration tests и `infra/scripts/ci-local.sh --fast` проходят; production release evidence records the exact deployed SHA and health/smoke result.
- **SC-005**: Native bridge принимает только allowlisted `quit` от main-frame allowed cabinet document и имеет contract test.

## Edge Cases / Out of Scope

- Browser cannot reliably close a user tab; the desktop-only close action is omitted from the web menu.
- No new support, diagnostics, documentation, Telegram, telemetry or account APIs are introduced.
- No production deploy, release or installed-app mutation is included.
