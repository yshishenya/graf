# Tasks: Переименование встречи

Feature: 253. Branch: `codex/253-meeting-rename`.
Source: [spec.md](spec.md), [plan.md](plan.md), [quickstart.md](quickstart.md).
Lane: high-risk-product. Umbrella: https://github.com/yshishenya/graf/issues/6684.

## Phase 1 — Проверка требований

- [X] T001 Получить рецензирование `specs/253-meeting-rename/checklists/ux.md` и `specs/253-meeting-rename/checklists/security.md`; зафиксировать решение и устранить замечания в spec/plan до продуктовых правок.

## Phase 2 — Серверные гарантии (US1/US2)

Независимая проверка: реальное сохранение и конкурентные транзакции PostgreSQL.

- [X] T002 [US1] Добавить сценарии сохранения, доступа, CSRF, валидации, версии, повтора и календаря/удаления в `apps/server/tests/integration/test_cabinet_meeting_rename.py`; регрессию stale MeetingRecord и исходного ingest retry с/без fingerprint в существующие ingest tests. Покрытие FR-001, FR-004–010, SC-002–003.
- [X] T003 [US1] Реализовать сервис `apps/server/src/twobrain_rec_server/cabinet/meeting_titles.py`, формы `cabinet/web_routes/titles.py`, регистрацию `cabinet/web.py`, версию в `api/schemas.py`/`cabinet/view_models.py`; убрать перезапись имени из existing-ветки `ingest/store.py`, сохранить legacy retry в `ingest/meetings.py`; сохранить полное пользовательское имя в `cabinet/exports.py`. Покрытие FR-001, FR-004–010.

## Phase 3 — Простое редактирование (US1/US2)

Независимая проверка: клик → ввод → Enter/blur, Esc; свежая карточка/список;
без постоянных дополнительных кнопок и без остановки воспроизведения.

- [X] T004 [US1] Добавить одно поле в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`, контекст в `cabinet/rendering.py`, стили в `cabinet/static/cabinet/cabinet.css` и сохранение Enter/blur, Esc/IME, ошибки без подписи при успехе и обновление заголовка в `cabinet/static/cabinet/cabinet.js`. Покрытие FR-002–005, FR-008–009, FR-011, FR-013, SC-001, SC-004.
- [X] T005 [US2] В `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` завершить ошибки/тайм-аут/явный повтор конфликта, сохранение черновика, ожидание перед htmx-навигацией, beforeunload, защиту от позднего ответа и свежесть списка; дополнить сценарии браузерной проверки в `specs/253-meeting-rename/quickstart.md`. Покрытие FR-006–008, FR-012, SC-002, SC-004.

## Phase 4 — Проверка и завершение

- [X] T006 Проверить матрицу браузера, JS-off, настоящего WKWebView, тем, размеров, доступности и воспроизведения по `specs/253-meeting-rename/quickstart.md`; записать синтетические результаты и ограничения в `specs/253-meeting-rename/validation.md`. Покрытие FR-001–013, SC-001–005.
- [X] T007 Выполнить speckit-converge и `infra/scripts/ci-local.sh --fast`, добавить `changes/unreleased/F253.yaml`, сверить задачи/issues и точный diff; сохранить доказательства в `specs/253-meeting-rename/validation.md`. Коммит/PR/выпуск не считать выполненными без их отдельных gates.

## Dependencies and Strategy

T001 → T002 → T003 → T004 → T005 → T006 → T007.
Параллельных продуктовых правок не требуется: общий сервер и общий JS.
После T001 отдельно можно готовить синтетическую матрицу проверок, но T006
принимается только на итоговом коде. US1 предоставляет основной путь; US2
обязательна до завершения, поскольку пользователь требует надёжного сохранения.

## Issue mapping

- T001: https://github.com/yshishenya/graf/issues/6693
- T002: https://github.com/yshishenya/graf/issues/6694
- T003: https://github.com/yshishenya/graf/issues/6695
- T004: https://github.com/yshishenya/graf/issues/6696
- T005: https://github.com/yshishenya/graf/issues/6697
- T006: https://github.com/yshishenya/graf/issues/6698
- T007: https://github.com/yshishenya/graf/issues/6699

T001–T007 выполнены в локальном объёме; доказательства и ограничения проверки перечислены в validation.md. Umbrella остаётся открытым до отдельного завершения PR/выпуска.
