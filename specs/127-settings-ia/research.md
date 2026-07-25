# Research: единая архитектура настроек

## Decision 1: list-detail IA с максимум двумя уровнями

**Decision**: Основное меню ведёт на обзор `/settings`. Внутренняя навигация
ведёт в поддерживаемые категории: «Запись», «Итоги», «Интеграции →
Календари», «Аккаунт и безопасность» и «Пространство и команда». Пустые
будущие категории не добавляются.

**Rationale**: Настройки должны быть обнаружимыми из глобального входа и не
требовать знания deep link. Плоский список смешивает личные, workspace и
machine-only изменения. Два уровня достаточно для текущего инвентаря и не
создаёт скрытую третью навигацию.

**Evidence**:

- `apps/server/src/twobrain_rec_server/cabinet/view_models.py` направляет
  глобальную ссылку «Настройки» прямо в calendar deep link.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html`
  смешивает summary, calendar, auth provider, workspace и invitation surfaces в
  одном списке.
- `specs/030-mvp-experience-design-system/design/screens/settings-recording-theme.md`
  уже описывает list-detail layout и scope labels.

### Feature inventory

| Existing surface | Current source | Canonical category |
|---|---|---|
| Summary default, built-ins and personal formats | `settings_content.html`, `/api/v1/cabinet/summary-templates` | `Итоги → Форматы` |
| Calendar sources, providers, preferences, preview and disconnect | `calendar.py`, `calendar_settings.html` | `Интеграции → Календари` |
| Linked provider start/confirm flow | `provider_links.py`, `provider_link_settings.html` | `Аккаунт и безопасность` |
| Active spaces and join offers | `spaces.py`, `settings_content.html` | `Пространство и команда` |
| Registered devices | `/api/v1/auth/me`, `/api/v1/auth/devices/:id/revoke` | `Аккаунт и безопасность` |
| Native target-scoped meeting detection | `MeetingDetectionSettingsView.swift` | `Запись` handoff |
| Admin users/files/metrics/audit/meeting detection | `admin/web.py` | Remains separate admin area |

## Decision 2: использовать существующий server-rendered cabinet stack

**Decision**: Сохранить FastAPI/Jinja/vanilla JS/CSS и существующие route,
query, CSRF и tenant-context helpers. Не добавлять UI-фреймворк, state library,
новую схему настроек или отдельный persistence layer.

**Rationale**: Все текущие settings surfaces уже рендерятся этим стеком. Новый
framework увеличил бы diff и создал две параллельные системы доступности,
вложенности и ошибок.

**Alternatives considered**: отдельный React settings shell — отклонён, потому
что не нужен для server-rendered pages и усложняет embedded desktop parity;
schema-driven settings registry — отложен до появления третьего независимого
клиента или десятков новых настроек.

## Decision 3: scope и permission должны быть видимы до действия

**Decision**: В общем settings navigation и на каждом category page показывать
scope badge/copy из ограниченного словаря: «Личная настройка», «В этом
пространстве», «Только владелец», «На этом Mac», «Только в браузере», «Только в
приложении».

**Rationale**: Scope — часть смысла настройки, а не второстепенная справка.
Владелец и доступность берутся из уже существующих membership/session/policy
границ; UI не выводит сырые идентификаторы или внутренние role values без
перевода.

## Decision 4: account surface показывает безопасную производную данных

**Decision**: Для «Аккаунт и безопасность» использовать существующие
`ExternalIdentity`, `RegisteredDevice` и provider-link flow. В HTML выводить
только человекочитаемый provider, primary/status, platform/version и
маскированные даты/состояния; `provider_subject`, email/phone candidates,
tokens и credential values не выводить. Отзыв устройства переиспользует
существующую авторизационную проверку и audit path.

**Rationale**: `/api/v1/auth/me` уже предоставляет связанные providers и
registered devices, а `/api/v1/auth/devices/{device_id}/revoke` уже содержит
проверки workspace/owner-admin и блокировку bindings. Представление должно
использовать эти границы, а не дублировать authorization policy или раскрывать
сырой subject.

## Decision 5: календарь остаётся отдельной integration page

**Decision**: Канонический путь `/settings/integrations/calendar` сохраняется.
Внутри него порядок остаётся от boundary/status к sources, selection, sync
preferences, preview/conflicts и disconnect. Provider dialogs получают
возврат фокуса к инициатору, semantic actions и безопасные error states.

**Rationale**: Calendar page уже содержит значительную предметную модель,
privacy boundary и failure copy. Переносить её в общий flat card нельзя;
settings IA должна только дать ясный вход и общий shell.

**References**:

- [WCAG 2.2](https://www.w3.org/TR/wcag/) — keyboard, focus, error and status
  requirements.
- [MDN: `<dialog>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog)
  — modal semantics and `showModal()` behavior.
- [GOV.UK checkboxes](https://design-system.service.gov.uk/components/checkboxes/)
  — grouped choices and explanatory hint text.
- [GOV.UK error message](https://design-system.service.gov.uk/components/error-message/)
  and [error summary](https://design-system.service.gov.uk/components/error-summary/)
  — field-level and summary-level failure communication.

## Decision 6: recording settings are a truthful native handoff

**Decision**: Web adds a «Запись» category that explains scope and links to the
native macOS meeting-detection settings where appropriate. Web MUST NOT gain a
global recording toggle or any audio-routing fallback. Existing native copy and
visible capture/Stop behavior remain authoritative.

**Rationale**: The constitution requires target-scoped, visible, native capture
control. The web page can solve discoverability without moving capture policy
across the trust boundary.

## Decision 7: compatibility is explicit

**Decision**: Keep existing calendar, provider-link, spaces and summary API
paths. Add category paths as new canonical entry points and mirror them in the
embedded desktop shell. Existing redirects receive a category-aware return
path only where the current flow already supports it.

**Rationale**: Deep links and existing tests are part of the product contract.
The global navigation bug is fixed at its source instead of adding a second
settings destination.
