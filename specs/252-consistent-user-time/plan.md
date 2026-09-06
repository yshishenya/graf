# Implementation Plan: Единые даты и время

**Branch**: `codex/252-consistent-user-time` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

## Summary
Исправить общий выбор времени для представления и числовую сортировку, сохранив абсолютные значения в хранении и транспортных контрактах.

## Technical Context
Python/FastAPI/SQLAlchemy/Postgres, Jinja/vanilla JS/HTMX, Swift/Foundation. Миграция 0086 снимает ограничение Moscow/UTC и делает timezone nullable; Babel даёт русские CLDR-названия городов и регионов. Используем zoneinfo, ContextVar, Intl, DateFormatter и существующие тесты.

## Risk and Validation Lane
Significant feature / high-risk UX (общие форматирование, SQL-поиск и административное отображение). Полная последовательность Spec Kit; clarify пройден. Focused tests и синтетический браузерный прогон обязательны. PR требует governance-fast на точном SHA; локальный fast только при недоступном PR как диагностический fallback. Full CI и production относятся к отдельному разрешённому релизу.

## Constitution Check
До и после дизайна: PASS. Только представление/сортировка, capture, consent, tenants, серверные сроки и расчётные границы не меняются. Evidence синтетический. Legacy Impact: untouched; собственные legacy aliases отсутствуют; Babel/CLDR используется для стандартных переводов. Public macOS distribution не выполняется.

## Project Structure
- `apps/server/src/twobrain_rec_server/cabinet/user_time.py`: общий formatter, IANA validation, request-local timezone middleware (ContextVar reset в finally), UTC fallback.
- `cabinet/static/cabinet/user-time.js`: cookie с IANA-поясом устройства, безопасное обновление первого GET при несовпадении, без повторного POST/циклов/действий; общие функции форматирования.
- `main.py`, cabinet/admin templates: подключение display context и локального script. Cookie не является auth/tenant/business authority.
- `cabinet/view_models.py`, `queries.py`, `rendering.py`, `static/cabinet/cabinet.js`: эффективная дата, SQL timezone search, данные для смешанной сортировки, локальные фильтры, полные даты карточки/календаря.
- `cabinet/web_routes/{billing,referrals,fair_use,settings}.py`, `review_policy_rendering.py`, `admin/{audit,files}.py`, cabinet/admin HTML: общий display formatter, одно поле выбора пояса в настройках.
- `cabinet/access.py`, `web_routes/browser.py`, HTML-ветки `api/cabinet.py`: отдельная проекция даты общего доступа, сохраняющая транспортные контракты.
- `apps/macos/RecApp/Sources/{Cabinet,Calendar,Upload}`: настоящее начало, стабильная сортировка, единый DateFormatter, доступные даты, дедлайны.

## Phases
1. Синтетическая регрессия и общий форматтер/контекст.
2. Серверный список, SQL-поиск, смешанные локальные строки и карточка.
3. Остальные HTML-поверхности и нативный список.
4. Focused Python/JS/Swift, браузерный сценарий, converge и changelog fragment.

## Review Gates
Рецензент отдельно оценивает `checklists/ux.md` и `checklists/time-contract.md`; реализация не отмечает их самостоятельно. Analyze: CRITICAL 0, HIGH 0 до реализации. Umbrella #6663.

## Дополнение: настройка пояса в той же Feature 252
Nullable UserIdentity.timezone — единственный источник сохранённого выбора. Нет timezone_mode и второго поля. До выбора применяется cookie устройства (native — системный пояс). Auth resolution после проверки пользователя задаёт request-local предпочтение до SQL/render. Метаданные graf-time-preferred/user/session передают только authenticated viewer. JS учитывает предпочтение до cookie/reload логики.
Каталог: Babel CLDR canonical zones + zoneinfo validation, русские города/страны и текущее UTC-смещение; native select с progressive поиском и предпросмотром, без собственной combobox библиотеки. Для конкретной даты смещение определяется по её моменту.
Native использует доверенный документ/существующую cookie reconciliation, хранит подтверждённое значение только в процессе с привязкой origin/user/session, сбрасывает при auth change. После холодного запуска до подтверждения аккаунта — устройство; отдельного протокола offline identity нет.
Constitution recheck PASS: auth semantics, custody deadlines, capture metadata и machine API не меняются. T006–T008 зависят от reviewer gate и issue sync, T009 закрывает расширение.
