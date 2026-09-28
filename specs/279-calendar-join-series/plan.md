# Implementation Plan: F279 — подключение и серии календаря

**Branch**: `codex/279-calendar-join-series` | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

**Input**: `specs/279-calendar-join-series/spec.md`.
**Status**: локальная реализация и автоматические проверки выполнены; нативная приёмка по T008 остаётся открытой.

## Summary

Исправить переход «Подключиться» через авторизованное разрешение цели и native-действие без навигации страницы GRAF. Представлять календарную серию одной карточкой в обзоре с ближайшим повтором и раскрываемой историей; дневное расписание, напоминания и записи сохраняют отдельные события.

Поведение: [design-proposal.md](design-proposal.md). Проверенные источники, обратный анализ Krisp и принятые решения: [research.md](research.md). Необязательное предпочтение пользователя не считается полученным ответом: основной вариант выбран как явное рабочее допущение в clarify.

## Technical Context

**Language/Version**: существующие Python/FastAPI/Pydantic/SQLAlchemy, Swift/SwiftUI/AppKit/WebKit, JavaScript/Jinja. Версии runtime/dependencies фиксируются существующими lock-файлами, здесь не обновляются.

**Primary Dependencies**: действующие календарные provider adapters, `DesktopUploadClient`, `WKScriptMessageHandler`, `NSWorkspace`, текущий сервис синхронизации.

**Storage**: существующий PostgreSQL и календарные snapshots/context links. Новая самостоятельно синхронизируемая таблица серии не нужна для первой итерации.

**Testing**: pytest unit/contract/integration, Swift tests, браузерные проверки шаблонов и native-проверка только GRAF Dev.

**Risk / Validation Lane**: high-risk product area: calendar data/access, shared API, native navigation boundary, reference-fidelity UX. Полная последовательность Spec Kit обязательна до кода.

**Release Gate**: сейчас no deploy — локальная реализация и проверка. После реализации required exact-SHA PR checks; release-full и dry-run/явное разрешение на production нужны отдельному релизу.

**Target Platform**: GRAF macOS и браузерный кабинет; существующие клиенты должны продолжать получать прежний список экземпляров. Windows-native parity не заявляется этим этапом.

**Project Type**: серверное приложение + native macOS-клиент.

**Performance Goals**: индикация действия ≤200 мс, локальное раскрытие уже загруженной серии p95 ≤500 мс; ограниченная пагинация истории до 50 строк на запрос и отсутствие N+1 запросов к записям. Внешний запуск/сеть измеряются отдельно.

**Constraints**: без передачи GRAF auth наружу, без логирования полного meeting URL, без автозаписи из join, без угадывания серии по названию/ссылке, без неограниченного раскрытия RRULE и без расширения retention.

**Scale/Scope**: существующие лимиты выбранных источников/календарей сохраняются. Страницы карточек/дат ограничены; одна частая серия не вытесняет остальные через преждевременный LIMIT экземпляров.

## Constitution Check

Проверка до исследования и после проектирования:

| Граница | Проектное решение | Результат |
|---|---|---|
| Capture-first / visible controls | Join не включает запись; текущие Start/Stop и три состояния автозаписи сохранены | Соответствует проекту |
| Credentials / ownership | Сервер сам разрешает цель по UUID; внешнее приложение не получает auth GRAF | Соответствует проекту |
| Data lifecycle | Серия — проекция существующих данных; источник/записи сохраняют текущий срок хранения и права | Соответствует проекту |
| Reference / provenance | UI и доступные клиентские признаки изучены по запросу; исходники и ресурсы Krisp не переносятся, закрытый код не объявляется известным | Соответствует проекту; независимый reviewer проверит происхождение реализации |
| Spec Kit | specify/clarify/research/plan выполнены; checklist/tasks/analyze/issues/review выполнены до реализации | Допуск по требованиям подтверждён |
| App continuity | Native-приёмка только GRAF Dev через штатный dev-harness | Обязательное условие дальнейшей проверки |


## Architecture and implementation order

