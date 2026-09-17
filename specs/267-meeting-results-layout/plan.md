# Implementation Plan: Спокойная страница итогов встречи

**Branch**: 267-meeting-results-layout | **Date**: 2026-09-15 | **Spec**: [spec.md](spec.md)

## Summary

Одна шапка и порядок «Главное → решения → задачи → вопросы → темы → примечания». HTML использует существующий полный протокол, нативные раскрытия и текущие стили. Содержательный тип встречи генерируется тем же этапом модели; происхождение новой семантики сохраняется через существующую версию генератора.

## Technical Context

- Language/Version: Python 3.13, серверный Jinja/HTML/CSS, существующий JavaScript.
- Dependencies: FastAPI, Pydantic, SQLAlchemy, Langfuse 4.15.1, pytest, Playwright 1.63.0 из lockfiles.
- Storage: существующий MeetingOutcomeSet.protocol_json и generator_version; миграций нет.
- Risk / Validation Lane: high-risk-product; уточнение AI-инструкции и общая пользовательская поверхность.
- Release Gate: локальная реализация/проверка. До merge нужны governance-fast, macos-pr, pr-metadata на точном SHA. Production-промпт/деплой и implementation commit требуют отдельного разрешения.
- Platform: браузер и встроенный кабинет macOS; сервер Linux. Автотесты могут выполняться в worktree, ручная установленная проверка — только GRAF Dev через harness.
- Performance: без новых запросов БД, сетевых вызовов, этапов модели или зависимостей при чтении.
- Scope: исходная инструкция, классификация результата при сохранении, HTML detail/share, CSS и проверочные сценарии.

## Constitution Check

До исследования: PASS. Пользователь утвердил редакционное уточнение исходного промпта; один модельный этап, точный снимок, структура/источники, access/deletion fences сохраняются. Новых внешних направлений и данных нет.
После проектирования: PASS. Используем существующий response-format descriptor и generator_version; сами JSON Schema и schema_version неизменны. Исторические ответы/слова не переписываются. Экспорт остаётся полным. Новых активов, управления записью или правами нет.

## Design

1. В существующем response_format.json_schema.name нового набора инструкций использовать graf_meeting_protocol_about_v1; схема прежняя. В функции конфигурации оставить совместимый прежний default для старых фикстур/потребителей, новый descriptor задаёт desired_prompts вместе с редакционным текстом. sync_prompts сохраняет desired response_format при объединении с выбранной моделью и разрешёнными текущими параметрами; не пересобирает старый descriptor по умолчанию. Редакционные уточнения meeting_type и executive_summary добавляются в существующий GRAF transport adapter; исходное ядро meeting_minutes.md сохраняется.
2. При _store_candidate_protocol прочитать integrity-checked pinned snapshot; только точный новый descriptor сохраняет generator_version meeting-protocol-v1-about-v1, остальные — прежнюю версию. Не менять глобальную AI_GENERATOR_VERSION, участвующую в попытках/retry.
3. Из существующей provenance.generator_version вычислить аргумент представления. Не добавлять API/DB/протокольные поля. Shared HTML получает его аргументом из уже загруженного outcome.
4. Шапка detail использует актуальное название и существующий user_time_element. Описание и участники находятся в ней; при переключении/замене итогов обновляются существующим механизмом замены страницы. Для shared HTML — аналогичная разрешённая шапка.
5. _render_full_protocol строит интерактивный порядок напрямую. protocol_blocks/protocol_lines остаются экспортным представлением без изменений. Новые <details> закрыты; итог темы первый; задачи таблицей, отсутствие краткой строкой.
6. _render_outcome_item переиспользует source controls: одна видимая ссылка, остальные в вертикальном раскрытии. Источники следуют сразу за текстом перед дополнительными сведениями; CSS размещает текст и источники в одной строке с естественным переносом. Каждый тезис остаётся отдельным блочным абзацем. Сохраняются source revision guard и JS-навигация/возврат.
7. CSS удаляет устаревшие правила шапки полного протокола и использует существующие токены. Узкая таблица сохраняет семантику и переносы. Изменения не создают новый редактор/экран.

## Validation Plan

- Требования: checklists/ux.md и infra.md проверяет отдельный reviewer до tasks; автор реализации не отмечает их сам.
- Существующая база: 38 protocol/render/export unit tests PASS до изменения.
- Focused tests: протокол/публикация и replay, HTML title/time/legacy/new, shared scope, источники/экспорт и prompt config.
- Browser: реальный render_meeting_detail_page на синтетической фикстуре; 320/390/768/1024/1440, light/dark, embedded/non-embedded, 200% text, клавиатура, источник/возврат, пустые/длинные данные, screenshots вне git.
- Содержательное чтение: решения отличимы от предложений, задачи понятны без расшифровки, итог темы доступен одним раскрытием.
- Ruff, JS syntax, git diff --check. Никаких заявлений о живой генерации/установленном Dev без фактической проверки.
- GRAF Dev status: активен другой feature 6793, SHA f6effc37ac7f436f7cd5b164ef3d586af87d29c1; пока не меняется. Promotion требует чистого авторизованного коммита по local-development.md.

## Project Structure

- apps/server/src/twobrain_rec_server/outcomes/{models.py,prompts.py,ai_service.py}
- apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py
- apps/server/src/twobrain_rec_server/cabinet/{rendering.py,meeting_protocol.py}
- apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/{meeting_detail_content.html,shared_meeting_summary_content.html}
- apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
- apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py
- apps/server/src/twobrain_rec_server/api/cabinet.py
- apps/server/tests/unit/test_meeting_protocol_rendering.py and related existing generation tests
- apps/server/tests/browser/meeting-results.test.cjs
- apps/server/tests/fixtures/meeting_results.py
- changes/unreleased/F267.yaml
- Feature docs: research.md, data-model.md, contracts/presentation.md, quickstart.md, checklists/, tasks.md.

## Complexity Tracking

Нарушений нет. Никаких новых библиотек, таблиц, пользовательских полей или фоновый перерасчёт истории.
