# Implementation Plan: Страница итогов по интерфейсу Krisp

**Branch**: `codex/257-krisp-meeting-detail` | **Date**: 2026-09-08 | **Spec**: [spec.md](spec.md)

## Summary

Воспроизвести наблюдаемую композицию Krisp на общей серверной странице GRAF. Использовать существующие сохранение названия, шаблоны, генерацию, экспорт, доступ, источники и плеер. Пользователь исключил новые чат, редакторы, папки и задачи. Исследование сохранено без приватных данных в [reference-audit.md](reference-audit.md); подробная композиция, измерения, состояния и границы доказательств — в [design-handoff.md](design-handoff.md).

## Technical Context

**Language/Version**: Python >=3.13, Jinja, CSS, обычный JavaScript; существующий macOS WKWebView.
**Primary Dependencies**: существующие FastAPI/Jinja, без новых зависимостей.
**Storage**: существующие сущности, без миграций.
**Testing**: pytest и существующий JS/browser runtime; Computer Use для референса и GRAF Dev.
**Risk / Validation Lane**: high-risk-product / reference-fidelity: общая пользовательская страница с доступом, AI и приватным экспортом.
**Release Gate**: no deploy; отдельное одобрение коммита после проверки; штатный build/promote GRAF Dev только из чистого точного SHA. Governance-fast для PR; release-full только для выпуска.
**Target Platform**: браузеры, macOS GRAF Dev.
**Project Type**: серверный веб-кабинет и встроенный кабинет.
**Performance Goals**: оформление не вводит сетевые запросы до действия пользователя, таймеры или новые наблюдатели; копирование использует один существующий запрос экспорта.
**Constraints**: 390/768/1024/1440 CSS px, 200% zoom; WCAG 2.2 AA, русский интерфейс, существующая семантика безопасности.
**Scale/Scope**: одна страница и её существующие меню/диалоги; общая навигация и внутренняя панель плеера вне изменения.

## Constitution Check

До и после проектирования: независимая реализация, только наблюдаемый интерфейс; метаданные установки без декомпиляции; приватные данные не сохраняются. Запись, AI-маршрут, генерация, удаление и права не меняются. Reviewer-owned UX/security checklist и analyze с CRITICAL 0 / HIGH 0 обязательны до кода. Общая страница остаётся внутри #cabinet-main, чтобы отзыв доступа и обновление заменяли весь приватный интерфейс.

## Design

1. В `meeting_detail_content.html` вынести ссылку возврата и action-row в верхнюю строку внутри существующей sticky шапки; название и компактные метаданные в центрированную колонку.
2. Сохранить отдельный tablist с двумя вкладками. Picker формата — соседний контейнер, не потомок role=tab; рядом копирование текущей вкладки. Существующий контейнер data-summary-format-controls сохраняет данные, picker, refresh и pendingLabel.
3. Объяснение последствий формата поместить в раскрываемую/всплывающую область перед выбором, сохранив видимое сообщение при отсутствии итогов или недоступности. Refresh доступен рядом с форматом; не добавлять ещё один механизм генерации.
4. CSS ограничить страницей. Использовать подтверждённое DOM-измерение из contracts/ui.md и design-handoff.md: наружная колонка 674px, текст 664px с внутренним отступом 5px, название 22/32px, текст 16/28px, заголовки разделов 20/24px. Метаданные 12/16px, высота24px; вкладки14/20px, высота28px. Наблюдённые экранные координаты не становятся фиксированными CSS-позициями. Оценка масштаба82% отменена. T009 измеряет SC-003 по перечисленным в контракте опорным точкам; при отсутствии измерения нет PASS.
5. Протокол F239 и вторичные разделы сохраняют все данные. Для непрерывного документа раскрыть существующие дополнительные разделы по умолчанию; без потери возможности сворачивания. Источники менее заметны, но остаются доступными ссылками.
6. В initContentExport расширить существующий copy handler на кнопку в шапке, с requestExport('txt', selectedScope). Scope фиксируется при клике; разрешённые составы берутся из существующей формы. Статус и отказ видимы рядом с кнопкой. Перед clipboard проверять подключённость исходной формы и trigger, отсутствие replacement-active и доступность захваченного option. Один pending-gate общий для прямого копирования и диалога; finally восстанавливает только актуально разрешённые действия. Пары: outcomes→summary, recording→transcript; текущий select диалога не менять. Shared endpoints, CSRF, revision ids, no-store и recoverMeetingDetailFromResponse остаются общими.
7. activateDetailTab управляет доступностью группы формата и состоянием copy. После перехода на Transcript picker скрыт; назад — показан. Без JavaScript обе разрешённые панели видны и доступны по якорям; скачиваются только разрешённые текущие артефакты через существующие owner/shared download routes. Выбор формата и генерация требуют JavaScript, что объясняется видимым текстом; ссылка на личные форматы остаётся. Это скачивание артефакта, а не JSON-экспорт выбранного состава.
8. Существующее replacement-active скрытие расширить на перенесённые управляющие группы; не оставить кнопок старого содержимого поверх замены/отзыва доступа.

