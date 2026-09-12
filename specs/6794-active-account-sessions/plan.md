# Implementation Plan: Актуальные входы
**Branch**: `codex/6794-active-account-sessions` | **Date**: 2026-09-11 | **Spec**: [spec.md](spec.md)
## Summary
Убрать историю из представления, уточнить область списка и согласовать действия завершения во всём существующем пути.
## Technical Context
Python/FastAPI/Jinja, существующий cabinet.css, pytest и имеющиеся браузерные инструменты. Новых зависимостей, схем и API нет. Источник — origin/master `ad71f2ce4db68d846d7c333213961c5f5f7d5e89`.
## Constitution Check
High-risk product area (auth/sessions/UX), полный Spec Kit; clarify завершён в spec.md. CSRF, tenant/user scope, текущий вход, доступ через устройство и сроки не меняются. Данные исследований и тестов синтетические. Правила capture/retention не меняются. Рецензент проверяет checklist до реализации. После локальной проверки — governance-fast на точном SHA PR, перед выпуском — release-full; коммит и выпуск требуют отдельного разрешения. Legacy Impact: remove (история в интерфейсе), хранимые данные untouched; legacy_new=0.
## Project Structure
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`: основной список, подсказки, подписи кнопок подтверждения.
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`: только формулировки подтверждений; `cabinet/rendering.py` — согласованная формулировка ошибки и повторного входа.
- `apps/server/tests/contract/test_account_routes.py`: смешанные состояния, действие/подтверждение, пустота и ошибка.
- `apps/server/tests/integration/test_account_lifecycle.py`: существующая проверка реального подтверждения/отмены/завершения.
- `changes/unreleased/F6794.yaml`: русский фрагмент изменений.
## Design
Повторно использовать active_sessions, can_revoke, сортировку и native details/forms. Никакой новой модели устройств, геолокации или фонового опроса. Минимальное улучшение существующего initSettingsConfirmations: отмена/Escape и возврат фокуса. Удалить session_history property лишь если больше нет действительных потребителей; иначе не расширять работу. CSS заменяет карточки единым списком; native details раскрывается основной строкой. Подтверждение переносится внутрь списка по совпадению action, с fallback под списком для исчезнувшей цели. Серверные POST и CSRF сохраняются.
## Validation
[quickstart.md](quickstart.md): focused tests, синтетические браузерные состояния, 390/1280 px, темы, клавиатура и формы без JS. Для нативного ручного запуска разрешён только GRAF Dev по local-development.md; браузерная embedded-разметка не считается installed-native proof.
## Phases
1. Требования, reviewer checklist, tasks/analyze, issue sync.
2. US1: регрессия скрытых недействующих входов, основной список.
3. US2: согласованное завершение и сохранённые защитные проверки.
4. Проверка, converge, фрагмент изменений и честный отчёт о границах выпуска.

## Уточнение после одобрения прототипа
T005: тесты и компактная реализация в settings_account_content.html, cabinet.css, cabinet.js; update tests/contract/test_account_routes.py. T004 повторяет проверки после T005. Первый POST сохраняет серверную проверку пользователя и цели; клиентский код только отменяет показ, не выполняет отзыв. Поля confirm=1 остаются только в форме подтверждения.
