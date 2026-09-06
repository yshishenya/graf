# Implementation Plan: Достоверные устройства и сеансы
**Branch**: `codex/248-trustworthy-account-sessions` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

## Summary
Исправить источник сведений о клиенте и отзыв доступа, затем заменить два несогласованных списка единым списком сеансов. Использовать существующие модели, Jinja, CSS и WebKit; не добавлять зависимости или миграции.

## Technical Context
**Language/Version**: Python 3.12+, Swift 6.
**Primary Dependencies**: FastAPI, SQLAlchemy, Jinja, WebKit, существующие pytest/XCTest.
**Storage**: существующий PostgreSQL, таблицы auth_sessions, registered_devices, auth_session_device_bindings.
**Testing**: pytest + изолированный PostgreSQL RLS; Swift tests и живой WKWebView; браузерная проверка синтетических данных.
**Risk / Validation Lane**: high-risk-product — auth, session/device lifecycle, UX.
**Release Gate**: no deploy; PR governance-fast на exact SHA. Full CI, notarization и deployment — при отдельном релизе.
**Target Platform**: macOS, веб-браузеры, Linux backend.
**Project Type**: desktop + server-rendered web.
**Performance Goals**: обновлять активность не чаще раза в 300 секунд на сеанс; без нового polling/UI framework.
**Constraints**: сохранить RLS, CSRF, сроки токенов и приватность; User-Agent только подсказка отображения.
**Scale/Scope**: сеансы текущего пользователя в текущем рабочем пространстве. Существующие записи не мигрируют догадками.

## Constitution Check
До исследования: PASS — принципы III (секреты), VI (полный Spec Kit), VII (независимая реализация, доступность) соблюдены. Capture/удаление/публичная дистрибуция не изменяются.
После проектирования: PASS — новых источников приватных данных нет, старые данные не переклассифицируются; отзыв гарантируется сервером, доказательства синтетические. Высокорисковые checklist проходят отдельного рецензента до реализации.
Legacy Impact: untouched — исторические записи трактуются как неизвестные без нового совместимого маршрута или fallback.

## Architecture and Phases
1. `auth/sessions.py`: общий helper создаёт уникальную login:<uuid> регистрацию; ограниченно разбирает GRAFDesktop/<version> и известные браузеры/ОС, не хранит полный UA. Метаданные браузера ограничены allowlist и хранятся в существующем client_version (внутренний формат описан в data-model). Вызовы: email, OAuth, magic invitation, workspace continuation, billing handoff. Регистрация API остаётся отдельным существующим протоколом, исправляется её session binding.
2. macOS `EmbeddedCabinetWebView.swift`: `WKWebViewConfiguration.applicationNameForUserAgent` до создания WKWebView, устойчивый GRAFDesktop/<version> для форм/redirect. Версия валидируется сервером. Не переписывать UA целиком, не использовать URL или X-GRAF-Client как доказательство типа.
3. `auth/dependencies.py`: после membership перейти из auth_bootstrap в TenantDatabaseContext; проверить устройство и binding для bound-сеансов, обновлять last_seen условным SQL с active/expiry и порогом 300 секунд. Unbound API bootstrap остаётся допустим для регистрации, заблокированная binding-only запись не даёт обход.
4. Единый helper device revoke в `auth/sessions.py` используется API и bulk settings; найти связанные session через device_id И binding, блокировать привязки и сеансы. Проверки владельца до изменения. Session revoke блокирует свои bindings. Не менять revoked на expired при повторной проверке и не обновлять last_seen при logout.
5. `billing.py`: callback one-time lock, source session/user/workspace/device checks, новое browser разрешение с остатком TTL; flush перед сменой RLS-контекста, callback завершить в той же транзакции. Token app в browser cookie не передавать.
6. `view_models.py` + `queries.py`: привязать клиент к session, вычислить эффективное состояние с учётом устройства/binding/expiry, текущий первым; active и history разделены. Даты через ZoneInfo с безопасным fallback UTC, явный часовой пояс.
7. `settings_account_content.html`: единый список «Где вы вошли», кнопки только для действующих чужих сеансов; отдельные раскрываемые подробности и история; область рабочего пространства и фоновая активность объяснены. Существующие device endpoints сохраняются и проверяются, сырой дублирующий список registrations убирается.
8. `settings.py`: серверная страница подтверждения точечного и массового завершения при POST без confirm; второй POST с CSRF и confirm завершает действие. Отмена возвращает настройки, без JS действие безопасно; JS dialog не дублируется. Существующие маршруты/redirect сохраняются.