## Validation Plan

[quickstart.md](quickstart.md): focused contract/unit/integration, одна небольшая JS runtime проверка прямого копирования, synthetic UI reflow/focus и Computer Use в единственном GRAF Dev после одобренного коммита. Затем canonical fast, converge и review. Изменение production и release-full не заявляются выполненными.

## Project Structure

- `specs/257-krisp-meeting-detail/`: spec, reference-audit, plan, research, data-model, contracts/ui.md, quickstart, checklists, tasks, validation.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`: композиция.
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`: локальные правила страницы.
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`: повторное использование копирования и состояния вкладки.
- `apps/server/src/twobrain_rec_server/cabinet/rendering.py`: только недостающая проекция доступных метаданных/экспорта и показ дополнительных разделов.
- `apps/server/tests/contract/test_meeting_detail_reference_contract.py`: структурные и ограничительные проверки.
- `apps/server/tests/unit/test_meeting_detail_copy_runtime.py`: минимальная исполняемая проверка асинхронного копирования.
- `changes/unreleased/F257.yaml`: принадлежащий фиче changelog.

## Dependencies And Overlap

F181/F239/F253 — действующая основа. F256 отдельно меняет панель воспроизведения в другом worktree; не переносить и не переписывать её изменения. Прокрутка страницы и переход по источнику совместимы с существующим mount плеера. Исследование Krisp не требует изменений в его настройках доступа.

Граница владения и порядок проверки стыка с F256 зафиксированы в contracts/ui.md. Подготовка F256 ещё не является готовым контрактом новой панели; F257 начинает с существующего плеера, без ожидания будущих функций и без предположения о его высоте. Responsive-наблюдения R49/R50 служат опорой композиции; обнаруженное обрезание действия на390 исправляется по требованиям доступности GRAF.


## Дополнение 2026-09-09 — US2 / FR-020–024

**Lane**: active Spec Kit slice + high-risk reference-fidelity; bounded amendment. Уточнение запроса выполнено в spec. Constitution до/после проектирования: PASS — независимые собственные значки, метаданные наблюдений, неизменные доступ/CSRF/генерация/данные и обязательная доступность.

Повторно использовать `initSummaryFormats` и текущие данные форматов в `meeting_detail_content.html`, `cabinet.js`, `cabinet.css`. Одна внешняя `data-summary-format-popover` без modal, внутри один `data-summary-format-listbox` с role=listbox и быстрыми строками. Дополнительные встроенные строки отмечены `data-summary-format-extra`, личные находятся в группе `data-summary-personal-options`; в быстром режиме они скрыты. «Все форматы», «Назад» и существующая ссылка управления находятся вне listbox. Одна `data-summary-format-description` показывает назначение фокуса/наведения и связывается через aria-describedby; статические длинные описания строк убрать.

Сохранить существующий submit и ограничения current/busy/disabled. Ввод управляет только видимыми option; закрытие, возврат фокуса и смену режима обслуживает текущий picker. CSS ограничивает ширину/высоту viewport, переносит названия и прокручивает список; не добавлять библиотеку, поиск, новые сетевые запросы или отдельную модалку.

Порядок: T012 исполняемая проверка → T013 реализация → T014 браузерная проверка → T015 приёмка GRAF Dev и closeout. До кода reviewer-owned `checklists/format-picker-ux.md`, analyze и issue sync. До одобрения коммита доступны scoped tests и synthetic browser. Установка единственного GRAF Dev, exact-SHA governance-fast и завершение tracker требуют существующих отдельных гейтов; старое одобрение коммита T009 не переносится на дополнение.

Проверки T012: использовать существующий browser runner в `apps/server/tests/browser/summary-format-picker.test.cjs` и pytest wrapper `apps/server/tests/unit/test_summary_format_picker_browser.py`, обновить существующие contract suites. Отдельный дублирующий runtime в static-assets suite не вводится.