1. **Фикстуры и контракты**. Сначала синтетическая матрица владельцев/серий/исключений/URL, затем типизированный контракт цели подключения и серии. Отдельно проверить существующие повторения и переносы, чтобы не переписать исправный provider ingestion.
2. **Join resolver**. Общая server-функция для текущего `/open` и нового `/join-target`; собственник, workspace, источник/выбор, состояние события, расшифровка и проверка URL. JSON не перенаправляет наружу.
3. **Native join**. Узкий мост принимает только UUID; текущий авторизованный HTTP-клиент; единая операция opener с защитой от повторных нажатий и устаревших ответов. Отдельные state/error около кнопки.
4. **Приложения**. Телемост, Zoom и Teams — кандидаты первой матрицы прямого запуска, Google Meet — браузерный путь; остальные распознанные HTTPS-провайдеры — безопасный browser fallback. Не объявлять кандидата поддержанным без проверки документированного механизма и GRAF Dev. Не добавлять непроверенные custom schemes. Для кандидата без подтверждённого direct-app сохранить явный незакрытый acceptance пункт, а не считать браузер эквивалентом требования.
5. **Серии**. Ввести версионированную identity с внешним календарём; сохранить отдельные snapshots и контексты. Группировать до LIMIT карточек, после owner/privacy фильтров. Текущий occurrence API сохраняет прежнюю семантику.
6. **История**. Добавить самостоятельный ограниченный запрос дат/доступных результатов серии и UI раскрытия. История не запрашивает неограниченное прошлое у провайдера и не показывает скрытые записи в счётчиках.
7. **Совместимость**. Версионировать новый ключ вместо молчаливой замены старого хеша. Старые контексты связывать только при однозначных имеющихся доказательствах; неподтверждённые сохраняются отдельно.
8. **Приёмка и closeout**. Все сценарии quickstart, независимое reviewer-owned UX/security checklist review, analyze до кода, converge после реализации, owned changelog fragment, exact-SHA PR evidence. Commit только с отдельным разрешением пользователя.

## Validation Plan

[quickstart.md](quickstart.md) разделяет проверки исследования, будущие unit/integration проверки и сквозную приёмку. Результаты серверных, Swift и браузерных проверок записаны в validation.md. Они не заменяют проверку установленного GRAF Dev и фактического открытия приложений.

Неизвестное поведение Krisp отмечено в research; приёмка GRAF основывается на явных собственных требованиях, а не на неподтверждённых утверждениях о референсе.

## Project Structure

Документация: `spec.md`, `research.md`, `design-proposal.md`, `plan.md`, `data-model.md`, `contracts/calendar.md`, `quickstart.md`, `validation.md`, `checklists/requirements.md` в текущем каталоге.

Основные пути:

- `apps/server/src/twobrain_rec_server/api/calendar.py`, `api/schemas.py`.
- `apps/server/src/twobrain_rec_server/calendar/{service,matching,normalize,sync,conference_links,lifecycle}.py`.
- `apps/server/src/twobrain_rec_server/cabinet/{view_models,rendering,queries}.py` и `cabinet/static/cabinet/`.
- `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`, новый узкий `EmbeddedCabinetCalendarJoinBridge.swift`.
- `apps/macos/RecApp/Sources/Calendar/` — единый сервис открытия и существующие меню/напоминания.
- `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`.
- `apps/macos/Shared/Sources/Models/CalendarContextModels.swift` — только совместимые дополнения, где необходимо.
- Соответствующие `apps/server/tests/{unit,contract,integration}` и macOS tests.

**Structure Decision**: расширить существующие границы календаря и клиента; не создавать второй механизм синхронизации или общий обход политики WebView.

## Complexity Tracking

Новые постоянные сущности серии не обязательны. Возможные индексы/версионированный ключ должны быть доказаны запросами и стратегией совместимости до миграции. Исключений для безопасности, доступа и записи нет.

Уточнение SC-002 для обычного браузера: initial GET resolver сопровождается read-only POST с существующим session-bound CSRF. Перед внешним переходом клиент сравнивает случайный неавторизующий marker cookie, меняющийся в существующих auth-cookie issuer/clear путях. Это отмена устаревшего действия между вкладками, а не новый механизм входа; HttpOnly bearer и server ACL сохранены. Обычное продление не меняет marker. Host-policy проверяется общим корпусом Python/Swift с нормализацией формы адреса перед фильтром глобальности.