## Validation Plan
Сначала регрессионные тесты источника клиента/отзыва/проекции, затем реализация. Изолированный PostgreSQL проверяет реальные auth_bootstrap→request границы. Быстрые server lint/tests, Swift целевые тесты; full не запускать для итерации. Реальный browser/WKWebView с синтетическими аккаунтами проверяет form POST, текущий вход, подтверждение/отмену/ошибки и ширины 375/768/1280. Converge и Ponytail review перед PR; GitHub governance-fast на итоговом SHA. Ограничения живого OAuth провайдеров/production перечислить, не подменять синтетическим успехом.

## Project Structure
- `apps/server/src/twobrain_rec_server/auth/{sessions,dependencies,callbacks,workspace_onboarding}.py`
- `apps/server/src/twobrain_rec_server/api/auth.py`
- `apps/server/src/twobrain_rec_server/cabinet/{view_models,queries,rendering}.py`
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/{auth_email_flow,browser,billing,settings}.py`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`
- `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`
- Existing unit/contract/integration and macOS tests; `changes/unreleased/F248.yaml`.

## Complexity Tracking
Новые библиотеки, migration, hardware tracking, геолокация, отдельная модель устройств и фоновые jobs не требуются. Существующий backend сохраняет область рабочего пространства.

### Unbound API bootstrap
Законно не привязанным считается только сеанс с device_id=NULL и без каких-либо binding rows. Он сохраняет прежний ограниченный доступ к principal-only API (включая auth/me и регистрацию устройства); tenant/cabinet доступ без регистрации не разрешается. В списке другого действующего сеанса такого же владельца он показывается как «Устройство не подключено», с пояснением «Вход выполнен, устройство ещё не подключено», и доступен завершению. Он действующий по сроку/статусу, но не означает доступ к данным пространства. Если device_id указан, но устройство/binding отсутствует, или есть blocked/несогласованная binding, запрос отклоняется и UI не считает запись действующей. Историческая binding-only запись проверяется по этой связи; разрешённая trusted связь может восстановить контекст текущего запроса без изменения типа клиента.

## UX-продолжение T010/T011 — 2026-09-06
Risk lane остаётся high-risk-product как продолжение существующего сценария управления доступом; scope нового diff — представление/микротексты, auth helpers и БД неизменны. Конституция до/после уточнения: PASS (III/VI/VII), повторный clarify зафиксирован в spec; независимый рецензент принимает дополнение checklists/ux.md до кода.

1. `cabinet/view_models.py`: короткая локализованная дата на основе существующего timezone профиля и фиксируемого now; полные labels сохраняются для details/aria/подтверждения. Метки unknown/unbound только переименовываются; доступ определяется прежним helper. Для сегодняшнего/вчерашнего дня сравниваются даты после перевода обеих отметок в одну зону.
2. `cabinet/templates/cabinet/pages/settings_account_content.html` и существующий `cabinet/static/cabinet/cabinet.css`: один выделенный текущий вход; иконки можно опустить, не добавляя ресурсы ради декора. Primary — клиент, secondary — «Последняя активность: сегодня, 14:20»; точные сведения под native details. Массовая кнопка после списка, scope всегда виден, история и объяснения свёрнуты.
3. `cabinet/web_routes/settings.py`, `cabinet/rendering.py`: понятные тексты подтверждения/результата, уникальная цель. Перенести data-outcome-focus с контейнера на ссылку отмены, использовать native autofocus на отмене и проверить фактический фокус; не добавлять новый JS и не оставлять конфликтующий autofocus на подтверждающем действии.
4. T011: целевые unit/route/UI контракты, реальный synthetic browser/WebKit preview на 375/768/1280 px, no-JS и клавиатура; независимый review результата и Ponytail. Evidence дополнить в evidence/implementation.md, fragment — changes/unreleased/F248.yaml. Полная auth/RLS реализация и guards предыдущего этапа сохраняются. Снимки только синтетические. PR #6626 после итогового коммита отдельно обязан пройти governance-fast на новом SHA; T011 завершается по локальному результату, без требования знать SHA будущего коммита.

Итоговые тексты, принятые UX-рецензентом: вступление «Проверьте входы и выйдите из тех, которыми больше не пользуетесь.»; подпись «Последняя активность»; пустое состояние «Других входов нет.». Короткое пустое состояние относится к постоянно указанному текущему рабочему пространству. Эти уточнения не меняют действие, область доступа или достоверность времени.
