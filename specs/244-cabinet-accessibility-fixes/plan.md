# Implementation Plan: Темы и доступность кабинета

**Branch**: `codex/244-cabinet-accessibility-fixes` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

**Input**: Пять подтверждённых дефектов визуального аудита.

## Summary

Проверить исправления цветов и приоритета темы из F240 на согласованной совместной ревизии. В F244 обеспечить прокрутку, видимый фокус и доступное имя окна загрузки, устранить сжатие и перекрытие фокуса основной области раскрытой панелью на узких экранах. Не менять серверные сценарии и не добавлять зависимости.

## Technical Context

**Language/Version**: CSS, HTML/Jinja, существующий JavaScript кабинета; Python 3.12 для тестов.

**Primary Dependencies**: Существующие Jinja, pytest, Node sandbox и Playwright CLI; новых зависимостей нет.

**Storage**: Существующее sessionStorage-предпочтение панели сохраняется без изменения формата. Серверных данных и миграций нет.

**Testing**: Контрактные/unit/integration проверки кабинета; локальный синтетический HTTP-стенд с реальными render functions и CSS/JS.

**Risk / Validation Lane**: high-risk-product — общие стили, доступность и пользовательские состояния. Полный Spec Kit, обязательный reviewer-owned UX checklist перед реализацией.

**Release Gate**: no deploy — запрос заканчивается PR; full CI, merge, release и production deploy не запрошены.

**Target Platform**: Обычный браузер и HTML встроенного кабинета; установленный WKWebView не объявляется проверенным по Chromium.

**Project Type**: Серверный веб-кабинет, общий для web/desktop.

**Performance Goals**: Не добавлять сетевых запросов, polling, зависимостей или обработчиков прокрутки.

**Constraints**: Палитра F240 и текущие контролы сохраняются, включая светлую панель в светлой теме; данные проверок синтетические; не расширять исправления до полного редизайна.

**Scale/Scope**: Пять дефектов, две поверхности, три пользовательские темы и две системные.

## Constitution Check

До проектирования: capture-first, visible controls, privacy, server-owned secrets, truthful deletion и AI boundaries не затронуты. Доступность, независимая реализация и синтетические доказательства обязательны.

После проектирования: новых внешних сервисов, данных, assets, зависимостей, legacy aliases и миграций нет. `Legacy Impact: untouched`. UX checklist проверен Codex по отдельному явному поручению владельца; это одобрение качества требований, не независимая приёмка кода. При реализации маркеры checklist не меняются.

## Validation Plan

1. Прочитать результаты проверки требований рецензентом; затем tasks → analyze → taskstoissues → implement. Сами эти стадии пока не выполнены.
2. До исправлений добавить минимальные регрессионные проверки; подтвердить, что они воспроизводят дефекты.
3. Выполнить [quickstart.md](quickstart.md): существующие pytest проверки и browser matrix, включая динамическую смену системной темы, отрицательные состояния загрузки и изменение размера.
4. Проверить diff по Ponytail: использовать CSS/native dialog и существующие helpers, не ослаблять accessibility.
5. Converge; feature fragment `changes/unreleased/F244.yaml`; проверка PR metadata и отсутствие секретов.
6. После локальной валидации получить требуемое проектом явное разрешение на implementation commit. Commit/push/PR, затем GitHub `governance-fast` на точном SHA. Локальный repository-wide CI — только отдельная диагностика/fallback по release-and-validation.md, full CI не запускать.

## Project Structure

Артефакты: `specs/244-cabinet-accessibility-fixes/` — spec, plan, research, data-model, UI contract, quickstart, checklist, tasks и metadata-only evidence.

Продуктовые точки изменения:

- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` — существующие `initCabinetRail`, `initManualUpload`, при необходимости узкий параметр существующего `trapModalFocus`; его прочие callers сохраняют текущую семантику.
- `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- `apps/server/tests/unit/test_cabinet_web_shell.py` — только затронутые assertions, если необходимы.

Повторно использовать существующий runtime fixture `specs/058-web-cabinet-htmx-shell/evidence/cabinet_runtime_check.py`. API upload, models, routes, сохранение профиля, billing и другие параллельные фичи не менять.

## Design Decisions

- Убрать фиксированные несовместимые пары foreground/background у перечисленных элементов, переиспользовать theme tokens. Проверить соседние hover/selected/loading/error и меню тёмной панели.
- Удалить локальное переопределение токенов тем через неограниченный prefers-color-scheme; общие root tokens остаются единственным источником темы. Перенести необходимые delete/selected цвета на токены, чтобы светлый режим также работал.
- Владение двумя предыдущими пунктами подтверждено F240/PR#6560; F244 их не реализует повторно. Получить проверенный финальный SHA F240, затем согласовать основу PR/совместную проверку. Текущий SHA `8eb1bb8078140d51ae910197a613ce0999a98ed9` не содержит ещё не закоммиченные исправления и не является их evidence.
- Native dialog: max-height с динамической высотой viewport и overflow auto; связать видимый h2 через aria-labelledby. Существующий `trapModalFocus` переносит фокус с `preventScroll: true`: для загрузки обеспечить видимый переход в обоих направлениях и при повторном открытии. Не добавлять второй focus trap/дублирующие roles и не менять поведение остальных диалогов без доказанной необходимости.
- Для узкой панели сохранить grid64+main, но CSS-only overlay отклонён как полное решение после браузерного эксперимента: он полностью закрывает focused search. В существующем `initCabinetRail` добавить минимальную защиту при focus в main и при переходе через narrow media query с уже установленным фокусом; временное скрытие не пишет sessionStorage. Явные toggle/Escape пишут как раньше. Возврат к >640 восстанавливает предпочтение. Не вводить новый layout controller, modal overlay или обработчик каждого resize.
- Результаты проверки требований и экспериментов: [evidence/checklist-review.md](evidence/checklist-review.md). Browser evidence является отрицательным контролем предложенных решений, а не доказательством готовой реализации. Итог всех пяти находок запрещено закрывать без точного F240 source SHA и повторной совместной проверки; отдельный F244 PR может быть только явно зависимым до этой проверки.
