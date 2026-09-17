# Implementation Plan: Переименование встречи

**Branch**: `codex/253-meeting-rename` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

## Summary

Общий редактор в заголовке браузерной и встроенной карточки. Сервер сохраняет
название с проверкой доступа и версии; загрузка и календарь не затирают его.
Требования приняты независимым рецензентом; реализация и проверки отражены в validation.md.

## Technical Context

- Python >=3.13, FastAPI, SQLAlchemy AsyncSession, PostgreSQL.
- Jinja2, существующий cabinet.js и cabinet.css, htmx, WKWebView.
- Новые зависимости и таблицы не нужны.
- Risk / Validation Lane: **high-risk-product** — пользовательский сценарий,
  reference fidelity, общие данные, авторизация и гонки записи.
- Release Gate: **no deploy**. После реализации focused + fast; коммит/PR и
  production отдельно. Авторитетный release-full — только точный кандидат.
- Один объект на операцию, один короткий lock; отсутствие внешних вызовов.
- UI pending <=100 мс, клиентский тайм-аут 15 с. Плеер не перезапускается.

## Constitution Check

До исследования: область ограничена названием, захват/LLM/media не меняются.
После проектирования: CSRF, авторство, tenant isolation, deletion fence,
метаданные без приватного контента, независимый код и доступность сохранены.
Проверка требований UX/security пройдена: 7/7 и 5/5, см. requirements-review.md.
Legacy Impact: существующая совместимость старых записей без fingerprint
сохраняется; новые legacy aliases/flags не добавляются. Историческое имя
не восстанавливается выдуманным fingerprint. Изменение fallback ограничено
сравнением уже вручную изменённых title/title_source; прочая идентичность строга.

## Implementation

1. `cabinet/meeting_titles.py`: версия имени, валидация, транзакция сохранения.
   Переиспользовать `processing/fences.py::lock_meeting_fence` и
   `meeting_is_deleted_or_deleting`; проверить автора после блокировки.
   Для timestamp брать max(now UTC, previous + 1 microsecond), чтобы версия
   различала A → B → A даже при одинаковом времени часов.
2. `ingest/store.py::persist_meeting`: existing-ветка больше не пишет title,
   title_source, title_updated_at из устаревшего MeetingRecord; создание
   сохраняет эти поля. Проверены все 9 production callers — они сохраняют
   состояние загрузки, а календарь уже пишет заблокированную ORM Meeting.
3. `ingest/meetings.py`: при отсутствии исходного fingerprint после ручного
   переименования не сравнивать изменяемые title/title_source с исходным
   запросом; сохранить duration/time/revision и прочие проверки. Не заменять
   существующий fingerprint и не добавлять новую схему совместимости.
4. `cabinet/web_routes/titles.py`, регистрация в `cabinet/web.py`: два form POST
   пути, JSON при Accept, HTML/303 без JS. Черновик в HTML сохранять только при исправимой ошибке и действующем
   доступе; 401/403/404/удаление используют безопасную штатную страницу.
5. `api/schemas.py` + `cabinet/view_models.py`: минимальное поле версии и
   доступности редактора только в авторизованной проекции; общий read model
   остаётся источником title. `rendering.py` передаёт форму/версию/CSRF.
6. `meeting_detail_content.html`: встроенная форма с настоящими label/input/
   form без постоянных кнопок. `cabinet.js`: init из
   initCabinet после htmx swap; очистка listeners через существующий pattern;
   Enter/blur с одной отправкой, Esc без blur-save, IME, pending/error/conflict,
   beforeunload/htmx navigation,
   защита от позднего ответа, фоновая перерисовка не уничтожает черновик.
7. Список не получает новых элементов. После возврата из карточки список
   загружается с актуальными данными и прежними фильтрами, без старого htmx cache.
8. В `cabinet/exports.py` использовать полное допустимое пользовательское
   имя в заголовке нового документа (сейчас общий fallback обрезает до 160).
   Ограничение имени файла не менять.
9. CSS ограничен редактором; темы берутся из существующих переменных.
   Не переписывать остальные компоненты кабинета.

## Validation Plan

[quickstart.md](quickstart.md) задаёт матрицу; обязательны реальные PostgreSQL
гонки и проверка браузерного поведения. Тесты используют существующие fixtures.
Критические случаи: stale ingest snapshot, два автора редактирования одного
владельца, календарь в обоих порядках, deletion, права, CSRF, потерянный ответ,
Unicode и путь/запрещённые метаданные, плеер, htmx, экспорт, JS-off.

Продуктовая реализация начинается только после T001. Затем tests → code →
focused → browser/WKWebView → converge → fast. Блокирующие результаты нельзя
переименовать в необязательные ограничения. Все release gates остаются отдельно.

## Project Structure

Документы: spec.md, research.md, data-model.md, contracts/rename.md,
quickstart.md, checklists/{requirements,ux,security}.md, tasks.md, validation.md.
Продуктовые пути выше относительно `apps/server/src/twobrain_rec_server/`.
Проверки: `apps/server/tests/integration/test_cabinet_meeting_rename.py`,
существующие calendar/ingest tests и синтетический UI harness при необходимости.
Фрагмент изменений: `changes/unreleased/F253.yaml` после реализации.

## Complexity Tracking

Один сервис и один редактор; нет очереди переименований, нового состояния
Swift, новых таблиц, библиотек, брокеров и фоновой синхронизации названий.
Неопределённый ответ разрешается безопасным повтором с версией.
