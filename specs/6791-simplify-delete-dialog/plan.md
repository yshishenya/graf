# Implementation Plan: Простое подтверждение удаления

**Branch**: `codex/6791-simplify-delete-dialog` | **Date**: 2026-09-09 | **Spec**: [spec.md](spec.md)

## Summary

Сократить существующий HTML подтверждения: один короткий абзац, две кнопки, без технического перечня и неработающей до удаления ссылки.

## Technical Context

- Language/Version: Python 3.13+, существующий серверный HTML.
- Primary Dependencies: существующие FastAPI/Jinja; новых зависимостей нет.
- Storage: без изменений.
- Testing: pytest, ruff; действующие контракты доступности и отчёта.
- Risk / Validation Lane: high-risk-feature (deletion UX), полный Spec Kit с clarify, независимой проверкой требований и analyze.
- Release Gate: no deploy в этой задаче; перед PR governance-fast на точном SHA, перед выпуском release-full на замороженном SHA. Продакшен только после отдельной авторизации и cd-remote.sh --dry-run.
- Target Platform: браузерный кабинет и встроенный кабинет GRAF macOS.
- Performance Goals: без новых запросов, обработчиков, зависимостей; уменьшение HTML.
- Constraints: сохранить защиту формы, границу подтверждения, доступность и правдивость удаления.
- Scope: общий renderer, параметр обработчика фокуса, разрешение существующего адреса формы в native route policy, целевые контракты и проверки, changelog fragment.

## Constitution Check

До и после проектирования: PASS. §IV/Deletion Truth: «из GRAF»; по прямому уточнению пользователя оговорка отсутствует в окне, подробности остаются в отчёте. Права, CSRF, lifecycle, локальная очистка, обработка ошибок и retention не меняются. Доступность обеспечивается существующими dialog/JS/CSS. Capture, AI и инфраструктура не меняются. Новых данных и сторонних материалов нет.
Clarify: выполнен 2026-09-09, блокирующих вопросов нет. Пользователь явно просит минимальный текст.

## Validation Plan

Сначала обновить контракт и добавить параметризованный тест HTML для web/embedded и unavailable. Затем изменить renderer. Выполнить тесты короткого окна, shell, accessibility и deletion report, lint затронутых Python файлов, git diff --check. Проверки POST/CSRF выполняются, если доступна штатная тестовая БД; пропуски явно записать. Проверка установленного приложения требует чистого SHA и dev-harness; без коммита не выдавать её за пройденную. Полный CI не запускать для локальной итерации.

## Project Structure

- `apps/server/src/twobrain_rec_server/cabinet/review_policy_rendering.py`: только _render_delete_confirmation.
- `apps/server/tests/contract/test_recording_governance_ui_contract.py`: короткий текст вместо технического списка.
- `apps/server/tests/unit/test_cabinet_web_shell.py`: проверка фактического HTML обоих кабинетов и скрытого состояния.
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`: cycleAll для окна удаления.
- `apps/server/tests/browser/meeting-delete-focus.test.cjs`: Tab/Shift-Tab на реальном обработчике с моделью DOM.
- `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`: разрешить существующий /desktop/meetings/{id}/deletion-requests как действие страницы встречи на доверенном origin.
- `apps/macos/Shared/Tests/DesktopCabinetNavigationRequestPolicyTests.swift`: разрешённый POST без повторной отправки, запрет соседних и внешних адресов.
- `changes/unreleased/F6791.yaml`: русский changelog.
- Документы в этой папке: spec, plan, research, data-model, contracts, quickstart, checklists, tasks, validation.

## Implementation Strategy

Ponytail: используется существующий renderer; удаляются лишние абзацы, ссылка и её вычисление. CSS и сервис удаления сохраняются. Для FR-005 обработчик окна использует существующий trapModalFocus с cycleAll: true: в установленном WebKit обычный Tab пропускал кнопку подтверждения и уходил в native-панель. Спецификация и независимый review не заменяют проверку работающего приложения перед выпуском.

Установленная приёмка выявила блокировку формы удаления native route policy до обращения к серверу. Для FR-004/005 разрешается только существующий адрес deletion-requests; origin, безопасный ID, точное число сегментов и запреты остальных адресов сохраняются. HTTP-метод и тело POST проходят без replay; серверные права/CSRF не меняются. Нового API или процесса удаления нет.
