# Implementation Plan: Понятная оплата

**Branch**: `codex/280-payment-clarity` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)
**Input**: `specs/280-payment-clarity/spec.md`

## Summary

Упростить существующий кабинет: один главный шаг, полная сумма и условия на виду, второстепенные расчеты по раскрытию. Исправить обнаруженные препятствия и недостоверные состояния. Сохранить финансовую модель F278, существующие шаблоны и компоненты, цены, отдельные согласия и запрет повторных платежей.

## Technical Context

- Language/Version: существующие Python 3.13+ и Swift 6; Jinja2/HTML/CSS и небольшой существующий JavaScript.
- Primary Dependencies: FastAPI, SQLAlchemy, Jinja2, WKWebView; новых зависимостей нет.
- Storage: существующий PostgreSQL; без миграций и изменения денежных вычислений.
- Testing: существующие pytest, Playwright (Node), Swift Testing/XCTest.
- Risk / Validation Lane: `high-risk-product`, поскольку денежные решения, состояния и защищенная навигация macOS.
- Release Gate: коммит реализации только после локальной проверки и одобрения владельца; затем точные SHA checks `governance-fast`, `macos-pr`, `pr-metadata`. Выпуск отдельно: frozen `release-full`, dry-run, разрешение; F278 financial gates сохраняются.
- Target Platform: веб 320/360/768/1280 px, light/dark, 200%; macOS embedded, только GRAF Dev через harness.
- Performance Goals: не добавлять внешних запросов/тяжелых библиотек/новых polling loops; локальные раскрытия мгновенны, путь не длиннее исходного.
- Constraints: не менять provider, idempotency, authority, catalog, receipt/refund, privacy, analytics; синтетические данные в проверках.
- Scale/Scope: 12 платежных шаблонов и приглашения, связанные модели представления, узкая native route policy, тексты JS storage и целевые проверки.

## Constitution Check

До исследования: PASS — цель соответствует §II (явное согласие), §III (ограничение данных), §VI (полный Spec Kit), §VII (существующий стиль/собственный код). Capture и AI не меняются.
После проектирования: PASS по тем же основаниям. Никаких новых сторонних ресурсов/шрифтов/изображений, источники — исследование поведения. Проверка reviewer-owned checklist до кода обязательна. Успешные локальные тесты не заменяют внешнее финансовое подтверждение, людей или установленный Dev.

## Phase 0 — Research

Исследование: [research.md](research.md), исходная карта и замечания [audit.md](audit.md), независимая оценка [ux-audit.md](ux-audit.md). Источники прочитаны и сохраняются с применимостью/ограничениями; выводы проверены по реальным исходникам. Гипотеза опровергается, если скрытие текста лишает человека важных условий: такие сведения остаются на виду.

## Phase 1 — Design

[contracts/payment-journey.md](contracts/payment-journey.md) определяет экраны и состояния. [data-model.md](data-model.md) фиксирует только представление существующих данных. Новую машину платежей и слой компонентов не создавать.

Исправления recovery принадлежат существующему `cabinet/web_routes/billing.py`: ссылка invoice→status, сохранение cycle, ранняя понятная проверка verified receipt contact с существующим путем account. Выявленная потеря контекста требует переноса узко проверенного `next` через существующие settings/email/merge формы и переходы: `auth/redirects.py`, `cabinet/web_routes/settings.py`, `auth_email_flow.py`, `account_merge.py`, `cabinet/rendering.py`, `cabinet/auth_rendering.py`, два account templates и auth `email_code.html`/`login.html` для явного возврата на каждом шаге. Это только навигация; правила доказательства владения почтой, сессий, CSRF и объединения не меняются, состояния refused/service_gap/renewal blockers. Новые backend fields только там, где шаблон не может правдиво использовать существующие данные. Финансовые обработчики не переписывать.

Нативная политика разрешает ровно четыре существующих POST: storage preview, cancel-selection, subscription early-preview и purchases confirm; остальные неизвестные пути запрещены. Контроль method/origin и внешний provider handoff сохраняются.

## Validation Plan

[quickstart.md](quickstart.md): целевые серверные/браузерные/native тесты; синтетическая визуальная матрица и подсчет видимых пояснений до/после. Три независимых reviewer-прохода после кода; исправления запускают повторный узкий набор. Реальные пользователи SC-005 и наблюдение SC-006 остаются отдельными задачами. Без нового коммита нельзя продвигать dirty checkout в GRAF Dev; сначала все возможные локальные проверки.

## Project Structure

- `specs/280-payment-clarity/`: spec, plan, research, audits, contracts, checklists, tasks, quickstart, validation.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_*_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/{cabinet.css,cabinet.js}`
- `apps/server/tests/{contract,integration,unit,browser}/` — существующие billing tests + один focused regression suite.
- `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`
- `changes/unreleased/F280.yaml`

## Complexity Tracking

Нарушений конституции нет; миграции, новые пакеты, framework, экспериментальная аналитика и изменение тарифов не требуются.
